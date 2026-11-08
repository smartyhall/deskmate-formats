"""Bounded stdio client for the stable Codex app-server 0.166.0 subset."""

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
import json
import math
import os
from pathlib import Path
from queue import Empty, Full, Queue
import re
import subprocess
from threading import Event, Thread, current_thread
from time import monotonic
from uuid import uuid4

from deskmate_formats.observer.events import decode_json, encode_json
from deskmate_formats.observer.process_health import process_claim

VERSION = "0.166.0"
PROFILE_SHA256 = "c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9"
MAX_FRAME = 256 * 1024
MAX_EVENTS = 64
PARAM_FIELDS = {
    "initialize": {"clientInfo", "capabilities"},
    "thread/start": {"ephemeral"},
    "thread/resume": {"threadId", "excludeTurns"},
    "thread/read": {"threadId", "includeTurns"},
    "thread/turns/list": {"threadId", "itemsView", "cursor", "limit"},
    "turn/start": {"threadId", "input"},
    "turn/steer": {"threadId", "expectedTurnId", "input"},
    "turn/interrupt": {"threadId", "turnId"},
}
APPROVALS = {
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
}
_EOF = object()


class ProtocolError(ValueError):
    """Local contract violation before sending a frame."""


class TransportError(OSError):
    """The connection failed. A write may already have reached the server."""


class RemoteError(RuntimeError):
    """An explicitly correlated app-server JSON-RPC error."""

    def __init__(self, code):
        super().__init__(f"app-server reported JSON-RPC error {code}")
        self.code = code


def request_id(value):
    if type(value) is int and -(1 << 63) <= value < (1 << 63):
        return value
    if type(value) is str and 0 < len(value) <= 256 and value.isprintable():
        return value
    raise ProtocolError("unsupported request ID")


def entity_id(value):
    if type(value) is not str or not 0 < len(value) <= 256 or not value.isprintable():
        raise ProtocolError("unsupported thread, turn or item ID")
    return value


def _tree(value, depth=0):
    if depth > 32:
        raise ProtocolError("JSON exceeds nesting limit")
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ProtocolError("JSON member name must be a string")
            _tree(child, depth + 1)
    elif type(value) is list:
        for child in value:
            _tree(child, depth + 1)
    elif type(value) is float:
        if not math.isfinite(value):
            raise ProtocolError("JSON contains a non-finite number")
    elif value is not None and type(value) not in (str, int, bool):
        raise ProtocolError("unsupported JSON value")


def encode_frame(message):
    _tree(message)
    try:
        frame = encode_json(message) + b"\n"
    except (ValueError, UnicodeError) as error:
        raise ProtocolError("cannot encode protocol JSON") from error
    if len(frame) > MAX_FRAME:
        raise ProtocolError("protocol frame exceeds byte limit")
    return frame


class Schema:
    def __init__(self):
        from jsonschema import Draft7Validator

        raw = files(__package__).joinpath(f"codex-{VERSION}.json").read_bytes()
        if sha256(raw).hexdigest() != PROFILE_SHA256:
            raise ProtocolError("app-server schema profile hash mismatch")
        profile = json.loads(raw)
        self.methods = profile["methods"]
        self.notifications = profile["notifications"]
        self._validator = Draft7Validator({"definitions": profile["definitions"]})

    def validate(self, name, value):
        if not self._validator.evolve(schema={
            "$ref": f"#/definitions/{name.replace('~', '~0').replace('/', '~1')}",
            "definitions": self._validator.schema["definitions"],
        }).is_valid(value):
            raise ProtocolError(f"invalid {name} shape")

    def fields(self, name):
        return self._validator.schema["definitions"][name]["properties"]

    def params(self, method, params):
        if method not in PARAM_FIELDS or type(params) is not dict or not params.keys() <= PARAM_FIELDS[method]:
            raise ProtocolError("unsupported app-server method or parameter")
        self.validate(self.methods[method][0], params)
        for key in ("threadId", "turnId", "expectedTurnId"):
            if key in params:
                entity_id(params[key])
        if method in {"turn/start", "turn/steer"}:
            if not params["input"] or any(item.keys() != {"type", "text"} or item["type"] != "text"
                                          for item in params["input"]):
                raise ProtocolError("S0 supports plain text input only")


@dataclass(frozen=True, slots=True)
class Approval:
    generation: str
    request_id: int | str
    method: str
    thread_id: str
    turn_id: str
    item_id: str
    decisions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Notification:
    method: str
    params: dict


class AppServer:
    """Own a single child and generation. All public calls use the owning thread."""

    def __init__(self, argv, *, timeout=5, cwd=None, env=None):
        if type(argv) not in (tuple, list) or not argv or any(type(arg) is not str for arg in argv):
            raise ProtocolError("expected a local executable argument vector")
        executable = Path(argv[0])
        if not executable.is_absolute() or executable.suffix.lower() in {".bat", ".cmd"}:
            raise ProtocolError("expected an absolute executable path")
        if not 0 < timeout <= 60:
            raise ProtocolError("invalid protocol timeout")
        self.schema = Schema()
        self.generation = uuid4().hex
        self.timeout = timeout
        self._owner = current_thread()
        self._frames = Queue(MAX_EVENTS)
        self._overflow = Event()
        self._events = deque()
        self._approvals = {}
        self._seen_approvals = set()
        self._terminal_turns = set()
        self._next_id = 0
        self._requesting = False
        self._broken = False
        self._closed = False
        self._writer = None
        self._child = subprocess.Popen(
            argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        self._reader = Thread(target=self._read, daemon=True)
        self._reader.start()
        try:
            claim = process_claim(self._child.pid)
            if claim is None:
                raise TransportError("could not establish child process identity")
            self.pid, self.process_identity = claim["pid"], claim["identity"]
            result = self._request("initialize", {
                "clientInfo": {"name": "deskmate_supervisor", "version": "0.1.0"},
                "capabilities": {"experimentalApi": False},
            })
            if not re.match(r"^[^/\s]+/" + re.escape(VERSION) + r" ", result["userAgent"]):
                raise TransportError("app-server build version mismatch")
            initialized = {"method": "initialized"}
            self.schema.validate("ClientNotification", initialized)
            self._write(encode_frame(initialized))
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _owned(self):
        if current_thread() is not self._owner:
            raise ProtocolError("protocol session has a single owner")

    def _usable(self):
        self._owned()
        if self._closed or self._broken:
            raise TransportError("protocol session is unavailable")

    def _fail(self, reason):
        self._broken = True
        self._approvals.clear()
        return TransportError(reason)

    def _read(self):
        try:
            while True:
                frame = self._child.stdout.readline(MAX_FRAME + 1)
                self._frames.put_nowait(frame or _EOF)
                if not frame or len(frame) > MAX_FRAME or not frame.endswith(b"\n"):
                    break
        except (Full, OSError, ValueError):
            self._overflow.set()

    def _write(self, frame):
        self._usable()
        outcome = Queue(1)

        def write():
            try:
                remaining = memoryview(frame)
                while remaining:
                    count = os.write(self._child.stdin.fileno(), remaining)
                    if not count:
                        raise OSError("short stdio write")
                    remaining = remaining[count:]
            except (OSError, ValueError):
                outcome.put(False)
            else:
                outcome.put(True)

        self._writer = Thread(target=write, daemon=True)
        self._writer.start()
        try:
            success = outcome.get(timeout=self.timeout)
        except Empty:
            raise self._fail("stdio write timed out") from None
        if not success:
            raise self._fail("stdio write failed")
        self._writer.join()
        self._writer = None

    def _receive(self, deadline):
        if self._overflow.is_set():
            raise self._fail("stdio read failed or receive queue overflowed")
        try:
            frame = self._frames.get(timeout=max(0, deadline - monotonic()))
        except Empty:
            return None
        if frame is _EOF:
            raise self._fail("app-server stdout closed")
        if len(frame) > MAX_FRAME or not frame.endswith(b"\n"):
            raise self._fail("oversized or incomplete stdio frame")
        try:
            message = decode_json(frame, MAX_FRAME)
            _tree(message)
            if type(message) is not dict:
                raise ProtocolError("expected a JSON object")
            return message
        except ValueError:
            raise self._fail("malformed app-server JSON frame") from None

    def request(self, method, params, *, before_send=None):
        """Call one supported method. before_send receives its reserved client ID."""
        if method == "initialize":
            raise ProtocolError("initialization is performed once per connection")
        return self._request(method, params, before_send)

    def _request(self, method, params, before_send=None):
        self._usable()
        if self._requesting:
            raise ProtocolError("another request is in progress")
        self._requesting = True
        try:
            return self._exchange(method, params, before_send)
        finally:
            self._requesting = False

    def _exchange(self, method, params, before_send):
        if type(method) is not str:
            raise ProtocolError("invalid app-server method")
        self.schema.params(method, params)
        identifier = request_id(self._next_id)
        self._next_id += 1
        frame = encode_frame({"method": method, "params": params, "id": identifier})
        if before_send is not None:
            before_send(identifier)
        self._write(frame)
        deadline = monotonic() + self.timeout
        while monotonic() < deadline:
            message = self._receive(deadline)
            if message is None:
                break
            try:
                if "method" in message:
                    self._event(message)
                    continue
                if type(request_id(message.get("id"))) is not int or message["id"] != identifier:
                    raise ProtocolError("duplicate or mismatched response ID")
                if message.keys() == {"id", "error"}:
                    self.schema.validate("JSONRPCError", message)
                    code = message["error"]["code"]
                    if type(code) is not int or not -(1 << 63) <= code < (1 << 63):
                        raise ProtocolError("invalid remote error code")
                    raise RemoteError(code)
                if message.keys() != {"id", "result"}:
                    raise ProtocolError("unexpected response members")
                self.schema.validate(self.schema.methods[method][1], message["result"])
                return message["result"]
            except ProtocolError as error:
                raise self._fail(str(error)) from None
        raise self._fail("app-server response timed out")

    def _event(self, message):
        method = message["method"]
        params = message.get("params")
        if type(method) is not str:
            raise ProtocolError("invalid server method")
        if "id" in message:
            if method not in APPROVALS or message.keys() != {"method", "params", "id"}:
                raise ProtocolError("unsupported server request")
            identifier = request_id(message["id"])
            self.schema.validate(self.schema.methods[method][0], params)
            if identifier in self._seen_approvals or len(self._seen_approvals) >= 4096:
                raise ProtocolError("duplicate server request ID or session request limit reached")
            decisions = ("accept", "decline", "cancel")
            # This version's command schema has no availableDecisions field.
            # Refuse to offer a decision for unrecognized policy extensions.
            definition = self.schema.methods[method][0]
            allowed = self.schema.fields(definition)
            if (not params.keys() <= allowed.keys() or params.get("networkApprovalContext") is not None
                    or params.get("kind", "command") != "command"):
                decisions = ()
            approval = Approval(self.generation, identifier, method, entity_id(params["threadId"]),
                                entity_id(params["turnId"]), entity_id(params["itemId"]), decisions)
            if (approval.thread_id, approval.turn_id) in self._terminal_turns:
                raise ProtocolError("approval arrived for a terminal turn")
            self._seen_approvals.add(identifier)
            self._approvals[identifier] = approval
            event = approval
        else:
            if not message.keys() <= {"method", "params", "emittedAtMs"}:
                raise ProtocolError("unexpected notification members")
            if "emittedAtMs" in message and type(message["emittedAtMs"]) is not int:
                raise ProtocolError("invalid notification timestamp")
            if method not in self.schema.notifications:
                # Discard unhandled payloads without treating them as activity.
                return
            self.schema.validate(self.schema.notifications[method], params)
            if method == "serverRequest/resolved":
                identifier = request_id(params["requestId"])
                approval = self._approvals.get(identifier)
                if approval is not None and approval.thread_id != params["threadId"]:
                    raise ProtocolError("mismatched approval resolution")
                self._approvals.pop(identifier, None)
            if method == "turn/completed":
                identity = entity_id(params["threadId"]), entity_id(params["turn"]["id"])
                if (params["turn"]["status"] == "inProgress" or len(self._terminal_turns) >= 4096
                        or identity in self._terminal_turns):
                    raise ProtocolError("invalid terminal status or session turn limit reached")
                self._terminal_turns.add(identity)
                for identifier, approval in tuple(self._approvals.items()):
                    if (approval.thread_id, approval.turn_id) == identity:
                        del self._approvals[identifier]
            if method == "turn/started":
                identity = entity_id(params["threadId"]), entity_id(params["turn"]["id"])
                if params["turn"]["status"] != "inProgress" or identity in self._terminal_turns:
                    raise ProtocolError("invalid turn start status or terminal turn restarted")
            event = Notification(method, params)
        if len(self._events) >= MAX_EVENTS:
            raise ProtocolError("protocol event queue overflowed")
        self._events.append(event)

    def next_event(self, *, timeout=0):
        """Return a queued approval or notification, or None when idle."""
        self._usable()
        if not 0 <= timeout <= self.timeout:
            raise ProtocolError("invalid event timeout")
        deadline = monotonic() + timeout
        for _ in range(MAX_EVENTS):
            if self._events:
                return self._events.popleft()
            message = self._receive(deadline)
            if message is None:
                return None
            try:
                if "method" not in message:
                    raise ProtocolError("unexpected response without outstanding request")
                self._event(message)
            except ProtocolError as error:
                raise self._fail(str(error)) from None
        return None

    def _take_synthetic_approval(self, approval, *, generation, thread_id, turn_id, decision):
        """Consume and serialize one exact approval. Only the offline harness writes it."""
        self._usable()
        if self._requesting or type(approval) is not Approval:
            raise ProtocolError("approval must be an outstanding request object")
        # Process already available resolutions and turn completions before a decision.
        for _ in range(MAX_EVENTS):
            message = self._receive(monotonic())
            if message is None:
                break
            try:
                if "method" not in message:
                    raise ProtocolError("unexpected response without outstanding request")
                self._event(message)
            except ProtocolError as error:
                raise self._fail(str(error)) from None
        else:
            raise self._fail("receive backlog during approval")
        current = self._approvals.get(request_id(approval.request_id))
        if (current is not approval or generation != self.generation
                or (thread_id, turn_id) != (approval.thread_id, approval.turn_id)
                or decision not in approval.decisions):
            raise ProtocolError("stale, mismatched or unauthorized approval")
        result = {"decision": decision}
        self.schema.validate(self.schema.methods[approval.method][1], result)
        frame = encode_frame({"id": approval.request_id, "result": result})
        del self._approvals[approval.request_id]
        return frame

    def close(self):
        self._owned()
        if self._closed:
            return
        self._closed = True
        self._approvals.clear()
        self._events.clear()
        # Kill before closing a pipe if a timed-out writer may hold its lock.
        if self._writer is None:
            try:
                self._child.stdin.close()
            except OSError:
                pass
        try:
            self._child.wait(timeout=min(self.timeout, 0.5) if self._writer is None else 0)
        except subprocess.TimeoutExpired:
            self._child.kill()
            self._child.wait(timeout=2)
        if self._writer is not None:
            self._writer.join(timeout=2)
        self._reader.join(timeout=2)
        if self._reader.is_alive() or self._writer is not None and self._writer.is_alive():
            raise TransportError("child pipe workers did not exit")
        self._child.stdin.close()
        self._child.stdout.close()
