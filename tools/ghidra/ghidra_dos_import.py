"""Deterministic PyGhidra import driver for historical DOS images.

Provider-neutral command-line tool: it calls no model service and needs no
emulator. It imports one stored DOS image into an owned Ghidra project with an
explicit processor language, optionally applies Ghidra autoanalysis, optionally
verifies a fresh-process reopen, and writes a machine-readable receipt.

Design rules (see docs/research/ghidra-dos-binary-analysis.md):

* The processor language is always explicit; the resolved language is read
  back from the imported program rather than echoed from the request.
* Every stage runs under a timeout. The import itself always runs in a
  separate worker process, so a hung JVM cannot outlive the driver.
* Result states are explicit. A failed analysis or a failed reopen is a
  non-success exit, never a receipt that merely mentions the failure.
* Reopen verification compares the original and reopened program, including a
  content fingerprint, not only their summaries.
* Project locks are never deleted. A clean process exit releases Ghidra's
  lock; a lock that outlives the process is reported, and may only be
  quarantined on explicit request.

Exit codes::

    0  success
    2  usage or validation error
    3  import failed
    4  timed out
    5  autoanalysis failed
    6  reopen or reopen-comparison failed
    7  reopened program does not match the imported program

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
from pathlib import Path

DEFAULT_LANGUAGE = "x86:LE:16:Real Mode"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_IMPORT_FAILED = 3
EXIT_TIMEOUT = 4
EXIT_ANALYSIS_FAILED = 5
EXIT_REOPEN_FAILED = 6
EXIT_REOPEN_MISMATCH = 7

PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")
LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_]+:[A-Za-z0-9_]+:[A-Za-z0-9_]+.*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

RECEIPT_SCHEMA = "ghidra-dos-import/2"


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
        return errors

    if not args.input:
        errors.append("--input is required")
        return errors

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


def _application_properties() -> dict:
    """Read the installed Ghidra version record instead of assuming one."""
    install = os.environ.get("GHIDRA_INSTALL_DIR")
    if not install:
        return {}
    path = Path(install) / "Ghidra" / "application.properties"
    if not path.is_file():
        return {}
    wanted = {
        "application.version",
        "application.release.name",
        "application.build.date",
        "application.java.min",
        "application.java.compiler",
        "application.revision.ghidra",
    }
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in wanted:
            values[key] = value
    return values


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
    """Compare the compared fields and report every difference."""
    differences = []
    for field in COMPARED_FIELDS:
        before = original.get(field)
        after = reopened.get(field)
        if before != after:
            differences.append({"field": field, "before": before, "after": after})
    return {
        "match": not differences,
        "compared": list(COMPARED_FIELDS),
        "differences": differences,
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
    proof that another process owns the project; nothing here acts on it.
    """
    result = {
        "present": False,
        "files": [],
        "note": (
            "sampled at one instant; a lock released by JVM shutdown may still "
            "be visible. Presence alone does not establish ownership"
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
    record: dict = {"host": None, "user": None, "port": None, "raw_length": len(text)}
    for key, pattern in (
        ("host", r"<host>([^<]*)</host>"),
        ("user", r"<user>([^<]*)</user>"),
        ("port", r"<port>([^<]*)</port>"),
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            record[key] = match.group(1).strip()
    return record


def quarantine_lock(project_dir: Path, name: str) -> dict:
    """Move a lock file aside instead of deleting it.

    Only meaningful when the caller has established that no live process owns
    the project. The file is renamed, never removed, so the evidence survives.
    """
    moved = []
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    for suffix in (".lock", ".lock~"):
        candidate = project_dir / f"{name}{suffix}"
        if not candidate.exists():
            continue
        target = project_dir / f"{name}{suffix}.stale-{stamp}"
        if target.exists():
            continue
        candidate.rename(target)
        moved.append({"from": candidate.name, "to": target.name})
    return {"moved": moved}


def _open_or_create(project_dir: Path, name: str, allow_existing: bool):
    """Open a writable owned project, creating it when allowed.

    ``pyghidra.open_project`` returns a temporary or read-only project, which
    cannot persist an analysed program, so the project manager is used
    directly.
    """
    from ghidra.framework.model import ProjectLocator  # noqa: PLC0415
    from ghidra.pyghidra import PyGhidraProjectManager  # noqa: PLC0415

    manager = PyGhidraProjectManager()
    locator = ProjectLocator(str(project_dir), name)
    if locator.exists():
        if not allow_existing:
            raise RuntimeError(
                f"project {name} already exists in {project_dir}; refusing to open it"
            )
        return manager.openProject(locator, False, False)
    return manager.createProject(locator, None, False)


# --------------------------------------------------------------------------
# import (runs inside a JVM)
# --------------------------------------------------------------------------
def run_import(args) -> dict:
    """Import one image in this process and return the receipt body."""
    source = Path(args.input).resolve()
    project_dir = Path(args.project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    actual_sha256 = _sha256(source)
    receipt: dict = {
        "schema": RECEIPT_SCHEMA,
        "tool": "tools/ghidra/ghidra_dos_import.py",
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
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
            "allow_existing_project": bool(args.allow_existing_project),
        },
        "stages": [],
        "status": "started",
    }

    if receipt["input"]["matches_expected"] is False:
        receipt["status"] = "import_failed"
        receipt["error"] = "input SHA-256 does not match --expect-sha256"
        return receipt

    import pyghidra  # noqa: PLC0415 - imported late so --help needs no JVM

    receipt["ghidra"] = {
        "pyghidra": getattr(pyghidra, "__version__", None),
        "install_dir": os.environ.get("GHIDRA_INSTALL_DIR"),
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

    receipt["ghidra"].update(
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
        receipt["status"] = "import_failed"
        receipt["error"] = f"unknown processor language: {args.language}"
        return receipt

    project = _open_or_create(project_dir, args.project, args.allow_existing_project)
    try:
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
        }
        receipt["program"] = {"project_path": program.getDomainFile().getPathname()}
        receipt["program"].update(_program_summary(program))

        status = "ok"
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
                status = "analysis_failed"
            receipt["stages"].append(
                {"stage": "autoanalysis", "seconds": round(time.time() - stage, 2)}
            )
            refreshed = _program_summary(program)
            for key in ("instruction_count", "function_count", "blocks",
                        "content_sha256", "block_count"):
                receipt["program"][key] = refreshed[key]
        else:
            receipt["analysis"] = {"requested": False, "ok": None}

        # LoadResults.save() requires a real TaskMonitor and must run before
        # release. Program.save() would raise ReadOnlyException on an
        # unmodified program, so persistence goes through the load results.
        stage = time.time()
        results.save(pyghidra.task_monitor())
        results.release(consumer)
        receipt["stages"].append(
            {"stage": "save", "seconds": round(time.time() - stage, 2)}
        )
        receipt["status"] = status
    except Exception as exc:  # noqa: BLE001 - a failed import is a result, not a crash
        receipt["status"] = "import_failed"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            project.save()
            project.close()
        except Exception as exc:  # noqa: BLE001
            receipt.setdefault("close_error", f"{type(exc).__name__}: {exc}")
    return receipt


def reopen_only(project_dir: Path, name: str, program_name: str) -> tuple[int, dict]:
    """Describe a stored program after reopening the project from disk."""
    import pyghidra  # noqa: PLC0415

    program_path = program_name if program_name.startswith("/") else "/" + program_name
    payload: dict = {"ok": False, "project_files": []}
    pyghidra.start()
    try:
        project = _open_or_create(project_dir, name, allow_existing=True)
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
        payload["ok"] = True
        return EXIT_OK, payload
    except Exception as exc:  # noqa: BLE001
        payload["error"] = f"{type(exc).__name__}: {exc}"
        return EXIT_REOPEN_FAILED, payload
    finally:
        try:
            project.close()
        except Exception:  # noqa: BLE001
            pass


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


def _read_receipt(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _failure_receipt(args, status: str, error: str, stage: str) -> dict:
    return {
        "schema": RECEIPT_SCHEMA,
        "tool": "tools/ghidra/ghidra_dos_import.py",
        "input": {
            "name": Path(args.input).name if args.input else None,
            "size": Path(args.input).stat().st_size
            if args.input and Path(args.input).is_file()
            else None,
            "sha256": _sha256(Path(args.input))
            if args.input and Path(args.input).is_file()
            else None,
            "expected_sha256": (args.expect_sha256 or "").lower() or None,
            "matches_expected": None,
        },
        "requested": {"language": args.language, "analyze": bool(args.analyze)},
        "stages": [{"stage": stage, "failed": True}],
        "status": status,
        "error": error,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = Path(args.project_dir).resolve() if args.project_dir else None

    errors = validate_args(args)
    if errors:
        payload = {"schema": RECEIPT_SCHEMA, "status": "usage_error", "errors": errors}
        if args.output:
            Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        sys.stderr.write("\n".join(errors) + "\n")
        return EXIT_USAGE

    if args.reopen_only:
        code, payload = reopen_only(project_dir, args.project, args.input)
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return code

    if args.import_worker:
        receipt = run_import(args)
        text = json.dumps(receipt, indent=2)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        else:
            sys.stdout.write(text + "\n")
        return EXIT_OK if receipt.get("status") == "ok" else EXIT_IMPORT_FAILED

    # Supervisor mode never starts a JVM in this process, so every stage is
    # bounded by the driver's own timeout.
    worker_output = Path(str(args.output or "receipt.json") + ".import.json")
    worker_args = [
        "--import-worker",
        "--project-dir", str(project_dir),
        "--project", args.project,
        "--input", args.input,
        "--language", args.language,
        "--output", str(worker_output),
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
        )
        receipt["elapsed_seconds"] = elapsed
        receipt["lock_after_failure"] = project_lock_state(project_dir, args.project)
        receipt["guidance"] = (
            "The project is in an unknown state after termination. Treat it as "
            "unusable and remove it deliberately; do not reopen it as evidence."
        )
        _write(args, receipt)
        return EXIT_TIMEOUT

    receipt = _read_receipt(worker_output)
    if receipt is None:
        receipt = _failure_receipt(
            args,
            "import_failed",
            f"import worker exited {completed.returncode} without a readable receipt",
            "import",
        )
        receipt["worker_stderr"] = (completed.stderr or "")[-4000:]
        receipt["worker_exit_code"] = completed.returncode
        receipt["elapsed_seconds"] = elapsed
        _write(args, receipt)
        return EXIT_IMPORT_FAILED

    receipt["elapsed_seconds"] = elapsed
    receipt["worker_exit_code"] = completed.returncode
    receipt["lock_after_exit"] = project_lock_state(project_dir, args.project)

    status = receipt.get("status")
    if status != "ok":
        code = EXIT_ANALYSIS_FAILED if status == "analysis_failed" else EXIT_IMPORT_FAILED
        _write(args, receipt)
        return code

    if args.reopen_check:
        receipt["reopen"] = _run_reopen(args, receipt, project_dir)
        if receipt["reopen"]["status"] != "ok":
            status = receipt["reopen"]["status"]
        receipt["status"] = status

    _write(args, receipt)
    if status == "ok":
        return EXIT_OK
    if status == "reopen_mismatch":
        return EXIT_REOPEN_MISMATCH
    if status.startswith("reopen"):
        return EXIT_REOPEN_FAILED
    return EXIT_IMPORT_FAILED


def _run_reopen(args, receipt: dict, project_dir: Path) -> dict:
    program_path = receipt.get("program", {}).get("project_path")
    if not program_path:
        return {
            "status": "reopen_failed",
            "error": "the import receipt recorded no project path",
            "attempts": 0,
        }

    attempts = []
    deadline = time.time() + min(args.timeout, args.lock_wait)
    result: dict = {"status": "reopen_failed", "attempts": 0}
    while True:
        result = {"attempts": len(attempts) + 1, "status": "started"}
        started = time.time()
        completed, timed_out = _spawn(
            [
                "--reopen-only",
                "--project-dir", str(project_dir),
                "--project", args.project,
                "--input", program_path,
                "--timeout", str(args.timeout),
            ],
            args.timeout,
            args.python,
        )
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
                "reason": "timeout",
                "error": f"reopen did not finish within {args.timeout}s",
                "attempts": len(attempts),
                "history": attempts,
            }
            break
        payload = None
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
        if payload is not None and payload.get("ok"):
            comparison = compare_programs(receipt.get("program", {}), payload.get("program", {}))
            result = {
                "status": "ok" if comparison["match"] else "reopen_mismatch",
                "attempts": len(attempts),
                "history": attempts,
                "program": payload.get("program"),
                "project_files": payload.get("project_files"),
                "comparison": comparison,
            }
            break
        reason = (payload or {}).get("reason")
        if reason == "project_locked_or_unopenable" and time.time() < deadline:
            time.sleep(min(2.0, max(0.2, deadline - time.time())))
            continue
        result = {
            "status": "reopen_failed",
            "reason": reason or "reopen_error",
            "error": (payload or {}).get("error")
            or (completed.stderr or "")[-2000:],
            "attempts": len(attempts),
            "history": attempts,
            "project_files": (payload or {}).get("project_files"),
        }
        break

    result["lock_after"] = project_lock_state(project_dir, args.project)
    if args.quarantine_stale_lock and result["lock_after"]["present"]:
        result["quarantine"] = quarantine_lock(project_dir, args.project)
        if result["status"] != "ok":
            retry = _run_reopen_single(args, project_dir, program_path)
            result["retry_after_quarantine"] = retry
            if retry.get("status") == "ok":
                comparison = compare_programs(
                    receipt.get("program", {}), retry.get("program", {})
                )
                result.update(
                    {
                        "status": "ok" if comparison["match"] else "reopen_mismatch",
                        "program": retry.get("program"),
                        "comparison": comparison,
                    }
                )
    return result


def _run_reopen_single(args, project_dir: Path, program_path: str) -> dict:
    completed, timed_out = _spawn(
        [
            "--reopen-only",
            "--project-dir", str(project_dir),
            "--project", args.project,
            "--input", program_path,
            "--timeout", str(args.timeout),
        ],
        args.timeout,
        args.python,
    )
    if timed_out:
        return {"status": "reopen_failed", "reason": "timeout"}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "reopen_failed", "error": (completed.stderr or "")[-2000:]}
    if not payload.get("ok"):
        return {"status": "reopen_failed", "error": payload.get("error")}
    return {"status": "ok", "program": payload.get("program")}


def _write(args, receipt: dict) -> None:
    text = json.dumps(receipt, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a DOS image into an owned Ghidra project and write a receipt.",
        epilog="Exit codes: 0 ok, 2 usage, 3 import failed, 4 timeout, "
        "5 analysis failed, 6 reopen failed, 7 reopen mismatch.",
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
    parser.add_argument("--output", help="write the receipt JSON here")
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
        "--quarantine-stale-lock",
        action="store_true",
        help="rename an outliving lock file aside instead of failing (never deletes)",
    )
    parser.add_argument("--import-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--reopen-only", action="store_true", help=argparse.SUPPRESS)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
