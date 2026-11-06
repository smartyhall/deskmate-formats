"""Distinguish reported lifecycle, publication signals and OS process identity."""

import os
import subprocess
import sys
import unittest

from deskmate_formats.observer.agents import AgentProjection
from deskmate_formats.observer.process_health import process_claim, verify_process
from observatory_fixture import event
from test_observer_events import record


class AgentTests(unittest.TestCase):
    def project(self, *payloads, age=0, start=1, probe=lambda *_: "unknown"):
        records = [record(payload, index) for index, payload in enumerate(payloads, 1)]
        projection = AgentProjection(records, started_ns=start, scanned_ns=10000, quiet_seconds=2, stale_seconds=5)
        return projection.views(10000 + age * 10**9, probe=probe)

    def test_actual_activity_and_heartbeat_are_independent_of_wall_clock(self):
        note = event(source_time_utc="2099-01-01T00:00:00Z")
        beat = event(2, "process.heartbeat", process={"pid": 123, "identity": "synthetic"},
                     source_time_utc="1990-01-01T00:00:00Z")
        active, = self.project(note, beat)
        self.assertEqual((active.state, active.transport, active.process), ("active-reporting", "recent", "unknown"))
        self.assertEqual(active.last_activity.type, "agent.note")
        quiet, = self.project(note, beat, age=3, probe=lambda *_: "alive")
        self.assertEqual((quiet.state, quiet.activity_age_ms, quiet.verified_pid), ("alive-no-new-events", 3000, 123))
        old, = self.project(note, beat, age=6, probe=lambda *_: "alive")
        self.assertEqual((old.state, old.transport, old.stale), ("alive-no-new-events", "stale", True))
        old_without_process, = self.project(note, age=6)
        self.assertEqual(old_without_process.state, "disconnected")
        unknown, = self.project(beat)
        self.assertEqual((unknown.state, unknown.last_activity, unknown.verified_pid), ("unknown", None, None))

    def test_explicit_disconnect_restart_and_pid_reuse(self):
        note = event()
        disconnected = event(2, "source.disconnected")
        beat = event(3, "process.heartbeat", process={"pid": 123, "identity": "synthetic"})
        cut, = self.project(note, disconnected, beat, probe=lambda *_: "alive")
        self.assertEqual((cut.state, cut.transport), ("disconnected", "disconnected"))
        connected = event(4, "source.reconnected")
        resumed, = self.project(note, disconnected, beat, connected, age=3, probe=lambda *_: "alive")
        self.assertEqual((resumed.state, resumed.transport), ("alive-no-new-events", "recent"))
        restarted, = self.project(note, beat, start=1000, probe=lambda *_: "alive")
        self.assertEqual((restarted.state, restarted.transport, restarted.process), ("disconnected", "historical", "alive"))
        self.assertIsNone(restarted.activity_age_ms)
        reused, = self.project(note, beat, probe=lambda *_: "identity-mismatch")
        self.assertEqual((reused.state, reused.process, reused.verified_pid), ("disconnected", "identity-mismatch", None))

    def test_approval_is_explicit_correlated_and_independent_of_terminal_state(self):
        generic = event(summary="Paused awaiting approval")
        self.assertEqual(self.project(generic)[0].state, "active-reporting")
        request = event(2, "approval.requested", correlation={"approval": "one"})
        wrong = event(3, "approval.resolved", correlation={"approval": "other"})
        pending, = self.project(generic, request, wrong)
        self.assertEqual((pending.state, pending.pending_approval_ids), ("approval-needed", ("one",)))
        stale, = self.project(generic, request, age=6)
        self.assertEqual((stale.state, stale.pending_approval_count), ("disconnected", 1))
        resolved = event(4, "approval.resolved", correlation={"approval": "one"})
        repeated = event(5, "approval.requested", correlation={"approval": "one"})
        self.assertEqual(self.project(generic, request, wrong, resolved, repeated)[0].pending_approval_count, 0)

    def test_conflicting_terminal_events_and_new_turn(self):
        start = event(1, "turn.started", correlation={"turn": "first"})
        mismatch = event(2, "turn.completed", correlation={"turn": "other"})
        fail = event(3, "turn.failed", correlation={"turn": "first"})
        conflict = event(4, "turn.completed", correlation={"turn": "first"})
        self.assertEqual(self.project(start, mismatch)[0].reported_lifecycle, "running")
        self.assertEqual(self.project(start, mismatch, fail, conflict, start=10000)[0].state, "failed")
        turn2 = event(5, "turn.started", correlation={"turn": "second"})
        end = event(6, "turn.completed", correlation={"turn": "second"})
        self.assertEqual(self.project(start, mismatch, fail, conflict, turn2, end)[0].state, "completed")
        session_end = event(7, "session.ended")
        late = event(8, "turn.started")
        self.assertEqual(self.project(start, fail, session_end, late)[0].state, "failed")

    def test_private_events_do_not_influence_public_state(self):
        visible = event(1)
        private = event(2, "source.disconnected", visibility="private")
        other = event(agent="beta", visibility="private")
        projection = AgentProjection([record(visible, 1), record(private, 2), record(other, 3)],
                                     started_ns=1, scanned_ns=500)
        self.assertEqual(len(projection.events), 1)
        self.assertEqual([(view.agent_id, view.state) for view in projection.views(500)], [("alpha", "active-reporting")])

    def test_reported_process_exit_stays_stopped_without_claim_or_terminal_turn(self):
        turn = event(1, "turn.started")
        exited = event(2, "process.exited")
        disconnected, = self.project(turn, exited)
        self.assertEqual((disconnected.process, disconnected.state, disconnected.reported_lifecycle),
                         ("stopped", "disconnected", "running"))
        self.assertEqual(disconnected.transport, "recent")
        self.assertEqual(disconnected.last_activity.type, "turn.started")
        self.assertIsNone(disconnected.verified_pid)

    @unittest.skipUnless(sys.platform in ("win32", "linux"), "platform has no local process identity probe")
    def test_actual_local_identity_and_child_exit(self):
        claim = process_claim()
        self.assertEqual(claim["pid"], os.getpid())
        self.assertEqual(verify_process(os.getpid(), claim["identity"]), "alive")
        self.assertEqual(verify_process(os.getpid(), "synthetic-old-identity"), "identity-mismatch")
        with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"]) as child:
            try:
                claim = process_claim(child.pid)
                self.assertEqual(verify_process(child.pid, claim["identity"]), "alive")
            finally:
                child.terminate()
                child.wait(timeout=5)
            self.assertIn(verify_process(child.pid, claim["identity"]), ("stopped", "not-found"))
