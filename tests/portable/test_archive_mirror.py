"""Local-only regression tests for the research mirror."""
import hashlib
import http.server
import importlib.util
from pathlib import Path
import sqlite3
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
        if self.server.fail == self.path:
            self.send_response(503)
            self.send_header("Retry-After", "120")
            self.end_headers()
            return
        offset = int(self.headers["Range"][6:-1]) if self.headers.get("Range") else 0
        self.send_response(206 if offset else 200)
        if offset:
            self.send_header("Content-Range", f"bytes {offset}-{len(content)-1}/{len(content)}")
        self.send_header("ETag", '"fixed"')
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(content)-offset))
        self.end_headers()
        self.wfile.write(content[offset:])


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.seen, self.server.fail = [], None
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

    def test_cooldown_persists(self):
        self.server.fail = "/tree/"
        with self.assertRaises(mirror.Stop):
            self.m.run()
        count = len(self.server.seen)
        with self.assertRaises(mirror.Stop):
            self.m.run()
        self.assertEqual(len(self.server.seen), count)

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
