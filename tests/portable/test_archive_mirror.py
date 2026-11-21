"""Local-only regression tests for the research mirror."""
from collections import deque
from email.utils import formatdate
import hashlib
import http.server
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("archive_mirror",
    Path(__file__).resolve().parents[2]/"tools"/"archive"/"archive_mirror.py")
mirror = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirror)


class Handler(http.server.BaseHTTPRequestHandler):
    body = b"abcdefghij"
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.seen.append((self.path, self.headers.get("Range")))
        if self.server.disconnect == self.path:
            self.server.disconnect = None
            return
        responses = self.server.responses.get(self.path)
        if responses:
            status, retry_after = responses.popleft()
            self.send_response(status)
            if retry_after is not None:
                self.send_header("Retry-After", retry_after)
            self.end_headers()
            return
        if self.path == "/robots.txt":
            content, kind = b"User-agent: *\nDisallow: /tree/excluded.bin\n", "text/plain"
        elif self.path == "/tree/":
            content, kind = (b"<title>Index of /tree/</title><a href='../'>up</a>"
                             b"<a href='sub/'>sub</a><a href='excluded.bin'>x</a>"
                             b"<a href='CON.bin'>reserved</a><a href='a.bin'>a</a>"
                             b"<a href='/other.bin'>out</a>", "text/html")
        elif self.path == "/tree/sub/":
            content, kind = b"<title>Index of sub</title><a href='b.bin'>b</a>", "text/html"
        else:
            content, kind = self.body, "application/octet-stream"
        offset = int(self.headers["Range"][6:-1]) if self.headers.get("Range") else 0
        self.send_response(206 if offset else 200)
        if offset:
            self.send_header("Content-Range", f"bytes {offset}-{len(content)-1}/{len(content)}")
        self.send_header("ETag", '"fixed"')
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(content)-offset))
        self.end_headers()
        if self.server.cut == self.path:
            self.server.cut = None
            self.wfile.write(content[:4])
            return
        self.wfile.write(content[offset:])


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.seen, self.server.responses = [], {}
        self.server.cut = self.server.disconnect = None
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(self.server.shutdown)
        self.root = f"http://127.0.0.1:{self.server.server_port}/tree/"
        self.m = mirror.Mirror(self.root, self.temp.name, reserve_gib=0)
        self.addCleanup(self.m.db.close)
        # No real pacing delays in local-only tests; stop checks remain active.
        self.m.wait = lambda _: self.m.check_stop()

    def mock_clock(self):
        self.epoch = 1_800_000_000
        self.cooldown_waits = []
        clock = patch.object(mirror.time, "time", lambda: self.epoch)
        jitter = patch.object(mirror.random, "uniform", return_value=0)
        clock.start()
        jitter.start()
        self.addCleanup(clock.stop)
        self.addCleanup(jitter.stop)
        self.m.wait = self.advance_cooldown

    def advance_cooldown(self, delay):
        # The fixture removes rate waits but records host waits against wall time.
        if delay >= 30:
            self.cooldown_waits.append(delay)
            self.epoch += delay

    def test_tree_resume_and_robots(self):
        self.m.run(limit=1)
        rel = "a.bin"
        part = self.m.state/(hashlib.sha256(rel.encode()).hexdigest()+".part")
        part.write_bytes(Handler.body[:4])
        self.m.update(rel, status="partial", expected=10, etag='"fixed"')
        self.m.run()
        self.assertIn(("/tree/a.bin", "bytes=4-"), self.server.seen)
        self.assertNotIn(("/tree/excluded.bin", None), self.server.seen)
        self.assertNotIn(("/other.bin", None), self.server.seen)
        self.assertEqual((self.m.dest/"originals/a.bin").read_bytes(), Handler.body)
        self.assertEqual((self.m.dest/"originals/sub/b.bin").read_bytes(), Handler.body)
        local = self.m.db.execute("SELECT local FROM entries WHERE rel='CON.bin'").fetchone()[0]
        self.assertTrue(local.startswith("mapped/"))
        self.assertEqual((self.m.dest/local).read_bytes(), Handler.body)
        before = len(self.server.seen)
        self.m.run()
        self.assertEqual(self.server.seen[before:], [("/robots.txt", None)])

    def test_stop_before_network(self):
        self.m.stop_file.touch()
        with self.assertRaises(mirror.Stop):
            self.m.run()
        self.assertEqual(self.server.seen, [])
        self.assertTrue(self.m.stop_file.exists())

    def test_stop_during_transfer_and_resume(self):
        self.m.run(limit=1)
        self.m.priorities = ["a.bin"]
        real_wait = self.m.wait
        def stop_after_chunk(delay):
            row = self.m.db.execute("SELECT status FROM entries WHERE rel='a.bin'").fetchone()
            if row and row[0] == "partial":
                self.m.stop_file.touch()
            real_wait(delay)
        self.m.wait = stop_after_chunk
        with self.assertRaises(mirror.Stop):
            self.m.run()
        self.assertEqual(self.m.db.execute("SELECT status FROM entries WHERE rel='a.bin'").fetchone()[0], "partial")
        self.m.stop_file.unlink()
        self.m.wait = real_wait
        self.m.run()
        self.assertEqual((self.m.dest/"originals/a.bin").read_bytes(), Handler.body)

    def test_stop_during_cooldown_and_restart_respects_saved_epoch(self):
        self.mock_clock()
        self.server.responses["/tree/"] = deque([(503, "120")])
        initial_epoch = self.epoch

        def stop_during_wait(delay):
            if delay >= 60:
                with patch.object(mirror.time, "sleep", lambda _: self.m.stop_file.touch()):
                    mirror.Mirror.wait(self.m, delay)

        self.m.wait = stop_during_wait
        with self.assertRaisesRegex(mirror.Stop, "STOP file"):
            self.m.run(limit=1)
        self.assertEqual(self.server.seen, [("/robots.txt", None), ("/tree/", None)])
        summary = json.loads((self.m.dest / "manifests" / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["host_not_before_epoch"], initial_epoch + 120)
        self.assertEqual(summary["host_last_error"], "HTTP 503")
        self.assertEqual(self.m.db.execute("SELECT status,attempts FROM entries WHERE rel=''").fetchone()[:],
                         ("deferred", 1))

        reopened = mirror.Mirror(self.root, self.m.dest, reserve_gib=0)
        self.addCleanup(reopened.db.close)
        reopened.wait = self.advance_cooldown
        with self.assertRaises(mirror.Stop):
            reopened.run(limit=1)
        self.assertEqual(len(self.server.seen), 2)
        self.epoch += 30
        self.m.stop_file.unlink()
        reopened.run(limit=1)
        self.assertEqual(self.cooldown_waits, [90])
        self.assertEqual(self.server.seen[-2:], [("/robots.txt", None), ("/tree/", None)])
        self.assertEqual(reopened.meta("host_failures"), "0")
        self.assertEqual(reopened.meta("not_before"), "0")

    def test_automatic_policy_and_entry_retry_honors_date_and_seconds(self):
        self.mock_clock()
        self.server.responses["/robots.txt"] = deque([(408, "120")])
        self.server.responses["/tree/"] = deque([(429, formatdate(self.epoch + 640, usegmt=True))])
        self.m.run(limit=1)
        self.assertEqual(self.cooldown_waits, [120, 520])
        self.assertEqual(self.server.seen, [("/robots.txt", None), ("/robots.txt", None),
                                           ("/tree/", None), ("/tree/", None)])
        self.assertEqual(self.m.db.execute("SELECT status,attempts FROM entries WHERE rel=''").fetchone()[:],
                         ("verified", 2))

    def test_persistent_failure_stops_and_retains_extended_cooldown(self):
        self.mock_clock()
        self.server.responses["/tree/"] = deque([(503, None)] * 4)
        with self.assertRaisesRegex(mirror.Stop, "Persistent host failures"):
            self.m.run()
        self.assertEqual(self.cooldown_waits, [60, 300, 900])
        self.assertEqual(self.m.meta("host_failures"), "4")
        self.assertEqual(float(self.m.meta("not_before")), self.epoch + 3600)
        self.assertEqual(self.m.db.execute("SELECT status,attempts FROM entries WHERE rel=''").fetchone()[:],
                         ("deferred", 4))
        self.assertEqual(self.server.seen.count(("/tree/", None)), 4)

    def test_early_disconnect_preserves_partial_and_resumes_with_range(self):
        self.mock_clock()
        self.m.run(limit=1)
        self.m.priorities = ["a.bin"]
        self.server.cut = "/tree/a.bin"
        self.m.run(limit=1)
        self.assertEqual(self.cooldown_waits, [60])
        self.assertEqual(self.server.seen[-2:], [("/tree/a.bin", None), ("/tree/a.bin", "bytes=4-")])
        self.assertEqual((self.m.dest / "originals/a.bin").read_bytes(), Handler.body)
        self.assertEqual(self.m.db.execute("SELECT status,attempts FROM entries WHERE rel='a.bin'").fetchone()[:],
                         ("verified", 2))

    def test_disconnect_before_headers_automatically_retries(self):
        self.mock_clock()
        self.m.run(limit=1)
        self.m.priorities = ["a.bin"]
        self.server.disconnect = "/tree/a.bin"
        self.m.run(limit=1)
        self.assertEqual(self.cooldown_waits, [60])
        self.assertEqual(self.server.seen[-2:], [("/tree/a.bin", None), ("/tree/a.bin", None)])
        self.assertEqual((self.m.dest / "originals/a.bin").read_bytes(), Handler.body)

    def test_access_denial_terminates_without_retry(self):
        self.mock_clock()
        self.m.run(limit=1)
        self.m.priorities = ["a.bin"]
        self.server.responses["/tree/a.bin"] = deque([(403, "300")])
        with self.assertRaisesRegex(mirror.Stop, "Access denied"):
            self.m.run()
        self.assertEqual(self.cooldown_waits, [])
        self.assertEqual(self.server.seen[-2:], [("/robots.txt", None), ("/tree/a.bin", None)])
        self.assertEqual(self.m.db.execute("SELECT status,attempts FROM entries WHERE rel='a.bin'").fetchone()[:],
                         ("blocked", 1))

    def test_config_and_existing_state(self):
        cfg = self.m.dest/"targets.toml"
        cfg.write_text('[targets.local]\nroot = "'+self.root+'"\ndestination = "."\n', encoding="utf-8")
        self.assertEqual(mirror.load_config(cfg)["destination"].resolve(), self.m.dest)
        self.m.run(limit=1)
        reopened = mirror.Mirror(**mirror.load_config(cfg))
        try:
            self.assertEqual(reopened.meta("root"), self.root)
            self.assertEqual(reopened.db.execute("SELECT status FROM entries WHERE rel=''").fetchone()[0], "verified")
        finally:
            reopened.db.close()

    def test_status_read_only(self):
        cfg = self.m.dest/"targets.toml"
        cfg.write_text('[targets.local]\nroot = "'+self.root+'"\ndestination = "."\n', encoding="utf-8")
        self.assertEqual(mirror.main(["--config", str(cfg), "--status"]), 0)
        self.assertEqual(self.server.seen, [])

    def test_robot_precedence(self):
        r = mirror.Robots("User-agent: *\nDisallow: /tree/*\nAllow: /tree/sub/$\nCrawl-delay: 12\n")
        self.assertFalse(r.allowed(self.root+"a.bin"))
        self.assertTrue(r.allowed(self.root+"sub/"))
        self.assertEqual(r.delay, 12)
