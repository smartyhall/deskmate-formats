"""Contract and deterministic ordering checks without a running collector."""

import unittest

from deskmate_formats.observer.events import (
    EventError, IngestionOrder, MAX_INPUT_BYTES, decode_json, decode_record, encode_json,
    envelope, normalize_event,
)
from observatory_fixture import event, trace


def record(payload, cursor):
    return envelope(normalize_event(payload), cursor, "2026-11-06T14:00:00Z", cursor * 100)


class EventTests(unittest.TestCase):
    def test_validation_and_byte_bounds(self):
        for fields in (
            {"schema_version": True}, {"schema_version": 2}, {"source_sequence": -1},
            {"source_sequence": 2**53}, {"agent_id": "../private"}, {"type": ["agent.note"]},
            {"type": "thinking"}, {"severity": "ok"}, {"summary": "x" * 241},
            {"summary": "\ud800"}, {"summary": "newline\ntext"}, {"visibility": "full"},
            {"machine_ids": [["x"]]}, {"machine_ids": ["id", "id"]},
            {"type": "approval.requested"}, {"details": {"value": float("inf")}},
            {"details": {"value": [0] * 33}}, {"details": {str(i): "😀" * 1024 for i in range(3)}},
            {"source_time_utc": "2026-02-30T00:00:00Z"}, {"source_time_utc": "2026-11-06"},
            {"cursor": 9}, {"ingested_at_utc": "2026-11-06T00:00:00Z"},
        ):
            with self.subTest(field=next(iter(fields))), self.assertRaises(EventError):
                normalize_event(event(**fields))
        for raw in (b'{"x":1,"x":2}', b'{"x":', b'{"x":"\xff"}', b' ' * (MAX_INPUT_BYTES + 1),
                    b'[' * 2000 + b']' * 2000):
            with self.assertRaises(EventError):
                normalize_event(decode_json(raw))
        self.assertEqual(normalize_event(event(visibility="private"))["visibility"], "private")

    def test_deterministic_replay_ignores_upstream_time(self):
        def replay():
            order = IngestionOrder()
            accepted = []
            for cursor, payload in enumerate(trace(), 1):
                encoded = encode_json(record(payload, cursor)) + b"\n"
                decoded = decode_record(encoded)
                order.accept(decoded)
                accepted.append(decoded)
            self.assertEqual(order.cursor, len(trace()))
            return accepted

        first = replay()
        self.assertEqual(first, replay())
        self.assertGreater(first[0]["source_time_utc"], first[1]["source_time_utc"])
        self.assertLess(first[0]["cursor"], first[1]["cursor"])
        self.assertEqual([entry["machine_ids"] for entry in first[:3]],
                         [["synthetic-rsx"], ["synthetic-at"], []])
        with self.assertRaisesRegex(EventError, "incomplete"):
            decode_record(encode_json(first[0]))

    def test_rejections_leave_order_untouched(self):
        order = IngestionOrder()
        order.accept(record(event(2), 1))
        for payload, reason in (
            (event(2), "duplicate"), (event(2, summary="Conflict"), "conflicting"),
            (event(1), "out-of-order"), (event(3, run_id="different"), "identity changed"),
        ):
            with self.assertRaisesRegex(EventError, reason):
                order.accept(record(payload, 2))
            self.assertEqual(order.cursor, 1)
        with self.assertRaisesRegex(EventError, "cursor"):
            order.accept(record(event(3), 1))
        order.accept(record(event(3), 2))
        self.assertEqual(order.cursor, 2)
