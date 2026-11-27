"""Versioned deterministic tasks: validated intake, trusted acceptance, real execution."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.supervisor import deterministic, task_execution
from deskmate_formats.supervisor.task_manifest import TaskError, validate_manifest
from deskmate_formats.supervisor.task_queue import open_queue

from task_fixture import TASK_PATH, TaskRepo


def manifest(**changes):
    return {
        "schema_version": 3, "id": "sample", "revision": 1, "idempotency_key": "sample-1",
        "title": "Hash a synthetic fixture", "description": "Hash one tracked fixture file.",
        "category": "verification", "profile": "offline", "resources": ["source-read"],
        "dependencies": [],
        "deterministic": {"procedure": "hash-files", "arguments": {"paths": ["fixture.txt"]}},
    } | changes


class DeterministicManifestTests(unittest.TestCase):
    def test_valid_deterministic_manifest_is_accepted(self):
        value = validate_manifest(json.dumps(manifest()).encode())
        self.assertEqual(value["deterministic"]["procedure"], "hash-files")

    def test_invalid_deterministic_manifests_are_refused(self):
        cases = [
            manifest(deterministic={"procedure": "shell", "arguments": {}}),
            manifest(deterministic={"procedure": "hash-files", "arguments": {"paths": ["../x"]}}),
            manifest(resources=["portable-tests"]),
            manifest(deterministic={"procedure": "hash-files"}),
            manifest(development={"source_revision": "a" * 40}),
            {key: value for key, value in manifest().items() if key != "deterministic"},
            manifest(deterministic={"procedure": "repository-audit", "arguments": {},
                                    "command": "echo pwned"}),
        ]
        for case in cases:
            with self.subTest(case=sorted(case)), self.assertRaises(TaskError):
                validate_manifest(json.dumps(case).encode())

    def test_a_deterministic_task_cannot_be_rendered_as_a_model_prompt(self):
        with self.assertRaises(TaskError):
            task_execution.task_prompt({"class": "deterministic-v1",
                                        "manifest_utf8": json.dumps(manifest()),
                                        "documents": []})


class TrustedDeterministicTaskTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo = TaskRepo(self.root / "repo")
        # The procedure runs against a real working tree, not only Git objects.
        (self.repo.path / "fixture.txt").write_bytes(b"synthetic fixture\n")
        self.repo.git("add", "fixture.txt")
        self.commit = self.repo.commit(manifest())
        self.queue = self.root / "queue"
        self.source = self.repo.source()

    def initialize(self, *, accept=True):
        with open_queue(self.queue, source=self.source):
            pass
        with open_queue(self.queue) as queue:
            candidate = queue.discover(self.commit, TASK_PATH)
            row = None
            if accept:
                row, created = queue.decide(self.commit, TASK_PATH, candidate.review_token,
                                            "accepted", "Synthetic acceptance")
                self.assertTrue(created)
        return candidate, row

    def test_unaccepted_revision_cannot_be_prepared(self):
        candidate, _ = self.initialize(accept=False)
        with open_queue(self.queue) as queue:
            with self.assertRaisesRegex(deterministic.DeterministicError,
                                        "accepted revision required"):
                deterministic.accepted(queue, "sample", 1, candidate.review_token)

    def test_wrong_review_token_is_refused(self):
        self.initialize()
        with open_queue(self.queue) as queue:
            with self.assertRaises(deterministic.DeterministicError):
                deterministic.accepted(queue, "sample", 1, "0" * 64)

    def test_accepted_task_runs_a_real_procedure_end_to_end(self):
        candidate, row = self.initialize()
        with open_queue(self.queue) as queue:
            binding = deterministic.accepted(queue, "sample", 1, candidate.review_token)
            context = queue.execution_context(row.candidate)
        self.assertEqual(binding["procedure"], "hash-files")
        self.assertEqual(binding["source"]["commit"], self.commit)
        self.assertEqual(context["class"], "deterministic-v1")

        state = self.root / "attempt"
        attempt = deterministic.prepare(state, campaign="synthetic-campaign",
                                        procedure=binding["procedure"],
                                        arguments=binding["arguments"],
                                        working_directory=str(self.repo.path),
                                        source_commit=binding["source"]["commit"])
        outcome = deterministic.run(state, authorization=attempt.plan_sha256)
        self.assertEqual(outcome["state"], "completed", outcome["stderr"]["excerpt"])
        payload = b"synthetic fixture\n"
        self.assertEqual(outcome["structured_result"]["files"],
                         [{"path": "fixture.txt", "size": len(payload),
                           "sha256": sha256(payload).hexdigest()}])
        self.assertEqual(outcome["source_revision_before"], self.commit)
        self.assertEqual(outcome["source_revision_after"], self.commit)

    def test_superseded_revision_blocks_dispatch(self):
        candidate, _ = self.initialize()
        superseded = self.repo.commit(manifest(revision=2, idempotency_key="sample-2",
                                               title="Second revision"))
        with open_queue(self.queue) as queue:
            token = queue.discover(superseded, TASK_PATH).review_token
            queue.decide(superseded, TASK_PATH, token, "accepted", "Second acceptance")
            with self.assertRaisesRegex(deterministic.DeterministicError, "superseded"):
                deterministic.accepted(queue, "sample", 1, candidate.review_token)


if __name__ == "__main__":
    unittest.main()
