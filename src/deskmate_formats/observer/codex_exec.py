"""Normalize the pinned Codex exec JSONL protocol without executing anything."""

from dataclasses import dataclass
from hashlib import sha256
import json

from .events import SCHEMA_VERSION, EventError, decode_json, normalize_event

SUPPORTED_VERSION = "0.166.0"
MAX_LINE_BYTES = 1024 * 1024  # Including LF
_MAX_ITEMS = 10_000
_TURN = {
    "turn.started": ("turn.started", "Codex turn started"),
    "turn.completed": ("turn.completed", "Codex turn completed"),
    "turn.failed": ("turn.failed", "Codex turn failed"),
}
_TOOLS = {"file_change": "File change", "mcp_tool_call": "MCP tool", "collab_tool_call": "Collaboration tool"}
_ITEM_FIELDS = {
    "command_execution": ("command aggregated_output exit_code status", ""),
    "file_change": ("changes status", ""),
    "mcp_tool_call": ("server tool result error status", "arguments"),
    "collab_tool_call": ("tool sender_thread_id receiver_thread_ids prompt agents_states status", ""),
    "agent_message": ("text", ""),
    "todo_list": ("items", ""),
    "error": ("message", ""),
    "reasoning": ("text", ""),
}


def _object(value, required, optional=""):
    fields = set(required.split())
    if type(value) is not dict or not fields <= value.keys() <= fields | set(optional.split()):
        raise EventError("unexpected Codex JSONL fields")
    return value


def _string(value):
    if type(value) is not str:
        raise EventError("expected a Codex JSONL string")
    return value


def _source_id(value):
    value = _string(value)
    if not value or not value.isprintable() or len(value.encode("utf-8")) > 256:
        raise EventError("invalid Codex source identity")
    return value


def _list(value):
    if type(value) is not list:
        raise EventError("expected a Codex JSONL array")
    return value


def _integer(value, bits):
    if type(value) is not int or not -(1 << (bits - 1)) <= value < 1 << (bits - 1):
        raise EventError("invalid Codex JSONL integer")
    return value


def _private_excerpt(value):
    # The journal accepts printable strings only. The line hash identifies the full record.
    return json.dumps(_string(value), ensure_ascii=True)[1:-1][:512]


@dataclass(frozen=True)
class _Item:
    kind: str
    alias: str
    started: bool
    completed: bool
    fingerprint: str


class CodexExecAdapter:
    """One ordered stdout stream per invocation. Callers own process and journal I/O."""

    def __init__(self, version, *, run_id, agent_id="codex", visibility="private"):
        if version != SUPPORTED_VERSION:
            raise EventError("unsupported Codex exec version")
        self._base = {
            "schema_version": SCHEMA_VERSION,
            "source": f"codex-exec-{version}",
            "agent_id": agent_id,
            "run_id": run_id,
            "origin_id": run_id,
            "visibility": visibility,
        }
        self._sequence = 0
        self._line = 0
        self._buffer = bytearray()
        self._oversized = False
        self._finished = False
        self._thread = None
        self._turn = None
        self._items = {}
        # Validate the operator-supplied fields before spawning or reading.
        normalize_event({**self._base, "source_sequence": 1,
                         "type": "source.reconnected", "summary": "Codex telemetry initialized"})

    @property
    def turn_state(self):
        return self._turn

    @property
    def unfinished_items(self):
        return sum(item.started and not item.completed for item in self._items.values())

    def event(self, kind, summary, *, details=None, correlation=None, severity="info", process=None, private=False):
        """Build one event, including wrapper-owned observations in the same order."""
        self._sequence += 1
        event = {
            **self._base, "source_sequence": self._sequence, "type": kind,
            "summary": summary, "severity": severity,
            "details": {"codex_version": SUPPORTED_VERSION, **(details or {})},
        }
        event["correlation"] = {
            **({"session": "session-1"} if self._thread is not None else {}),
            **({"turn": "turn-1"} if self._turn is not None else {}),
            **(correlation or {}),
        }
        if private:
            event["visibility"] = "private"
        if process is not None:
            event["process"] = process
        return event

    def feed(self, chunk):
        """Yield events from complete LF-terminated lines in byte arrival order."""
        if self._finished:
            raise RuntimeError("Codex JSONL stream already ended")
        start = 0
        while start < len(chunk):
            end = chunk.find(b"\n", start) + 1
            stop = end or len(chunk)
            if len(self._buffer) + stop - start > MAX_LINE_BYTES:
                self._oversized = True
                self._buffer.clear()
            if not self._oversized:
                self._buffer.extend(chunk[start:stop])
            if end:
                self._line += 1
                line, oversized = bytes(self._buffer), self._oversized
                self._buffer.clear()
                self._oversized = False
                yield self._issue("oversized JSONL line") if oversized else self._decode(line)
            start = stop

    def finish(self):
        """Reject an incomplete tail even if its bytes would parse as JSON."""
        if self._finished:
            return None
        self._finished = True
        if self._buffer or self._oversized:
            self._line += 1
            details = {} if self._oversized else self._line_details(self._buffer)
            self._buffer.clear()
            return self._issue("unterminated JSONL line", details)
        return None

    def _line_details(self, line):
        return {"line_bytes": len(line), "line_sha256": sha256(line).hexdigest()}

    def _issue(self, reason, details=None):
        return self.event("source.error", "Codex JSONL record skipped", severity="warning",
                          details={"stdout_line": self._line, "reason": reason, **(details or {})})

    def _decode(self, line):
        details = {"stdout_line": self._line, **self._line_details(line)}
        if self._thread is not None:
            details["thread_id"] = self._thread
        try:
            source = decode_json(line, MAX_LINE_BYTES)
            if type(source) is not dict:
                raise EventError("expected a Codex JSONL object")
            kind = _string(source.get("type"))
            details["source_event"] = _private_excerpt(kind)
            if kind == "thread.started":
                return self._start_thread(source, details)
            if kind in _TURN:
                return self._apply_turn(source, kind, details)
            if kind in ("item.started", "item.updated", "item.completed"):
                return self._apply_item(_object(source, "type item")["item"], kind, details)
            if kind == "error":
                details["error"] = _private_excerpt(_object(source, "type message")["message"])
                return self.event("source.error", "Codex reported a stream error", details=details, severity="error")
            raise EventError("unsupported Codex JSONL event type")
        except EventError as error:
            return self._issue(str(error), details)

    def _start_thread(self, source, details):
        details["thread_id"] = _source_id(_object(source, "type thread_id")["thread_id"])
        if self._thread is not None:
            raise EventError("duplicate or conflicting thread start")
        self._thread = details["thread_id"]
        return self.event("session.started", "Codex thread started", details=details)

    def _apply_turn(self, source, kind, details):
        if kind == "turn.started":
            _object(source, "type")
            if self._thread is None or self._turn is not None:
                raise EventError("turn start out of order or duplicate")
            self._turn = "running"
        else:
            if self._turn != "running":
                raise EventError("turn outcome out of order or duplicate")
            if kind == "turn.failed":
                error = _object(_object(source, "type error")["error"], "message")
                details["error"] = _private_excerpt(error["message"])
            else:
                usage = _object(_object(source, "type usage")["usage"],
                                "input_tokens cached_input_tokens output_tokens reasoning_output_tokens",
                                "cache_write_input_tokens")
                for count in usage.values():
                    _integer(count, 64)
            details["unfinished_items"] = self.unfinished_items
            self._turn = kind.split(".")[1]
        normalized, summary = _TURN[kind]
        return self.event(normalized, summary, details=details, severity="error" if kind == "turn.failed" else "info")

    def _apply_item(self, item, kind, details):
        if type(item) is not dict:
            raise EventError("expected a Codex JSONL item")
        item_type = _string(item.get("type"))
        raw_id = _source_id(item.get("id"))
        details.update(item_type=_private_excerpt(item_type), item_id=raw_id)
        if item_type not in _ITEM_FIELDS:
            raise EventError("unsupported Codex JSONL item type")
        required, optional = _ITEM_FIELDS[item_type]
        _object(item, "type id " + required, optional)
        if item_type != "error" and self._turn != "running":
            raise EventError("item outside active turn")
        started, completed = kind == "item.started", kind == "item.completed"
        previous = self._items.get(raw_id)
        if previous:
            if previous.kind != item_type or previous.completed or started:
                raise EventError("conflicting, reordered or duplicate item lifecycle")
            if not completed and previous.fingerprint == details["line_sha256"]:
                raise EventError("duplicate item update")
        elif len(self._items) >= _MAX_ITEMS:
            raise EventError("Codex item tracking limit reached")
        if not started and not completed and (item_type != "todo_list" or previous is None):
            raise EventError("unsupported or unpaired item update")
        alias = previous.alias if previous else f"item-{len(self._items) + 1}"
        normalized, summary, severity = self._item_outcome(item, details, started, completed)
        seen_start = started or (previous is not None and previous.started)
        self._items[raw_id] = _Item(item_type, alias, seen_start, completed, details["line_sha256"])
        details["start_observed"] = seen_start
        correlation = {"command" if item_type == "command_execution" else "tool": alias}
        return self.event(normalized, f"{summary} [{alias}]", correlation=correlation,
                          details=details, severity=severity, private=item_type == "reasoning")

    def _item_outcome(self, item, details, started, completed):
        item_type = item["type"]
        if item_type == "todo_list":
            steps = _list(item["items"])
            for step in steps:
                _string(_object(step, "text completed")["text"])
                if type(step["completed"]) is not bool:
                    raise EventError("invalid Codex plan step")
            details["plan_steps"] = len(steps)
            details["plan_steps_completed"] = sum(step["completed"] for step in steps)
            return "plan.updated", "Codex plan snapshot recorded" if completed else "Codex plan updated", "info"
        if item_type in ("agent_message", "reasoning", "error"):
            if not completed:
                raise EventError("unexpected Codex message lifecycle")
            if item_type == "error":
                details["error"] = _private_excerpt(item["message"])
                return "source.error", "Codex reported a diagnostic", "warning"
            _string(item["text"])
            summary = "Codex agent message received" if item_type == "agent_message" else "Codex reasoning item omitted"
            return "agent.note", summary, "info"
        return self._tool_outcome(item, details, started)

    def _tool_outcome(self, item, details, started):
        item_type, status = item["type"], _string(item["status"])
        command = item_type == "command_execution"
        terminal = ("completed", "failed", "declined") if command else ("completed", "failed")
        if status not in (("in_progress",) if started else terminal):
            # The upstream reconciler can serialize an unfinished item at turn end.
            raise EventError("item status does not establish the reported lifecycle")
        details["item_status"] = status
        if command:
            _string(item["command"])
            _string(item["aggregated_output"])
            code = item["exit_code"]
            if code is not None:
                _integer(code, 32)
            details["exit_code"] = code
            if started:
                if code is not None:
                    raise EventError("in-progress command has an exit code")
                return "command.started", "Codex command started", "info"
            if status == "declined":
                return "command.completed", "Codex command declined", "warning"
            if status == "failed" or code not in (0, None):
                return "command.completed", "Codex command failed", "error"
            return "command.completed", "Codex command completion reported", "info"
        if item_type == "mcp_tool_call":
            _string(item["server"])
            _string(item["tool"])
            if item["result"] is not None:
                result = _object(item["result"], "content structured_content", "_meta")
                _list(result["content"])
            if item["error"] is not None:
                details["error"] = _private_excerpt(_object(item["error"], "message")["message"])
        elif item_type == "file_change":
            for change in _list(item["changes"]):
                _string(_object(change, "path kind")["path"])
                if change["kind"] not in ("add", "delete", "update"):
                    raise EventError("unsupported Codex file change kind")
        elif item_type == "collab_tool_call":
            self._collaboration_details(item, details)
        label = _TOOLS[item_type]
        if started:
            return "tool.started", f"{label} started", "info"
        if status == "failed":
            return "tool.failed", f"{label} failed", "error"
        return "tool.completed", f"{label} completed", "info"

    def _collaboration_details(self, item, details):
        if item["tool"] not in ("spawn_agent", "send_input", "wait", "close_agent"):
            raise EventError("unsupported Codex collaboration tool")
        if item["prompt"] is not None:
            _string(item["prompt"])
        details["sender_thread_id"] = _source_id(item["sender_thread_id"])
        receivers = [_source_id(value) for value in _list(item["receiver_thread_ids"])]
        details["receiver_thread_ids"] = receivers[:8]
        details["receiver_thread_count"] = len(receivers)
        states = item["agents_states"]
        if type(states) is not dict:
            raise EventError("invalid Codex collaboration state map")
        for thread_id, state in states.items():
            _source_id(thread_id)
            _object(state, "status message")
            if state["status"] not in ("pending_init", "running", "interrupted", "completed",
                                       "errored", "shutdown", "not_found"):
                raise EventError("unsupported Codex collaboration state")
            if state["message"] is not None:
                _string(state["message"])
