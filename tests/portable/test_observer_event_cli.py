"""Exercise the standalone CLI across real process boundaries."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.observer.events import MAX_INPUT_BYTES, encode_json
from deskmate_formats.observer.journal import read_journal
from observatory_fixture import event


class PublisherTests(unittest.TestCase):
    def test_cli_argv_stdin_and_error_exit_codes(self):
        directory = Path(self.enterContext(TemporaryDirectory())) / "spool"
        env = {**os.environ, "DESKMATE_OBSERVER_JOURNAL": str(directory)}

        def cli(*args, data=None):
            return subprocess.run([sys.executable, "-m", "deskmate_formats.observer.event_cli", *args],
                                  input=data, capture_output=True, env=env, timeout=10)

        result = cli("--origin", "fixture-alpha", "--agent", "alpha", "--run", "run-alpha", "--seq", "1",
                     "--type", "milestone.completed", "--summary", "Synthetic milestone", "--machine", "synthetic-rsx")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["cursor"], 1)
        data = encode_json(event(2, "agent.note", source="explicit", details={"diagnostic": "synthetic-sentinel"}))
        result = cli("--json", data=data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["cursor"], 2)
        self.assertNotIn(b"synthetic-sentinel", result.stdout + result.stderr)
        for rejected in (data, data[:-3], b"x" * (MAX_INPUT_BYTES + 1)):
            result = cli("--json", data=rejected)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, b"")
            self.assertNotIn(b"synthetic-sentinel", result.stderr)
        full = cli("--json", "--journal-max-records", "2", data=encode_json(event(1, agent="beta")))
        self.assertEqual(full.returncode, 1)
        self.assertIn(b"retention limit", full.stderr)
        self.assertEqual([item["visibility"] for item in read_journal(directory).records], ["private", "observer"])
