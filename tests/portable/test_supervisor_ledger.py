import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest

from deskmate_formats.supervisor.ledger import DATABASE, LedgerError, open_ledger
from deskmate_formats.supervisor.operations import Operations
from deskmate_formats.supervisor.protocol import RemoteError, TransportError

from test_supervisor_protocol import AVAILABLE, INPUT, fake


def crash_probe(root):
    """Get killed after observing a running turn, with no supervisor cleanup."""
    with (open_ledger(root / "receipts", create=True) as ledger,
          fake(root / "synthetic.json") as client):
        operations = Operations(client, ledger)
        operations.execute("create", "thread/start", {})
        operations.execute("run", "turn/start", INPUT)
        (root / "ready").touch()
        sleep(60)


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and Windows or Linux process identity")
class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.directory = self.root / "receipts"
        self.state = self.root / "synthetic.json"

    def test_lost_ack_after_server_mutation_is_never_replayed_or_guessed(self):
        with open_ledger(self.directory, create=True) as ledger, fake(self.state, "lost-ack") as client:
            ops = Operations(client, ledger)
            ops.execute("create", "thread/start", {})
            with self.assertRaises(TransportError):
                ops.execute("mutate", "turn/start", INPUT)
            receipt = ledger.get("mutate")
            self.assertEqual((receipt.state, receipt.acknowledged, receipt.turn_id),
                             ("needs-reconciliation", 0, None))
            self.assertEqual(ledger.process_for(receipt.generation), (client.pid, client.process_identity))
        stored = self.state.read_bytes()
        self.assertEqual(len(json.loads(stored)["turns"]), 1)
        with open_ledger(self.directory) as ledger, fake(self.state) as client:
            ops = Operations(client, ledger)
            self.assertEqual(ops.reconcile("mutate"), receipt)
            with self.assertRaises(LedgerError):
                ops.execute("mutate", "turn/start", INPUT)
            self.assertEqual(self.state.read_bytes(), stored)

    def test_explicit_terminal_notification_and_recovered_terminal_history(self):
        for consume in (True, False):
            with self.subTest(consume=consume):
                directory = self.root / f"receipts-{consume}"
                with open_ledger(directory, create=True) as ledger, fake(self.state, "out-of-order") as client:
                    ops = Operations(client, ledger)
                    ops.execute("create", "thread/start", {})
                    turn = ops.execute("run", "turn/start", INPUT)["turn"]
                    self.assertEqual(ledger.get("run").state, "running")
                    if consume:
                        while ops.next_event(timeout=0.05) is not None:
                            pass
                        self.assertEqual(ledger.get("run").state, "completed")
                with open_ledger(directory) as ledger, fake(self.state) as client:
                    ops = Operations(client, ledger)
                    if not consume:
                        self.assertEqual(ledger.get("run").state, "needs-reconciliation")
                    receipt = ops.reconcile("run")
                    self.assertEqual((receipt.turn_id, receipt.state), (turn["id"], "completed"))
                    self.assertEqual(receipt.evidence, "turn-notification" if consume else "server-turn-history")
                    if not consume:
                        self.assertEqual(receipt.evidence_generation, client.generation)
                        self.assertNotEqual(receipt.generation, receipt.evidence_generation)

    def test_running_status_from_old_generation_is_uncertain_after_forced_termination(self):
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(self.root)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW
                                 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        try:
            deadline = monotonic() + 10
            while not (self.root / "ready").exists() and child.poll() is None and monotonic() < deadline:
                sleep(0.02)
            self.assertTrue((self.root / "ready").exists())
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
        with open_ledger(self.directory) as ledger, fake(self.state) as client:
            ops = Operations(client, ledger)
            receipt = ops.reconcile("run")
            self.assertEqual((receipt.state, receipt.acknowledged), ("needs-reconciliation", 1))
            self.assertIsNotNone(receipt.turn_id)
            self.assertNotEqual(ledger.process_for(receipt.generation), (client.pid, client.process_identity))

    def test_failed_send_gate_leaves_prepared_without_sending(self):
        with open_ledger(self.directory, create=True) as ledger, fake(self.state) as client:
            ops = Operations(client, ledger)
            ledger._db.execute("""CREATE TRIGGER fail_send BEFORE UPDATE ON operations
                WHEN NEW.state = 'sent-unknown' BEGIN SELECT RAISE(ABORT, 'injected'); END""")
            with self.assertRaises(LedgerError):
                ops.execute("prepare", "thread/start", {})
            self.assertFalse(self.state.exists())
        with open_ledger(self.directory) as ledger, fake(self.state) as client:
            ops = Operations(client, ledger)
            self.assertEqual(ops.reconcile("prepare").state, "prepared")
            with self.assertRaises(LedgerError):
                ops.execute("prepare", "thread/start", {})
            self.assertFalse(self.state.exists())

    def test_failed_acknowledgement_write_leaves_uncertainty(self):
        with open_ledger(self.directory, create=True) as ledger, fake(self.state) as client:
            ops = Operations(client, ledger)
            ledger._db.execute("""CREATE TRIGGER fail_ack BEFORE UPDATE ON operations
                WHEN NEW.state = 'acknowledged' BEGIN SELECT RAISE(ABORT, 'injected'); END""")
            with self.assertRaises(LedgerError):
                ops.execute("mutate", "thread/start", {})
            self.assertTrue(self.state.exists())
        with open_ledger(self.directory) as ledger:
            self.assertEqual(ledger.get("mutate").state, "sent-unknown")
            with fake(self.state) as client:
                self.assertEqual(Operations(client, ledger).reconcile("mutate").state, "needs-reconciliation")

    def test_truncated_ledger_refuses_recovery(self):
        with open_ledger(self.directory, create=True):
            pass
        with (self.directory / DATABASE).open("r+b") as stream:
            stream.truncate(8192)
        with self.assertRaises(LedgerError), open_ledger(self.directory):
            self.fail("opened a truncated ledger")

    def test_interrupt_acknowledged_then_interruption_observed(self):
        with open_ledger(self.directory, create=True) as ledger, fake(self.state) as client:
            ops = Operations(client, ledger)
            ops.execute("create", "thread/start", {})
            turn = ops.execute("run", "turn/start", INPUT)["turn"]
            ops.execute("stop", "turn/interrupt", {"threadId": INPUT["threadId"], "turnId": turn["id"]})
            self.assertEqual(ledger.get("stop").state, "acknowledged")
            while ops.next_event(timeout=0.05) is not None:
                pass
            self.assertEqual(ledger.get("stop").state, "completed")
            self.assertEqual(ledger.get("run").state, "failed")

    def test_explicit_remote_error(self):
        with open_ledger(self.directory, create=True) as ledger, fake(self.state, "remote-error") as client:
            ops = Operations(client, ledger)
            with self.assertRaises(RemoteError):
                ops.execute("reject", "thread/start", {})
            receipt = ledger.get("reject")
            self.assertEqual((receipt.state, receipt.evidence), ("failed", "remote-error"))


if __name__ == "__main__":
    crash_probe(Path(sys.argv[1]))
