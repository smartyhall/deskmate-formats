import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.supervisor.protocol import (
    AppServer, Approval, ProtocolError, RemoteError, TransportError, encode_frame, request_id,
)


AVAILABLE = importlib.util.find_spec("jsonschema") is not None and sys.platform in ("win32", "linux")
FIXTURE = Path(__file__).with_name("app_server_fixture.py").resolve()
INPUT = {"threadId": "test-thread", "input": [{"type": "text", "text": "private-canary-prompt"}]}


def fake(path, mode="normal"):
    return SyntheticServer([sys.executable, "-I", str(FIXTURE), str(path), mode])


class SyntheticServer(AppServer):
    """Test transport with an explicit one-shot decision supplied by the test."""

    def decline(self, approval, *, generation, thread_id, turn_id, authorized):
        if authorized is not True:
            raise ProtocolError("synthetic authorization required")
        frame = self._take_synthetic_approval(
            approval, generation=generation, thread_id=thread_id, turn_id=turn_id, decision="decline",
        )
        self._write(frame)


def events(client):
    while (event := client.next_event(timeout=0.15)) is not None:
        yield event


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and Windows or Linux process identity")
class AppServerTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "synthetic-state.json"

    def test_lifecycle_and_early_terminal_notifications(self):
        with fake(self.path, "out-of-order") as client:
            thread = client.request("thread/start", {})["thread"]
            turn = client.request("turn/start", INPUT)["turn"]
            self.assertEqual(turn["status"], "inProgress")
            seen = list(events(client))
            self.assertEqual([e.method for e in seen], [
                "thread/started", "item/completed", "turn/started", "turn/completed",
            ])
            self.assertEqual(seen[-1].params["turn"]["id"], turn["id"])
            self.assertEqual(seen[-1].params["turn"]["status"], "completed")
            generation, process = client.generation, (client.pid, client.process_identity)
        with fake(self.path) as client:
            self.assertNotEqual(client.generation, generation)
            self.assertNotEqual((client.pid, client.process_identity), process)
            resumed = client.request("thread/resume", {"threadId": thread["id"]})["thread"]
            self.assertEqual(resumed["id"], thread["id"])
            self.assertEqual(resumed["turns"][0]["id"], turn["id"])

    def test_approval_requires_exact_session_association_and_identity(self):
        for mode in ("approval", "string-approval", "file-approval"):
            with self.subTest(mode=mode), fake(self.path, mode) as client:
                client.request("thread/start", {})
                turn = client.request("turn/start", INPUT)["turn"]
                approval, = [event for event in events(client) if isinstance(event, Approval)]
                self.assertEqual(approval.request_id, "2" if mode == "string-approval" else 2)
                args = dict(generation=client.generation, thread_id="test-thread",
                            turn_id=turn["id"], decision="decline")
                for change in ({"generation": "old"}, {"thread_id": "wrong"},
                               {"turn_id": "wrong"}, {"decision": "acceptForSession"}):
                    with self.assertRaises(ProtocolError):
                        client._take_synthetic_approval(approval, **(args | change))
                with self.assertRaises(ProtocolError):
                    client._take_synthetic_approval(Approval(
                        approval.generation, approval.request_id, approval.method, approval.thread_id,
                        approval.turn_id, approval.item_id, approval.decisions,
                    ), **args)
                expected = {key: value for key, value in args.items() if key != "decision"}
                with self.assertRaises(ProtocolError):
                    client.decline(approval, authorized=False, **expected)
                self.assertIsNone(client.next_event(timeout=0.05))
                client.decline(approval, authorized=True, **expected)
                self.assertEqual([e.method for e in events(client)], ["serverRequest/resolved", "turn/completed"])
                with self.assertRaises(ProtocolError):
                    client.decline(approval, authorized=True, **expected)

    def test_resolved_and_old_generation_approvals_are_stale(self):
        with fake(self.path, "stale-approval") as client:
            client.request("thread/start", {})
            turn = client.request("turn/start", INPUT)["turn"]
            approval, = [event for event in events(client) if isinstance(event, Approval)]
            expected = dict(generation=client.generation, thread_id="test-thread", turn_id=turn["id"])
            with self.assertRaises(ProtocolError):
                client.decline(approval, authorized=True, **expected)
        with fake(self.path, "approval") as client:
            client.request("thread/start", {})
            client.request("turn/start", INPUT)
            with self.assertRaises(ProtocolError):
                client.decline(approval, authorized=True, **expected)

    def test_steer_and_interrupt(self):
        with fake(self.path) as client:
            client.request("thread/start", {})
            turn = client.request("turn/start", INPUT)["turn"]
            result = client.request("turn/steer", INPUT | {"expectedTurnId": turn["id"]})
            self.assertEqual(result["turnId"], turn["id"])
            self.assertEqual(client.request("turn/interrupt", {"threadId": "test-thread", "turnId": turn["id"]}), {})
            self.assertEqual(list(events(client))[-1].params["turn"]["status"], "interrupted")

    def test_correlated_remote_failure_keeps_connection_usable(self):
        with fake(self.path, "remote-error") as client:
            for _ in range(2):
                with self.assertRaises(RemoteError) as error:
                    client.request("thread/start", {})
                self.assertEqual(error.exception.code, -32602)
                self.assertNotIn("private-canary", str(error.exception))

    def test_transport_failures_and_duplicate_response(self):
        for mode in ("malformed", "partial", "oversized", "mismatch", "eof", "unknown-request", "duplicate"):
            with self.subTest(mode=mode), fake(self.path, mode) as client:
                with self.assertRaises(TransportError):
                    client.request("thread/start", {})
                    list(events(client))
                with self.assertRaises(TransportError):
                    client.request("thread/start", {})
        with self.assertRaises(TransportError):
            fake(self.path, "wrong-version")

    def test_outbound_validation_precedes_send_hook(self):
        with fake(self.path) as client:
            for method, params in (
                ("unknown", {}), ("thread/start", {"cwd": "hidden"}), ("turn/start", INPUT | {"input": []}),
                ("turn/start", INPUT | {"input": [{"type": "text", "text": "x", "extra": "x"}]}),
                ("turn/interrupt", {"turnId": "x"}), ("thread/read", {"threadId": 42}),
            ):
                with self.subTest(method=method), self.assertRaises(ProtocolError):
                    client.request(method, params, before_send=lambda _: self.fail("unexpected send"))

    def test_strict_json_and_request_identifiers(self):
        for identifier in (True, 1.0, None, 2**63, "", "x\n"):
            with self.assertRaises(ProtocolError):
                request_id(identifier)
        for value in ({1: 2}, {"x": float("nan")}, {"x": "\ud800"}, {"x": "x" * (256 * 1024)}):
            with self.assertRaises(ProtocolError):
                encode_frame(value)


if __name__ == "__main__":
    unittest.main()
