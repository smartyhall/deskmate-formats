"""Installed driver acceptance with a real, owned synthetic stdio subprocess."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from deskmate_formats.observer._private_storage import LockBusy
from deskmate_formats.supervisor.driver import (
    DriverError, _effective_policy, implementation_hashes, load_plan, preflight, prepare, read_record, reconcile_synthetic,
    run, status, verify_native, write_record,
)
from deskmate_formats.supervisor.ledger import open_ledger
from test_supervisor_protocol import AVAILABLE


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and supported process identity")
class DriverTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.directory = self.root / "run"

    def prepare(self, mode="success", **kw):
        return prepare(self.directory, mode=mode, timeout=2, deadline=0.25, **kw)

    def test_prepare_status_help_and_import_have_no_child(self):
        with patch("subprocess.Popen", side_effect=AssertionError("unexpected launch")):
            token = self.prepare()
            view = status(self.directory)
            self.assertEqual(view["plan_sha256"], token)
            self.assertFalse(view["attempted"])
            self.assertEqual(view["operations"], [])
        for module in ("driver_cli", "bridge_cli"):
            result = subprocess.run([sys.executable, "-m", "deskmate_formats.supervisor." + module, "--help"],
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.directory / "evidence" / "peer.json").exists())

    def test_success_has_exact_operations_private_evidence_and_clean_exit(self):
        token = self.prepare()
        result = run(self.directory, authorization=token)
        self.assertEqual(result["state"], "completed", result)
        self.assertIn(result["child_status"], ("stopped", "not-found"))
        self.assertFalse(result["telemetry_failed"])
        self.assertEqual([(r["method"], r["state"], r["acknowledged"]) for r in result["operations"]],
                         [("thread/start", "completed", 1), ("turn/start", "completed", 1)])
        self.assertEqual(read_record(self.directory / "outcome.json"), result)
        self.assertIn(b"S0_CANARY_OK", b"".join(p.read_bytes() for p in (self.directory / "evidence").glob("*.json")))
        public = (self.directory / "spool" / "events.jsonl").read_bytes()
        for secret in (b"S0_CANARY_OK", b"test-thread", b"private-canary", str(self.root).encode()):
            self.assertNotIn(secret, public)
        state = (self.directory / "evidence" / "peer.json").read_bytes()
        self.assertEqual(len(read_record(self.directory / "evidence" / "peer.json")["turns"]), 1)
        with self.assertRaises(DriverError):
            run(self.directory, authorization=token)
        self.assertEqual((self.directory / "evidence" / "peer.json").read_bytes(), state)

    def test_missing_delayed_ack_never_replayed_and_unacknowledged_restart_stays_unresolved(self):
        for mode in ("lost-ack", "delayed-ack"):
            with self.subTest(mode=mode):
                directory = self.root / mode
                token = prepare(directory, mode=mode, timeout=0.8, deadline=0.1)
                result = run(directory, authorization=token)
                self.assertEqual(result["state"], "blocked")
                turn = result["operations"][-1]
                self.assertEqual((turn["state"], turn["acknowledged"], turn["turn_id"]),
                                 ("needs-reconciliation", 0, None))
                state_path = directory / "evidence" / "peer.json"
                before = state_path.read_bytes()
                self.assertEqual(len(json.loads(before)["turns"]), 1)
                reconciled = reconcile_synthetic(directory, authorization=token)
                self.assertEqual(reconciled[-1]["state"], "needs-reconciliation")
                self.assertEqual(state_path.read_bytes(), before)
                with self.assertRaises(DriverError):
                    run(directory, authorization=token)

    def test_unexpected_approvals_stale_ids_exit_and_unresolved_turn_block(self):
        for mode in ("driver-approval", "approval", "unknown-request", "mismatch", "duplicate", "eof", "normal", "stale-turn"):
            with self.subTest(mode=mode):
                directory = self.root / mode
                token = prepare(directory, mode=mode, timeout=1, deadline=0.1)
                result = run(directory, authorization=token)
                self.assertEqual(result["state"], "blocked", result)
                self.assertIn(result.get("child_status"), ("stopped", "not-found"))
                self.assertTrue(all(row["state"] not in ("running", "sent-unknown", "acknowledged")
                                    for row in result["operations"]))

    def test_restart_of_acknowledged_turn_uses_only_exact_history(self):
        token = self.prepare("history-only")
        run(self.directory, authorization=token)
        before = (self.directory / "evidence" / "peer.json").read_bytes()
        result = reconcile_synthetic(self.directory, authorization=token)
        self.assertEqual(result[-1]["state"], "completed")
        self.assertEqual(result[-1]["evidence"], "server-turn-history")
        self.assertEqual((self.directory / "evidence" / "peer.json").read_bytes(), before)

    def test_plan_grant_config_scratch_and_attempt_are_fail_closed(self):
        token = self.prepare()
        with self.assertRaises(DriverError):
            run(self.directory, authorization="0" * 64)
        (self.directory / "scratch" / "unexpected").touch()
        with self.assertRaises(DriverError):
            run(self.directory, authorization=token)
        (self.directory / "scratch" / "unexpected").unlink()
        write_record(self.directory / "attempt.json", {"crash": "before-child"})
        with patch("subprocess.Popen", side_effect=AssertionError("replayed child")), self.assertRaises(DriverError):
            run(self.directory, authorization=token)
        self.assertEqual(status(self.directory)["operations"], [])

    def test_configuration_edit_and_nonempty_run_refused(self):
        token = self.prepare()
        with self.assertRaises(DriverError):
            self.prepare()
        (self.directory / "codex-home" / "config.toml").write_bytes(b"changed")
        with self.assertRaises(DriverError):
            run(self.directory, authorization=token)

    def test_unpinned_native_is_never_executed_and_environment_is_allowlisted(self):
        with patch("subprocess.run", side_effect=AssertionError("executed unpinned input")):
            with self.assertRaises(DriverError):
                verify_native(sys.executable)
        with patch.dict("os.environ", {"86BOX_TOKEN": "private", "OPENAI_API_KEY": "private", "GIT_DIR": "private"}):
            self.prepare()
        plan, _ = load_plan(self.directory)
        self.assertFalse({"86BOX_TOKEN", "OPENAI_API_KEY", "GIT_DIR", "PATH"} & plan["env"].keys())

    def test_live_isolation_requires_separate_exact_grant_and_has_no_restart(self):
        with patch("deskmate_formats.supervisor.driver.verify_native", return_value=str(Path(sys.executable).resolve())):
            token = prepare(self.directory, executable=sys.executable, model="operator-selected-placeholder", effort="low")
        with patch("deskmate_formats.supervisor.driver.AppServer", side_effect=AssertionError("live launch")):
            with self.assertRaises(DriverError):
                run(self.directory, authorization=token)
            with self.assertRaises(DriverError):
                reconcile_synthetic(self.directory, authorization=token)
            with patch("deskmate_formats.supervisor.driver.verify_native"), self.assertRaisesRegex(DriverError, "live launch blocked"):
                run(self.directory, authorization=token, isolation_reviewed=token)
            with patch("deskmate_formats.supervisor.driver.verify_native"):
                self.assertEqual(preflight(self.directory)["state"], "blocked")
        self.assertFalse(status(self.directory)["attempted"])

    def test_scratch_and_sanitized_environment_are_not_filesystem_containment(self):
        # Synthetic negative evidence: no private lab input is opened.
        marker = self.root / "outside-scratch.txt"
        marker.write_text("synthetic-outside-scratch", encoding="ascii")
        self.prepare()
        plan, _ = load_plan(self.directory)
        child = subprocess.run(
            [sys.executable, "-I", "-c", "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())", str(marker)],
            env=plan["env"], cwd=self.directory / "scratch", capture_output=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(child.returncode, 0)
        self.assertEqual(child.stdout.strip(), b"synthetic-outside-scratch")

    def test_preflight_never_launches_and_reports_requested_not_effective(self):
        self.prepare()
        with patch("subprocess.Popen", side_effect=AssertionError("unexpected child")):
            report = preflight(self.directory)
        self.assertEqual(report["state"], "synthetic-only")
        self.assertEqual(report["app_server_launches"], 0)
        self.assertIn("unverified", report["effective_codex_configuration"])
        self.assertTrue(all(report["checks"].values()))
        (self.directory / "codex-home" / "config.toml").write_bytes(b"changed")
        self.assertEqual(preflight(self.directory)["state"], "blocked")

    def test_dependency_drift_blocks_before_launch(self):
        token = self.prepare()
        hashes = implementation_hashes()
        self.assertIn("observer/_private_storage.py", hashes)
        hashes["observer/_private_storage.py"] = "0" * 64
        with patch("deskmate_formats.supervisor.driver.implementation_hashes", return_value=hashes), \
                patch("subprocess.Popen", side_effect=AssertionError("unexpected child")), self.assertRaises(DriverError):
            run(self.directory, authorization=token)

    def test_effort_and_approval_reviewer_drift_block_before_turn(self):
        for mode in ("unsafe-effort", "unsafe-reviewer"):
            with self.subTest(mode=mode):
                directory = self.root / mode
                token = prepare(directory, mode=mode, timeout=2)
                result = run(directory, authorization=token)
                self.assertEqual(result["state"], "blocked")
                self.assertEqual([r["method"] for r in result["operations"]], ["thread/start"])
                self.assertEqual(read_record(directory / "evidence" / "peer.json")["turns"], [])

    def test_thread_start_must_be_empty_and_persistent(self):
        scratch = self.root / "scratch"
        policy = {"cwd": str(scratch), "approvalPolicy": "never", "sandbox": {"type": "readOnly"},
                  "model": "synthetic", "modelProvider": "synthetic", "approvalsReviewer": "user",
                  "reasoningEffort": "low", "thread": {"ephemeral": False, "turns": []}}
        _effective_policy(policy, {"kind": "synthetic"}, scratch)
        for thread in ({"ephemeral": True, "turns": []},
                       {"ephemeral": False, "turns": [{"id": "pre-existing", "status": "completed", "items": []}]}):
            with self.subTest(thread=thread), self.assertRaises(DriverError):
                _effective_policy(policy | {"thread": thread}, {"kind": "synthetic"}, scratch)

    def test_non_canary_items_and_incomplete_history_never_pass(self):
        for mode in ("web-tool", "image-tool", "hook-item", "terminal-tool", "history-tool",
                     "history-sentinel", "history-not-loaded", "history-extra-turn", "history-cursor",
                     "malformed", "oversized", "partial", "duplicate-terminal", "restart-terminal"):
            with self.subTest(mode=mode):
                directory = self.root / mode
                # These cases test rejection, not startup timing. Keep enough
                # handshake margin for the Windows host under concurrent I/O.
                token = prepare(directory, mode=mode, timeout=5, deadline=0.3)
                result = run(directory, authorization=token)
                self.assertEqual(result["state"], "blocked", result)
                self.assertIn(result.get("child_status"), ("stopped", "not-found"), result)
                self.assertNotIn(b"private-canary", (directory / "spool" / "events.jsonl").read_bytes())

    def test_teardown_timeout_is_durable_blocked_even_after_terminal_success(self):
        from deskmate_formats.supervisor.protocol import AppServer
        close = AppServer.close
        def close_then_timeout(client):
            close(client)  # Keep the synthetic child cleaned up.
            raise subprocess.TimeoutExpired("private-command", 2)
        token = self.prepare()
        with patch.object(AppServer, "close", close_then_timeout):
            result = run(self.directory, authorization=token)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["reason"], "child-teardown-failed")
        self.assertEqual(status(self.directory)["outcome"], result)

    def test_stale_process_identity_cannot_report_success(self):
        token = self.prepare()
        with patch("deskmate_formats.supervisor.driver.verify_process", return_value="identity-mismatch"):
            result = run(self.directory, authorization=token)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(result["reason"], "child-exit-not-verified")

    def test_effective_policy_drift_blocks_before_model_input(self):
        token = self.prepare("unsafe-policy")
        result = run(self.directory, authorization=token)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual([row["method"] for row in result["operations"]], ["thread/start"])
        self.assertEqual(json.loads((self.directory / "evidence" / "peer.json").read_bytes())["turns"], [])

    def test_reconciliation_refuses_a_live_old_process_claim(self):
        token = self.prepare()
        run(self.directory, authorization=token)
        with patch("deskmate_formats.supervisor.driver.verify_process", return_value="alive"):
            with self.assertRaises(DriverError):
                reconcile_synthetic(self.directory, authorization=token)

    def test_offline_status_does_not_modify_operation_bytes(self):
        token = self.prepare()
        run(self.directory, authorization=token)
        path = self.directory / "receipts" / "operations.sqlite3"
        before = sha256(path.read_bytes()).digest()
        status(self.directory)
        self.assertEqual(sha256(path.read_bytes()).digest(), before)
        with open_ledger(self.directory / "receipts") as ledger:
            self.assertEqual(len(ledger.sessions()), 1)

    def test_owner_termination_leaves_permanent_fence_and_read_only_restart(self):
        token = prepare(self.directory, mode="history-only", timeout=5, deadline=60)
        owner = subprocess.Popen([sys.executable, "-I", "-m", "deskmate_formats.supervisor.driver_cli",
                                  "--run", str(self.directory), "synthetic", "--authorize-plan", token],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        observed = False
        try:
            deadline = monotonic() + 10
            while monotonic() < deadline and owner.poll() is None:
                for path in (self.directory / "evidence").glob("[0-9]*.json"):
                    try:
                        observed |= read_record(path)["kind"] == "turn-result"
                    except (ValueError, OSError):
                        pass
                if observed:
                    break
                sleep(0.02)
            self.assertTrue(observed, "owner never durably observed acknowledgement")
        finally:
            if owner.poll() is None:
                owner.kill()  # Retained synthetic owner handle only.
            owner.wait(timeout=5)
        # Windows can signal process exit just before releasing its file locks.
        # Poll this read-only observation; never retry a dispatch or mutation.
        deadline = monotonic() + 5
        while True:
            try:
                view = status(self.directory)
                break
            except LockBusy:
                if monotonic() >= deadline:
                    raise
                sleep(0.02)
        self.assertTrue(view["attempted"])
        self.assertIsNone(view["outcome"])
        before = (self.directory / "evidence" / "peer.json").read_bytes()
        with self.assertRaises(DriverError):
            run(self.directory, authorization=token)
        from deskmate_formats.observer.process_health import verify_process
        with open_ledger(self.directory / "receipts") as ledger:
            _, pid, stamp = ledger.sessions()[0]
        deadline = monotonic() + 5
        while verify_process(pid, stamp) == "alive" and monotonic() < deadline:
            sleep(0.02)
        result = reconcile_synthetic(self.directory, authorization=token)
        self.assertEqual(result[-1]["state"], "completed")
        self.assertEqual((self.directory / "evidence" / "peer.json").read_bytes(), before)
