"""Exercise task validation and real, local Git objects."""

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deskmate_formats.supervisor.task_manifest import (
    MAX_MANIFEST_BYTES, TaskError, canonical_manifest, validate_manifest,
)
from task_fixture import REPOSITORY, TASK_PATH, TaskRepo, manifest


class ManifestTests(unittest.TestCase):
    def test_strict_and_deterministic(self):
        normal = manifest()
        self.assertEqual(canonical_manifest(json.dumps(normal).encode()),
                         canonical_manifest(json.dumps(normal, sort_keys=True, indent=2).encode()))
        invalid = [
            b'{"id":"a","id":"b"}', b"\xff", b" " * (MAX_MANIFEST_BYTES + 1),
            b'{"revision":NaN}', b"[" * 1500 + b"]" * 1500,
        ]
        for changes in (
            {"schema_version": True}, {"schema_version": 2}, {"revision": True},
            {"id": "../x"}, {"idempotency_key": "bad key"}, {"title": "\x1b[31m"},
            {"description": "x" * 2049}, {"description": "\ud800"}, {"command": "echo x"},
            {"env": {}}, {"approval_policy": "always"}, {"profile": "unrestricted"},
            {"resources": ["emulator"]}, {"resources": ["source-read", "source-read"]},
            {"dependencies": [{"id": "sample", "revision": 2}]},
            {"dependencies": [{"id": "other", "revision": True}]},
            {"expires_at": "2026-02-30T00:00:00Z"},
            {"instructions": [{"path": "docs/../evil.md", "sha256": "a" * 64}]},
            {"instructions": [{"path": "docs/aux.md", "sha256": "a" * 64}]},
        ):
            invalid.append(json.dumps(manifest(**changes)).encode())
        for index, data in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(TaskError):
                validate_manifest(data)


class GitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = TaskRepo(Path(temp.name) / "git")

    def test_pinned_bytes_and_instruction_digest(self):
        raw = json.dumps(manifest(instructions=[{
            "path": "docs/instructions.md", "sha256": sha256(b"reviewed").hexdigest(),
        }])).encode()
        self.repo.stage("docs/instructions.md", b"reviewed")
        blob = self.repo.stage(TASK_PATH, raw)
        commit = self.repo.commit()
        with patch.dict("os.environ", {"GIT_DIR": "bogus", "GIT_NAMESPACE": "bogus"}):
            candidate = self.repo.source().discover(commit, TASK_PATH)
        self.assertEqual(candidate.raw, raw)
        self.assertEqual(candidate.source.blob, blob)
        self.assertEqual(candidate.source.commit, commit)
        self.assertEqual(candidate.source.repository, REPOSITORY)
        self.assertEqual(candidate.source.sha256, sha256(raw).hexdigest())
        self.repo.stage("docs/instructions.md", b"changed")
        with self.assertRaisesRegex(TaskError, "digest differs"):
            self.repo.source().discover(self.repo.commit(), TASK_PATH)

    def test_reject_untrusted_branch_and_origin(self):
        commit = self.repo.commit(manifest())
        self.repo.git("branch", "untrusted")
        self.repo.git("update-ref", "refs/heads/main", self.repo.anchor)
        with self.assertRaisesRegex(TaskError, "branch tip"):
            self.repo.source().discover(commit, TASK_PATH)
        self.repo.git("symbolic-ref", "refs/heads/main", "refs/heads/untrusted")
        with self.assertRaisesRegex(TaskError, "direct branch"):
            self.repo.source().discover(commit, TASK_PATH)
        self.repo.git("config", "--add", "remote.origin.url", REPOSITORY)
        with self.assertRaisesRegex(TaskError, "ambiguous"):
            self.repo.source().discover(commit, TASK_PATH)
        self.repo.git("config", "--replace-all", "remote.origin.url",
                      "https://example.invalid/lab/substitute.git")
        with self.assertRaisesRegex(TaskError, "differs"):
            self.repo.source().discover(commit, TASK_PATH)

    def test_reject_force_moved_branch_and_abbreviated_hash(self):
        first = self.repo.commit(manifest())
        self.repo.git("update-ref", "refs/heads/main", self.repo.anchor)
        second = self.repo.commit(manifest(title="Sibling history"))
        source = self.repo.source()
        with self.assertRaisesRegex(TaskError, "diverges"):
            source.discover(second, TASK_PATH, previous=first)
        with self.assertRaisesRegex(TaskError, "diverges"):
            self.repo.source(anchor=first).discover(second, TASK_PATH)
        with self.assertRaisesRegex(TaskError, "full Git object"):
            source.discover(second[:10], TASK_PATH)

    def test_unsafe_paths_blob_modes_and_oversize(self):
        source = self.repo.source()
        for path in ("../ops/tasks/sample.json", "ops/tasks//sample.json", "ops/tasks/SAMPLE.json",
                     "ops/tasks/sample.json:stream", "ops/tasks/aux.json"):
            with self.subTest(path=path), self.assertRaises(TaskError):
                source.discover(self.repo.anchor, path)
        for mode in ("120000", "100755"):
            with self.subTest(mode=mode), self.assertRaisesRegex(TaskError, "regular"):
                source.discover(self.repo.commit(manifest(), mode=mode), TASK_PATH)
        with self.assertRaisesRegex(TaskError, "byte limit"):
            source.discover(self.repo.commit(b" " * (MAX_MANIFEST_BYTES + 1)), TASK_PATH)
        with self.assertRaisesRegex(TaskError, "canonical"):
            source.discover(self.repo.commit(manifest(id="other")), TASK_PATH)
