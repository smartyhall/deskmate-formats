"""Exercise the published observation through a real, local HTTP listener."""

from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from io import BytesIO
import json
from random import Random
import re
import socket
from threading import Barrier, Event, Thread
import unittest
from unittest.mock import patch

from deskmate_formats.observer.demo import MACHINES, publish_scene
from deskmate_formats.observer.frames import Frame
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.publication import Machine, ObservationRegistry, decode_cp437, host_time_ms
from test_observer_publication import PILLOW, observation, png_fixture


class LocalObserver(unittest.TestCase):
    machines = (Machine("fixture", "PC <Test>"),)

    def setUp(self):
        self.registry = ObservationRegistry(self.machines, history_limit=5, stale_after=60)
        self.server = ObserverServer(self.registry, port=0)
        self.addCleanup(self.server.server_close)
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02})
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        if self.thread.is_alive():
            self.server.shutdown()
            self.thread.join(timeout=5)
            self.assertFalse(self.thread.is_alive())

    @property
    def host(self):
        return f"127.0.0.1:{self.server.port}"

    def request(self, path, method="GET", headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.port, timeout=4)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
        finally:
            connection.close()

    def raw(self, data):
        with socket.create_connection(self.server.server_address, timeout=4) as peer:
            peer.sendall(data)
            # Read the framed reply before closing, including when extra request
            # bytes are waiting and the server closes after an error response.
            response = bytearray()
            while b"\r\n\r\n" not in response:
                part = peer.recv(4096)
                if not part:
                    break
                response.extend(part)
            head, _, body = bytes(response).partition(b"\r\n\r\n")
            first, *lines = head.split(b"\r\n")
            headers = {key.lower(): value.strip() for key, value in
                       (line.split(b":", 1) for line in lines)}
            length = int(headers[b"content-length"])
            while len(body) < length:
                part = peer.recv(length - len(body))
                if not part:
                    break
                body += part
            return first, headers, body


class HttpTests(LocalObserver):
    @property
    def stream(self):
        return self.registry.stream("fixture")

    def test_empty_startup_and_assets(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(self.request("/healthz")[2], b"ok\r\n")
        status = json.loads(self.request("/api/status")[2])
        self.assertEqual(status["machine"], {"id": "fixture", "label": "PC <Test>"})
        self.assertIsNone(status["observation"])
        self.assertTrue(status["stale"])
        self.assertEqual(status["timeline"], [])
        self.assertEqual(self.request("/frame.png")[0], 404)
        self.assertEqual(self.request("/frame.gif")[0], 404)
        modern = self.request("/")[2]
        self.assertIn(b"PC &lt;Test&gt;", modern)
        self.assertIn(b"/dashboard.js", modern)
        self.assertIn(b"Classic view", modern)
        css = self.request("/dashboard.css")
        js = self.request("/dashboard.js")
        self.assertIn("text/css", css[1]["content-type"])
        self.assertIn("javascript", js[1]["content-type"])
        self.assertIn(b'fetch("api/status"', js[2])

    def test_http_10_legacy_text_and_escaping(self):
        text = decode_cp437(row.encode("cp437") for row in ("╔═╗ café", '<script> & "<"'))
        self.stream.publish(observation(screen=text))
        line, headers, legacy = self.raw(b"GET /legacy/ HTTP/1.0\r\n\r\n")
        self.assertEqual(line, b"HTTP/1.0 200 OK")
        self.assertEqual(headers[b"content-type"], b"text/html; charset=us-ascii")
        self.assertEqual(int(headers[b"content-length"]), len(legacy))
        self.assertIn(b"HTML 2.0", legacy)
        self.assertIn(b'href="./">Refresh', legacy)
        self.assertIn(b"+=+ cafe", legacy)
        self.assertIn(b'&lt;script&gt; &amp; "&lt;"', legacy)
        self.assertNotIn(b"<script", legacy.lower())
        self.assertNotIn(b"<style", legacy.lower())
        self.assertNotIn(b"set-cookie", headers)
        line, headers, plain = self.raw(b"GET /status.txt HTTP/1.0\r\n\r\n")
        self.assertEqual(line, b"HTTP/1.0 200 OK")
        self.assertEqual(headers[b"content-type"], b"text/plain; charset=us-ascii")
        self.assertEqual(int(headers[b"content-length"]), len(plain))
        self.assertIn(b"+=+ cafe\r\n<script>", plain)
        status = json.loads(self.request("/api/status")[2])
        self.assertEqual(status["observation"]["screen"], text)
        for path in ("/", "/legacy/", "/status.txt", "/api/status", "/dashboard.js", "/healthz", "/frame.png"):
            code, headers, body = self.request(path, method="HEAD")
            self.assertEqual(code, 404 if path == "/frame.png" else 200)
            self.assertGreater(int(headers["content-length"]), 0)
            self.assertEqual(body, b"")

    def test_path_method_body_and_header_rejection(self):
        for path, expected in (
            ("/../status.txt", 400), ("/i/fixture/./", 400), ("/%2e%2e/status.txt", 400),
            ("/i/fixture/..%5cstatus.txt", 400), ("//localhost/status.txt", 400),
            ("/status.txt?source=private", 400), ("/api/status?", 400), ("/frame.gif?x=1", 400),
            ("/healthz?frame=" + "0" * 32 + ".0.1", 400), ("/status.txt#fragment", 400),
            ("http://127.0.0.1/status.txt", 400), ("/reset", 404), ("/memory", 404),
            ("/i/missing/status.txt", 404), ("/i/fixture", 404), ("/i/fixture/healthz", 404),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], expected)
        for method in ("POST", "PUT", "OPTIONS", "DELETE", "CONNECT", "PATCH", "TRACE"):
            with self.subTest(method=method):
                code, headers, _ = self.request("/healthz", method=method)
                self.assertEqual(code, 405)
                self.assertEqual(headers["allow"], "GET, HEAD")

        requests = (
            (b"GET / HTTP/1.1\r\n\r\n", b"400"),
            (b"GET / HTTP/1.1\r\nHost: bad.example\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nHost: 127.0.0.1:1\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nHost: localhost.bad.example\r\n\r\n", b"400"),
            (b"GET / HTTP/1.1\r\nHost: " + self.host.encode() + b"\r\nHOST: bad.example\r\n\r\n", b"400"),
            (b"GET /x\x00 HTTP/1.0\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nX-Test: bad\x1bdata\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nX-Test: bad\nsplit\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nX-Test: hi\r\n continuation\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nContent-Length: 1\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\nTransfer-Encoding: chunked\r\n\r\n", b"400"),
            (b"GET / HTTP/1.0\r\n\r\nunexpected body", b"400"),
            (b"GET / HTTP/1.0\r\nX-Large: " + b"x" * 8190, b"431"),
            (b"GET / HTTP/0.9\r\n\r\n", b"400"),
        )
        for data, expected in requests:
            with self.subTest(data=data[:80]):
                line, headers, body = self.raw(data)
                self.assertEqual(line.split()[1], expected)
                self.assertEqual(int(headers[b"content-length"]), len(body))
                self.assertNotIn(b"bad.example", body)
        code, headers, _ = self.request("/api/status", headers={"Origin": "http://other.example"})
        self.assertEqual(code, 403)
        self.assertNotIn("access-control-allow-origin", headers)
        self.assertEqual(self.request("/healthz", headers={"Origin": "http://" + self.host})[0], 200)
        self.assertEqual(self.request("/healthz", headers={"Host": f"localhost:{self.server.port}"})[0], 200)

    def test_stalled_request_has_deadline_and_abandoned_viewer_does_not_block(self):
        with patch("deskmate_formats.observer.http._READ_SECONDS", 0.4):
            with socket.create_connection(self.server.server_address, timeout=3) as slow:
                slow.sendall(b"GET /status.txt HTTP/1.0\r\n")
                self.stream.publish(observation(emulated_ms=50))
                with socket.create_connection(self.server.server_address, timeout=3) as abandoned:
                    abandoned.sendall(b"GET /status.txt HTTP/1.0\r\n\r\n")
                self.assertEqual(self.request("/healthz")[0], 200)
                self.assertEqual(slow.recv(64), b"")
        status = json.loads(self.request("/api/status")[2])
        self.assertEqual(status["observation"]["emulated_ms"], 50)
        self.assertEqual(len(status["timeline"]), 1)

    def test_silence_marks_the_last_report_stale(self):
        with patch("deskmate_formats.observer.publication.monotonic", return_value=100) as clock:
            self.stream.publish(observation(screen="Frozen screen", emulated_ms=150))
            first = json.loads(self.request("/api/status")[2])
            clock.return_value = 160
            expired = json.loads(self.request("/api/status")[2])
            self.assertIn(b"STALE - last reported held", self.request("/legacy/")[2])
        self.assertFalse(first["stale"])
        self.assertTrue(expired["stale"])
        self.assertEqual(expired["observation"], first["observation"])
        self.assertEqual(expired["timeline"], first["timeline"])

    def test_worker_limit_and_shutdown_wait_for_stalled_clients(self):
        entered = Event()
        handler = self.server.RequestHandlerClass

        class SignallingHandler(handler):
            def _read_headers(self):
                entered.set()
                return super()._read_headers()

        self.server.RequestHandlerClass = SignallingHandler
        for _ in range(self.server.request_queue_size - 1):
            self.assertTrue(self.server._slots.acquire(blocking=False))
        with patch("deskmate_formats.observer.http._READ_SECONDS", 0.5):
            with socket.create_connection(self.server.server_address, timeout=3) as first:
                self.assertTrue(entered.wait(2))
                with socket.create_connection(self.server.server_address, timeout=3) as surplus:
                    self.assertEqual(surplus.recv(16), b"")
                self.stop()
                self.server.server_close()
                self.assertEqual(first.recv(16), b"")
        self.assertEqual(self.server.fileno(), -1)
        self.assertFalse(self.thread.is_alive())
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", self.server.port), timeout=1)

    def test_http_only_reads_publication_and_never_connects_outbound(self):
        self.stream.publish(observation())
        before = self.stream.view()
        connect = socket.socket.connect
        connect_ex = socket.socket.connect_ex

        def guard(operation):
            def local_only(peer, address):
                if address != self.server.server_address:
                    self.fail("attempted a connection other than test HTTP loopback")
                return operation(peer, address)
            return local_only

        paths = ("/", "/legacy/", "/api/status", "/status.txt", "/frame.png", "/frame.gif", "/healthz")
        with patch.object(socket.socket, "connect", guard(connect)), \
                patch.object(socket.socket, "connect_ex", guard(connect_ex)):
            with ThreadPoolExecutor(max_workers=6) as pool:
                replies = list(pool.map(self.request, paths * 5))
        self.assertEqual(sum(code == 200 for code, _, _ in replies), 25)
        self.assertEqual(sum(code == 404 for code, _, _ in replies), 10)
        self.assertEqual(self.stream.view(), before)
        self.assertEqual(before.observation.emulated_ms, 20)

    @unittest.skipUnless(PILLOW, "requires the observer extra")
    def test_private_frame_metadata_and_request_headers_are_never_published(self):
        from PIL import Image

        secret = b"synthetic-credential-sentinel"
        private_path = b"C:/private/do-not-export.img"
        source = png_fixture(metadata=(secret + b" " + private_path).decode())
        self.assertIn(secret, source)
        frame = Frame(source, generation=1, captured_at_ms=10_000, rendered_at_ms=9_950)
        self.stream.publish(observation(frame=frame))
        for route in ("/api/status", "/status.txt", "/legacy/", "/frame.png", "/frame.gif"):
            code, headers, body = self.request(route, headers={"Authorization": secret.decode()})
            self.assertEqual(code, 200)
            self.assertNotIn(secret, body)
            self.assertNotIn(private_path, body)
            self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(self.request("/api/status")[2])
        self.assertEqual(set(payload), {"machine", "publication_session", "served_at_ms", "stale", "observation",
                                        "timeline"})
        self.assertEqual(set(payload["observation"]["frame"]), {
            "key", "generation", "width", "height", "captured_at_ms", "rendered_at_ms",
            "rendered_emulated_ms", "age_ms", "age_basis",
        })
        self.assertEqual(payload["observation"]["frame"]["age_basis"], "render")
        with Image.open(BytesIO(self.request("/frame.png")[2])) as image:
            self.assertEqual(image.info, {})
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))
            self.assertEqual(image.getpixel((1, 0)), (250, 20, 10))

    @unittest.skipUnless(PILLOW, "requires the observer extra")
    def test_versioned_frame_only_serves_matching_latest_generation(self):
        frame = Frame(png_fixture(), generation=1, captured_at_ms=10_000)
        self.stream.publish(observation(frame=frame))
        payload = json.loads(self.request("/api/status")[2])
        key = payload["observation"]["frame"]["key"]
        path = f"/frame.png?frame={key}"
        self.assertEqual(self.request(path)[2], frame.png)
        _, headers, body = self.request(path, method="HEAD")
        self.assertEqual(int(headers["content-length"]), len(frame.png))
        self.assertEqual(body, b"")
        self.stream.mark_unavailable(sequence=2, observed_at_ms=11_000)
        self.assertEqual(self.request(path)[2], frame.png)
        self.assertIn(b"STALE - disconnected", self.request("/legacy/")[2])
        self.stream.publish(observation(sequence=3, generation=1))
        self.assertEqual(self.request(path)[0], 404)
        new_frame = Frame(png_fixture(), generation=1, captured_at_ms=10_000)
        self.stream.publish(observation(sequence=4, generation=1, frame=new_frame))
        self.assertEqual(self.request("/frame.png")[2], new_frame.png)
        self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request("/frame.png?frame=" + "0" * 32 + ".1.1")[0], 404)
        self.assertEqual(self.request("/frame.png?frame=" + "0" * 32 + ".01.1")[0], 400)

    @unittest.skipUnless(PILLOW, "requires the observer extra")
    def test_viewer_that_does_not_read_a_large_frame_cannot_delay_publication(self):
        from PIL import Image

        image = Image.frombytes("RGB", (768, 320), Random(5).randbytes(768 * 320 * 3))
        source = BytesIO()
        image.save(source, "PNG")
        frame = Frame(source.getvalue(), generation=0, captured_at_ms=10_000)
        with Image.open(BytesIO(frame.gif)) as gif:
            self.assertEqual(gif.width, 640)
            self.assertLessEqual(gif.height, 480)
        self.stream.publish(observation(frame=frame))
        writing = Event()
        handler = self.server.RequestHandlerClass

        class LimitedSendBuffer(handler):
            def _respond(self, code, content_type, body):
                if content_type == "image/png":
                    self.request.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                    writing.set()
                return super()._respond(code, content_type, body)

        self.server.RequestHandlerClass = LimitedSendBuffer
        with socket.socket() as slow:
            slow.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            slow.settimeout(3)
            slow.connect(self.server.server_address)
            slow.sendall(b"GET /frame.png HTTP/1.0\r\n\r\n")
            self.assertTrue(writing.wait(2))
            self.stream.publish(observation(sequence=2, emulated_ms=25))
            self.assertEqual(self.request("/frame.png")[0], 404)
            status = json.loads(self.request("/api/status")[2])
            self.assertEqual(status["observation"]["emulated_ms"], 25)
            self.assertEqual(len(status["timeline"]), 2)


class SyntheticLabTests(LocalObserver):
    machines = MACHINES

    @unittest.skipUnless(PILLOW, "requires the observer extra")
    def test_same_scene_through_modern_and_classic_interfaces(self):
        from PIL import Image

        stream = self.registry.stream(MACHINES[0].instance_id)
        now = host_time_ms()
        expected = ["STATION FIRMWARE", "COMMAND INTERPRETER", "MEDIA CHECK", "DIAGNOSTIC PASS",
                    "DIAGNOSTIC PASS"]
        keys, images = [], []
        for index, scene in enumerate(expected):
            publish_scene(stream, index, now + index)
            payload = json.loads(self.request("/api/status")[2])
            snapshot = payload["observation"]
            self.assertEqual(snapshot["sequence"], index)
            self.assertIn(scene, snapshot["screen"])
            self.assertIn(scene.encode(), self.request("/status.txt")[2])
            classic = self.request("/legacy/")[2]
            self.assertIn(scene.encode(), classic)
            key = snapshot["frame"]["key"]
            gif_url = re.search(rb'src="\.\.(/frame\.gif\?frame=[^"]+)"', classic)[1].decode()
            self.assertEqual(gif_url, f"/frame.gif?frame={key}")
            _, png_headers, png = self.request(f"/frame.png?frame={key}")
            line, gif_headers, gif = self.raw(f"GET {gif_url} HTTP/1.0\r\n\r\n".encode())
            self.assertEqual(line, b"HTTP/1.0 200 OK")
            self.assertEqual(png_headers["content-type"], "image/png")
            self.assertEqual(gif_headers[b"content-type"], b"image/gif")
            self.assertEqual(int(gif_headers[b"content-length"]), len(gif))
            self.assertTrue(gif.startswith(b"GIF87a"))
            with Image.open(BytesIO(png)) as native, Image.open(BytesIO(gif)) as legacy:
                self.assertEqual(native.size, (640, 350))
                self.assertEqual(legacy.size, native.size)
                self.assertEqual(legacy.n_frames, 1)
                self.assertGreater(len(legacy.getcolors()), 1)
                self.assertLessEqual(len(legacy.getpalette()) // 3, 64)
                self.assertEqual(native.getpixel((0, 0)), legacy.convert("RGB").getpixel((0, 0)))
            keys.append(key)
            images.append(png)
        self.assertEqual(len(set(keys)), 4)
        self.assertEqual(len(set(images)), 4)
        self.assertEqual((keys[3], images[3]), (keys[4], images[4]))
        self.assertTrue(payload["stale"])
        self.assertEqual(snapshot["connection"], "disconnected")
        self.assertEqual(snapshot["emulated_ms"], 7330)
        self.assertEqual(snapshot["frame"]["rendered_emulated_ms"], 7290)
        box_lines = [line for line in snapshot["screen"].splitlines() if line.startswith(tuple("╔║╠╚"))]
        self.assertEqual({len(line) for line in box_lines}, {30})
        self.assertIn(b"STALE", classic)

    def test_independent_streams_publish_and_poll_concurrently(self):
        barrier = Barrier(len(self.machines))
        now = host_time_ms()

        def exercise(entry):
            machine, last = entry
            stream = self.registry.stream(machine.instance_id)
            path = f"/i/{machine.instance_id}/api/status"
            barrier.wait(timeout=5)
            for index in range(last + 1):
                publish_scene(stream, index, now + index, with_frames=PILLOW)
                code, _, body = self.request(path)
                self.assertEqual(code, 200)
                payload = json.loads(body)
                self.assertEqual(payload["machine"]["id"], machine.instance_id)
                self.assertEqual(payload["observation"]["sequence"], index)
                self.assertEqual(payload["timeline"][-1]["sequence"], index)
            return payload

        with ThreadPoolExecutor(max_workers=3) as pool:
            states = list(pool.map(exercise, zip(self.machines, (2, 4, 6), strict=True)))
        self.assertEqual([s["observation"]["generation"] for s in states], [0, 0, 1])
        self.assertEqual([s["observation"]["emulated_ms"] for s in states], [4250, 7330, 1200])
        self.assertEqual([s["stale"] for s in states], [False, True, False])
        self.assertEqual(len(states[2]["timeline"]), 5)
        if PILLOW:
            frames = []
            for machine, state in zip(self.machines, states, strict=True):
                key = state["observation"]["frame"]["key"]
                frames.append(self.request(f"/i/{machine.instance_id}/frame.gif?frame={key}")[2])
            self.assertEqual(len(set(frames)), 3)
            foreign_key = states[1]["observation"]["frame"]["key"]
            self.assertEqual(self.request(f"/frame.png?frame={foreign_key}")[0], 404)
        for machine in self.machines:
            self.assertIn(f'href="/i/{machine.instance_id}/"'.encode(), self.request("/")[2])
        self.assertIn(b"DIAGNOSTIC PASS", self.request("/i/synthetic-at/legacy/")[2])
        self.assertEqual(json.loads(self.request("/api/status")[2])["machine"]["id"], "synthetic-rsx")
