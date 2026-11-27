"""Regression: cloning the shared task template must keep clones independent.

``TaskRepo`` builds one template repository per process and copies it per test.
That trades a repeated fixed cost for a shared origin, so it is only sound while
a clone cannot write back into the template or into another clone.  These tests
mutate one clone as destructively as a test might and assert the others and the
template are unaffected.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from deskmate_formats.supervisor.task_git import TaskError
from task_fixture import TaskRepo, manifest


class TaskFixtureIsolationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="deskmate-fixture-isolation-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_a_commit_in_one_clone_does_not_reach_another(self):
        first = TaskRepo(self.root / "first")
        second = TaskRepo(self.root / "second")
        self.assertEqual(first.head(), second.head())

        advanced = first.commit(manifest(title="Mutated in one clone only"))
        self.assertNotEqual(advanced, first.anchor)
        self.assertEqual(second.head(), second.anchor)
        self.assertEqual(second.git("status", "--porcelain"), b"")
        self.assertEqual(second.git("rev-parse", "HEAD").decode("ascii").strip(),
                         second.anchor)

    def test_the_template_still_builds_clean_clones_after_mutation(self):
        first = TaskRepo(self.root / "first")
        first.commit(manifest(title="Mutated in one clone only"))

        third = TaskRepo(self.root / "third")
        self.assertEqual(third.head(), third.anchor)
        self.assertEqual(third.git("status", "--porcelain"), b"")
        third.git("cat-file", "-e", third.anchor)

    def test_each_clone_is_a_trusted_source_for_its_own_history(self):
        # The template is only a build source: every clone is independently
        # verifiable by the Supervisor's source-identity check, and a commit
        # made in one clone is not history in another.
        first = TaskRepo(self.root / "first")
        second = TaskRepo(self.root / "second")
        first.source().verify()
        advanced = first.commit(manifest(title="Mutated in one clone only"))
        first.source(anchor=advanced).verify()
        with self.assertRaises(TaskError):
            second.source(anchor=advanced).verify()

    def test_removing_one_clone_object_store_leaves_others_intact(self):
        first = TaskRepo(self.root / "first")
        second = TaskRepo(self.root / "second")

        # A clone owns its objects: destroying them damages only that clone.
        shutil.rmtree(first.path / ".git" / "objects", ignore_errors=True)

        self.assertEqual(second.head(), second.anchor)
        second.git("cat-file", "-e", second.anchor)
        fresh = TaskRepo(self.root / "fresh")
        self.assertEqual(fresh.head(), second.anchor)


if __name__ == "__main__":
    unittest.main()
