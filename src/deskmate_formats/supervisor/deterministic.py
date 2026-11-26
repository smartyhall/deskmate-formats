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
import subprocess
import sys
from threading import Thread
from time import monotonic, sleep
from uuid import uuid4

from deskmate_formats.observer._private_storage import (LockBusy, journal_lock, private_file,
                                                       storage_directory)
from deskmate_formats.observer.events import EventError, decode_json, encode_json
from deskmate_formats.observer.process_health import process_claim, verify_process

from . import procedures
from .task_manifest import utc_now

SCHEMA_VERSION = 1
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
    """Create an immutable private record. Never overwrite."""
    path = Path(path)
    if os.path.lexists(path):
        raise DeterministicError("record already exists; inspect instead of retrying")
    with private_file(path, write=True) as stream:
        stream.write(encode_json(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read(path, limit=MAX_PLAN_BYTES):
    with private_file(Path(path)) as stream:
        return decode_json(stream.read(limit + 1), limit)


def _digest(path):
    with Path(path).open("rb") as stream:
        return sha256(stream.read()).hexdigest()


def implementation_hashes():
    """Bind the installed supervisor sources this attempt was prepared against."""
    package = Path(__file__).parent
    return {path.name: _digest(path) for path in sorted(package.glob("*.py"))}


def _git(working_directory, *args):
    from shutil import which

    git = which("git")
    if not git:
        return None
    try:
        result = subprocess.run([git, "--no-replace-objects", *args], cwd=working_directory,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.decode("utf-8", "replace").strip() if result.returncode == 0 else None


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
    })
    # A disposable checkout carries its own sources; do not import the installed
    # package when the owned worktree has one.
    if working_directory is not None:
        source_tree = Path(working_directory) / "src"
        if source_tree.is_dir():
            env["PYTHONPATH"] = str(source_tree)
    return env


def _working_directory(value):
    if type(value) is not str or not 0 < len(value) <= 260:
        raise DeterministicError("invalid working directory")
    path = Path(value).absolute()
    if not path.is_dir():
        raise DeterministicError("working directory must be an existing directory")
    return str(path)


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


def prepare(directory, *, campaign, procedure, arguments, working_directory,
            source_commit=None, timeout_seconds=None, interpreter=None):
    """Freeze a new private attempt plan. No process is started."""
    root = Path(directory).absolute()
    if root.exists():
        raise DeterministicError("attempt directory must be new")
    if type(campaign) is not str or not 0 < len(campaign) <= 64:
        raise DeterministicError("invalid campaign identity")
    working = _working_directory(working_directory)
    spec = procedures.get(procedure)
    normalized = spec.normalize(arguments)
    timeout = spec.timeout_seconds if timeout_seconds is None else timeout_seconds
    if (type(timeout) not in (int, float)
            or not MIN_TIMEOUT_SECONDS <= timeout <= min(MAX_TIMEOUT_SECONDS, spec.timeout_seconds)):
        raise DeterministicError("attempt timeout must be a positive value within the procedure limit")
    if source_commit is not None and (type(source_commit) is not str or len(source_commit) != 40
                                      or any(char not in "0123456789abcdef" for char in source_commit)):
        raise DeterministicError("invalid source revision")
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
    observed = source_revision(working)
    if source_commit is not None and observed is not None and observed != source_commit:
        raise DeterministicError("working directory revision differs from the requested source")
    plan = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": uuid4().hex,
        "campaign": campaign,
        "procedure": spec.name,
        "arguments": normalized,
        "argv": argv,
        "interpreter_sha256": _digest(argv[0]),
        "working_directory": working,
        "source_commit": source_commit,
        "source_revision": observed,
        "resources": list(spec.resources),
        "timeout_seconds": float(timeout),
        "created_at_utc": utc_now(),
        "implementation_sha256": implementation_hashes(),
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


def _stop_tree(process):
    """Terminate the process and its descendants; never leave an orphan."""
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


def _artifacts(directory):
    """Hash the bounded artifact directory a procedure may write."""
    found = []
    total = 0
    for path in sorted(Path(directory).rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        info = path.lstat()
        if info.st_size > MAX_ARTIFACT_BYTES:
            raise DeterministicError("artifact exceeds the byte limit")
        total += info.st_size
        if total > MAX_ARTIFACT_TOTAL or len(found) >= MAX_ARTIFACTS:
            raise DeterministicError("artifact set exceeds its bounds")
        with path.open("rb") as stream:
            data = stream.read(MAX_ARTIFACT_BYTES + 1)
        found.append({"path": path.relative_to(directory).as_posix(),
                      "size": len(data), "sha256": sha256(data).hexdigest()})
    return found


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


def run(directory, *, authorization, reservation=None):
    """Execute the frozen plan once. ``authorization`` is the exact plan digest.

    ``reservation`` is an optional zero-argument callable acquiring resource
    leases and returning a release callable, used by the campaign registry.
    """
    root = storage_directory(directory)
    # The exclusive lock covers validation and the durable attempt fence only.
    # It is released before execution so an authorized cancellation can be
    # written while the child runs.
    with journal_lock(root):
        plan, token = load_plan(root)
        if authorization != token:
            raise DeterministicError("explicit authorization must match the exact plan digest")
        if plan["implementation_sha256"] != implementation_hashes():
            raise DeterministicError("supervisor implementation changed after preparation")
        if _digest(plan["argv"][0]) != plan["interpreter_sha256"]:
            raise DeterministicError("interpreter changed after preparation")
        if not Path(plan["working_directory"]).is_dir():
            raise DeterministicError("working directory disappeared after preparation")
        if (root / "attempt.json").exists():
            raise DeterministicError("attempt already started; replay is forbidden")
        if (root / "cancel.json").exists():
            raise DeterministicError("cancellation was requested before start")
        observed = source_revision(plan["working_directory"])
        if plan["source_revision"] is not None and observed != plan["source_revision"]:
            raise DeterministicError("working directory revision changed after preparation")
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
        "timeout_seconds": plan["timeout_seconds"], "started_at_utc": started,
        "state": "uncertain", "reason": "attempt-interrupted",
        "exit_status": None, "timed_out": False, "cancelled": False,
        "inference": {"required": False, "measurements": [], "note":
                      "deterministic procedure; no model usage is expected or reported"},
        "git_status_before": _git(plan["working_directory"], "status", "--porcelain",
                                  "--untracked-files=all"),
    }
    process = None
    try:
        process = _limited_subprocess(plan["argv"], cwd=plan["working_directory"],
                                      env=environment(artifacts, plan["working_directory"]))
        claim = process_claim(process.pid)
        if claim is not None:
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
                _stop_tree(process)
                break
            if monotonic() >= deadline:
                timed_out = True
                _stop_tree(process)
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
        if process is not None and process.poll() is None:
            _stop_tree(process)
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
        process = "unknown"
        if child is not None:
            process = verify_process(child["pid"], child["identity"])
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
            "outcome": outcome,
            "requires_inspection": attempt is not None and outcome is None,
            "implementation_unchanged": plan["implementation_sha256"] == implementation_hashes(),
        }


def recover(directory):
    """Close an interrupted attempt as ``uncertain``. Never respawns work."""
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        if (root / "outcome.json").exists():
            return _read(root / "outcome.json")
        if not (root / "attempt.json").exists():
            raise DeterministicError("no interrupted attempt to recover")
        attempt = _read(root / "attempt.json")
        child = _read(root / "child.json") if (root / "child.json").exists() else None
        if child is not None and verify_process(child["pid"], child["identity"]) == "alive":
            # An orphaned child is still executing. Closing the attempt now would
            # hide a live process and race its own terminal record.
            raise DeterministicError("attempt child is still alive; stop it before recovery")
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
            "process": ("unknown" if child is None
                        else verify_process(child["pid"], child["identity"])),
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
