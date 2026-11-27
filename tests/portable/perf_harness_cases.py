"""Synthetic cases exercised by ``test_perf_harness``.

This module deliberately does not match the ``test_*.py`` discovery pattern, so
the cases are only executed by the harness tests that load them explicitly.
"""

from __future__ import annotations

import subprocess
import sys
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


class FailureCase(unittest.TestCase):
    def test_reports_failure(self):
        self.fail("synthetic failure for the harness")
