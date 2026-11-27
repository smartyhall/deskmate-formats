"""Bounded deterministic execution without model inference.

One attempt owns one plan directory, one immutable attempt fence and one
terminal outcome. The runner never replays a mutation: if a durable start
record exists without a terminal record, the attempt is ``uncertain`` and must
be inspected by the operator, exactly like the Codex operation ledger.

The executable is always the pinned running interpreter and the argument
vector is always assembled by :mod:`procedures`. A caller cannot supply an
executable, shell fragment or arbitrary argument vector.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
import platform
import signal
import stat
import subprocess
import sys
from threading import Thread
from time import monotonic, sleep
from uuid import uuid4

from deskmate_formats.observer._private_storage import (LockBusy, journal_lock, private_file,
                                                       storage_directory)
from deskmate_formats.observer.events import EventError, decode_json, encode_json
from deskmate_formats.observer.process_health import verify_process

from . import procedures, process_tree
from .task_manifest import utc_now

SCHEMA_VERSION = 2
MAX_INPUT_FILES = 20000
MAX_INPUT_BYTES = 1024 * 1024 * 1024
MAX_GIT_BYTES = 4 * 1024 * 1024
_SKIP_PARTS = frozenset((".git", "build", "dist", "__pycache__", ".venv", "node_modules",
                         ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "_site"))
_REPARSE_POINT = 0x400
MAX_STDOUT_BYTES = 256 * 1024
MAX_STDERR_BYTES = 256 * 1024
MAX_EXCERPT_CHARS = 4096
MAX_ARTIFACTS = 32
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_TOTAL = 32 * 1024 * 1024
MAX_PROGRESS_RECORDS = 64
MAX_PLAN_BYTES = 64 * 1024
MAX_TIMEOUT_SECONDS = 3600
MIN_TIMEOUT_SECONDS = 1
TERMINAL = frozenset(("completed", "failed", "cancelled", "timed-out"))
_POLL_SECONDS = 0.05
_PROGRESS_INTERVAL = 5.0


class DeterministicError(ValueError):
    """The attempt was refused. Diagnostics omit private values."""


@dataclass(frozen=True, slots=True)
class Attempt:
    attempt_id: str
    campaign: str
    procedure: str
    plan_sha256: str
    state: str
    unchanged: bool
    directory: str


def _write_once(path, value):
    """Create an immutable private record atomically. Never overwrite.

    The record is written to a sibling temporary file, flushed to disk and then
    renamed into place, so an interrupted write cannot leave a half-record that
    later reads as authoritative.
    """
    path = Path(path)
    if os.path.lexists(path):
        raise DeterministicError("record already exists; inspect instead of retrying")
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with private_file(temp, write=True) as stream:
            stream.write(encode_json(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.path.lexists(path):
            raise DeterministicError("record already exists; inspect instead of retrying")
        os.replace(temp, path)
        _fsync_directory(path.parent)
    finally:
        if os.path.lexists(temp):
            try:
                os.unlink(temp)
            except OSError:
                pass


def _fsync_directory(directory):
    """Persist a rename on POSIX. Windows has no directory fsync."""
    if os.name == "nt":
        return
    try:
        handle = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def _read(path, limit=MAX_PLAN_BYTES):
    with private_file(Path(path)) as stream:
        return decode_json(stream.read(limit + 1), limit)


def _digest(path):
    with Path(path).open("rb") as stream:
        return sha256(stream.read()).hexdigest()


def _is_link(info):
    """A symlink, or a Windows junction/reparse point."""
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & _REPARSE_POINT)


def _link_components(path):
    """Components of ``path`` that are links, so a boundary cannot be faked."""
    found = []
    current = Path(Path(path).anchor)
    for part in Path(path).parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError:
            continue
        if _is_link(info):
            found.append(str(current))
    return found


def _canonical_directory(value):
    """Resolve a working directory and refuse a link anywhere in its prefix."""
    if type(value) is not str or not 0 < len(value) <= 260:
        raise DeterministicError("invalid working directory")
    path = Path(value)
    if not path.is_absolute():
        raise DeterministicError("working directory must be absolute")
    if not path.is_dir():
        raise DeterministicError("working directory must be an existing directory")
    links = _link_components(path)
    if links:
        raise DeterministicError("working directory is reached through a link; pass its canonical path")
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        raise DeterministicError("working directory must be an existing directory") from None
    if not resolved.is_dir():
        raise DeterministicError("working directory must be an existing directory")
    return str(resolved)


def _within(root, candidate):
    """True when ``candidate`` resolves inside ``root`` after following links."""
    try:
        root_real = os.path.realpath(root)
        candidate_real = os.path.realpath(candidate)
        return os.path.commonpath([root_real, candidate_real]) == root_real
    except (OSError, ValueError):
        return False


def implementation_binding():
    """Bind the installed supervisor implementation this attempt depends on."""
    package = Path(__file__).parent
    digest, files, total = sha256(), 0, 0
    for path in sorted(package.glob("*.py")):
        data = path.read_bytes()
        files += 1
        total += len(data)
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(sha256(data).digest())
    return {"package": "deskmate_formats.supervisor", "files": files,
            "bytes": total, "sha256": digest.hexdigest()}


def implementation_hashes():
    """Digest of the supervisor sources. Retained for callers that want one value."""
    return implementation_binding()["sha256"]


def module_bindings(names):
    """Resolve the modules a procedure imports so drift is detectable."""
    from importlib.util import find_spec

    found = []
    for name in names:
        try:
            spec = find_spec(name)
        except (ImportError, AttributeError, ValueError):
            spec = None
        origin = getattr(spec, "origin", None)
        if origin and Path(origin).is_file():
            path = Path(origin).resolve()
            found.append({"module": name, "origin": str(path), "sha256": _digest(path)})
        else:
            found.append({"module": name, "origin": None, "sha256": None})
    return found


def _input_binding(working, patterns):
    """Hash the working-tree inputs a procedure will read or execute.

    Git HEAD alone says nothing about modified or untracked files, so the plan
    binds their content. A file set that cannot be bound within the reviewed
    limits is refused rather than partially bound.
    """
    root = Path(working)
    selected = {}
    for pattern in patterns:
        literal = not any(char in pattern for char in "*?[")
        matches = [root / pattern] if literal else sorted(root.glob(pattern))
        if literal and not matches[0].is_file():
            raise DeterministicError("a named procedure input does not exist in the working tree")
        for path in matches:
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(root)
            except ValueError:
                raise DeterministicError("an input is outside the working directory") from None
            if _SKIP_PARTS & set(relative.parts):
                continue
            selected[relative.as_posix()] = path
            if len(selected) > MAX_INPUT_FILES:
                raise DeterministicError("the bound input set exceeds its file limit")
    digest, total, files = sha256(), 0, 0
    for relative, path in sorted(selected.items()):
        try:
            info = os.lstat(path)
        except OSError:
            raise DeterministicError("an input disappeared before it could be bound") from None
        if _is_link(info) or not stat.S_ISREG(info.st_mode):
            raise DeterministicError("an input is a link or not a regular file")
        if not _within(root, path):
            raise DeterministicError("an input resolves outside the working directory")
        if info.st_size > procedures.MAX_FILE_BYTES:
            raise DeterministicError("an input exceeds the reviewed size limit")
        total += info.st_size
        if total > MAX_INPUT_BYTES:
            raise DeterministicError("the bound input set exceeds its byte limit")
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(sha256(path.read_bytes()).digest())
        files += 1
    return {"patterns": list(patterns), "files": files, "bytes": total,
            "sha256": digest.hexdigest()}


def _git(working_directory, *args):
    from shutil import which

    git = which("git")
    if not git:
        return None
    env = {"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_ALLOW_PROTOCOL": ""}
    for key in ("PATH", "SYSTEMROOT", "HOME", "USERPROFILE", "TEMP", "TMP"):
        if key in os.environ:
            env[key] = os.environ[key]
    try:
        result = subprocess.run([git, "--no-replace-objects", *args], cwd=working_directory,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=10, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or len(result.stdout) > MAX_GIT_BYTES:
        return None
    return result.stdout.decode("utf-8", "replace").strip()


def source_revision(working_directory):
    return _git(working_directory, "rev-parse", "HEAD")


def environment(artifacts, working_directory=None):
    """Minimal environment: no inherited secrets, MCP tables or proxy settings."""
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    env = {key: value for key, value in os.environ.items() if key.upper() in keep}
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8", "DESKMATE_ARTIFACTS": str(artifacts),
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull, "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "",
        # A package build must not resolve dependencies from an index. This is
        # a refusal at the tool level, not network isolation: a procedure that
        # opens a socket itself is not prevented by these settings.
        "PIP_NO_INDEX": "1", "PIP_NO_INPUT": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CONFIG_FILE": os.devnull, "UV_OFFLINE": "1", "UV_NO_INDEX": "1",
    })
    # A disposable checkout carries its own sources; do not import the installed
    # package when the owned worktree has one.
    if working_directory is not None:
        source_tree = Path(working_directory) / "src"
        if source_tree.is_dir():
            env["PYTHONPATH"] = str(source_tree)
    return env


def accepted(queue, identifier, revision, review_token):
    """Read the existing immutable trusted-intake acceptance for a v3 task.

    This deliberately repeats the S2 bridge's acceptance conditions rather than
    importing the Codex protocol stack into a no-model backend: exact current
    revision, matching review token, no unresolved or superseded record.
    """
    row = queue.get(identifier, revision)
    if row is None or row.state != "accepted" or row.candidate.review_token != review_token:
        raise DeterministicError("exact current accepted revision required")
    if any(other.state == "unresolved"
           or (other.id == identifier and other.revision > revision) for other in queue.list()):
        raise DeterministicError("unresolved or superseded tasks block dispatch")
    manifest = row.candidate.manifest
    if manifest["schema_version"] != 3 or "deterministic" not in manifest:
        raise DeterministicError("accepted revision is not a deterministic task")
    expiry = manifest.get("expires_at")
    if expiry and expiry <= utc_now():
        raise DeterministicError("accepted revision expired")
    for dependency in manifest["dependencies"]:
        receipt = queue.get(dependency["id"], dependency["revision"])
        if receipt is None or receipt.state != "accepted":
            raise DeterministicError("dependency revision has no prior acceptance")
    return {"queue_id": queue.queue_id, "sequence": row.sequence, "id": row.id,
            "revision": row.revision, "idempotency_key": row.idempotency_key,
            "review_token": row.candidate.review_token,
            "source": asdict(row.candidate.source),
            "procedure": manifest["deterministic"]["procedure"],
            "arguments": manifest["deterministic"]["arguments"]}


_ACCEPTANCE_KEYS = frozenset(("queue_id", "sequence", "id", "revision", "idempotency_key",
                               "review_token", "source", "procedure", "arguments"))


def _acceptance(value, spec, normalized):
    """Validate the trusted-intake binding copied into the plan."""
    if value is None:
        return None
    if type(value) is not dict or set(value) != _ACCEPTANCE_KEYS:
        raise DeterministicError("invalid trusted-intake acceptance binding")
    if value["procedure"] != spec.name or value["arguments"] != normalized:
        raise DeterministicError("acceptance binding does not match the requested procedure")
    if type(value["source"]) is not dict:
        raise DeterministicError("invalid acceptance source binding")
    return dict(value)


def prepare(directory, *, campaign, procedure, arguments, working_directory,
            source_commit=None, timeout_seconds=None, interpreter=None, acceptance=None):
    """Freeze a new private attempt plan. No process is started."""
    root = Path(directory).absolute()
    if root.exists():
        raise DeterministicError("attempt directory must be new")
    if type(campaign) is not str or not 0 < len(campaign) <= 64:
        raise DeterministicError("invalid campaign identity")
    working = _canonical_directory(working_directory)
    spec = procedures.get(procedure)
    normalized = spec.normalize(arguments)
    timeout = spec.timeout_seconds if timeout_seconds is None else timeout_seconds
    if (type(timeout) not in (int, float)
            or not MIN_TIMEOUT_SECONDS <= timeout <= min(MAX_TIMEOUT_SECONDS, spec.timeout_seconds)):
        raise DeterministicError("attempt timeout must be a positive value within the procedure limit")
    if source_commit is not None and (type(source_commit) is not str or len(source_commit) != 40
                                      or any(char not in "0123456789abcdef" for char in source_commit)):
        raise DeterministicError("invalid source revision")
    binding = _acceptance(acceptance, spec, normalized)
    observed = source_revision(working)
    if source_commit is not None and observed is None:
        # A requested identity that cannot be established is a refusal, not a
        # note: otherwise the plan would merely claim a revision nobody checked.
        raise DeterministicError("the requested source revision cannot be established")
    if source_commit is not None and observed != source_commit:
        raise DeterministicError("working directory revision differs from the requested source")
    inputs = _input_binding(working, procedures.input_patterns(procedure, normalized))
    modules = module_bindings(procedures.module_origins(procedure))
    status = _git(working, "status", "--porcelain", "--untracked-files=all")
    implementation = implementation_binding()
    # One level of owned private parent may be created, so an attempt can live
    # under a campaign subdirectory without a caller bypassing private storage.
    if not root.parent.exists():
        storage_directory(root.parent, create=True)
    storage_directory(root, create=True)
    artifacts = root / "artifacts"
    for name, sub in (("artifacts", artifacts), ("evidence", root / "evidence"),
                      ("spool", root / "spool"), ("scratch", root / "scratch")):
        storage_directory(sub, create=True)
    argv = procedures.build(procedure, normalized, artifacts=artifacts,
                            working_directory=working,
                            interpreter=Path(interpreter) if interpreter else None)
    interpreter_digest = _digest(argv[0])
    plan = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": uuid4().hex,
        "campaign": campaign,
        "procedure": spec.name,
        "procedure_detail": {"executes": spec.executes, "network": spec.network,
                             "resources": list(spec.resources),
                             "declared_timeout_seconds": spec.timeout_seconds},
        "arguments": normalized,
        "argv": argv,
        "interpreter": {"path": argv[0], "sha256": interpreter_digest,
                        "version": sys.version,
                        "implementation": platform.python_implementation()},
        "interpreter_sha256": interpreter_digest,
        "working_directory": working,
        "source": {
            "requested_commit": source_commit,
            "revision": observed,
            "identity": "git" if observed else "unavailable",
            "status_sha256": None if status is None else sha256(status.encode("utf-8")).hexdigest(),
            "dirty": None if status is None else bool(status),
            "inputs": inputs,
        },
        "source_commit": source_commit,
        "source_revision": observed,
        "modules": modules,
        "implementation": implementation,
        "implementation_sha256": implementation["sha256"],
        "resources": list(spec.resources),
        "timeout_seconds": float(timeout),
        "created_at_utc": utc_now(),
        "acceptance": binding,
        "runtime": {"python": sys.version, "platform": platform.platform()},
    }
    with journal_lock(root, write=True):
        _write_once(root / "plan.json", plan)
    return Attempt(plan["attempt_id"], campaign, spec.name, _plan_digest(plan), "prepared",
                   True, str(root))


def _plan_digest(plan):
    return sha256(encode_json(plan)).hexdigest()


def load_plan(directory):
    root = storage_directory(directory)
    plan = _read(root / "plan.json")
    if (type(plan) is not dict or plan.get("schema_version") != SCHEMA_VERSION
            or plan.get("attempt_id") is None
            or Path(plan.get("working_directory", "")).name == ""):
        raise DeterministicError("unsupported or relocated attempt plan")
    return plan, _plan_digest(plan)


class _Sink:
    """Capture a bounded prefix while continuing to drain the pipe."""

    def __init__(self, limit):
        self.limit = limit
        self.buffer = bytearray()
        self.total = 0

    def feed(self, chunk):
        self.total += len(chunk)
        room = self.limit - len(self.buffer)
        if room > 0:
            self.buffer.extend(chunk[:room])

    @property
    def truncated(self):
        return self.total > self.limit

    def text(self):
        return bytes(self.buffer).decode("utf-8", "replace")


def _pump(stream, sink):
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            sink.feed(chunk)
    except (OSError, ValueError):
        return


_STOP_ROUNDS = 20
_STOP_PAUSE = 0.05


def _kill_pid(pid):
    """Kill exactly one positively observed process; never by name pattern."""
    if os.name == "nt":
        from shutil import which

        taskkill = which("taskkill")
        if taskkill:
            try:
                subprocess.run([taskkill, "/F", "/PID", str(pid)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _observe_tree(claim):
    """Observe a tree without touching it: an exit is not an empty tree."""
    if claim is None:
        return {"requested": False, "descendants": "unknown",
                "enumeration": "unavailable", "remaining": None,
                "reason": "no-tree-handle"}
    state = process_tree.tree_state(claim)
    return {"requested": False, "descendants": state["descendants"],
            "enumeration": state["enumeration"], "remaining": state["live"],
            "reason": state["reason"]}


def _stop_tree(process, claim=None):
    """Terminate the process and its descendants, then observe the result.

    Termination is requested, never assumed: the returned observation records
    what a bounded re-scan could still see, and an unobservable tree stays
    ``unknown``.
    """
    if os.name == "nt":
        from shutil import which

        taskkill = which("taskkill")
        if taskkill:
            try:
                subprocess.run([taskkill, "/F", "/T", "/PID", str(process.pid)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            process.kill()
        except OSError:
            pass
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                process.kill()
            except OSError:
                pass
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    if claim is None:
        return {"requested": True, "descendants": "unknown", "enumeration": "unavailable",
                "remaining": None, "reason": "no-tree-handle"}
    for _ in range(_STOP_ROUNDS):
        # A descendant that left the group or session survives the group kill,
        # so the scan decides what is left instead of the kill call succeeding.
        scan = process_tree.live_pids(claim)
        for pid in scan.pids:
            _kill_pid(pid)
        if not scan.pids:
            break
        sleep(_STOP_PAUSE)
    state = process_tree.tree_state(claim)
    return {"requested": True, "descendants": state["descendants"],
            "enumeration": state["enumeration"], "remaining": state["live"],
            "reason": state["reason"]}


def _artifacts(directory):
    """Hash the bounded artifact directory a procedure may write.

    The walk is manual so a link, junction or reparse point is refused instead
    of being followed: an artifact tree must not be able to point elsewhere.
    """
    root = Path(directory)
    found, total, pending = [], 0, [root]
    while pending:
        current = pending.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError:
            raise DeterministicError("the artifact directory is unreadable") from None
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                raise DeterministicError("an artifact disappeared while it was read") from None
            if _is_link(info):
                raise DeterministicError("an artifact is a link")
            if stat.S_ISDIR(info.st_mode):
                pending.append(Path(entry.path))
                continue
            if not stat.S_ISREG(info.st_mode):
                raise DeterministicError("an artifact is not a regular file")
            if not _within(root, entry.path):
                raise DeterministicError("an artifact resolves outside the artifact directory")
            if info.st_size > MAX_ARTIFACT_BYTES:
                raise DeterministicError("artifact exceeds the byte limit")
            total += info.st_size
            if total > MAX_ARTIFACT_TOTAL or len(found) >= MAX_ARTIFACTS:
                raise DeterministicError("artifact set exceeds its bounds")
            with Path(entry.path).open("rb") as stream:
                data = stream.read(MAX_ARTIFACT_BYTES + 1)
            found.append({"path": Path(entry.path).relative_to(root).as_posix(),
                          "size": len(data), "sha256": sha256(data).hexdigest()})
    return sorted(found, key=lambda item: item["path"])


def _progress(root, event, **fields):
    path = root / "progress.jsonl"
    if path.exists() and path.lstat().st_size > 64 * 1024:
        return
    record = {"event": event, "at_utc": utc_now(), **fields}
    with private_file(path, write=True) as stream:
        stream.seek(0, os.SEEK_END)
        stream.write(encode_json(record) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def _structured(stdout):
    """Parse a small JSON result if the procedure emitted one."""
    text = stdout.text().strip()
    if not text or len(text) > 64 * 1024:
        return None
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if type(value) in (dict, list) else None


def _limited_subprocess(argv, *, cwd, env):
    """Spawn one owned process group. Kept separate so tests can instrument it."""
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
                                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def _verify_plan(plan):
    """Re-establish every identity the plan bound before it was approved."""
    implementation = implementation_binding()
    if plan["implementation"]["sha256"] != implementation["sha256"]:
        raise DeterministicError("supervisor implementation changed after preparation")
    interpreter = plan["interpreter"]
    if _digest(interpreter["path"]) != interpreter["sha256"]:
        raise DeterministicError("interpreter changed after preparation")
    current_modules = module_bindings([item["module"] for item in plan["modules"]])
    if current_modules != plan["modules"]:
        raise DeterministicError("a module this procedure imports changed after preparation")
    working = plan["working_directory"]
    if _canonical_directory(working) != working:
        raise DeterministicError("working directory no longer resolves to the prepared location")
    source = plan["source"]
    current_inputs = _input_binding(working, source["inputs"]["patterns"])
    if current_inputs != source["inputs"]:
        raise DeterministicError("working-tree inputs changed after preparation")
    observed = source_revision(working)
    if source["identity"] == "git":
        if observed != source["revision"]:
            raise DeterministicError("working directory revision changed after preparation")
    elif observed is not None:
        raise DeterministicError("working directory gained a Git identity after preparation")


def _verify_acceptance(plan, revalidate):
    """Refuse when the accepted task revision was superseded or withdrawn."""
    acceptance = plan.get("acceptance")
    if acceptance is None:
        return
    if revalidate is None:
        raise DeterministicError("this attempt is bound to an accepted task and requires revalidation")
    current = revalidate(acceptance)
    if current is None:
        raise DeterministicError("the accepted revision is no longer current")
    for key in ("queue_id", "id", "revision", "sequence", "idempotency_key", "review_token"):
        if current.get(key) != acceptance.get(key):
            raise DeterministicError("the accepted revision changed after preparation")


def run(directory, *, authorization, reservation=None, revalidate=None):
    """Execute the frozen plan once. ``authorization`` is the exact plan digest.

    ``reservation`` is an optional callable that acquires resource leases for the
    duration of the attempt and returns a release callable. ``revalidate`` is
    required when the plan is bound to an accepted trusted task, and must raise
    or return the current acceptance when the revision is still current.
    """
    root = storage_directory(directory)
    # The exclusive lock covers validation and the durable attempt fence only.
    # It is released before execution so an authorized cancellation can be
    # written while the child runs.
    with journal_lock(root):
        plan, token = load_plan(root)
        if authorization != token:
            raise DeterministicError("explicit authorization must match the exact plan digest")
        _verify_plan(plan)
        _verify_acceptance(plan, revalidate)
        if (root / "attempt.json").exists():
            raise DeterministicError("attempt already started; replay is forbidden")
        if (root / "cancel.json").exists():
            raise DeterministicError("cancellation was requested before start")
        if any((root / "scratch").iterdir()):
            raise DeterministicError("attempt scratch directory must be empty")
        _write_once(root / "attempt.json", {"plan_sha256": token, "started_at_utc": utc_now(),
                                            "attempt_id": plan["attempt_id"]})
    release = None
    try:
        if reservation is not None:
            release = reservation(plan)
        if (root / "cancel.json").exists():
            raise DeterministicError("cancellation was requested before start")
        return _execute(root, plan, token)
    finally:
        if release is not None:
            release()


def _execute(root, plan, token):
    artifacts = root / "artifacts"
    stdout, stderr = _Sink(MAX_STDOUT_BYTES), _Sink(MAX_STDERR_BYTES)
    started = utc_now()
    clock = monotonic()
    _progress(root, "started", attempt_id=plan["attempt_id"], procedure=plan["procedure"])
    outcome = {
        "schema_version": SCHEMA_VERSION, "attempt_id": plan["attempt_id"],
        "campaign": plan["campaign"], "procedure": plan["procedure"],
        "arguments": plan["arguments"], "argv": plan["argv"],
        "plan_sha256": token, "working_directory": plan["working_directory"],
        "source_commit": plan["source_commit"], "source_revision_before": plan["source_revision"],
        "source_inputs_sha256": plan["source"]["inputs"]["sha256"],
        "acceptance_binding": plan.get("acceptance"),
        "timeout_seconds": plan["timeout_seconds"], "started_at_utc": started,
        "state": "uncertain", "reason": "attempt-interrupted",
        "exit_status": None, "timed_out": False, "cancelled": False,
        "inference": {"required": False, "measurements": [], "note":
                      "deterministic procedure; no model usage is expected or reported"},
        "git_status_before": _git(plan["working_directory"], "status", "--porcelain",
                                  "--untracked-files=all"),
    }
    process = None
    claim = None
    termination = None
    try:
        process = _limited_subprocess(plan["argv"], cwd=plan["working_directory"],
                                      env=environment(artifacts, plan["working_directory"]))
        # A degraded claim is still written: "the tree handle was lost" must be
        # visible to recovery instead of looking like "nothing was started".
        claim = process_tree.tree_claim(process.pid) or process_tree.unclaimed(process.pid)
        _write_once(root / "child.json", claim)
        readers = [Thread(target=_pump, args=(process.stdout, stdout), daemon=True),
                   Thread(target=_pump, args=(process.stderr, stderr), daemon=True)]
        for reader in readers:
            reader.start()
        deadline = clock + plan["timeout_seconds"]
        next_sample = clock + _PROGRESS_INTERVAL
        timed_out = cancelled = False
        while True:
            if process.poll() is not None:
                break
            if (root / "cancel.json").exists():
                cancelled = True
                termination = _stop_tree(process, claim)
                break
            if monotonic() >= deadline:
                timed_out = True
                termination = _stop_tree(process, claim)
                break
            if monotonic() >= next_sample:
                next_sample += _PROGRESS_INTERVAL
                _progress(root, "running", elapsed_seconds=round(monotonic() - clock, 3))
            sleep(_POLL_SECONDS)
        for reader in readers:
            reader.join(timeout=15)
        exit_status = process.returncode
        if timed_out:
            outcome.update(state="timed-out", reason="timeout", exit_status="timeout")
        elif cancelled:
            outcome.update(state="cancelled", reason="operator-cancelled", exit_status="cancelled")
        elif exit_status == 0:
            outcome.update(state="completed", reason="exit-zero", exit_status=0)
        elif exit_status is None:
            outcome.update(state="uncertain", reason="exit-status-unavailable", exit_status=None)
        else:
            outcome.update(state="failed", reason="nonzero-exit", exit_status=exit_status)
        outcome["timed_out"], outcome["cancelled"] = timed_out, cancelled
    except (OSError, ValueError) as error:
        outcome.update(state="failed", reason="spawn-failed", exit_status=None,
                       error_type=type(error).__name__)
    finally:
        if process is not None:
            if process.poll() is None:
                termination = _stop_tree(process, claim)
            elif termination is None:
                # A clean exit says nothing about what it started.
                termination = _observe_tree(claim)
        outcome["termination"] = termination or {
            "requested": False, "descendants": "unknown", "enumeration": "unavailable",
            "remaining": None, "reason": "no-process-was-spawned"}
        outcome["custody"] = ("clean" if outcome["termination"]["descendants"] == "stopped"
                              else "descendants-alive" if outcome["termination"]["descendants"] == "alive"
                              else "unobserved")
        for stream in getattr(process, "stdout", None), getattr(process, "stderr", None):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        outcome["finished_at_utc"] = utc_now()
        outcome["elapsed_seconds"] = round(monotonic() - clock, 3)
        outcome["source_revision_after"] = source_revision(plan["working_directory"])
        outcome["git_status_after"] = _git(plan["working_directory"], "status", "--porcelain",
                                           "--untracked-files=all")
        outcome["stdout"] = _stream_receipt(root, "stdout.bin", stdout)
        outcome["stderr"] = _stream_receipt(root, "stderr.bin", stderr)
        try:
            outcome["artifacts"] = _artifacts(artifacts)
        except DeterministicError as error:
            outcome["artifacts"] = []
            outcome["artifact_error"] = str(error)
        try:
            outcome["structured_result"] = _structured(stdout)
        except (ValueError, RecursionError):
            outcome["structured_result"] = None
        outcome["limitations"] = [
            "cooperating-owner custody only; not an operating system sandbox",
            "host kill cannot prove a descendant completed no external effect",
            "captured output is a bounded prefix; the full stream was drained and discarded",
        ]
        if outcome["custody"] != "clean":
            outcome["limitations"].append(
                "the attempt's process tree could not be shown empty after it ended")
        _progress(root, "finished", outcome_state=outcome["state"],
                  exit_status=outcome["exit_status"])
        with journal_lock(root):
            _write_once(root / "outcome.json", outcome)
    return outcome


def _stream_receipt(root, name, sink):
    path = root / name
    with private_file(path, write=True) as stream:
        stream.write(bytes(sink.buffer))
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": name, "bytes": sink.total, "captured_bytes": len(sink.buffer),
            "truncated": sink.truncated, "sha256": sha256(bytes(sink.buffer)).hexdigest(),
            "excerpt": sink.text()[:MAX_EXCERPT_CHARS]}


def cancel(directory, *, authorization):
    """Request cancellation of a running attempt. One-shot and exact."""
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        if authorization != token:
            raise DeterministicError("exact plan digest required to cancel")
        if (root / "outcome.json").exists():
            raise DeterministicError("attempt is already terminal")
        if not (root / "attempt.json").exists():
            raise DeterministicError("no started attempt to cancel")
        _write_once(root / "cancel.json", {"plan_sha256": token, "requested_at_utc": utc_now()})
    return True


def status(directory):
    """Offline inspection. Never starts, resumes, cancels or reconciles anything."""
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        attempt = _read(root / "attempt.json") if (root / "attempt.json").exists() else None
        outcome = _read(root / "outcome.json") if (root / "outcome.json").exists() else None
        child = _read(root / "child.json") if (root / "child.json").exists() else None
        # A record path is predictable, so a record is only this attempt's if it
        # names this plan. Copied or stale evidence must not read as current.
        for name, record in (("attempt", attempt), ("outcome", outcome)):
            if record is not None and record.get("plan_sha256") != token:
                raise DeterministicError("the recorded %s belongs to another plan; "
                                         "it is not evidence for this attempt" % name)
        tree = {"owner": "unknown", "descendants": "unknown", "live": None,
                "scope": "none", "enumeration": "unavailable", "reason": "no-child-record"}
        if child is not None:
            tree = process_tree.tree_state(child)
        process = tree["owner"]
        if outcome is not None:
            state = outcome["state"]
        elif attempt is not None:
            state = "uncertain"
        else:
            state = "prepared"
        return {
            "attempt_id": plan["attempt_id"], "campaign": plan["campaign"],
            "procedure": plan["procedure"], "arguments": plan["arguments"],
            "plan_sha256": token, "state": state,
            "attempted": attempt is not None, "terminal": outcome is not None,
            "cancel_requested": (root / "cancel.json").exists(),
            "process": process,
            "descendants": tree["descendants"],
            "observation": {key: tree.get(key) for key in ("scope", "enumeration", "reason")},
            "outcome": outcome,
            "requires_inspection": attempt is not None and outcome is None,
            "implementation_unchanged": plan["implementation_sha256"] == implementation_hashes(),
        }


def recover(directory, *, confirm_descendants_stopped=False):
    """Close an interrupted attempt as ``uncertain``. Never respawns work.

    Closing the record while a process may still be running would hide it, so
    an owner or descendant that is alive, or a tree that cannot be observed at
    all, refuses recovery. Only an explicit operator confirmation overrides an
    unobservable tree, and the confirmation is recorded in the outcome.
    """
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        if (root / "outcome.json").exists():
            recorded = _read(root / "outcome.json")
            if recorded.get("plan_sha256") != token:
                raise DeterministicError("the recorded outcome belongs to another plan")
            return recorded
        if not (root / "attempt.json").exists():
            raise DeterministicError("no interrupted attempt to recover")
        attempt = _read(root / "attempt.json")
        if attempt.get("plan_sha256") != token:
            raise DeterministicError("the recorded attempt belongs to another plan")
        child = _read(root / "child.json") if (root / "child.json").exists() else None
        tree = ({"owner": "unknown", "descendants": "unknown", "live": None,
                 "scope": "none", "enumeration": "unavailable", "reason": "no-child-record"}
                if child is None else process_tree.tree_state(child))
        proven = (tree["owner"] in process_tree.OWNER_GONE
                  and tree["descendants"] == "stopped")
        if tree["owner"] == "alive" or tree["descendants"] == "alive":
            # The owner, or something it started, is still executing. Closing the
            # attempt now would hide a live process and race its own terminal
            # record.
            raise DeterministicError("attempt owner or a descendant is still running; "
                                     "stop it before recovery")
        if not proven and not confirm_descendants_stopped:
            # An unavailable, degraded or scope-limited observation is never
            # read as proof that nothing is running.
            raise DeterministicError(
                "the attempt's process tree cannot be shown stopped (%s); inspect the "
                "observed processes, then confirm explicitly to record an uncertain outcome"
                % tree.get("reason"))
        outcome = {
            "schema_version": SCHEMA_VERSION, "attempt_id": plan["attempt_id"],
            "campaign": plan["campaign"], "procedure": plan["procedure"],
            "arguments": plan["arguments"], "argv": plan["argv"], "plan_sha256": token,
            "working_directory": plan["working_directory"],
            "source_commit": plan["source_commit"],
            "source_revision_before": plan["source_revision"],
            "started_at_utc": attempt["started_at_utc"], "finished_at_utc": utc_now(),
            "elapsed_seconds": None, "timeout_seconds": plan["timeout_seconds"],
            "state": "uncertain", "reason": "attempt-without-terminal-record",
            "exit_status": None, "timed_out": False, "cancelled": False,
            "process": tree["owner"], "descendants": tree["descendants"],
            "observation": {key: tree.get(key) for key in ("scope", "enumeration", "reason")},
            "descendants_confirmed": bool(confirm_descendants_stopped) and not proven,
            "requires_manual_process_check": tree["descendants"] == "unknown",
            "source_revision_after": source_revision(plan["working_directory"]),
            "artifacts": [], "structured_result": None,
            "stdout": None, "stderr": None,
            "inference": {"required": False, "measurements": [],
                          "note": "no model usage; recovery performed no work"},
            "limitations": ["outcome was not recorded by the owning process",
                            "the external effect of the attempt is unknown",
                            "no automatic replay is permitted"],
        }
        _write_once(root / "outcome.json", outcome)
        _progress(root, "recovered", outcome_state="uncertain")
    return outcome
