from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


SPEC = importlib.util.spec_from_file_location(
    "codex_usage", Path(__file__).resolve().parents[2] / "tools/experimental/codex_usage.py"
)
usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(usage)


class UsageTests(unittest.TestCase):
    def test_usage_import(self):
        private = TemporaryDirectory()
        self.addCleanup(private.cleanup)
        tmp_path = Path(private.name)
        root = tmp_path / "project"
        live = tmp_path / "sessions"
        archive = tmp_path / "archived_sessions"
        for directory in (root, live, archive):
            directory.mkdir()

        def rec(kind, payload, second=0):
            return json.dumps({"type": kind, "payload": payload,
                               "timestamp": f"2026-01-01T00:00:{second:02d}Z"})

        def token(total, used, reset, second, model_shape=False):
            info = ({"total": {"totalTokens": total}, "last": {"inputTokens": 2}}
                    if model_shape else {"total_token_usage": {"total_tokens": total}})
            return rec("event_msg", {
                "type": "token_count", "info": info,
                "rate_limits": {
                    "primary": {"window_minutes": 10080, "remaining_percent": 3},
                    "secondary": {"windowDurationMins": 300, "usedPercent": used, "resetsAt": reset},
                    "credits": {"private": "do not export"},
                },
            }, second)

        meta = rec("session_meta", {"id": "private-id", "cwd": str(root)})
        context = rec("turn_context", {"model": "gpt-6.2-sol", "effort": "high"})
        before = token(30, 15, 1767225700, 1)
        repeated = token(30, 15, 1767225700, 2)
        after = token(3, 1, 1767240000, 3, True)
        missing = rec("event_msg", {"type": "token_count"}, 4)
        (live / "rollout-project.jsonl").write_text(
            "\n".join((meta, context, before, "{broken", repeated, after, missing, "{partial")),
            encoding="utf-8",
        )
        (archive / "rollout-copy.jsonl").write_text("\n".join((meta, context, before, "")), encoding="utf-8")
        unrelated = rec("session_meta", {"id": "unrelated-id", "cwd": str(tmp_path / "project-other")})
        (live / "rollout-other.jsonl").write_text("\n".join((unrelated, context, after, "")), encoding="utf-8")
        sessions, index, coverage = usage.collect([tmp_path], [root], b"key")
        assert len(sessions) == 1
        assert len(next(iter(index.values()))) == 2
        assert coverage["duplicate_token_records"] == 1
        assert coverage["malformed_lines"] == coverage["incomplete_lines"] == 1
        assert "private" not in usage.encode(sessions)
        events = next(iter(sessions.values()))
        assert [event["counter_state"] for event in events] == ["first", "repeated", "decreased", "missing"]
        assert events[0]["windows"][10080]["used_percent"] == 97
        assert events[2]["windows"][300]["boundary"] == "epoch_advanced"
        assert events[2]["reported_last"]["input"] == 2
        assert events[2]["effort"] == "high"
        assert events[3]["windows"][300]["status"] == "missing"
        history = usage.compact_history(sessions)
        packed = dict(zip(history["columns"], next(iter(history["sessions"].values()))[0]))
        assert packed["300"][0] == 15
        assert packed["cumulative"][-1] == 30


    def test_window_validation_and_staleness(self):
        at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        readings = usage.windows({
            "primary": {"window_minutes": 300, "used_percent": 12, "resets_at": 1},
            "secondary": {"window_minutes": 10080, "used_percent": True},
        }, at)
        assert readings[300]["status"] == "expired"
        assert readings[10080]["status"] == "missing"
        event = {"kind": "token_count", "measured_at": "2025-12-31T23:00:00+00:00",
                 "windows": {300: {"status": "observed", "reset_epoch": None}}}
        assert usage.checkpoint({"opaque": [event]}, at, 900)["windows"][300]["status"] == "stale"
