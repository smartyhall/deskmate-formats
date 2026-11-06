"""Bounded loopback-only HTTP/1.0 replies for a small set of read routes."""

from email.utils import formatdate
from http import HTTPStatus
from importlib.resources import files
import json
import re
from socketserver import BaseRequestHandler, TCPServer, ThreadingMixIn
import sys
from threading import BoundedSemaphore
from time import monotonic

from .agent_http import MAX_PAGE, match_route, query_snapshot
from .agent_publication import AgentPublication
from .presentation import dashboard, frame_key, legacy_page, plain_status, status
from .publication import INSTANCE_ID, ObservationRegistry, host_time_ms

_HEADER_LIMIT = 8192
_READ_SECONDS = 3
_WRITE_SECONDS = 3
_TOKEN = re.compile(rb"[!#$%&'*+\-.^_|~0-9A-Za-z]+")
_REQUEST_LINE = re.compile(rb"([^ ]+) ([^ ]+) HTTP/1\.([01])")
_TARGET = re.compile(r"/[a-z0-9/._-]*(?:\?[a-z0-9=.&_-]+)?")
_FRAME_QUERY = re.compile(r"frame=[0-9a-f]{32}\.(?:0|[1-9][0-9]{0,15})\.(?:0|[1-9][0-9]{0,15})")
_POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; "
           "connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'")
_PLAIN = "text/plain; charset=us-ascii"
_IMAGE_TYPES = {"/frame.png": "image/png", "/frame.gif": "image/gif"}
_ROUTES = {"/", "/legacy/", "/api/status", "/status.txt", *_IMAGE_TYPES}
_ASSETS = {
    "/dashboard.css": "text/css; charset=utf-8",
    "/dashboard.js": "text/javascript; charset=utf-8",
}


class _RequestError(Exception):
    def __init__(self, status_code):
        self.status_code = HTTPStatus(status_code)


def _ascii_body(text):
    return text.replace("\n", "\r\n").encode("ascii")


class _RequestHandler(BaseRequestHandler):
    def handle(self):
        self._head = False
        try:
            try:
                target = self._parse()
                content_type, body = self.server.resource(target)
                self._respond(HTTPStatus.OK, content_type, body)
            except _RequestError as error:
                self._respond(error.status_code, _PLAIN, _ascii_body(error.status_code.phrase + "\n"))
        except OSError:
            # Peer gone, or a read/write deadline expired.
            return

    def _read_headers(self):
        deadline = monotonic() + _READ_SECONDS
        received = bytearray()
        while len(received) < _HEADER_LIMIT:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError
            self.request.settimeout(remaining)
            part = self.request.recv(min(4096, _HEADER_LIMIT - len(received)))
            if not part:
                raise _RequestError(400)
            received.extend(part)
            self._head = received.startswith(b"HEAD ")
            end = received.find(b"\r\n\r\n")
            if end >= 0:
                if end + 4 != len(received):
                    raise _RequestError(400)  # No request body or pipelining.
                return bytes(received[:end]).split(b"\r\n")
        raise _RequestError(431)

    def _parse(self):
        line, *headers = self._read_headers()
        match = _REQUEST_LINE.fullmatch(line)
        if match is None:
            raise _RequestError(400)
        method, target, version = match.groups()
        if not _TOKEN.fullmatch(method):
            raise _RequestError(400)
        self._head = method == b"HEAD"
        if method not in (b"GET", b"HEAD"):
            raise _RequestError(405)
        if not all(33 <= byte <= 126 for byte in target):
            raise _RequestError(400)
        values = {}
        for header in headers:
            key, sep, value = header.partition(b":")
            if not sep or not _TOKEN.fullmatch(key) or not all(32 <= byte <= 126 for byte in value):
                raise _RequestError(400)
            key = key.lower()
            if key in (b"host", b"origin", b"content-length", b"transfer-encoding"):
                if key in values:
                    raise _RequestError(400)
                values[key] = value.strip().decode("ascii")
        host = values.get(b"host")
        if ((version == b"1" or host is not None)
                and (host is None or host.lower() not in self.server.allowed_hosts)):
            raise _RequestError(400)
        origin = values.get(b"origin")
        if origin is not None and (host is None or origin.lower() != f"http://{host.lower()}"):
            raise _RequestError(403)
        if b"transfer-encoding" in values or values.get(b"content-length", "0") != "0":
            raise _RequestError(400)
        return target.decode("ascii")

    def _respond(self, code, content_type, body):
        allow = "Allow: GET, HEAD\r\n" if code is HTTPStatus.METHOD_NOT_ALLOWED else ""
        headers = (
            f"HTTP/1.0 {code.value} {code.phrase}\r\n"
            f"Date: {formatdate(usegmt=True)}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Cache-Control: no-store\r\n"
            "Pragma: no-cache\r\n"
            "Expires: Thu, 01 Jan 1970 00:00:00 GMT\r\n"
            "Connection: close\r\n"
            "X-Content-Type-Options: nosniff\r\n"
            "X-Frame-Options: DENY\r\n"
            "Cross-Origin-Resource-Policy: same-origin\r\n"
            "Referrer-Policy: no-referrer\r\n"
            f"Content-Security-Policy: {_POLICY}\r\n"
            f"{allow}\r\n"
        ).encode("ascii")
        self.request.settimeout(_WRITE_SECONDS)
        self.request.sendall(headers)
        if not self._head:
            self.request.sendall(body)


class ObserverServer(ThreadingMixIn, TCPServer):
    """Serve a registry on IPv4 loopback. Use port 0 for an ephemeral port."""

    allow_reuse_address = sys.platform != "win32"
    request_queue_size = 16

    def __init__(self, registry: ObservationRegistry, *, port=8086,
                 agent_publication: AgentPublication | None = None, agent_page_limit=MAX_PAGE):
        if type(registry) is not ObservationRegistry:
            raise ValueError("expected an observation registry")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("invalid observer port")
        if agent_publication is not None and type(agent_publication) is not AgentPublication:
            raise ValueError("expected an agent publication")
        if type(agent_page_limit) is not int or not 1 <= agent_page_limit <= MAX_PAGE:
            raise ValueError("invalid agent page limit")
        self.registry = registry
        self._agent_publication = agent_publication if agent_publication is not None else AgentPublication()
        self._agent_page_limit = agent_page_limit
        self._machines = registry.machines
        self._slots = BoundedSemaphore(self.request_queue_size)
        assets = files(__package__)
        self._assets = {path: (mime, assets.joinpath(path[1:]).read_bytes())
                        for path, mime in _ASSETS.items()}
        super().__init__(("127.0.0.1", port), _RequestHandler)
        self.port = self.server_address[1]
        hosts = ("127.0.0.1", "localhost")
        port_hosts = frozenset(f"{host}:{self.port}" for host in hosts)
        self.allowed_hosts = port_hosts.union(hosts) if self.port == 80 else port_hosts

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()

    def resource(self, target):
        if not _TARGET.fullmatch(target):
            raise _RequestError(400)
        path, _, query = target.partition("?")
        if "//" in path or any(part in (".", "..") for part in path.split("/")):
            raise _RequestError(400)
        agent_route = match_route(path)
        if agent_route is not None:
            try:
                data = query_snapshot(self._agent_publication.view(), agent_route, query, self._agent_page_limit)
            except ValueError:
                raise _RequestError(400) from None
            except LookupError:
                raise _RequestError(404) from None
            return "application/json", json.dumps(data, ensure_ascii=False).encode("utf-8")
        if query and (not _FRAME_QUERY.fullmatch(query) or path.rsplit("/", 1)[-1] not in
                      ("frame.png", "frame.gif")):
            raise _RequestError(400)
        if path == "/healthz":
            return _PLAIN, b"ok\r\n"
        if path in self._assets:
            return self._assets[path]
        instance_id = self._machines[0].instance_id
        if path.startswith("/i/"):
            instance_id, slash, route = path[3:].partition("/")
            if not slash or not INSTANCE_ID.fullmatch(instance_id):
                raise _RequestError(404)
            path = "/" + route
        if path not in _ROUTES:
            raise _RequestError(404)
        try:
            stream = self.registry.stream(instance_id)
        except KeyError:
            raise _RequestError(404) from None
        if path == "/":
            return "text/html; charset=utf-8", dashboard(stream.machine, self._machines).encode("utf-8")

        view, now = stream.view(), host_time_ms()
        if path == "/api/status":
            data = json.dumps(status(stream.machine, view, now), ensure_ascii=False).encode("utf-8")
            return "application/json", data
        if path == "/status.txt":
            return _PLAIN, _ascii_body(plain_status(stream.machine, view, now))
        if path == "/legacy/":
            return "text/html; charset=us-ascii", _ascii_body(legacy_page(stream.machine, self._machines, view, now))
        observation = view.observation
        if (observation is None or observation.frame is None
                or query and query.removeprefix("frame=") != frame_key(view)):
            raise _RequestError(404)
        frame = observation.frame
        return _IMAGE_TYPES[path], frame.png if path == "/frame.png" else frame.gif
