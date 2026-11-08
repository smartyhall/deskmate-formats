"""Single-use S0 operator driver. Preparation and inspection never launch a worker."""

from dataclasses import asdict
from hashlib import file_digest, sha256
from importlib.metadata import version
import json
import os
import platform
from pathlib import Path
import subprocess
import sqlite3
import sys
from time import monotonic
from uuid import uuid4

from deskmate_formats.observer._private_storage import journal_lock, private_file, storage_directory
from deskmate_formats.observer.events import decode_json, encode_json
from deskmate_formats.observer.process_health import verify_process

from .ledger import LedgerError, open_ledger
from .operations import Operations
from .protocol import AppServer, Approval, Notification, PROFILE_SHA256, ProtocolError, RemoteError, Schema, TransportError, VERSION
from .synthetic_peer import MODES
from .telemetry import AppServerTelemetry, TOOLS
from .task_manifest import utc_now

NATIVE_SHA256 = "9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42"
PROMPT = ("Reply exactly S0_CANARY_OK. Do not use tools, read or write files, "
          "run commands, access the network, or request approval.")
MAX_EVIDENCE = 4 * 1024 * 1024
IMPLEMENTATION_FILES = ("driver.py", "driver_cli.py", "protocol.py", "operations.py", "ledger.py",
                        "synthetic_peer.py", "telemetry.py", "bridge.py", "bridge_cli.py")


class DriverError(ValueError):
    """Fail closed without including private input in diagnostics."""


def digest(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def read_record(path):
    with private_file(Path(path)) as stream:
        return decode_json(stream.read(MAX_EVIDENCE + 1), MAX_EVIDENCE)


def write_record(path, value):
    """Create an immutable record under the caller's exclusive run lock."""
    path = Path(path)
    if os.path.lexists(path):
        raise DriverError("record already exists; inspect instead of retrying")
    with private_file(path, write=True) as stream:
        stream.write(encode_json(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def verify_native(executable):
    """Hash before executing even --version; never select a PATH shim."""
    path = Path(executable)
    if (not path.is_absolute() or path.suffix.lower() != ".exe" or path.is_symlink()
            or digest(path) != NATIVE_SHA256):
        raise DriverError("native executable pin mismatch; review compatibility drift without upgrading")
    result = subprocess.run([str(path), "--version"], capture_output=True, timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode or result.stdout.strip() != f"codex-cli {VERSION}".encode():
        raise DriverError("native executable version mismatch")
    Schema()
    return str(path.resolve())


def prepare(directory, *, executable=None, model=None, effort=None, mode="success", timeout=10, deadline=60,
            binding=None):
    """Freeze a fresh private plan. No app-server or model operation occurs."""
    root = Path(directory).absolute()
    if root.exists():
        raise DriverError("run directory must be new")
    if not 0 < timeout <= 30 or not 0 < deadline <= 60:
        raise DriverError("invalid bounded observation interval")
    if executable is None:
        if mode not in MODES:
            raise DriverError("unsupported synthetic scenario")
        executable = str(Path(sys.executable).resolve())
        kind = "synthetic"
        argv = [executable, "-I", "-m", "deskmate_formats.supervisor.synthetic_peer",
                str(root / "evidence" / "peer.json"), mode]
    else:
        if binding is not None:
            raise DriverError("S2 live dispatch is disabled")
        executable = verify_native(executable)
        if type(model) is not str or not 0 < len(model) <= 128 or not model.isascii() or not model.isprintable():
            raise DriverError("explicit operator-selected model required")
        if effort not in ("low", "medium", "high"):
            raise DriverError("explicit reviewed reasoning effort required")
        kind = "live"
        argv = [executable, "app-server", "--listen", "stdio://"]
    storage_directory(root, create=True)
    for name in ("evidence", "scratch", "codex-home", "spool"):
        storage_directory(root / name, create=True)
    with open_ledger(root / "receipts", create=True):
        pass
    # No inherited PATH, user profile, proxy, token, Git, MCP or emulator variables.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
    env.update(CODEX_HOME=str(root / "codex-home"), HOME=str(root / "codex-home"),
               USERPROFILE=str(root / "codex-home"), TEMP=str(root / "scratch"),
               TMP=str(root / "scratch"))
    config = (f"model = {json.dumps(model)}\nmodel_reasoning_effort = {json.dumps(effort)}\nmodel_provider = \"openai\"\n"
              "approval_policy = \"never\"\nsandbox_mode = \"read-only\"\n"
              "web_search = \"disabled\"\nmcp_servers = {}\n") if kind == "live" else "# synthetic only\n"
    config_path = root / "codex-home" / "config.toml"
    with private_file(config_path, write=True) as stream:
        stream.write(config.encode())
        stream.flush()
        os.fsync(stream.fileno())
    plan = {
        "schema_version": 1, "run_id": uuid4().hex, "kind": kind,
        "root": str(root), "argv": argv, "executable_sha256": digest(executable),
        "profile_sha256": PROFILE_SHA256, "codex_version": VERSION,
        "config_sha256": digest(config_path), "env": env, "model": model, "effort": effort,
        "timeout": timeout, "deadline": deadline, "prompt": PROMPT, "binding": binding,
        "prepared_at_utc": utc_now(),
        "runtime": {"python": sys.version, "platform": platform.platform(),
                    "sqlite": sqlite3.sqlite_version, "jsonschema": version("jsonschema")},
        "implementation_sha256": {name: digest(Path(__file__).with_name(name)) for name in IMPLEMENTATION_FILES},
    }
    with journal_lock(root, write=True):
        write_record(root / "plan.json", plan)
    return sha256(encode_json(plan)).hexdigest()


def load_plan(root):
    root = storage_directory(root)
    plan = read_record(root / "plan.json")
    if (plan["schema_version"] != 1 or plan["root"] != str(root)
            or plan["profile_sha256"] != PROFILE_SHA256 or plan["codex_version"] != VERSION
            or plan["kind"] not in ("live", "synthetic")):
        raise DriverError("unsupported or relocated plan")
    return plan, sha256(encode_json(plan)).hexdigest()


def status(directory):
    """Offline inspection. Does not reconcile, launch, send or publish."""
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        with open_ledger(root / "receipts") as ledger:
            receipts = [asdict(row) for row in ledger.receipts()]
        return {"plan_sha256": token, "plan": plan, "kind": plan["kind"], "binding": plan["binding"],
                "attempted": (root / "attempt.json").exists(), "operations": receipts,
                "outcome": read_record(root / "outcome.json") if (root / "outcome.json").exists() else None}


class Evidence:
    def __init__(self, root):
        self.root = root
        self.sequence = 0
        self.size = 0

    def save(self, kind, value):
        record = {"kind": kind, "value": value}
        size = len(encode_json(record))
        if self.sequence >= 512 or self.size + size > MAX_EVIDENCE:
            raise DriverError("private evidence bound reached")
        self.sequence += 1
        self.size += size
        write_record(self.root / f"{self.sequence:04d}.json", record)


def _validate_plan(root, plan, token, authorization, isolation_reviewed):
    if authorization != token:
        raise DriverError("explicit authorization must match the exact plan digest")
    if (set(plan["implementation_sha256"]) != set(IMPLEMENTATION_FILES)
            or any(digest(Path(__file__).with_name(name)) != value for name, value in plan["implementation_sha256"].items())):
        raise DriverError("driver implementation changed after preparation")
    if plan["kind"] == "synthetic":
        argv = plan["argv"]
        if (len(argv) != 6 or argv[0] != str(Path(sys.executable).resolve())
                or argv[1:4] != ["-I", "-m", "deskmate_formats.supervisor.synthetic_peer"]
                or argv[4] != str(root / "evidence" / "peer.json") or argv[5] not in MODES):
            raise DriverError("synthetic worker must be the installed fixed peer")
    elif plan["argv"][1:] != ["app-server", "--listen", "stdio://"]:
        raise DriverError("unreviewed live arguments")
    if (plan["prompt"] != PROMPT or not 0 < plan["timeout"] <= 30 or not 0 < plan["deadline"] <= 60
            or not plan["env"].keys() <= {"SystemRoot", "WINDIR", "CODEX_HOME", "HOME", "USERPROFILE", "TEMP", "TMP"}
            or any(plan["env"].get(key) != str(root / "codex-home") for key in ("CODEX_HOME", "HOME", "USERPROFILE"))
            or any(plan["env"].get(key) != str(root / "scratch") for key in ("TEMP", "TMP"))):
        raise DriverError("unreviewed prompt, environment or observation bounds")
    if digest(plan["argv"][0]) != plan["executable_sha256"]:
        raise DriverError("executable changed since preparation")
    if digest(root / "codex-home" / "config.toml") != plan["config_sha256"]:
        raise DriverError("configuration changed since preparation")
    for name in ("evidence", "scratch", "codex-home", "spool", "receipts"):
        storage_directory(root / name)
    if plan["kind"] == "live":
        if isolation_reviewed != token:
            raise DriverError("live launch requires separately reviewed effective isolation for this plan")
        verify_native(plan["argv"][0])
        if plan["binding"] is not None:
            raise DriverError("S2 live dispatch is disabled")
    Schema()


def _effective_policy(result, plan, scratch):
    if (Path(result["cwd"]).resolve() != scratch.resolve()
            or result["approvalPolicy"] != "never" or result["sandbox"] != {"type": "readOnly"}
            or result["model"] != (plan["model"] if plan["kind"] == "live" else "synthetic")
            or result["modelProvider"] != ("openai" if plan["kind"] == "live" else "synthetic")):
        raise DriverError("effective thread policy differs from reviewed plan")


def _event(ops, telemetry, evidence, thread_id, turn_id, *, timeout=0):
    event = ops.next_event(timeout=timeout)
    if event is None:
        return None
    evidence.save("event", asdict(event))
    telemetry.observe(event)
    if isinstance(event, Approval):
        raise DriverError("unexpected approval; no decision sent")
    if isinstance(event, Notification):
        params = event.params
        if event.method == "thread/started" and params["thread"]["id"] != thread_id:
            raise DriverError("stale thread notification")
        if event.method in ("turn/started", "turn/completed"):
            if (params["threadId"], params["turn"]["id"]) != (thread_id, turn_id):
                raise DriverError("stale turn notification")
        if event.method in ("item/started", "item/completed"):
            if (params["threadId"], params["turnId"]) != (thread_id, turn_id):
                raise DriverError("stale item notification")
            if params["item"]["type"] in TOOLS:
                raise DriverError("unexpected tool activity")
    return event


def run(directory, *, authorization, isolation_reviewed=None, accepted_binding=None):
    """Perform at most one thread/start and one turn/start. Never retry a run."""
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        if plan["binding"] != accepted_binding:
            raise DriverError("bound S2 plan requires the bridge's current acceptance check")
        _validate_plan(root, plan, token, authorization, isolation_reviewed)
        if any((root / "scratch").iterdir()):
            raise DriverError("scratch must be empty before dispatch")
        with open_ledger(root / "receipts") as ledger:
            if ledger.receipts():
                raise DriverError("recorded operations forbid another dispatch")
            # This marker is a permanent fence even if a crash precedes the first RPC.
            write_record(root / "attempt.json", {"plan_sha256": token, "binding": plan["binding"]})
            return _own(root, plan, ledger)


def _own(root, plan, ledger):
    evidence = Evidence(root / "evidence")
    client = ops = telemetry = None
    outcome = {"state": "blocked", "reason": "owner-interrupted", "run_id": plan["run_id"],
               "binding": plan["binding"], "kind": plan["kind"]}
    start = monotonic()
    try:
        evidence.save("launch-intent", plan)
        client = AppServer(plan["argv"], timeout=plan["timeout"], cwd=root / "scratch", env=plan["env"])
        ops = Operations(client, ledger)
        evidence.save("owned-child", {"generation": client.generation, "pid": client.pid,
                                      "process_identity": client.process_identity})
        telemetry = AppServerTelemetry(root / "spool", generation=client.generation,
                                       pid=client.pid, process_identity=client.process_identity)
        telemetry.connected()
        telemetry.sample_process()
        thread_operation = plan["run_id"] + ".thread"
        turn_operation = plan["run_id"] + ".turn"
        params = {"ephemeral": False}
        evidence.save("request-intent", {"operation_id": thread_operation, "method": "thread/start", "params": params})
        result = ops.execute(thread_operation, "thread/start", params)
        evidence.save("thread-result", result)
        _effective_policy(result, plan, root / "scratch")
        thread_id = result["thread"]["id"]
        # Drain queued approvals before any dependent mutation.
        while _event(ops, telemetry, evidence, thread_id, None) is not None:
            pass
        params = {"threadId": thread_id, "input": [{"type": "text", "text": plan["prompt"]}]}
        evidence.save("request-intent", {"operation_id": turn_operation, "method": "turn/start", "params": params})
        result = ops.execute(turn_operation, "turn/start", params)
        evidence.save("turn-result", result)
        turn_id = result["turn"]["id"]
        telemetry.bind(ledger.get(turn_operation))
        terminal = False
        answers = []
        deadline = monotonic() + plan["deadline"]
        while monotonic() < deadline:
            event = _event(ops, telemetry, evidence, thread_id, turn_id,
                           timeout=min(1, plan["timeout"], max(0, deadline - monotonic())))
            if isinstance(event, Notification):
                if event.method == "item/completed" and event.params["item"]["type"] == "agentMessage":
                    answers.append(event.params["item"]["text"])
                if event.method == "turn/completed":
                    terminal = True
            if terminal:
                # Validate already queued duplicate replies/approvals before declaring success.
                while _event(ops, telemetry, evidence, thread_id, turn_id) is not None:
                    pass
                break
        if not terminal:
            raise DriverError("observation deadline; execution outcome remains unresolved")
        if ledger.get(turn_operation).state != "completed" or answers != ["S0_CANARY_OK"]:
            raise DriverError("terminal receipt or sentinel did not pass canary")
        view = client.request("thread/read", {"threadId": thread_id})
        page = client.request("thread/turns/list", {"threadId": thread_id, "itemsView": "notLoaded", "limit": 50})
        evidence.save("history", {"view": view, "page": page})
        while _event(ops, telemetry, evidence, thread_id, turn_id) is not None:
            pass
        matches = [turn for turn in page["data"] if turn["id"] == turn_id]
        if view["thread"]["id"] != thread_id or len(matches) != 1 or matches[0]["status"] != "completed":
            raise DriverError("history did not confirm the exact completed turn")
        outcome.update(state="completed", reason="observed-terminal-and-history")
    except (OSError, ValueError, RuntimeError) as error:
        # Raw exception strings can contain private data. Full allowed results are saved above.
        outcome["reason"] = str(error) if isinstance(error, (DriverError, LedgerError, ProtocolError, TransportError, RemoteError)) else "driver-stopped-inspect-private-evidence"
        outcome["error_type"] = type(error).__name__
    finally:
        try:
            if ops is not None:
                ops.disconnect()
            if telemetry is not None:
                telemetry.disconnected()
        finally:
            if client is not None:
                try:
                    client.close()
                except OSError:
                    outcome.update(state="blocked", reason="child-teardown-failed")
                outcome["child_status"] = verify_process(client.pid, client.process_identity)
                if outcome["child_status"] not in ("stopped", "not-found"):
                    outcome.update(state="blocked", reason="child-exit-not-verified")
                if telemetry is not None:
                    telemetry.sample_process()
                    telemetry.driver_outcome(outcome["state"])
            outcome["telemetry_failed"] = telemetry.publication_failed if telemetry is not None else False
            outcome["operations"] = [asdict(row) for row in ledger.receipts()]
            outcome["elapsed_host_seconds"] = monotonic() - start
            write_record(root / "outcome.json", outcome)
    return outcome


def reconcile_synthetic(directory, *, authorization):
    """Explicit read-only synthetic restart. Never resume, recreate or replay a mutation."""
    root = storage_directory(directory)
    with journal_lock(root):
        plan, token = load_plan(root)
        if plan["kind"] != "synthetic" or authorization != token:
            raise DriverError("only explicitly authorized synthetic reconciliation is enabled")
        _validate_plan(root, plan, token, authorization, None)
        with open_ledger(root / "receipts") as ledger:
            if any(verify_process(pid, stamp) not in ("stopped", "not-found", "identity-mismatch")
                   for _, pid, stamp in ledger.sessions()):
                raise DriverError("previous child exit is unverified; no restart permitted")
            # One immutable restart receipt: even restart failure cannot implicitly retry.
            write_record(root / "reconciliation-intent.json", {"plan_sha256": token})
            with AppServer(plan["argv"][:-1] + ["success"], timeout=plan["timeout"],
                           cwd=root / "scratch", env=plan["env"]) as client:
                ops = Operations(client, ledger)
                try:
                    for row in ledger.receipts():
                        ops.reconcile(row.operation_id)
                    result = [asdict(row) for row in ledger.receipts()]
                    write_record(root / "reconciliation.json", result)
                finally:
                    ops.disconnect()
            return result
