"""Verified-input tests against an authored native peer; no emulator or ROMs.

The peer speaks the real authenticated line protocol over loopback so the tests
exercise the actual client transport, reply validation and facility logic. Guest
state is a 25x80 text screen plus a BIOS keyboard ring in low memory. Faults are
injected deliberately: dropped characters, substituted characters, a keyboard
buffer that never drains, and a screen that does not change.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('box_client', ROOT / 'tools/86box_client.py')
box = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(box)
SPEC_INPUT = importlib.util.spec_from_file_location(
    'automation_input', ROOT / 'src/deskmate_formats/automation/input.py')
inp = importlib.util.module_from_spec(SPEC_INPUT)
SPEC_INPUT.loader.exec_module(inp)

TOKEN = 'a1' * 32
ANCHOR_ROW = 2
PLAIN = '1234567890-=qwertyuiop[]asdfghjkl;\'`\\zxcvbnm,./'
SCANS = list(range(2, 14)) + list(range(16, 28)) + list(range(30, 42)) + [43] + list(range(44, 54))
KEYMAP = {scan: char for char, scan in zip(PLAIN, SCANS)}
KEYMAP[57] = ' '


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))


def screen_png(color):
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + bytes(color)))
            + chunk(b'IEND', b''))


class Peer:
    """One authenticated native peer with a synthetic guest and fault injection."""

    def __init__(self, *, drop=(), substitute=None, swallow=False, queue_only=False,
                 drop_last=False, history=False, bios_mode=3, blink=False, drain=True):
        self.ms = 0
        self.frames = 1
        self.bios_mode = bios_mode
        self.blink = blink
        self.screen = 'desktop'
        self.typed = ''
        self.received = ''
        self.drop = set(drop)
        self.substitute = dict(substitute or {})
        self.swallow = swallow
        self.queue_only = queue_only
        self.drop_last = drop_last
        self.history = history
        self.drain = drain
        self.shift = False
        self.head = 0x1E
        self.tail = 0x1E
        self.requests = []
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.error = None
        self.worker = threading.Thread(target=self._serve, daemon=True)
        self.worker.start()

    def close(self):
        self.listener.close()

    def _serve(self):
        try:
            conn, _ = self.listener.accept()
            with conn:
                stream = conn.makefile('rwb')
                auth = stream.readline().decode('ascii').rstrip('\n')
                if auth != 'auth ' + TOKEN:
                    stream.write(b'{"ok":false,"error":"authentication required"}\n')
                    stream.flush()
                    return
                stream.write(b'{"ok":true,"auth":true}\n')
                stream.flush()
                for line in stream:
                    request = line.decode('ascii').rstrip('\n')
                    self.requests.append(request)
                    stream.write((json.dumps(self.reply(request)) + '\n').encode('ascii'))
                    stream.flush()
        except Exception as exc:  # pragma: no cover - surfaced by the test body
            self.error = exc

    # ---- guest model ----

    def _queue_depth(self):
        size = 0x20
        return (self.head - self.tail) % size // 2 if size else 0

    def _screen_bytes(self):
        rows = [' ' * 80 for _ in range(25)]
        rows[ANCHOR_ROW] = ('C:\\>' + self.typed).ljust(80)
        if self.history:
            rows[ANCHOR_ROW - 1] = 'C:\\>VER'.ljust(80)
        return [row.encode('cp437').hex() for row in rows]

    def _memory(self):
        data = bytearray(0x10000)
        data[0x41A:0x41C] = struct.pack('<H', self.head)
        data[0x41C:0x41E] = struct.pack('<H', self.tail)
        data[0x480:0x482] = struct.pack('<H', 0x1E)
        data[0x482:0x484] = struct.pack('<H', 0x3E)
        return data

    def _color(self):
        state = self.screen + (str(self.ms // 500) if self.blink else '')
        return hashlib.sha256(state.encode('ascii')).digest()[:3]

    def _echo(self, scan, drop=False):
        char = KEYMAP.get(scan)
        if char is None:
            return
        if not self.shift and char.isalpha():
            char = char.lower()
        elif self.shift and char.isalpha():
            char = char.upper()
        index = len(self.received)
        self.received += char
        if drop or self.swallow or index in self.drop:
            return
        self.head = 0x1E + ((self.head - 0x1E + 2) % 0x20)
        if not self.queue_only:
            self.typed += self.substitute.get(index, char)

    def _key(self, request):
        parts = request.split()
        down = parts[1] == 'down'
        printable = [int(token, 0) for token in parts[2:] if int(token, 0) in KEYMAP]
        last = printable[-1] if (self.drop_last and down and printable) else None
        for token in parts[2:]:
            scan = int(token, 0)
            if scan == 0x2A:
                self.shift = down
            elif down:
                if scan == 0x44:
                    self.screen = 'menu'
                elif scan == 0x01 and self.screen == 'menu':
                    self.screen = 'desktop'
                self._echo(scan, drop=scan == last)
            self.ms += 2
        return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}

    def _step(self, amount):
        self.ms += amount
        if self.drain:
            self.tail = self.head
        return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}

    def reply(self, request):
        parts = request.split()
        verb = parts[0]
        if parts == ['status']:
            return {'ok': True, 'protocol': 1, 'version': 'SYNTHETIC-PEER', 'ms': self.ms,
                    'frames': self.frames, 'held': True, 'paused': False, 'ff': False,
                    'w': 1, 'h': 1, 'bios_mode': self.bios_mode, 'quantum_ms': 1}
        if parts == ['info']:
            return {'ok': True, 'version': 'SYNTHETIC-PEER', 'machine': 'SYNTHETIC',
                    'hard_resets': 1, 'soft_resets': 1, 'last_reset_ms': 0}
        if verb == 'step':
            return self._step(int(parts[1], 0))
        if verb in ('hold', 'release'):
            return {'ok': True, 'ms': self.ms, 'held': True}
        if verb == 'key':
            return self._key(request)
        if verb == 'memr':
            address, length = int(parts[1], 0), int(parts[2], 0)
            data = self._memory()
            return {'ok': True, 'addr': address, 'data': bytes(data[address:address + length]).hex()}
        if verb == 'text':
            rows = self._screen_bytes()
            return {'ok': True, 'chars': rows, 'attrs': ['0700' * 80 for _ in rows],
                    'cols': 80, 'rows': len(rows)}
        if verb == 'screenshot':
            png = screen_png(self._color())
            return {'ok': True, 'png': base64.b64encode(png).decode('ascii'),
                    'w': 1, 'h': 1, 'ms': self.ms, 'frames': self.frames}
        if parts[:2] == ['wait', 'text']:
            needle, budget = ' '.join(parts[3:]), int(parts[2], 0)
            rows = [bytes.fromhex(row).decode('cp437') for row in self._screen_bytes()]
            matched = any(needle in row for row in rows)
            self.ms += 0 if matched else budget
            return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True,
                    'matched': matched}
        if parts[:2] == ['wait', 'mem']:
            address, budget = int(parts[3], 0), int(parts[2], 0)
            expected = bytes.fromhex(parts[4])
            matched = bytes(self._memory()[address:address + len(expected)]) == expected
            self.ms += 0 if matched else budget
            return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True,
                    'matched': matched}
        if verb == 'mouse':
            self.screen = 'pointer:' + parts[1] + ',' + parts[2] + ',' + parts[3]
            return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}
        if verb == 'quit':
            return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}
        return {'ok': False, 'error': 'unsupported in synthetic peer'}


class FacilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token_file = Path(self.temp.name) / 'automation.token'
        self.token_file.write_text(TOKEN)
        self.peer = None

    def tearDown(self):
        if self.peer:
            self.peer.close()
        self.temp.cleanup()

    def facility(self, **kwargs):
        self.peer = Peer(**kwargs.pop('peer', {}))
        client = box.Client(self.token_file, port=self.peer.port, timeout=5)
        self.addCleanup(client.close)
        return inp.VerifiedInput(client, **kwargs)

    # ---- text entry ----

    def test_full_text_is_verified_and_reported_at_the_observed_level(self):
        facility = self.facility(chunk=4)
        report = facility.type_text('ABCDEFGHIJ', anchor='C:\\>')
        self.assertEqual(report.status, 'observed')
        self.assertEqual(report.level, inp.OBSERVED)
        self.assertEqual(report.observed, 'ABCDEFGHIJ')
        self.assertEqual(report.attempts, 3)
        self.assertEqual(self.peer.received, 'ABCDEFGHIJ')

    def test_missing_suffix_is_resumed_without_replaying_delivered_keys(self):
        facility = self.facility(peer={'drop': (9,)}, chunk=10)
        report = facility.type_text('ABCDEFGHIJ', anchor='C:\\>')
        self.assertEqual(report.status, 'observed')
        self.assertEqual(report.attempts, 2)
        # The dropped character is sent twice; nothing already echoed is resent.
        self.assertEqual(self.peer.received, 'ABCDEFGHIJJ')

    def test_loss_in_the_middle_is_ambiguous_and_never_replayed(self):
        facility = self.facility(peer={'drop': (3,)}, chunk=8)
        report = facility.type_text('ABCDEFGH', anchor='C:\\>')
        self.assertEqual(report.status, 'ambiguous')
        self.assertEqual(report.missing, 'DEFGH')
        self.assertEqual(self.peer.received, 'ABCDEFGH')
        self.assertEqual(report.attempts, 1)

    def test_silent_input_is_reported_unchanged_without_replay(self):
        facility = self.facility(peer={'swallow': True}, chunk=8)
        report = facility.type_text('ABCD', anchor='C:\\>')
        self.assertEqual(report.status, 'unchanged')
        self.assertEqual(report.missing, 'ABCD')
        self.assertEqual(report.level, inp.ACCEPTED)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_attempt_bound_stops_a_peer_that_keeps_dropping(self):
        facility = self.facility(peer={'drop': tuple(range(9, 20))}, chunk=10, max_attempts=2)
        report = facility.type_text('ABCDEFGHIJ', anchor='C:\\>')
        self.assertEqual(report.status, 'ambiguous')
        self.assertEqual(report.attempts, 2)

    # ---- guest acceptance versus delivery ----

    def test_a_delivered_keystroke_with_a_stuck_buffer_never_claims_acceptance(self):
        facility = self.facility(peer={'queue_only': True, 'drain': False}, chunk=4)
        report = facility.type_text('AB', anchor='C:\\>')
        self.assertEqual(report.level, inp.DELIVERED)
        self.assertEqual(report.status, 'unchanged')
        self.assertNotEqual(report.steps[0]['queue_depth'], 0)

    def test_bios_queue_depth_and_drain(self):
        facility = self.facility(peer={'queue_only': True})
        facility.client.type_ascii('AB')
        state = facility.bios_keyboard_queue()
        self.assertEqual((state['start'], state['end'], state['size']), (0x1E, 0x3E, 32))
        self.assertEqual(state['depth'], 2)
        drained = facility.wait_drained(timeout_ms=200)
        self.assertEqual(drained['depth'], 0)

    # ---- menus and pointer ----

    def test_menu_open_and_restore_are_observed_from_the_framebuffer(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        start = facility.snapshot()
        self.assertEqual(start['basis'], 'frame')
        opened = facility.press(0x44, expect='change')
        self.assertEqual(opened.status, 'observed')
        closed = facility.press(0x01, expect='restore', reference=start)
        self.assertEqual(closed.status, 'observed')
        self.assertEqual(closed.level, inp.OBSERVED)

    def test_text_basis_ignores_a_blinking_cursor(self):
        facility = self.facility(peer={'blink': True})
        first = facility.frame_digest()[0]
        facility.client.step(600)
        self.assertNotEqual(first, facility.frame_digest()[0])
        report = facility.press(0x44, expect='change')
        self.assertEqual(report.status, 'unchanged')
        self.assertEqual(report.steps[0]['basis'], 'text')

    def test_unexpected_no_change_is_reported_not_hidden(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.press(0x01, expect='change')
        self.assertEqual(report.status, 'unchanged')
        self.assertNotEqual(report.level, inp.OBSERVED)

    def test_render_gate_notices_a_live_guest(self):
        live = self.facility(peer={'bios_mode': 0x12, 'blink': True})
        self.assertTrue(live.await_render(budget_ms=2000, slice_ms=100))

    def test_render_gate_reports_a_guest_that_never_redraws(self):
        static = self.facility(peer={'bios_mode': 0x12})
        self.assertFalse(static.await_render(budget_ms=500, slice_ms=100))

    def test_pointer_motion_is_delivered_and_observable(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.pointer(5, -3, 1, expect='change')
        self.assertEqual(report.status, 'observed')
        self.assertIn('mouse 5 -3 1', self.peer.requests)

    # ---- protocol primitives ----

    def test_wait_text_reports_match_and_timeout(self):
        facility = self.facility()
        hit = facility.client.wait_text('C:\\>', 500)
        self.assertTrue(hit['matched'])
        miss = facility.client.wait_text('NOT PRESENT', 250)
        self.assertFalse(miss['matched'])

    def test_wait_memory_compares_expected_bytes(self):
        facility = self.facility()
        matched = facility.client.wait_memory(0x480, b'\x1e\x00', 250)
        self.assertTrue(matched['matched'])
        missed = facility.client.wait_memory(0x480, b'\xff\xff', 250)
        self.assertFalse(missed['matched'])

    def test_input_validation_precedes_any_wire_mutation(self):
        facility = self.facility()
        before = len(self.peer.requests)
        invalid = [
            lambda: facility.press(0x1C, expect='restore'),
            lambda: facility.type_text('A', anchor=''),
            lambda: facility.type_text('A', anchor='ABSENT'),
            lambda: facility.press(),
            lambda: facility.press(0x1C, expect='sometimes'),
            lambda: facility.client.wait_text('A\nB', 10),
            lambda: facility.client.wait_text('A', 0),
            lambda: facility.client.wait_memory(0, b'', 10),
            lambda: facility.client.mouse(0, 0, -1),
            lambda: inp.VerifiedInput(facility.client, chunk=0),
            lambda: inp.VerifiedInput(facility.client, max_attempts=9),
            lambda: facility.await_render(budget_ms=-1),
        ]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()
        # Observation commands may run first; no input command may reach the wire.
        sent = [request for request in self.peer.requests
                if request.split()[0] in ('key', 'mouse', 'tablet')]
        self.assertEqual(sent, [])
        self.assertGreaterEqual(len(self.peer.requests), before)

    def test_graphics_mode_refuses_anchor_verification(self):
        facility = self.facility()
        self.peer.bios_mode = 0x12
        with self.assertRaises(ValueError):
            facility.type_text('A', anchor='C:\\>')

    def test_repeated_anchor_needs_an_explicit_occurrence(self):
        facility = self.facility(peer={'history': True})
        with self.assertRaises(ValueError):
            facility.type_text('AB', anchor='C:\\>')
        report = facility.type_text('AB', anchor='C:\\>', occurrence='last')
        self.assertEqual(report.status, 'observed')
        self.assertEqual(report.observed, 'AB')

    def test_report_evidence_is_serializable_and_carries_the_decision(self):
        facility = self.facility(chunk=4)
        report = facility.type_text('ABCDE', anchor='C:\\>')
        payload = json.dumps(report.as_dict())
        self.assertIn('observed', payload)
        self.assertEqual(len(json.loads(payload)['steps']), report.attempts)
        self.assertNotIn(TOKEN, payload)


if __name__ == '__main__':
    unittest.main()
