"""Offline queue tests with actual Git ancestry and SQLite transactions."""

from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deskmate_formats.supervisor.task_manifest import TaskError
from deskmate_formats.supervisor.task_queue import DATABASE, QueueError, QueueUnresolved, TaskQueue, open_queue

from task_fixture import TASK_PATH, TaskRepo, manifest


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo = TaskRepo(self.root / "source")
        self.private = self.root / "queue"

    def create(self, capacity=10):
        with open_queue(self.private, source=self.repo.source(), capacity=capacity):
            pass

    def decide(self, queue, commit, *, path=TASK_PATH, decision="accepted"):
        candidate = queue.discover(commit, path)
        return queue.decide(commit, path, candidate.review_token, decision, "Reviewed synthetic task")

    def test_duplicate_preserves_original_receipt_and_provenance(self):
        commit = self.repo.commit(manifest())
        self.create()
        with open_queue(self.private) as queue:
            receipt, inserted = self.decide(queue, commit)
            self.assertTrue(inserted)
            self.assertEqual(receipt.candidate.source.commit, commit)
            self.assertEqual(receipt.state, "accepted")
            self.assertIsNotNone(receipt.resolved_at)
        new_commit = self.repo.commit()
        with open_queue(self.private) as queue:
            self.assertEqual(self.decide(queue, new_commit), (receipt, False))
            self.assertEqual(queue.list(), [receipt])
            with self.assertRaisesRegex(TaskError, "different outcome"):
                self.decide(queue, new_commit, decision="rejected")

    def test_conflicting_bytes_keys_and_revisions(self):
        self.create()
        commit = self.repo.commit(manifest())
        with open_queue(self.private) as queue:
            self.decide(queue, commit)
            for value, diagnostic in (
                (manifest(title="Tampered"), "bytes conflict"),
                (manifest(revision=2), "idempotency"),
                (manifest(revision=3, idempotency_key="sample-3"), "increase by one"),
            ):
                with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(TaskError, diagnostic):
                    self.decide(queue, self.repo.commit(value))
            commit = self.repo.commit(manifest(revision=2, idempotency_key="sample-2"))
            receipt, _ = self.decide(queue, commit, decision="rejected")
            self.assertEqual(receipt.state, "rejected")
            self.assertEqual(queue.counts(), {"accepted": 1, "rejected": 1, "unresolved": 0, "abandoned": 0})

    def test_cycles_and_missing_dependencies_cannot_enter_accepted_set(self):
        self.create()
        other_path = "ops/tasks/other.json"
        self.repo.commit(manifest(dependencies=[{"id": "other", "revision": 1}]))
        cyclic = self.repo.commit(manifest(id="other", idempotency_key="other-1", dependencies=[
            {"id": "sample", "revision": 1},
        ]), path=other_path)
        with open_queue(self.private) as queue:
            for path in (TASK_PATH, other_path):
                with self.subTest(path=path), self.assertRaisesRegex(TaskError, "prior acceptance"):
                    self.decide(queue, cyclic, path=path)
            self.assertEqual(queue.list(), [])
            acyclic = self.repo.commit(manifest())
            self.decide(queue, acyclic)
            receipt, _ = self.decide(queue, acyclic, path=other_path)
            self.assertEqual(receipt.state, "accepted")

    def test_capacity_expiry_token_and_decision_validation(self):
        self.create(capacity=1)
        expired = self.repo.commit(manifest(expires_at="2000-01-01T00:00:00Z"))
        with open_queue(self.private) as queue:
            token = queue.discover(expired, TASK_PATH).review_token
            for decision, reason, supplied, diagnostic in (
                ("dispatch", "reviewed", token, "invalid operator decision"),
                ("accepted", "\x1b", token, "operator reason"),
                ("accepted", "reviewed", "0" * 64, "review token"),
                ("accepted", "reviewed", token, "expired"),
            ):
                with self.subTest(diagnostic=diagnostic), self.assertRaisesRegex(TaskError, diagnostic):
                    queue.decide(expired, TASK_PATH, supplied, decision, reason)
            self.assertEqual(queue.list(), [])
            self.decide(queue, expired, decision="rejected")
            new = self.repo.commit(manifest(revision=2, idempotency_key="sample-2"))
            with self.assertRaisesRegex(TaskError, "record limit"):
                self.decide(queue, new)
            self.assertEqual(len(queue.list()), 1)

    def test_force_move_behind_recorded_commit_and_lock_contention(self):
        self.create()
        first = self.repo.commit(manifest())
        with open_queue(self.private) as queue:
            with self.assertRaisesRegex(QueueError, "busy"):
                with open_queue(self.private):
                    self.fail("concurrent owner reached the queue")
            self.decide(queue, first)
        self.repo.git("update-ref", "refs/heads/main", self.repo.anchor)
        second = self.repo.commit(manifest(title="Sibling history"))
        with open_queue(self.private) as queue:
            with self.assertRaisesRegex(TaskError, "diverges"):
                queue.discover(second, TASK_PATH)
            self.assertEqual(queue.get("sample", 1).candidate.source.commit, first)

    def test_error_mid_transaction_is_unresolved_and_blocks_replay(self):
        self.create()
        commit = self.repo.commit(manifest())
        def fail_after_update(queue, sequence, state):
            with queue._write():
                queue._db.execute("UPDATE tasks SET state=?, resolved_at=prepared_at WHERE sequence=?",
                                  (state, sequence))
                raise sqlite3.OperationalError("synthetic I/O failure before commit")

        with open_queue(self.private) as queue, patch.object(TaskQueue, "_complete", fail_after_update):
            with self.assertRaisesRegex(QueueUnresolved, "outcome unknown"):
                self.decide(queue, commit)
            with self.assertRaises(QueueUnresolved):
                queue.list()
        with open_queue(self.private) as queue:
            receipt = queue.get("sample", 1)
            self.assertEqual(receipt.state, "unresolved")
            self.assertIsNone(receipt.resolved_at)
            with self.assertRaisesRegex(QueueUnresolved, "requires operator"):
                self.decide(queue, commit)
            with self.assertRaisesRegex(TaskError, "review token"):
                queue.abandon("sample", 1, "0" * 64, "Reviewed crash")
            abandoned = queue.abandon("sample", 1, receipt.candidate.review_token, "Reviewed crash")
            self.assertEqual((abandoned.state, abandoned.requested, abandoned.recovery_reason),
                             ("abandoned", "accepted", "Reviewed crash"))
            with self.assertRaisesRegex(TaskError, "different outcome"):
                self.decide(queue, commit)

    def test_private_directory_and_corruption_fail_closed(self):
        with self.assertRaises(QueueError):
            with open_queue(self.repo.path / "queue", source=self.repo.source()):
                self.fail("Git working tree admitted")
        self.create()
        with self.assertRaisesRegex(QueueError, "already exists"):
            with open_queue(self.private, source=self.repo.source()):
                self.fail("queue reinitialized")
        (self.private / DATABASE).write_bytes(b"corrupt")
        with self.assertRaisesRegex(QueueError, "header"):
            with open_queue(self.private):
                self.fail("corrupt queue admitted")
