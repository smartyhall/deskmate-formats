"""One-way, allowlisted publication from one owned app-server turn."""

from hashlib import sha256
from time import monotonic, sleep
from uuid import uuid4

from deskmate_formats.observer.events import EventError, encode_json
from deskmate_formats.observer.journal import JournalBusy, JournalError, publish_event
from deskmate_formats.observer.process_health import verify_process

from .protocol import Approval, Notification, ProtocolError, VERSION


TERMINAL = {
    "completed": ("turn.completed", "App-server reported turn completion"),
    "failed": ("turn.failed", "App-server reported turn failure"),
    "interrupted": ("turn.interrupted", "App-server reported turn interruption"),
}
TOOLS = {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall", "collabAgentToolCall"}


class AppServerTelemetry:
    """Publish one tracked turn per origin. The publisher holds no transport handle."""

    def __init__(self, journal, *, generation, pid, process_identity):
        self.journal = journal
        self.generation = generation
        self.pid = pid
        self.process_identity = process_identity
        self.origin = uuid4().hex
        self._correlation_salt = uuid4().hex
        self.sequence = 0
        self.publication_failed = False
        self._turn = None
        self._started = False
        self._terminal = False
        self._connected = False
        self._disconnected = False
        self._exited = False
        self._pending = {}

    def bind(self, receipt):
        if (self._turn is not None or receipt.generation != self.generation
                or receipt.method != "turn/start" or not receipt.acknowledged
                or not receipt.thread_id or not receipt.turn_id):
            raise ProtocolError("telemetry requires an acknowledged turn receipt from this generation")
        self._turn = (receipt.thread_id, receipt.turn_id)

    def connected(self):
        if not self._connected and not self._disconnected:
            self._connected = True
            self._publish("source.reconnected", "App-server protocol handshake completed")

    def disconnected(self):
        if not self._disconnected:
            self._disconnected = True
            self._publish("source.disconnected", "App-server connection closed; unconfirmed state is uncertain")

    def sample_process(self):
        status = verify_process(self.pid, self.process_identity)
        if status == "alive":
            self._publish("process.heartbeat", "Host verified app-server process identity",
                          process={"pid": self.pid, "identity": self.process_identity})
        elif status in {"stopped", "not-found"} and not self._exited:
            self._exited = True
            self._publish("process.exited", "Host observed app-server process exit")

    def observe(self, event):
        if self._disconnected or self._terminal or self._turn is None:
            return
        if isinstance(event, Approval):
            if event.generation == self.generation and self._turn == (event.thread_id, event.turn_id):
                key = self._correlation(event.request_id)
                self._pending[event.request_id] = key
                self._publish("approval.requested", "App-server requested approval", approval=key)
        elif isinstance(event, Notification):
            self._observe_notification(event.method, event.params)

    def _observe_notification(self, method, params):
        if method == "serverRequest/resolved":
            if params["threadId"] == self._turn[0]:
                key = self._pending.pop(params["requestId"], None)
                if key is not None:
                    self._publish("approval.resolved", "App-server reported approval request resolved", approval=key)
            return
        turn_id = params["turn"]["id"] if method in {"turn/started", "turn/completed"} else params.get("turnId")
        if (params.get("threadId"), turn_id) != self._turn:
            return
        if method == "turn/started" and not self._started:
            self._started = True
            self._publish("turn.started", "App-server reported turn start")
        elif method == "turn/completed":
            self._terminal = True
            for key in self._pending.values():
                self._publish("approval.resolved", "Terminal turn closed the outstanding approval", approval=key)
            self._pending.clear()
            self._publish(*TERMINAL[params["turn"]["status"]])
        elif method in {"item/started", "item/completed"} and params["item"]["type"] in TOOLS:
            if method == "item/started":
                self._publish("tool.started", "App-server reported tool start")
            elif params["item"].get("status") == "failed":
                self._publish("tool.failed", "App-server reported tool failure")
            else:
                self._publish("tool.completed", "App-server reported tool end")

    def _correlation(self, value):
        return sha256(encode_json([self._correlation_salt, value])).hexdigest()

    def _publish(self, kind, summary, *, approval=None, process=None):
        if self.publication_failed:
            return
        self.sequence += 1
        correlation = {"turn": self._correlation(list(self._turn))} if self._turn else {}
        if approval is not None:
            correlation["approval"] = approval
        event = {
            "schema_version": 1, "source": f"codex-app-server-{VERSION}",
            "origin_id": self.origin, "agent_id": "codex-supervisor", "run_id": self.generation,
            "source_sequence": self.sequence, "type": kind, "summary": summary,
            "visibility": "observer", "correlation": correlation,
        }
        if process is not None:
            event["process"] = process
        deadline = monotonic() + 0.25
        while True:
            try:
                publish_event(self.journal, event)
                return
            except JournalBusy:
                if monotonic() < deadline:
                    sleep(0.01)
                    continue
            except (JournalError, EventError):
                pass
            # The protocol owner can inspect this flag. Never retry an ambiguous append.
            self.publication_failed = True
            return
