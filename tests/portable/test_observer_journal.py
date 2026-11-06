"""Failure injection for the private, local journal on Windows and POSIX."""

import errno
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from deskmate_formats.observer.events import EventError, MAX_RECORD_BYTES, encode_json
from deskmate_formats.observer.journal import JournalError, JournalLimits, publish_event, read_journal
from observatory_fixture import event, trace
from test_observer_events import record


class JournalTests(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(TemporaryDirectory())
        self.spool = Path(temporary) / "spool"
        self.journal = self.spool / "events.jsonl"

    def append_raw(self, data):
        with self.journal.open("ab") as stream:
            stream.write(data)

    def test_independent_publishers_and_replay_after_restart(self):
        self.assertEqual(read_journal(self.spool).records, ())
        self.assertFalse(self.spool.exists())
        for cursor, payload in enumerate(trace(), 1):
            receipt = publish_event(self.spool, payload)
            self.assertEqual(receipt.cursor, cursor)
        first = read_journal(self.spool)
        self.assertEqual(first, read_journal(self.spool))
        self.assertIsNone(read_journal(self.spool, unchanged=first.fingerprint))
        self.assertEqual([row["agent_id"] for row in first.records[:3]], ["alpha", "beta", "gamma"])
        original = self.journal.read_bytes()
        for payload, error in (
            (event(3, "turn.completed", "beta"), "duplicate"),
            (event(3, "turn.failed", "beta"), "conflicting"),
            (event(3), "out-of-order"),
            (event(6, agent_id="someone-else"), "identity changed"),
        ):
            with self.assertRaisesRegex(EventError, error):
                publish_event(self.spool, payload)
        self.assertEqual(self.journal.read_bytes(), original)

    def test_tail_is_hidden_and_repaired_only_before_a_valid_append(self):
        publish_event(self.spool, event())
        original = self.journal.read_bytes()
        tail = encode_json(record(event(2), 2))  # Even valid JSON needs its commit delimiter.
        self.append_raw(tail)
        replay = read_journal(self.spool)
        self.assertEqual((len(replay.records), replay.tail_bytes), (1, len(tail)))
        with self.assertRaises(EventError):
            publish_event(self.spool, event())
        self.assertEqual(self.journal.read_bytes(), original + tail)
        receipt = publish_event(self.spool, event(2, "turn.completed"))
        self.assertEqual((receipt.cursor, receipt.recovered_tail_bytes), (2, len(tail)))
        self.assertTrue(self.journal.read_bytes().startswith(original))
        recovered = read_journal(self.spool)
        self.assertEqual(recovered.tail_bytes, 0)
        self.assertEqual(recovered.records[-1]["type"], "turn.completed")

    def test_corrupt_complete_records_are_skipped_but_stop_appends(self):
        publish_event(self.spool, event())
        self.append_raw(b"malformed\n" + b"x" * (MAX_RECORD_BYTES * 3) + b"\n")
        self.append_raw(encode_json(record(event(4, agent="beta"), 4)) + b"\n")
        replay = read_journal(self.spool)
        self.assertEqual([row["cursor"] for row in replay.records], [1, 4])
        self.assertEqual((replay.corrupt_lines, replay.first_corrupt_line), (2, 2))
        original = self.journal.read_bytes()
        with self.assertRaisesRegex(JournalError, "corruption at line 2"):
            publish_event(self.spool, event(2))
        self.assertEqual(self.journal.read_bytes(), original)

    def test_bounded_retention_and_uncertain_flush(self):
        limits = JournalLimits(max_records=1)
        with patch("deskmate_formats.observer.journal.os.fsync", side_effect=OSError(errno.ENOSPC, "full")):
            with self.assertRaisesRegex(JournalError, "storage full; reconcile"):
                publish_event(self.spool, event(), limits=limits)
        replay = read_journal(self.spool, limits=limits)
        self.assertTrue(replay.at_capacity)
        self.assertEqual(replay.records[0]["cursor"], 1)
        with self.assertRaisesRegex(JournalError, "retention limit"):
            publish_event(self.spool, event(2), limits=limits)
        small_limits = JournalLimits(max_bytes=self.journal.stat().st_size - 1)
        self.assertTrue(read_journal(self.spool, limits=small_limits).capacity_exceeded)
        with self.assertRaisesRegex(JournalError, "retention limit"):
            publish_event(self.spool, event(2), limits=small_limits)

    def test_actual_cross_process_lock_and_forced_exit(self):
        publish_event(self.spool, event())
        ready = self.spool.parent / "ready"
        script = """
from pathlib import Path
import sys
from time import sleep
from deskmate_formats.observer._private_storage import journal_lock
with journal_lock(Path(sys.argv[1]), write=True):
    with (Path(sys.argv[1]) / 'events.jsonl').open('ab') as stream:
        stream.write(b'{"unfinished":')
        stream.flush()
    Path(sys.argv[2]).touch()
    sleep(30)
"""
        with subprocess.Popen([sys.executable, "-c", script, str(self.spool), str(ready)]) as child:
            try:
                deadline = monotonic() + 8
                while not ready.exists() and child.poll() is None and monotonic() < deadline:
                    sleep(0.025)
                self.assertTrue(ready.exists(), "synthetic writer did not acquire the lock")
                with self.assertRaisesRegex(JournalError, "busy"):
                    publish_event(self.spool, event(1, agent="beta"))
                with self.assertRaisesRegex(JournalError, "busy"):
                    read_journal(self.spool)
            finally:
                child.kill()
                child.wait(timeout=5)
        self.assertEqual(len(read_journal(self.spool).records), 1)
        receipt = publish_event(self.spool, event(1, agent="beta"))
        self.assertEqual((receipt.cursor, receipt.recovered_tail_bytes), (2, len(b'{"unfinished":')))

    def test_rejects_git_worktrees_non_private_directories_and_linked_files(self):
        worktree = self.spool.parent / "worktree"
        worktree.mkdir()
        (worktree / ".git").write_text("synthetic worktree marker")
        with self.assertRaisesRegex(JournalError, "private journal storage"):
            publish_event(worktree / "spool", event())
        self.assertFalse((worktree / "spool").exists())
        self.spool.mkdir(mode=0o755)
        with self.assertRaisesRegex(JournalError, "private journal storage"):
            publish_event(self.spool, event())
        self.spool.rmdir()
        publish_event(self.spool, event())
        os.link(self.journal, self.spool / "alias")
        with self.assertRaisesRegex(JournalError, "private journal storage"):
            read_journal(self.spool)
