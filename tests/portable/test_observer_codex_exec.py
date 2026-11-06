"""Offline schema, ordering and privacy checks for the Codex exec adapter."""

from pathlib import Path
import unittest

from deskmate_formats.observer.codex_exec import MAX_LINE_BYTES, SUPPORTED_VERSION, CodexExecAdapter
from deskmate_formats.observer.events import EventError, normalize_event

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex-exec-0.166.0"


def adapter(**kwargs):
    return CodexExecAdapter(SUPPORTED_VERSION, run_id="synthetic-run", **kwargs)


class CodexExecTests(unittest.TestCase):
    def replay(self, name):
        source = adapter(visibility="observer")
        raw = (FIXTURES / name).read_bytes()
        records = []
        for start in range(0, len(raw), 17):
            records.extend(map(normalize_event, source.feed(raw[start:start + 17])))
        self.assertIsNone(source.finish())
        self.assertEqual([event["details"]["stdout_line"] for event in records],
                         list(range(1, len(records) + 1)))
        self.assertEqual([event["source_sequence"] for event in records], list(range(1, len(records) + 1)))
        return source, records

    def test_success_and_private_source_identity(self):
        source, records = self.replay("success.jsonl")
        self.assertEqual([event["type"] for event in records], [
            "session.started", "turn.started", "plan.updated", "command.started", "tool.started",
            "command.completed", "tool.completed", "tool.completed", "plan.updated", "agent.note",
            "agent.note", "plan.updated", "turn.completed",
        ])
        self.assertEqual(source.turn_state, "completed")
        self.assertEqual(source.unfinished_items, 0)
        self.assertEqual(records[1]["correlation"], {"session": "session-1", "turn": "turn-1"})
        self.assertEqual(records[3]["correlation"], records[5]["correlation"])
        self.assertEqual(records[4]["correlation"], records[6]["correlation"])
        self.assertEqual(records[3]["details"]["item_id"], "item_1")
        self.assertEqual(records[3]["details"]["thread_id"], records[0]["details"]["thread_id"])
        self.assertFalse(records[7]["details"]["start_observed"])
        self.assertEqual(records[10]["visibility"], "private")
        self.assertNotIn("private-", repr(records))

    def test_command_and_turn_failures_are_separate(self):
        source, records = self.replay("failure.jsonl")
        self.assertEqual(source.turn_state, "failed")
        self.assertEqual(records[3]["type"], "command.completed")
        self.assertEqual(records[3]["severity"], "error")
        self.assertEqual(records[3]["details"]["exit_code"], 7)
        self.assertEqual(records[4]["details"]["item_status"], "declined")
        self.assertFalse(records[4]["details"]["start_observed"])
        self.assertEqual(records[5]["type"], "source.error")
        self.assertIn("private-error-marker", records[5]["details"]["error"])
        self.assertNotIn("private-error-marker", records[5]["summary"])
        self.assertEqual(records[6]["type"], "turn.failed")

    def test_unknown_approval_and_corrupt_records_cannot_invent_progress(self):
        source, records = self.replay("anomalies.jsonl")
        valid = [event["type"] for event in records if event["type"] != "source.error"]
        self.assertEqual(valid, ["session.started", "turn.started", "tool.failed", "command.started"])
        self.assertEqual((source.turn_state, source.unfinished_items), ("running", 1))
        self.assertEqual(records[5]["details"]["source_event"], "approval.requested")
        self.assertEqual(records[5]["details"]["reason"], "unsupported Codex JSONL event type")
        self.assertEqual(records[8]["details"]["reason"], "duplicate JSON member")
        self.assertEqual(records[13]["details"]["reason"], "item status does not establish the reported lifecycle")
        self.assertEqual(records[-1]["details"]["reason"], "unsupported Codex JSONL event type")

    def test_line_framing_recovery_and_version_gate(self):
        with self.assertRaisesRegex(EventError, "unsupported Codex exec version"):
            CodexExecAdapter("0.167.0", run_id="other")
        source = adapter()
        events = list(source.feed(b"x" * MAX_LINE_BYTES))
        self.assertEqual(events, [])
        chunk = b'\n\xff\n{"type":"error","message":"fixed"}\r\n{"type":"turn.started"}'
        records = list(source.feed(chunk))
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["details"]["reason"], "oversized JSONL line")
        self.assertEqual(records[1]["details"]["reason"], "invalid UTF-8 JSON")
        self.assertEqual(records[2]["details"]["error"], "fixed")
        self.assertEqual(records[2]["visibility"], "private")
        tail = source.finish()
        self.assertEqual(tail["details"]["reason"], "unterminated JSONL line")
        self.assertEqual(tail["details"]["stdout_line"], 4)
        self.assertIsNone(source.turn_state)
        self.assertIsNone(source.finish())
