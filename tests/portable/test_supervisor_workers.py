"""Worker capability negotiation and one real end-to-end deterministic task."""

from hashlib import sha256
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.supervisor import workers


class WorkerCapabilityTests(unittest.TestCase):
    def test_catalog_describes_three_distinct_worker_classes(self):
        kinds = {descriptor.kind for descriptor in workers.catalog()}
        self.assertEqual(kinds, {"deterministic", "codex", "freebuff"})
        freebuff = workers.freebuff_descriptor()
        self.assertEqual(freebuff.capabilities, frozenset())
        self.assertTrue(freebuff.limitations)
        with self.assertRaises(workers.WorkerUnsupported):
            freebuff.require("dispatch")

    def test_unsupported_and_unavailable_operations_do_not_pretend(self):
        with self.assertRaises(workers.WorkerUnsupported):
            workers.FreebuffWorker().prepare({})
        self.assertEqual(workers.FreebuffWorker().health().state, "unknown")
        codex = workers.CodexWorker()
        self.assertFalse(codex.health().available())
        with self.assertRaises(workers.WorkerUnavailable):
            codex.prepare({})
        self.assertTrue(codex.descriptor.supports("steering"))
        with self.assertRaises(workers.WorkerUnsupported):
            workers.DeterministicWorker().descriptor.require("steering")

    def test_eligibility_filters_by_advertised_capability(self):
        workers_ = [workers.DeterministicWorker(), workers.CodexWorker(),
                    workers.FreebuffWorker()]
        selected = workers.eligible(workers_, {"dispatch", "recovery"})
        # Codex advertises the protocol capability; availability is a separate
        # question answered by health(), not by erasing the capability.
        self.assertEqual([item.descriptor.kind for item in selected],
                         ["deterministic", "codex"])
        self.assertEqual(workers.eligible(workers_, set()), workers_)
        with self.assertRaises(workers.WorkerUnsupported):
            workers.eligible(workers_, {"teleport"})

    def test_synthetic_worker_requires_its_scripted_authorization(self):
        worker = workers.SyntheticWorker()
        attempt = worker.prepare({"procedure": "synthetic"})
        with self.assertRaises(workers.WorkerUnsupported):
            worker.dispatch(attempt, authorization="wrong")
        result = worker.dispatch(attempt, authorization="synthetic-authorization")
        self.assertTrue(result.completed())
        self.assertEqual(result.worker_id, worker.descriptor.worker_id)


class DeterministicWorkerIntegrationTests(unittest.TestCase):
    def test_real_procedure_runs_through_the_worker_interface(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        worktree = root / "worktree"
        worktree.mkdir()
        payload = b"deskmate synthetic fixture\n"
        (worktree / "sample.txt").write_bytes(payload)
        worker = workers.DeterministicWorker()
        self.assertTrue(worker.health().available())
        attempt = worker.prepare({
            "directory": root / "attempt",
            "campaign": "synthetic-campaign",
            "procedure": "hash-files",
            "arguments": {"paths": ["sample.txt"]},
            "working_directory": str(worktree),
        })
        result = worker.dispatch(attempt, authorization=attempt.plan_sha256)
        self.assertEqual((result.state, result.exit_status), ("completed", 0))
        status = worker.status(attempt)
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["outcome"]["structured_result"]["files"],
                         [{"path": "sample.txt", "size": len(payload),
                           "sha256": sha256(payload).hexdigest()}])
        # A deterministic worker reports that no inference occurred, not zero cost.
        usage = worker.usage()
        self.assertEqual(usage[0]["metric"], "model_inference")
        self.assertTrue(usage[0]["known"])

    def test_failing_procedure_reports_a_structured_failure(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        worktree = root / "worktree"
        worktree.mkdir()
        worker = workers.DeterministicWorker()
        attempt = worker.prepare({
            "directory": root / "attempt",
            "campaign": "synthetic-campaign",
            "procedure": "hash-files",
            "arguments": {"paths": ["missing.txt"]},
            "working_directory": str(worktree),
        })
        result = worker.dispatch(attempt, authorization=attempt.plan_sha256)
        self.assertEqual((result.state, result.exit_status), ("failed", 1))
        status = worker.status(attempt)
        self.assertIn("not a regular file", status["outcome"]["stderr"]["excerpt"])


if __name__ == "__main__":
    unittest.main()
