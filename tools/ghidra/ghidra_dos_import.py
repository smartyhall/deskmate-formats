"""Deterministic PyGhidra import driver for historical DOS images.

Provider-neutral command-line tool: it calls no model service and needs no
emulator. It imports one stored DOS image into an owned Ghidra project with an
explicit processor language, optionally applies Ghidra autoanalysis, optionally
verifies a fresh-process reopen, and publishes a machine-readable receipt.

Design rules (see docs/research/ghidra-dos-import-receipts.md):

* The processor language is always explicit; the resolved language is read
  back from the imported program and compared with the request.
* Every stage runs under a timeout. The import itself always runs in a
  separate worker process, so a hung JVM cannot outlive the driver.
* One invocation is one *attempt*. Each attempt has a unique identifier and
  its own private working directory, so a receipt written by an earlier
  attempt can never be read as this attempt's result.
* The worker's receipt is validated against the schema, the attempt identity,
  the input digest and the project identity, and is reconciled with the
  worker's exit status. A receipt that claims success cannot outrank a failed
  worker process, and a receipt missing required fields is rejected rather
  than treated as a success with blanks.
* Receipts are published atomically, so a reader never sees a half-written
  file.
* Reopen verification runs in a fresh process and carries the originating
  attempt's identity, so a reopen from a different attempt is detectable.
* Project locks are observed, never moved. A lock file's presence does not
  establish ownership or staleness, and no automatic recovery is attempted
  here.

Exit codes::

    0  success
    2  usage, validation or input-identity error
    3  import failed
    4  timed out
    5  autoanalysis failed
    6  reopen failed
    7  reopened program does not match the imported program
    8  receipt rejected (malformed, or inconsistent with the worker exit)
    9  analysis completed but persistence failed

Example::

    python ghidra_dos_import.py --project-dir PRIVATE/projects --project cal \\
        --input CALENDAR.PDM --expect-sha256 819df5... --analyze \\
        --reopen-check --timeout 600 --output PRIVATE/receipt.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LANGUAGE = "x86:LE:16:Real Mode"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_IMPORT_FAILED = 3
EXIT_TIMEOUT = 4
EXIT_ANALYSIS_FAILED = 5
EXIT_REOPEN_FAILED = 6
EXIT_REOPEN_MISMATCH = 7
EXIT_RECEIPT_REJECTED = 8
EXIT_PERSISTENCE_FAILED = 9

PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")
LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_]+:[A-Za-z0-9_]+:[A-Za-z0-9_]+.*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ATTEMPT_ID_RE = re.compile(r"^[0-9a-f]{32}$")

RECEIPT_SCHEMA = "ghidra-dos-import/3"

#: Every terminal outcome this tool can report. Nothing else is a result.
OUTCOMES = (
    "succeeded",
    "import_failed",
    "analysis_failed",
    "import_timeout",
    "persistence_failed",
    "reopen_failed",
    "reopen_mismatch",
    "invalid_request",
    "input_mismatch",
    "receipt_malformed",
    "receipt_inconsistent",
)

#: Fields a receipt must carry to be considered meaningful for its outcome.
#: A receipt missing any of these is rejected instead of being read as a
#: success whose blanks happen to look equal to another receipt's blanks.
REQUIRED_FIELDS = {
    "always": ("schema", "tool", "attempt", "input", "requested", "outcome"),
    "attempt": ("id", "started_utc"),
    "input": ("name", "size", "sha256"),
    "requested": ("language", "analyze", "project", "project_dir"),
    "project": ("name", "dir"),
    "resolved_language": ("language_id",),
    "program": ("project_path", "content_sha256", "block_count"),
    "persistence": ("save", "close"),
    "succeeded": (
        "project",
        "resolved_language",
        "program",
        "persistence",
        "toolchain",
    ),
    "reopen": ("attempt_id", "status"),
    "reopen_comparison": ("match", "complete"),
}

# The reopen worker's payload is a result document rather than a receipt, but
# it is read under the same rules: unknown statuses are not successes and a
# malformed payload is never a downgraded success.
REOPEN_STATUSES = ("ok", "reopen_mismatch", "reopen_failed", "reopen_malformed")

EXIT_FOR_OUTCOME = {
    "succeeded": EXIT_OK,
    "import_failed": EXIT_IMPORT_FAILED,
    "analysis_failed": EXIT_ANALYSIS_FAILED,
    "import_timeout": EXIT_TIMEOUT,
    "persistence_failed": EXIT_PERSISTENCE_FAILED,
    "reopen_failed": EXIT_REOPEN_FAILED,
    "reopen_mismatch": EXIT_REOPEN_MISMATCH,
    "invalid_request": EXIT_USAGE,
    "input_mismatch": EXIT_USAGE,
    "receipt_malformed": EXIT_RECEIPT_REJECTED,
    "receipt_inconsistent": EXIT_RECEIPT_REJECTED,
}


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def validate_args(args) -> list[str]:
    """Return human-readable validation errors; empty means acceptable."""
    errors: list[str] = []

    if not PROJECT_NAME_RE.match(args.project or ""):
        errors.append(
            "project name must start with a letter or digit and contain only "
            "letters, digits, space, dot, underscore or hyphen (max 64)"
        )
    if any(sep in (args.project or "") for sep in ("/", "\\", "..")):
        errors.append("project name must not contain a path separator")

    if not LANGUAGE_RE.match(args.language or ""):
        errors.append(
            "language must be an explicit Ghidra language id such as "
            "'x86:LE:16:Real Mode'"
        )

    if args.timeout is None or args.timeout <= 0:
        errors.append("timeout must be a positive number of seconds")
    elif args.timeout > 86400:
        errors.append("timeout must not exceed 86400 seconds")

    if args.expect_sha256 and not SHA256_RE.match(args.expect_sha256.lower()):
        errors.append("--expect-sha256 must be 64 hexadecimal characters")

    if args.reopen_only:
        if not args.input:
            errors.append("--input must name the stored program path to reopen")
        return errors

    if not args.input:
        errors.append("--input is required")
        return errors

    if not args.import_worker and not args.output:
        # A shared default such as ``receipt.json.import.json`` in the current
        # directory is how one attempt's receipt gets read as another's.
        errors.append(
            "--output is required: each attempt publishes its receipt to an "
            "explicit path, and a default name in the working directory is not "
            "attempt-specific"
        )

    source = Path(args.input)
    if not source.exists():
        errors.append(f"input not found: {source}")
    elif not source.is_file():
        errors.append(f"input is not a regular file: {source}")
    elif source.stat().st_size == 0:
        errors.append(f"input is empty: {source}")

    project_file = Path(args.project_dir) / f"{args.project}.gpr"
    if project_file.exists() and not args.allow_existing_project:
        errors.append(
            f"project already exists: {project_file}. An existing project may hold "
            "another worker's program or a lock; pass --allow-existing-project "
            "only when you own it and intend to reuse it."
        )
    return errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _application_properties() -> dict:
    """Read the installed Ghidra version record instead of assuming one."""
    install = os.environ.get("GHIDRA_INSTALL_DIR")
    if not install:
        return {}
    path = Path(install) / "Ghidra" / "application.properties"
    if not path.is_file():
        return {}
    return _parse_properties(path)


def _parse_properties(path: Path) -> dict:
    wanted = {
        "application.version",
        "application.release.name",
        "application.build.date",
        "application.java.min",
        "application.java.compiler",
        "application.revision.ghidra",
    }
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key.strip() in wanted:
            values[key.strip()] = value.strip()
    return values


# --------------------------------------------------------------------------
# receipt publication and schema
# --------------------------------------------------------------------------
def publish_json(path: Path, payload: dict) -> str:
    """Write ``payload`` to ``path`` atomically; return the published digest.

    The temporary file lives beside the target so ``os.replace`` is a rename
    on the same filesystem, and a reader either sees the previous complete
    file or this complete one.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    # Bytes, not text: platform newline translation would make the published
    # file differ from the digest recorded for it.
    temporary.write_bytes(text.encode("utf-8"))
    os.replace(temporary, path)
    return digest


def _same_path(left: str | None, right: str | None) -> bool:
    """Compare two path spellings without depending on case or short names.

    Windows reports the same directory as ``C:\\Users\\DeskMateLab`` or
    ``C:\\Users\\DESKMA~1`` depending on the API, so a literal comparison
    would reject a truthful receipt.
    """
    if left is None or right is None:
        return left == right
    try:
        return os.path.normcase(os.path.realpath(str(left))) == os.path.normcase(
            os.path.realpath(str(right))
        )
    except (OSError, ValueError):
        return str(left) == str(right)


def _missing_fields(mapping, keys: tuple[str, ...], prefix: str) -> list[str]:
    if not isinstance(mapping, dict):
        return [f"{prefix}{key}" for key in keys]
    return [
        f"{prefix}{key}"
        for key in keys
        if key not in mapping or mapping[key] is None
    ]


def validate_receipt(
    receipt: dict,
    *,
    attempt_id: str | None = None,
    input_sha256: str | None = None,
    project: str | None = None,
    project_dir: str | None = None,
) -> list[str]:
    """Return schema and identity problems with a worker receipt.

    Empty means the receipt is well formed, belongs to this attempt, describes
    this input and this project, and carries every field its outcome requires.
    """
    problems: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt is not a JSON object"]

    problems += _missing_fields(receipt, REQUIRED_FIELDS["always"], "")

    schema = receipt.get("schema")
    if schema is not None and schema != RECEIPT_SCHEMA:
        problems.append(f"schema is {schema!r}, expected {RECEIPT_SCHEMA!r}")

    attempt = receipt.get("attempt")
    problems += _missing_fields(attempt, REQUIRED_FIELDS["attempt"], "attempt.")
    if attempt_id is not None:
        found = attempt.get("id") if isinstance(attempt, dict) else None
        if found is not None and found != attempt_id:
            problems.append(
                f"attempt.id is {found!r}, so this receipt belongs to a "
                f"different attempt than {attempt_id!r}"
            )

    for section in ("input", "requested"):
        problems += _missing_fields(
            receipt.get(section), REQUIRED_FIELDS[section], f"{section}."
        )

    outcome = receipt.get("outcome")
    if outcome is not None and outcome not in OUTCOMES:
        problems.append(f"outcome {outcome!r} is not a recognised terminal outcome")

    if input_sha256 is not None:
        found = (receipt.get("input") or {}).get("sha256")
        if found is not None and found != input_sha256:
            problems.append(
                "input.sha256 does not describe the file this attempt was given "
                f"({found!r} != {input_sha256!r})"
            )

    requested = receipt.get("requested") or {}
    if project is not None and requested.get("project") not in (None, project):
        problems.append(
            f"requested.project is {requested.get('project')!r}, expected {project!r}"
        )
    recorded_dir = requested.get("project_dir")
    if (
        project_dir is not None
        and recorded_dir is not None
        and not _same_path(recorded_dir, project_dir)
    ):
        problems.append(
            f"requested.project_dir is {recorded_dir!r}, which is not the "
            f"project directory this attempt used ({project_dir!r})"
        )

    if outcome == "succeeded":
        problems += _missing_fields(receipt, REQUIRED_FIELDS["succeeded"], "")
        for section in ("project", "program", "persistence", "resolved_language"):
            problems += _missing_fields(
                receipt.get(section), REQUIRED_FIELDS[section], f"{section}."
            )
        program = receipt.get("program") or {}
        content = program.get("content_sha256")
        if content is not None and not SHA256_RE.match(str(content)):
            problems.append("program.content_sha256 is not a SHA-256 digest")
        recorded = receipt.get("project") or {}
        if project is not None and recorded.get("name") not in (None, project):
            problems.append(
                f"project.name is {recorded.get('name')!r}, expected {project!r}"
            )
        persistence = receipt.get("persistence") or {}
        for stage in ("save", "close"):
            if persistence.get(stage) not in (None, "ok"):
                problems.append(
                    f"persistence.{stage} is {persistence.get(stage)!r}, so this "
                    "analysis was not persisted"
                )

    # A published receipt that carries a reopen section is read as a whole: a
    # consumer of this file must not be able to see "ok" next to an attempt
    # identifier that belongs to someone else, or next to no identity at all.
    reopen = receipt.get("reopen")
    if reopen is not None:
        problems += _missing_fields(reopen, REQUIRED_FIELDS["reopen"], "reopen.")
        if isinstance(reopen, dict):
            status = reopen.get("status")
            if status is not None and status not in REOPEN_STATUSES:
                problems.append(
                    f"reopen.status {status!r} is not a recognised reopen status"
                )
            if attempt_id is not None and reopen.get("attempt_id") != attempt_id:
                problems.append(
                    f"reopen.attempt_id is {reopen.get('attempt_id')!r}, which is "
                    f"not this attempt ({attempt_id!r})"
                )
            if status == "ok":
                comparison = reopen.get("comparison")
                problems += _missing_fields(
                    comparison, REQUIRED_FIELDS["reopen_comparison"],
                    "reopen.comparison.",
                )
                if isinstance(comparison, dict):
                    for field in ("match", "complete"):
                        if comparison.get(field) is not True:
                            problems.append(
                                f"reopen.comparison.{field} is "
                                f"{comparison.get(field)!r}; a reopen reported as "
                                "ok must carry a literal true here"
                            )
    return problems


def validate_reopen_payload(
    payload,
    *,
    attempt_id: str,
    project: str | None = None,
    project_dir: str | None = None,
    require_success: bool = True,
) -> list[str]:
    """Return identity and content problems with a reopen worker's payload.

    Empty means the payload names this attempt exactly, describes the project
    the caller asked for and, when a success is claimed, carries a literal
    boolean and a complete, well-formed program identity. A missing field is a
    problem, never agreement with whatever is absent.

    A program whose fingerprint merely *differs* from the one this attempt
    recorded is not malformed: the payload is well formed and the difference is
    a real finding, so it is reported as a mismatch with the differing field
    named, rather than being thrown away as an unreadable document.
    """
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["the reopen payload is not a JSON object"]

    problems += _missing_fields(
        payload, ("schema", "mode", "attempt_id", "ok"), ""
    )

    schema = payload.get("schema")
    if schema is not None and schema != RECEIPT_SCHEMA:
        problems.append(
            f"payload schema is {schema!r}, expected {RECEIPT_SCHEMA!r}"
        )
    mode = payload.get("mode")
    if mode is not None and mode != "reopen_only":
        problems.append(f"payload mode is {mode!r}, expected 'reopen_only'")

    recorded_attempt = payload.get("attempt_id")
    if recorded_attempt != attempt_id:
        problems.append(
            f"attempt_id is {recorded_attempt!r}, so this payload does not "
            f"belong to attempt {attempt_id!r}"
        )

    recorded_project = payload.get("project")
    problems += _missing_fields(recorded_project, ("name", "dir"), "project.")
    if isinstance(recorded_project, dict):
        if project is not None and recorded_project.get("name") not in (
            None,
            project,
        ):
            problems.append(
                f"project.name is {recorded_project.get('name')!r}, expected "
                f"{project!r}"
            )
        recorded_dir = recorded_project.get("dir")
        if (
            project_dir is not None
            and recorded_dir is not None
            and not _same_path(recorded_dir, project_dir)
        ):
            problems.append(
                f"project.dir is {recorded_dir!r}, which is not the project "
                f"directory this attempt used ({project_dir!r})"
            )

    files = payload.get("project_files")
    if files is not None and not isinstance(files, list):
        problems.append("project_files is not a list")

    if not require_success:
        return problems

    if payload.get("ok") is not True:
        problems.append(
            f"ok is {payload.get('ok')!r}; a success claim must be the "
            "literal true"
        )

    program = payload.get("program")
    problems += _missing_fields(program, REQUIRED_FIELDS["program"], "program.")
    if isinstance(program, dict):
        content = program.get("content_sha256")
        if content is not None and not SHA256_RE.match(str(content)):
            problems.append("program.content_sha256 is not a SHA-256 digest")
    return problems


# --------------------------------------------------------------------------
# program facts and fingerprints
# --------------------------------------------------------------------------
def _block_records(program) -> list[dict]:
    records = []
    for block in program.getMemory().getBlocks():
        records.append(
            {
                "name": block.getName(),
                "start": str(block.getStart()),
                "end": str(block.getEnd()),
                "size": block.getSize(),
                "initialized": bool(block.isInitialized()),
                "read": bool(block.isRead()),
                "write": bool(block.isWrite()),
                "execute": bool(block.isExecute()),
            }
        )
    return records


def _program_fingerprint(program) -> dict:
    """Hash the program's byte content and block geometry.

    This is what makes a reopen check meaningful: names and counts can match
    while the stored bytes differ. Uninitialized blocks contribute their
    geometry only.
    """
    digest = hashlib.sha256()
    for block in program.getMemory().getBlocks():
        digest.update(
            f"{block.getName()}|{block.getStart()}|{block.getEnd()}|"
            f"{block.getSize()}|{int(bool(block.isInitialized()))}|".encode()
        )
        if block.isInitialized():
            data = bytearray(block.getSize())
            program.getMemory().getBytes(block.getStart(), data)
            digest.update(hashlib.sha256(bytes(data)).digest())
        else:
            digest.update(b"uninitialized")
    return {
        "content_sha256": digest.hexdigest(),
        "block_count": len(list(program.getMemory().getBlocks())),
    }


def _program_summary(program) -> dict:
    summary = {
        "name": program.getName(),
        "language_id": str(program.getLanguageID()),
        "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
        "image_base": str(program.getImageBase()),
        "min_address": str(program.getMinAddress()),
        "max_address": str(program.getMaxAddress()),
        "blocks": _block_records(program),
        "instruction_count": int(program.getListing().getNumInstructions()),
        "function_count": int(program.getFunctionManager().getFunctionCount()),
    }
    summary.update(_program_fingerprint(program))
    return summary


COMPARED_FIELDS = (
    "language_id",
    "compiler_spec",
    "image_base",
    "min_address",
    "max_address",
    "block_count",
    "content_sha256",
)


def compare_programs(original: dict, reopened: dict) -> dict:
    """Compare the required fields and report every difference.

    A field absent from either side counts as a difference, and two summaries
    that both omit the same fields do not compare equal: an incomplete summary
    cannot corroborate anything.
    """
    original = original if isinstance(original, dict) else {}
    reopened = reopened if isinstance(reopened, dict) else {}
    differences = []
    missing = []
    for field in COMPARED_FIELDS:
        before_present = field in original and original[field] is not None
        after_present = field in reopened and reopened[field] is not None
        if not before_present or not after_present:
            missing.append(
                {
                    "field": field,
                    "missing_in": [
                        side
                        for side, present in (
                            ("original", before_present),
                            ("reopened", after_present),
                        )
                        if not present
                    ],
                }
            )
            continue
        if original[field] != reopened[field]:
            differences.append(
                {"field": field, "before": original[field], "after": reopened[field]}
            )
    return {
        "match": not differences and not missing,
        "complete": not missing,
        "compared": list(COMPARED_FIELDS),
        "differences": differences,
        "missing": missing,
    }


# --------------------------------------------------------------------------
# project lifecycle
# --------------------------------------------------------------------------
def _project_file(project_dir: Path, name: str) -> Path:
    return project_dir / f"{name}.gpr"


def project_lock_state(project_dir: Path, name: str) -> dict:
    """Report lock files without touching them.

    A lock file that a JVM releases during shutdown can still be visible for a
    moment after ``wait()`` returns, and Ghidra removes it when the next JVM
    closes the project cleanly. Presence is therefore a diagnostic sample, not
    proof that another process owns the project, and never a licence to move
    it: the owner may be a live worker whose run this sample merely raced.
    """
    result = {
        "present": False,
        "files": [],
        "ownership_established": False,
        "action_taken": "none",
        "note": (
            "sampled at one instant; a lock released by JVM shutdown may still "
            "be visible. Presence alone does not establish ownership or "
            "staleness, so nothing is renamed, deleted or otherwise reclaimed"
        ),
    }
    for suffix in (".lock", ".lock~"):
        candidate = project_dir / f"{name}{suffix}"
        if candidate.exists():
            result["present"] = True
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            result["files"].append(
                {
                    "name": candidate.name,
                    "size": candidate.stat().st_size,
                    "owner_record": _lock_owner_record(text),
                }
            )
    return result


def _lock_owner_record(text: str) -> dict:
    """Extract whatever the lock file records about its owner.

    Ghidra versions differ here, so absent fields stay None rather than being
    guessed. No field is used to justify deleting anything automatically.
    """
    record: dict = {
        "host": None,
        "user": None,
        "port": None,
        "raw_length": len(text),
    }
    for key, pattern in (
        ("host", r"<host>([^<]*)</host>"),
        ("user", r"<user>([^<]*)</user>"),
        ("port", r"<port>([^<]*)</port>"),
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            record[key] = match.group(1).strip()
    return record


def _project_manager():
    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415

    return PyGhidraProjectManager(), ProjectLocator


def _open_existing(project_dir: Path, name: str):
    """Open a stored project for reading or writing, never creating one.

    A reopen-only operation that silently creates the project it was asked to
    verify would report success about a project that never existed.
    """
    manager, locator_type = _project_manager()
    locator = locator_type(str(project_dir), name)
    if not locator.exists():
        raise FileNotFoundError(
            f"project {name} does not exist in {project_dir}; reopening does not "
            "create projects"
        )
    return manager.openProject(locator, False, False)


def _open_or_create(project_dir: Path, name: str, allow_existing: bool):
    """Open a writable owned project, creating it when allowed.

    ``pyghidra.open_project`` returns a temporary or read-only project, which
    cannot persist an analysed program, so the project manager is used
    directly.
    """
    manager, locator_type = _project_manager()
    locator = locator_type(str(project_dir), name)
    if locator.exists():
        if not allow_existing:
            raise RuntimeError(
                f"project {name} already exists in {project_dir}; refusing to open it"
            )
        return manager.openProject(locator, False, False), True
    return manager.createProject(locator, None, False), False


# --------------------------------------------------------------------------
# import (runs inside a JVM)
# --------------------------------------------------------------------------
def _attempt_block(args, started_utc: str) -> dict:
    return {
        "id": getattr(args, "attempt_id", None) or uuid.uuid4().hex,
        "started_utc": started_utc,
        "worker_pid": os.getpid(),
    }


def run_import(args, started_utc: str | None = None) -> dict:
    """Import one image in this process and return the receipt body."""
    source = Path(args.input).resolve()
    project_dir = Path(args.project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    actual_sha256 = _sha256(source)
    receipt: dict = {
        "schema": RECEIPT_SCHEMA,
        "tool": "tools/ghidra/ghidra_dos_import.py",
        "attempt": _attempt_block(args, started_utc or _utc_now()),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
        },
        "input": {
            "name": source.name,
            "size": source.stat().st_size,
            "sha256": actual_sha256,
            "expected_sha256": (args.expect_sha256 or "").lower() or None,
            "matches_expected": (
                None
                if not args.expect_sha256
                else actual_sha256 == args.expect_sha256.lower()
            ),
        },
        "requested": {
            "language": args.language,
            "analyze": bool(args.analyze),
            "project": args.project,
            "project_dir": str(project_dir),
            "allow_existing_project": bool(args.allow_existing_project),
        },
        "stages": [],
        "outcome": "import_failed",
    }

    if receipt["input"]["matches_expected"] is False:
        receipt["outcome"] = "input_mismatch"
        receipt["error"] = "input SHA-256 does not match --expect-sha256"
        return receipt

    import pyghidra  # noqa: PLC0415 - imported late so --help needs no JVM

    receipt["toolchain"] = {
        "requested": {
            "language": args.language,
            "ghidra_install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
            "python": sys.executable,
        },
        "resolved": {"pyghidra": getattr(pyghidra, "__version__", None)},
    }

    started = time.time()
    pyghidra.start()
    receipt["stages"].append(
        {"stage": "jvm_start", "seconds": round(time.time() - started, 2)}
    )

    from ghidra.program.model.lang import LanguageID  # noqa: PLC0415
    from ghidra.program.util import DefaultLanguageService  # noqa: PLC0415
    from java.io import File  # noqa: PLC0415
    from java.lang import Object  # noqa: PLC0415
    from java.lang import System as JavaSystem  # noqa: PLC0415

    receipt["toolchain"]["resolved"].update(
        {
            "application_properties": _application_properties(),
            "java_runtime": str(JavaSystem.getProperty("java.runtime.version")),
            "java_vm": str(JavaSystem.getProperty("java.vm.name")),
        }
    )

    language = DefaultLanguageService.getLanguageService().getLanguage(
        LanguageID(args.language)
    )
    if language is None:
        receipt["outcome"] = "import_failed"
        receipt["error"] = f"unknown processor language: {args.language}"
        return receipt

    project = None
    outcome = "import_failed"
    persistence = {"save": "not_attempted", "close": "not_attempted"}
    try:
        project, existed = _open_or_create(
            project_dir, args.project, args.allow_existing_project
        )
        receipt["project"] = {"name": args.project, "dir": str(project_dir),
                              "existed_before": bool(existed)}

        builder = pyghidra.program_loader()
        builder.source(File(str(source)))
        builder.project(project)
        builder.projectFolderPath("/")
        builder.language(language)

        stage = time.time()
        results = builder.load()
        receipt["stages"].append(
            {"stage": "import", "seconds": round(time.time() - stage, 2)}
        )

        consumer = Object()
        program = results.getPrimaryDomainObject(consumer)
        receipt["resolved_language"] = {
            "language_id": str(program.getLanguageID()),
            "processor": str(program.getLanguage().getProcessor()),
            "compiler_spec": str(program.getCompilerSpec().getCompilerSpecID()),
            "matches_request": str(program.getLanguageID()) == args.language,
        }
        receipt["program"] = {"project_path": program.getDomainFile().getPathname()}
        receipt["program"].update(_program_summary(program))

        outcome = "succeeded"
        if args.analyze:
            stage = time.time()
            try:
                pyghidra.analyze(program)
                receipt["analysis"] = {"requested": True, "ok": True}
            except Exception as exc:  # noqa: BLE001 - reported, and fatal
                receipt["analysis"] = {
                    "requested": True,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                outcome = "analysis_failed"
            receipt["stages"].append(
                {"stage": "autoanalysis", "seconds": round(time.time() - stage, 2)}
            )
            refreshed = _program_summary(program)
            for key in (
                "instruction_count",
                "function_count",
                "blocks",
                "content_sha256",
                "block_count",
            ):
                receipt["program"][key] = refreshed[key]
        else:
            receipt["analysis"] = {"requested": False, "ok": None}

        # LoadResults.save() requires a real TaskMonitor and must run before
        # release. Program.save() would raise ReadOnlyException on an
        # unmodified program, so persistence goes through the load results.
        stage = time.time()
        try:
            results.save(pyghidra.task_monitor())
            persistence["save"] = "ok"
        except Exception as exc:  # noqa: BLE001 - a save failure is a result
            persistence["save"] = "failed"
            persistence["save_error"] = f"{type(exc).__name__}: {exc}"
            if outcome == "succeeded":
                outcome = "persistence_failed"
        finally:
            try:
                results.release(consumer)
            except Exception as exc:  # noqa: BLE001
                persistence.setdefault(
                    "release_error", f"{type(exc).__name__}: {exc}"
                )
        receipt["stages"].append(
            {"stage": "save", "seconds": round(time.time() - stage, 2)}
        )
        receipt["outcome"] = outcome
    except Exception as exc:  # noqa: BLE001 - a failed import is a result, not a crash
        receipt["outcome"] = "import_failed"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if project is not None:
            try:
                project.save()
                persistence["save"] = (
                    "ok" if persistence["save"] in ("ok", "not_attempted")
                    else persistence["save"]
                )
            except Exception as exc:  # noqa: BLE001
                persistence["save"] = "failed"
                persistence["save_error"] = f"{type(exc).__name__}: {exc}"
                if receipt.get("outcome") == "succeeded":
                    receipt["outcome"] = "persistence_failed"
            try:
                project.close()
                persistence["close"] = "ok"
            except Exception as exc:  # noqa: BLE001
                persistence["close"] = "failed"
                persistence["close_error"] = f"{type(exc).__name__}: {exc}"
                if receipt.get("outcome") == "succeeded":
                    receipt["outcome"] = "persistence_failed"
    receipt["persistence"] = persistence
    return receipt


def reopen_only(
    project_dir: Path,
    name: str,
    program_name: str,
    attempt_id: str | None = None,
    expect_content_sha256: str | None = None,
) -> tuple[int, dict]:
    """Describe a stored program after reopening the project from disk."""
    import pyghidra  # noqa: PLC0415

    program_path = program_name if program_name.startswith("/") else "/" + program_name
    payload: dict = {
        "schema": RECEIPT_SCHEMA,
        "mode": "reopen_only",
        "attempt_id": attempt_id,
        "ok": False,
        "project": {"name": name, "dir": str(project_dir)},
        "expected_content_sha256": expect_content_sha256,
        "project_files": [],
    }
    pyghidra.start()
    try:
        project = _open_existing(project_dir, name)
    except FileNotFoundError as exc:
        payload["error"] = str(exc)
        payload["reason"] = "project_missing"
        return EXIT_REOPEN_FAILED, payload
    except Exception as exc:  # noqa: BLE001
        payload["error"] = f"{type(exc).__name__}: {exc}"
        payload["reason"] = "project_locked_or_unopenable"
        return EXIT_REOPEN_FAILED, payload

    try:
        stack = [project.getProjectData().getRootFolder()]
        while stack:
            folder = stack.pop()
            for entry in folder.getFiles():
                payload["project_files"].append(entry.getPathname())
            for child in folder.getFolders():
                stack.append(child)
        payload["project_files"].sort()
        if program_path not in payload["project_files"]:
            payload["error"] = f"{program_path} is not present after reopening"
            payload["reason"] = "program_missing"
            return EXIT_REOPEN_FAILED, payload
        with pyghidra.program_context(project, program_path) as program:
            payload["program"] = _program_summary(program)
        if (
            expect_content_sha256
            and payload["program"]["content_sha256"] != expect_content_sha256
        ):
            payload["error"] = (
                "the reopened program's content digest differs from the digest "
                "this attempt recorded"
            )
            payload["reason"] = "program_content_mismatch"
            return EXIT_REOPEN_FAILED, payload
        payload["ok"] = True
        return EXIT_OK, payload
    except Exception as exc:  # noqa: BLE001
        payload["error"] = f"{type(exc).__name__}: {exc}"
        payload["reason"] = "reopen_error"
        return EXIT_REOPEN_FAILED, payload
    finally:
        try:
            project.close()
        except Exception as exc:  # noqa: BLE001
            payload["close_error"] = f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# worker supervision
# --------------------------------------------------------------------------
def _spawn(
    mode_args: list[str], timeout: int, python: str | None = None
) -> tuple[subprocess.CompletedProcess | None, bool]:
    """Run a worker; return (completed, timed_out). Kills the child on timeout.

    The worker interpreter defaults to this process's interpreter so that a
    run is reproducible from the same environment; ``--python`` names another
    one explicitly when PyGhidra lives in a dedicated environment.
    """
    try:
        return (
            subprocess.run(  # noqa: S603 - fixed argv, no shell
                [python or sys.executable, str(Path(__file__).resolve()), *mode_args],
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
            False,
        )
    except subprocess.TimeoutExpired as exc:
        return exc, True


def _read_receipt(path: Path) -> tuple[dict | None, str | None]:
    """Read a receipt and return (payload, digest) without trusting either.

    The digest is taken over the stored bytes, so it matches what was
    published rather than a re-encoded copy of it.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None, None
    digest = hashlib.sha256(raw).hexdigest()
    try:
        return json.loads(raw.decode("utf-8")), digest
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, digest


def _attempt_directory(output: Path, attempt_id: str) -> Path:
    """Private working directory for one attempt.

    Kept beside the receipt so a failed or interrupted attempt leaves its
    worker receipt and logs for inspection instead of being overwritten by the
    next run.
    """
    directory = Path(output).parent / f"{Path(output).name}.attempts" / attempt_id
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _failure_receipt(args, outcome: str, error: str, stage: str, attempt: dict) -> dict:
    source = Path(args.input) if args.input else None
    return {
        "schema": RECEIPT_SCHEMA,
        "tool": "tools/ghidra/ghidra_dos_import.py",
        "attempt": attempt,
        "input": {
            "name": source.name if source else None,
            "size": source.stat().st_size if source and source.is_file() else None,
            "sha256": _sha256(source) if source and source.is_file() else None,
            "expected_sha256": (args.expect_sha256 or "").lower() or None,
            "matches_expected": None,
        },
        "requested": {
            "language": args.language,
            "analyze": bool(args.analyze),
            "project": args.project,
            "project_dir": str(Path(args.project_dir).resolve())
            if args.project_dir
            else None,
        },
        "stages": [{"stage": stage, "failed": True}],
        "outcome": outcome,
        "error": error,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = Path(args.project_dir).resolve() if args.project_dir else None
    started_utc = _utc_now()
    attempt = _attempt_block(args, started_utc)

    errors = validate_args(args)
    if errors:
        payload = {
            "schema": RECEIPT_SCHEMA,
            "tool": "tools/ghidra/ghidra_dos_import.py",
            "attempt": attempt,
            "outcome": "invalid_request",
            "errors": errors,
        }
        if args.output:
            publish_json(Path(args.output), payload)
        sys.stderr.write("\n".join(errors) + "\n")
        return EXIT_USAGE

    if args.reopen_only:
        code, payload = reopen_only(
            project_dir,
            args.project,
            args.input,
            attempt_id=args.attempt_id,
            expect_content_sha256=args.expect_program_sha256,
        )
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return code

    if args.import_worker:
        receipt = run_import(args, started_utc)
        if args.output:
            publish_json(Path(args.output), receipt)
        else:
            sys.stdout.write(json.dumps(receipt, indent=2) + "\n")
        return EXIT_OK if receipt.get("outcome") == "succeeded" else EXIT_IMPORT_FAILED

    # Supervisor mode never starts a JVM in this process, so every stage is
    # bounded by the driver's own timeout.
    output = Path(args.output)
    actual_sha256 = _sha256(Path(args.input))
    if args.expect_sha256 and actual_sha256 != args.expect_sha256.lower():
        receipt = _failure_receipt(
            args,
            "input_mismatch",
            "input SHA-256 does not match --expect-sha256; the worker was not "
            "started",
            "validate",
            attempt,
        )
        receipt["input"]["matches_expected"] = False
        receipt["input"]["sha256"] = actual_sha256
        receipt["worker_started"] = False
        publish_json(output, receipt)
        return EXIT_USAGE

    attempt_dir = _attempt_directory(output, attempt["id"])
    worker_receipt = attempt_dir / "import-worker.json"
    worker_args = [
        "--import-worker",
        "--attempt-id",
        attempt["id"],
        "--project-dir", str(project_dir),
        "--project", args.project,
        "--input", args.input,
        "--language", args.language,
        "--output", str(worker_receipt),
        "--timeout", str(args.timeout),
    ]
    if args.analyze:
        worker_args.append("--analyze")
    if args.allow_existing_project:
        worker_args.append("--allow-existing-project")
    if args.expect_sha256:
        worker_args.extend(["--expect-sha256", args.expect_sha256])

    started = time.time()
    completed, timed_out = _spawn(worker_args, args.timeout, args.python)
    elapsed = round(time.time() - started, 2)

    if timed_out:
        receipt = _failure_receipt(
            args,
            "import_timeout",
            f"import did not finish within {args.timeout}s and was terminated",
            "import",
            attempt,
        )
        receipt["elapsed_seconds"] = elapsed
        receipt["attempt"]["work_dir"] = str(attempt_dir)
        # Preserve whatever the worker managed to write, but never read a
        # status out of it: a partial receipt is evidence, not a result.
        partial, partial_digest = _read_receipt(worker_receipt)
        receipt["partial_worker_receipt"] = {
            "present": partial is not None or partial_digest is not None,
            "path": str(worker_receipt),
            "sha256": partial_digest,
            "used_as_result": False,
        }
        receipt["lock_after_failure"] = project_lock_state(project_dir, args.project)
        receipt["guidance"] = (
            "The project is in an unknown state after termination. Treat it as "
            "unusable and remove it deliberately; do not reopen it as evidence. "
            "Nothing was renamed or deleted, because a lock or partial project "
            "may still belong to a live process."
        )
        publish_json(output, receipt)
        return EXIT_TIMEOUT

    receipt, receipt_digest = _read_receipt(worker_receipt)
    if receipt is None:
        receipt = _failure_receipt(
            args,
            "import_failed",
            f"import worker exited {completed.returncode} without a readable receipt",
            "import",
            attempt,
        )
        receipt["worker_stderr"] = (completed.stderr or "")[-4000:]
        receipt["worker_stdout"] = (completed.stdout or "")[-2000:]
        receipt["worker"] = {
            "exit_code": completed.returncode,
            "receipt_path": str(worker_receipt),
            "receipt_sha256": receipt_digest,
            "readable": False,
        }
        receipt["elapsed_seconds"] = elapsed
        receipt["attempt"]["work_dir"] = str(attempt_dir)
        publish_json(output, receipt)
        return EXIT_IMPORT_FAILED

    problems = validate_receipt(
        receipt,
        attempt_id=attempt["id"],
        input_sha256=actual_sha256,
        project=args.project,
        project_dir=str(project_dir),
    )
    if not isinstance(receipt.get("attempt"), dict):
        receipt["attempt"] = {"id": attempt["id"], "started_utc": started_utc}
    receipt["attempt"]["work_dir"] = str(attempt_dir)
    receipt["worker"] = {
        "exit_code": completed.returncode,
        "receipt_path": str(worker_receipt),
        "receipt_sha256": receipt_digest,
        "readable": True,
    }
    receipt["elapsed_seconds"] = elapsed
    receipt["lock_after_exit"] = project_lock_state(project_dir, args.project)

    claimed = receipt.get("outcome")
    if problems:
        receipt["schema_problems"] = problems
        receipt["claimed_outcome"] = claimed
        receipt["outcome"] = "receipt_malformed"
        publish_json(output, receipt)
        sys.stderr.write(
            "worker receipt rejected: " + "; ".join(problems) + "\n"
        )
        return EXIT_RECEIPT_REJECTED

    if claimed == "succeeded" and completed.returncode != 0:
        # A successful-looking receipt never outranks a failed worker process.
        receipt["claimed_outcome"] = claimed
        receipt["outcome"] = "receipt_inconsistent"
        receipt["error"] = (
            f"the worker reported success but exited {completed.returncode}"
        )
        receipt["worker_stderr"] = (completed.stderr or "")[-4000:]
        publish_json(output, receipt)
        return EXIT_RECEIPT_REJECTED

    if claimed != "succeeded":
        if completed.returncode == 0:
            receipt["worker_exit_disagrees"] = True
        publish_json(output, receipt)
        return EXIT_FOR_OUTCOME.get(claimed, EXIT_IMPORT_FAILED)

    if args.reopen_check:
        reopen = _run_reopen(args, receipt, project_dir, attempt, attempt_dir)
        receipt["reopen"] = reopen
        if reopen["status"] != "ok":
            if reopen["status"] == "reopen_mismatch":
                receipt["outcome"] = "reopen_mismatch"
            elif reopen["status"] == "reopen_malformed":
                # The worker's own document could not be trusted, so nothing
                # this attempt produced can be reported as verified.
                receipt["outcome"] = "receipt_malformed"
            else:
                receipt["outcome"] = "reopen_failed"
        publish_json(output, receipt)
        if reopen["status"] == "ok":
            return EXIT_OK
        return EXIT_FOR_OUTCOME.get(receipt["outcome"], EXIT_REOPEN_FAILED)

    publish_json(output, receipt)
    return EXIT_OK


def _run_reopen(args, receipt: dict, project_dir: Path, attempt: dict,
                attempt_dir: Path) -> dict:
    program_path = receipt.get("program", {}).get("project_path")
    if not program_path:
        return {
            "status": "reopen_failed",
            "attempt_id": attempt["id"],
            "error": "the import receipt recorded no project path",
            "attempts": 0,
        }

    expected_content = receipt.get("program", {}).get("content_sha256")
    if not expected_content:
        return {
            "status": "reopen_failed",
            "attempt_id": attempt["id"],
            "reason": "missing_expected_fingerprint",
            "error": (
                "the import receipt records no program fingerprint, so a "
                "reopened program cannot be corroborated"
            ),
            "attempts": 0,
        }
    attempts = []
    deadline = time.time() + min(args.timeout, args.lock_wait)
    result: dict = {"status": "reopen_failed", "attempt_id": attempt["id"],
                    "attempts": 0}
    while True:
        result = {
            "status": "started",
            "attempt_id": attempt["id"],
            "attempts": len(attempts) + 1,
        }
        started = time.time()
        reopen_args = [
            "--reopen-only",
            "--attempt-id", attempt["id"],
            "--project-dir", str(project_dir),
            "--project", args.project,
            "--input", program_path,
            "--timeout", str(args.timeout),
        ]
        if expected_content:
            reopen_args.extend(["--expect-program-sha256", expected_content])
        completed, timed_out = _spawn(reopen_args, args.timeout, args.python)
        attempts.append(
            {
                "attempt": len(attempts) + 1,
                "seconds": round(time.time() - started, 2),
                "timed_out": timed_out,
                "exit_code": None if timed_out else completed.returncode,
            }
        )
        if timed_out:
            result = {
                "status": "reopen_failed",
                "attempt_id": attempt["id"],
                "reason": "timeout",
                "error": f"reopen did not finish within {args.timeout}s",
                "attempts": len(attempts),
                "history": attempts,
            }
            break
        payload = None
        try:
            payload = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError):
            payload = None

        if payload is None:
            result = {
                "status": "reopen_failed",
                "attempt_id": attempt["id"],
                "reason": "payload_unreadable",
                "error": "the reopen worker wrote no readable payload",
                "worker_exit_code": completed.returncode,
                "worker_stderr": (completed.stderr or "")[-2000:],
                "attempts": len(attempts),
                "history": attempts,
            }
            break

        ok = payload.get("ok") if isinstance(payload, dict) else None
        problems = validate_reopen_payload(
            payload,
            attempt_id=attempt["id"],
            project=args.project,
            project_dir=str(project_dir),
            require_success=ok is True,
        )
        if not isinstance(ok, bool):
            # A truthy string or number is not a success claim.
            problems.append(
                f"ok is {ok!r}, which is not a boolean; success must be the "
                "literal true"
            )
        if problems:
            result = {
                "status": "reopen_malformed",
                "attempt_id": attempt["id"],
                "reason": "payload_malformed",
                "errors": problems,
                "worker_exit_code": completed.returncode,
                "attempts": len(attempts),
                "history": attempts,
            }
            break

        if ok is True:
            if completed.returncode != 0:
                result = {
                    "status": "reopen_malformed",
                    "attempt_id": attempt["id"],
                    "reason": "exit_disagrees",
                    "error": (
                        "the reopen payload claims success but the worker "
                        f"exited {completed.returncode}"
                    ),
                    "worker_exit_code": completed.returncode,
                    "attempts": len(attempts),
                    "history": attempts,
                }
                break
            comparison = compare_programs(
                receipt.get("program", {}), payload.get("program", {})
            )
            if not comparison["complete"]:
                # Every compared field should be present on both sides by now.
                # If one is not, the result is unknown, not equal.
                result = {
                    "status": "reopen_malformed",
                    "attempt_id": attempt["id"],
                    "reason": "comparison_incomplete",
                    "missing": comparison["missing"],
                    "attempts": len(attempts),
                    "history": attempts,
                }
                break
            result = {
                "status": "ok" if comparison["match"] else "reopen_mismatch",
                "attempt_id": attempt["id"],
                "attempts": len(attempts),
                "history": attempts,
                "program": payload.get("program"),
                "project_files": payload.get("project_files"),
                "comparison": comparison,
            }
            break
        reason = payload.get("reason")
        if reason == "project_locked_or_unopenable" and time.time() < deadline:
            time.sleep(min(2.0, max(0.2, deadline - time.time())))
            continue
        result = {
            "status": "reopen_failed",
            "attempt_id": attempt["id"],
            "reason": reason or "reopen_error",
            "error": payload.get("error") or (completed.stderr or "")[-2000:],
            "attempts": len(attempts),
            "history": attempts,
            "project_files": payload.get("project_files"),
        }
        if completed.returncode == 0:
            # A failure payload from a worker that exited zero is a real
            # failure, but the disagreement is worth recording.
            result["worker_exit_disagrees"] = True
        break

    result["lock_after"] = project_lock_state(project_dir, args.project)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a DOS image into an owned Ghidra project and write a receipt.",
        epilog="Exit codes: 0 ok, 2 usage, 3 import failed, 4 timeout, "
        "5 analysis failed, 6 reopen failed, 7 reopen mismatch, "
        "8 receipt rejected, 9 persistence failed.",
    )
    parser.add_argument("--project-dir", required=True, help="owned project directory")
    parser.add_argument("--project", required=True, help="project name")
    parser.add_argument("--input", required=True, help="stored DOS image, or project path")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"explicit processor language id (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="apply Ghidra autoanalysis after import (slow; unnecessary for byte probes)",
    )
    parser.add_argument(
        "--expect-sha256",
        help="fail the import unless the input has this digest",
    )
    parser.add_argument(
        "--allow-existing-project",
        action="store_true",
        help="open an existing project instead of refusing it",
    )
    parser.add_argument(
        "--output",
        help="write the receipt here (required in supervisor mode; each attempt "
        "publishes to an explicit path)",
    )
    parser.add_argument(
        "--python",
        help="interpreter for worker stages (default: this interpreter); point this "
        "at the environment that provides PyGhidra",
    )
    parser.add_argument(
        "--reopen-check",
        action="store_true",
        help="reopen the stored program in a separate process and compare it",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="timeout in seconds for each worker stage (default 900)",
    )
    parser.add_argument(
        "--lock-wait",
        type=int,
        default=30,
        help="seconds to keep retrying a locked project during reopen (default 30)",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--expect-program-sha256",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--import-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--reopen-only", action="store_true", help=argparse.SUPPRESS)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
