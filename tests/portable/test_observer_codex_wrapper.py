"""Exercise the opted-in child wrapper with local subprocesses only."""

from io import BytesIO, StringIO
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from codex_child_fixture import child_command, wrapper_command
from deskmate_formats.observer import codex_cli
from deskmate_formats.observer.codex_exec import SUPPORTED_VERSION
from deskmate_formats.observer.events import EventError
from deskmate_formats.observer.journal import JournalBusy, JournalError, publish_event, read_journal
from test_observer_codex_exec import FIXTURES


class CodexWrapperTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.spool = self.root / "journal"

    def capture(self, name, *options, **kwargs):
        return codex_cli.capture_codex(child_command(FIXTURES / name, *options), self.spool,
                                       version=SUPPORTED_VERSION, **kwargs)

    def test_preserves_stdout_and_distinct_exit_codes(self):
        raw = BytesIO()
        self.assertEqual(self.capture("failure.jsonl", "--exit", "13", raw_output=raw), 13)
        self.assertEqual(raw.getvalue(), (FIXTURES / "failure.jsonl").read_bytes())
        records = read_journal(self.spool).records
        self.assertTrue(all(event["visibility"] == "private" for event in records))
        self.assertEqual(records[0]["type"], "process.heartbeat")
        self.assertGreater(records[0]["details"]["child_pid"], 0)
        command, = (event for event in records if event["type"] == "command.completed"
                    and event["severity"] == "error")
        failed, = (event for event in records if event["type"] == "turn.failed")
        exited, = (event for event in records if event["type"] == "process.exited")
        self.assertEqual((command["details"]["exit_code"], exited["details"]["exit_code"]), (7, 13))
        self.assertLess(failed["cursor"], exited["cursor"])

    def test_missing_terminal_even_when_process_exits_zero(self):
        self.assertEqual(self.capture("open-turn.jsonl", "--tail"), 0)
        records = read_journal(self.spool).records
        self.assertFalse(any(event["type"] in ("command.completed", "turn.completed",
                                               "turn.failed", "turn.interrupted") for event in records))
        errors = [event for event in records if event["type"] == "source.error"]
        self.assertEqual(errors[0]["details"]["reason"], "unterminated JSONL line")
        self.assertEqual(errors[1]["details"]["unfinished_items"], 1)
        self.assertEqual(errors[1]["details"]["exit_code"], 0)

    def test_verified_interrupt_exit_does_not_finish_the_tool(self):
        code = self.capture("open-turn.jsonl", "--interrupt")
        expected = 0xC000013A if os.name == "nt" else -signal.SIGINT
        self.assertEqual(code, expected)
        records = read_journal(self.spool).records
        self.assertFalse(any(event["type"] == "command.completed" for event in records))
        interrupted, = (event for event in records if event["type"] == "turn.interrupted")
        self.assertEqual(interrupted["details"]["evidence"], "os-interrupt-exit")
        self.assertEqual(interrupted["details"]["unfinished_items"], 1)

    def test_stderr_inherited_and_stdout_private_by_default(self):
        child = subprocess.run(wrapper_command(self.spool, FIXTURES / "failure.jsonl",
                                               "--exit", "29", visible=False),
                               capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 29)
        self.assertEqual(child.stdout, b"")
        self.assertEqual(child.stderr.splitlines(), [b"synthetic child stderr"])

    def test_early_stdout_close_keeps_child_alive_and_waits_for_exit(self):
        gate = self.root / "release"
        with subprocess.Popen(wrapper_command(self.spool, FIXTURES / "open-turn.jsonl",
                                              "--close-stdout", "--gate", str(gate)),
                              stderr=subprocess.DEVNULL) as wrapper:
            try:
                until = monotonic() + 5
                while monotonic() < until:
                    try:
                        records = read_journal(self.spool).records
                    except JournalBusy:
                        continue
                    if any(event["type"] == "source.disconnected" for event in records):
                        break
                    sleep(0.02)
                else:
                    self.fail("no independent stdout disconnect while the child was alive")
                self.assertIsNone(wrapper.poll())
                self.assertFalse(any(event["type"] == "process.exited" for event in records))
            finally:
                gate.touch()
            self.assertEqual(wrapper.wait(timeout=8), 0)

    def test_descendant_holding_pipe_does_not_hide_parent_exit(self):
        with patch.object(codex_cli, "_DRAIN_SECONDS", 0.15):
            self.assertEqual(self.capture("open-turn.jsonl", "--hold-inherited-stdout", "--exit", "17"), 17)
        records = read_journal(self.spool).records
        self.assertEqual(records[-2]["type"], "process.exited")
        self.assertEqual(records[-1]["summary"], "Codex JSONL drain deadline expired after child exit")

    def test_uncertain_append_is_never_replayed_and_does_not_change_exit(self):
        attempts = []

        def fail_once(path, event, **kwargs):
            attempts.append(event["source_sequence"])
            receipt = publish_event(path, event, **kwargs)
            if len(attempts) == 2:
                raise JournalError("synthetic ambiguous append")
            return receipt

        raw = BytesIO()
        with patch.object(codex_cli, "publish_event", side_effect=fail_once), patch.object(codex_cli, "_warn") as warn:
            self.assertEqual(self.capture("success.jsonl", "--exit", "23", raw_output=raw), 23)
        self.assertEqual(attempts, [1, 2])
        self.assertEqual(len(read_journal(self.spool).records), 2)
        self.assertEqual(raw.getvalue(), (FIXTURES / "success.jsonl").read_bytes())
        warn.assert_called_once()

    def test_safe_contention_retry_and_broken_raw_sink(self):
        class ClosedSink:
            def write(self, _):
                raise BrokenPipeError

        sequences = []

        def busy_once(path, event, **kwargs):
            sequences.append(event["source_sequence"])
            if len(sequences) == 1:
                raise JournalBusy("no append attempted")
            return publish_event(path, event, **kwargs)

        with patch.object(codex_cli, "publish_event", side_effect=busy_once), patch.object(codex_cli, "_warn") as warn:
            self.assertEqual(self.capture("success.jsonl", raw_output=ClosedSink()), 0)
        self.assertEqual(sequences[:3], [1, 1, 2])
        self.assertEqual(len(read_journal(self.spool).records), len(sequences) - 1)
        warn.assert_called_once_with("raw stdout forwarding stopped")

    def test_invalid_journal_prevents_launch(self):
        self.spool.write_bytes(b"not a private directory")
        with patch.object(codex_cli.subprocess, "Popen") as child, self.assertRaises(JournalError):
            self.capture("success.jsonl")
        child.assert_not_called()

    def test_cli_checks_version_and_preserves_argv(self):
        command = [sys.executable, "exec", "--json", "--sandbox", "read-only", "-c",
                   'approval_policy="never"', "private prompt"]
        args = ["--journal", str(self.spool), "--", *command]
        version = subprocess.CompletedProcess([], 0, stdout=b"codex-cli 0.166.0\n")
        with patch.object(codex_cli.subprocess, "run", return_value=version) as probe, \
                patch.object(codex_cli, "capture_codex", return_value=37) as capture:
            self.assertEqual(codex_cli.main(args), 37)
            self.assertEqual(probe.call_args.args[0], [sys.executable, "--version"])
            self.assertEqual(capture.call_args.args[0], command)
            self.assertEqual(capture.call_args.kwargs["visibility"], "private")
            self.assertIsNone(capture.call_args.kwargs["raw_output"])
        with patch.object(codex_cli, "_codex_version", side_effect=EventError("unsupported Codex exec version")), \
                patch.object(codex_cli, "capture_codex") as capture, patch("sys.stderr", new_callable=StringIO) as err:
            self.assertEqual(codex_cli.main(args), 2)
            capture.assert_not_called()
            self.assertNotIn("private prompt", err.getvalue())
