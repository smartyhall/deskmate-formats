"""Synthetic cases exercised by ``test_perf_harness``.

This module deliberately does not match the ``test_*.py`` discovery pattern, so
the cases are only executed by the harness tests that load them explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


class FastCase(unittest.TestCase):
    def test_immediate(self):
        self.assertTrue(True)


class SlowCase(unittest.TestCase):
    def setUp(self):
        time.sleep(0.05)

    def tearDown(self):
        time.sleep(0.05)

    def test_deliberate_delay(self):
        time.sleep(0.12)


class SpawnCase(unittest.TestCase):
    def test_spawns_one_interpreter(self):
        subprocess.run([sys.executable, "-c", "pass"], check=True,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)


class GitCase(unittest.TestCase):
    def test_spawns_named_git_subcommands(self):
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        with tempfile.TemporaryDirectory() as directory:
            quiet = {"cwd": directory, "stdin": subprocess.DEVNULL,
                     "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            subprocess.run(["git", "init", "-q", "-b", "main", "--object-format=sha1"],
                           check=True, **quiet)
            # Fails in an empty repository; the spawn is what is being counted.
            subprocess.run(["git", "rev-parse", "HEAD"], check=False, **quiet)


class FailureCase(unittest.TestCase):
    def test_reports_failure(self):
        self.fail("synthetic failure for the harness")


class BrokenSetupCase(unittest.TestCase):
    """A class fixture that fails: the error happens outside any test."""

    @classmethod
    def setUpClass(cls):
        raise RuntimeError("synthetic class fixture failure")

    def test_first(self):
        pass

    def test_second(self):
        pass


class SubtestFailureCase(unittest.TestCase):
    def test_subtests(self):
        for value in (1, 2):
            with self.subTest(value=value):
                if value == 2:
                    self.fail("synthetic subtest failure")


class SubtestErrorCase(unittest.TestCase):
    def test_subtests(self):
        with self.subTest(value=1):
            raise RuntimeError("synthetic subtest error")


class UntrackedMutationCase(unittest.TestCase):
    """Rewrites an untracked file mid-run, leaving its path and status alone."""

    def test_rewrites_the_untracked_file(self):
        target = Path(os.environ["DESKMATE_PERF_UNTRACKED"])
        target.write_text("VALUE = 2\n", encoding="utf-8")


class PathMessageCase(unittest.TestCase):
    def test_mentions_a_path(self):
        self.fail(f"could not open {Path.cwd() / 'private' / 'evidence.json'}")
