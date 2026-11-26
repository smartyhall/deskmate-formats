"""Verified-input tests against an authored native peer; no emulator or ROMs.

The peer speaks the real authenticated line protocol over loopback, so the tests
exercise the actual client transport, reply validation and facility logic. Its
guest model is deliberately independent of the facility's assumptions: the BIOS
cursor decides how much of a row is typed input, the keyboard ring uses the
documented producer (INT 09h writes at TAIL) and consumer (INT 16h reads at
HEAD) pointers, and screens are built from completed lines plus the live prompt.

Faults are injected deliberately: dropped, substituted and duplicated
characters, a ring that never drains, a ring that is malformed, a cursor that
lags or leads the text, trimmed trailing spaces, delayed echo, a command that
does not return a prompt, and screens that never redraw.
"""
import base64
import hashlib
import importlib.util
import struct
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
import socket

ROOT = Path(__file__).resolve().parents[2]
BOX_SPEC = importlib.util.spec_from_file_location('box_client', ROOT / 'tools/86box_client.py')
box = importlib.util.module_from_spec(BOX_SPEC)
BOX_SPEC.loader.exec_module(box)

from deskmate_formats.automation import input as inp          # noqa: E402
from deskmate_formats.automation import profiles              # noqa: E402

TOKEN = 'a1' * 32
PROMPT = 'C:\\>'
COLS, ROWS = 80, 25
PLAIN = '1234567890-=qwertyuiop[]asdfghjkl;\'`\\zxcvbnm,./'
SCANS = list(range(2, 14)) + list(range(16, 28)) + list(range(30, 42)) + [43] + list(range(44, 54))
KEYMAP = {scan: char for char, scan in zip(PLAIN, SCANS)}
KEYMAP[57] = ' '


def chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload)))


def screen_png(color):
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + bytes(color)))
            + chunk(b'IEND', b''))


class Peer:
    """One authenticated native peer with a synthetic guest and fault injection."""

    def __init__(self, *, drop=(), substitute=None, duplicate_at=None, swallow=False,
                 queue_only=False, drain=True, trim=False, cursor_offset=0,
                 delay_steps=0, ring='normal', bios_mode=3, blink=False, history=False,
                 commands=None, prompt='C:\\>', no_prompt_return=False, stale=None):
        self.ms = 0
        self.frames = 1
        self.bios_mode = bios_mode
        self.blink = blink
        self.drop = set(drop)
        self.substitute = dict(substitute or {})
        self.duplicate_at = duplicate_at
        self.swallow = swallow
        self.queue_only = queue_only
        self.drain = drain
        self.trim = trim
        self.cursor_offset = cursor_offset
        self.delay_steps = delay_steps
        self.delay_left = 0
        self.deferred = ''
        self.prompt = prompt
        self.lines = [prompt + 'VER', 'MS-DOS Version 5.00'] if history else []
        self.typed = ''
        self.received = ''
        self.commands = dict(commands or {})
        self.no_prompt_return = no_prompt_return
        self.stale = stale
        self.menu = False
        self.shift = False
        self.head = 0x1E
        self.tail = 0x1E
        if ring == 'wrapped':
            self.head, self.tail = 0x38, 0x1E
        elif ring == 'malformed':
            self.head = 0x90
        self.ring = ring
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
                    stream.write((__import__('json').dumps(self.reply(request)) + '\n')
                                 .encode('ascii'))
                    stream.flush()
        except Exception as exc:  # pragma: no cover - surfaced by the test body
            self.error = exc

    # ---- guest model ----

    def _screen(self):
        # Stale cells are left by a longer previous line and become visible as
        # soon as this input starts overwriting that row.
        body = self.lines + [self.prompt + self.typed + ((self.stale or '') if self.typed else '')]
        body = body[-ROWS:]
        rows = [' ' * COLS] * (ROWS - len(body)) + [row[:COLS].ljust(COLS) for row in body]
        return rows[-ROWS:]

    def _cursor(self):
        rows = self._screen()
        row = len(rows) - 1
        column = len(self.prompt) + len(self.typed) + self.cursor_offset
        return [row, max(0, min(COLS - 1, column))]

    def _memory(self):
        data = bytearray(0x10000)
        data[0x41A:0x41C] = struct.pack('<H', self.head)
        data[0x41C:0x41E] = struct.pack('<H', self.tail)
        data[0x480:0x482] = struct.pack('<H', 0x1E)
        data[0x482:0x484] = struct.pack('<H', 0x3E)
        return data

    def _color(self):
        state = '\n'.join(self._screen()) + (str(self.ms // 500) if self.blink else '')
        return hashlib.sha256(state.encode('ascii')).digest()[:3]

    def _advance(self, amount):
        # A real BIOS refuses the sixteenth queued keystroke instead of aliasing
        # the full ring onto the empty head/tail pair.
        if ((self.tail - self.head) % 0x20) // 2 + amount // 2 > 15:
            return
        self.tail = 0x1E + ((self.tail - 0x1E + amount) % 0x20)

    def _echo(self, scan):
        char = KEYMAP.get(scan)
        if char is None:
            return
        if self.shift and char.isalpha():
            char = char.upper()
        elif not self.shift and char.isalpha():
            char = char.lower()
        index = len(self.received)
        self.received += char
        if self.swallow or index in self.drop:
            return
        # INT 09h stores the translated keystroke at TAIL and advances TAIL.
        self._advance(2)
        if self.queue_only:
            return
        text = self.substitute.get(index, char)
        if index == self.duplicate_at:
            text = text + text
        elif self.delay_steps:
            self.deferred += text
            self.delay_left = self.delay_steps
            return
        self.typed += text
        if self.trim:
            self.typed = self.typed.rstrip(' ')

    def _key(self, request):
        parts = request.split()
        down = parts[1] == 'down'
        for token in parts[2:]:
            scan = int(token, 0)
            if scan == 0x2A:
                self.shift = down
            elif down:
                if scan == 0x1C:
                    self._submit()
                elif self.bios_mode not in inp.TEXT_MODES and scan == 0x44:
                    self.menu = True
                    self.lines.append('Applications')
                elif self.bios_mode not in inp.TEXT_MODES and scan == 0x01 and self.menu:
                    self.menu = False
                    self.lines.remove('Applications')
                else:
                    self._echo(scan)
            self.ms += 2
        return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}

    def _submit(self):
        if self.no_prompt_return:
            return
        line = self.typed
        self.lines.append(self.prompt + line)
        output = self.commands.get(line.strip().upper())
        if output:
            self.lines.extend(output)
        self.typed = ''

    def _step(self, amount):
        self.ms += amount
        if self.drain:
            self.head = self.tail
        if self.deferred and self.delay_left > 0:
            self.delay_left -= 1
            if self.delay_left == 0:
                self.typed += self.deferred
                self.deferred = ''
        return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}

    def reply(self, request):
        import json
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
            return {'ok': True, 'addr': address,
                    'data': bytes(data[address:address + length]).hex()}
        if verb == 'text':
            rows = [row.encode('cp437').hex() for row in self._screen()]
            return {'ok': True, 'chars': rows, 'attrs': ['0700' * COLS for _ in rows],
                    'cols': COLS, 'rows': ROWS, 'mode': self.bios_mode,
                    'cursor': self._cursor()}
        if verb == 'screenshot':
            png = screen_png(self._color())
            return {'ok': True, 'png': base64.b64encode(png).decode('ascii'),
                    'w': 1, 'h': 1, 'ms': self.ms, 'frames': self.frames}
        if parts[:2] == ['wait', 'text']:
            needle, budget = ' '.join(parts[3:]), int(parts[2], 0)
            self.ms += 0 if any(needle in row for row in self._screen()) else budget
            matched = any(needle in row for row in self._screen())
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
            if parts[1] != '0' or parts[2] != '0':
                self.lines.append('pointer:' + parts[1] + ',' + parts[2] + ',' + parts[3])
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

    def facility(self, peer=None, **kwargs):
        self.peer = Peer(**(peer or {}))
        client = box.Client(self.token_file, port=self.peer.port, timeout=5)
        self.addCleanup(client.close)
        return inp.VerifiedInput(client, **kwargs)

    # ---- text entry and evidence ----

    def test_full_text_is_observed_with_all_four_layers(self):
        facility = self.facility(chunk=4)
        report = facility.type_text('ABCDEFGHIJ', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertTrue(report.evidence.acknowledged)
        self.assertTrue(report.evidence.delivered)
        self.assertIs(report.evidence.accepted, True)
        self.assertIs(report.evidence.observed, True)
        self.assertEqual(report.observed, 'ABCDEFGHIJ')
        self.assertEqual((report.bursts, report.recoveries), (3, 0))

    def test_long_input_is_not_limited_by_the_recovery_budget(self):
        text = 'ABCDEFGHIJ' * 4           # 40 characters, five bursts of eight
        facility = self.facility(chunk=8, max_recoveries=2)
        report = facility.type_text(text, anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertEqual(report.bursts, 5)
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(self.peer.received, text)

    def test_missing_suffix_resumes_at_the_proven_boundary(self):
        facility = self.facility(peer={'drop': (9,)}, chunk=10)
        report = facility.type_text('ABCDEFGHIJ', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        # Resending a suffix after confirmed progress is the next burst, not a
        # recovery; only a burst that produces nothing new is counted as one.
        self.assertEqual((report.bursts, report.recoveries), (2, 0))
        self.assertEqual(self.peer.received, 'ABCDEFGHIJJ')
        self.assertEqual(self.peer.typed, 'ABCDEFGHIJ')

    def test_missing_first_character_is_ambiguous(self):
        facility = self.facility(peer={'drop': (0,)}, chunk=8)
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        # The screen shows BCDEFGH at the anchor, so the missing character is not
        # a suffix and nothing may be resent.
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.missing, 'ABCDEFGH')
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(self.peer.received, 'ABCDEFGH')

    def test_loss_in_the_middle_is_ambiguous_and_never_replayed(self):
        facility = self.facility(peer={'drop': (3,)}, chunk=8)
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.missing, 'DEFGH')
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(self.peer.received, 'ABCDEFGH')

    def test_substitution_is_ambiguous(self):
        facility = self.facility(peer={'substitute': {2: 'X'}}, chunk=8)
        report = facility.type_text('ABCDE', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.missing, 'CDE')
        self.assertEqual(report.recoveries, 0)

    def test_duplicate_character_is_ambiguous(self):
        facility = self.facility(peer={'duplicate_at': 2}, chunk=8)
        report = facility.type_text('ABCDE', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(self.peer.typed, 'ABCCDE')

    def test_every_character_swallowed_is_unchanged_without_replay(self):
        facility = self.facility(peer={'swallow': True}, chunk=8)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(report.missing, 'ABCD')
        self.assertIs(report.evidence.accepted, True)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_queued_input_blocks_sending_and_is_reported_pending(self):
        facility = self.facility(peer={'queue_only': True, 'drain': False})
        self.peer._advance(4)              # two translated keystrokes still queued
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.PENDING)
        self.assertEqual(report.bursts, 0)
        self.assertEqual(self.peer.received, '')

    def test_pending_input_after_a_burst_prevents_a_resend(self):
        facility = self.facility(peer={'queue_only': True, 'drain': False}, chunk=8)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.PENDING)
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_delayed_echo_is_waited_for_and_never_duplicated(self):
        facility = self.facility(peer={'delay_steps': 2}, chunk=4)
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(self.peer.typed, 'ABCDEFGH')

    def test_echo_slower_than_the_verify_budget_is_reported_not_retried(self):
        facility = self.facility(peer={'delay_steps': 200}, chunk=4)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_attempt_budget_stops_a_peer_that_keeps_dropping(self):
        facility = self.facility(peer={'drop': tuple(range(9, 30))}, chunk=10,
                                 max_recoveries=2)
        report = facility.type_text('ABCDEFGHIJ', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.recoveries, 2)

    # ---- cursor, insertion point and whitespace ----

    def test_intentional_trailing_spaces_are_verified(self):
        facility = self.facility(chunk=8)
        report = facility.type_text('AB  ', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertEqual(report.observed, 'AB  ')

    def test_repeated_interior_spaces_are_verified(self):
        facility = self.facility(chunk=16)
        report = facility.type_text('A  B   C', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)

    def test_trailing_spaces_trimmed_by_the_guest_cannot_be_verified(self):
        facility = self.facility(peer={'trim': True}, chunk=8, max_recoveries=1)
        report = facility.type_text('AB  ', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.detail, 'recovery budget exhausted')

    def test_cursor_lagging_behind_echoed_text_blocks_recovery(self):
        facility = self.facility(peer={'cursor_offset': -2}, chunk=4)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(report.bursts, 1)

    def test_cursor_ahead_of_the_echoed_text_is_ambiguous(self):
        facility = self.facility(peer={'cursor_offset': 2}, chunk=4)
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.recoveries, 0)

    def test_stale_characters_after_the_input_position_are_refused(self):
        facility = self.facility(peer={'stale': 'CDEF'}, chunk=8)
        report = facility.type_text('AB', anchor=PROMPT)
        # The row reads AB followed by leftover CDEF: the cursor cannot prove the
        # insertion point, so nothing is resent and no success is claimed.
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(self.peer.received, 'AB')

    # ---- BIOS ring ----

    def test_ring_depth_uses_producer_tail_minus_consumer_head(self):
        facility = self.facility(peer={'ring': 'wrapped'})
        state = facility.bios_keyboard_queue()
        self.assertTrue(state['valid'])
        self.assertEqual((state['head'], state['tail']), (0x38, 0x1E))
        self.assertEqual(state['depth'], 3)     # three words queued across the wrap

    def test_ring_wraps_and_refuses_overflow_like_the_bios(self):
        facility = self.facility(peer={'queue_only': True, 'drain': False})
        facility.client.type_ascii('ABCDEFGHIJKLMNO')       # 15 keystrokes
        state = facility.bios_keyboard_queue()
        self.assertTrue(state['valid'])
        self.assertEqual((state['tail'], state['depth']), (0x3C, 15))
        facility.client.type_ascii('P')                     # the sixteenth is dropped
        state = facility.bios_keyboard_queue()
        self.assertEqual((state['tail'], state['depth']), (0x3C, 15))
        self.peer.drain = True                              # the consumer resumes
        facility.client.step(50)
        self.assertEqual(facility.bios_keyboard_queue()['depth'], 0)

    def test_malformed_ring_is_not_reported_as_empty(self):
        facility = self.facility(peer={'ring': 'malformed'}, chunk=8)
        state = facility.bios_keyboard_queue()
        self.assertFalse(state['valid'])
        self.assertIsNone(state['depth'])
        self.assertEqual(state['reason'], 'pointer outside extents')
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertIsNone(report.evidence.accepted)

    def test_ring_drain_steps_until_empty(self):
        facility = self.facility(peer={'queue_only': True})
        facility.client.type_ascii('AB')
        self.assertEqual(facility.bios_keyboard_queue()['depth'], 2)
        self.assertEqual(facility.wait_drained(timeout_ms=200)['depth'], 0)

    # ---- menus, pointer and render gates ----

    def test_menu_open_and_restore_are_observed_against_a_reference(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        start = facility.snapshot()
        self.assertEqual(start['basis'], 'frame')
        opened = facility.press(0x44, expect='change')
        self.assertEqual(opened.status, inp.OBSERVED)
        self.assertIsNone(opened.evidence.accepted)
        closed = facility.press(0x01, expect='restore', reference=start)
        self.assertEqual(closed.status, inp.OBSERVED)

    def test_a_press_without_an_expectation_never_claims_observation(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.press(0x44)
        self.assertEqual(report.status, 'changed')
        self.assertIsNone(report.evidence.observed)

    def test_text_basis_ignores_a_blinking_cursor(self):
        facility = self.facility(peer={'blink': True})
        first = facility.frame_digest()[0]
        facility.client.step(600)
        self.assertNotEqual(first, facility.frame_digest()[0])
        report = facility.press(0x44, expect='change')
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(report.steps[0]['basis'], 'text')

    def test_unexpected_no_change_is_reported_not_hidden(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.press(0x01, expect='change')
        self.assertEqual(report.status, inp.UNCHANGED)

    def test_pointer_motion_is_delivered_and_visible(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.pointer(5, -3, 1, expect='change')
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertIn('mouse 5 -3 1', self.peer.requests)

    def test_pointer_click_without_change_is_not_success(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.pointer(0, 0, 1, expect='change')
        self.assertEqual(report.status, inp.UNCHANGED)

    def test_render_gate_notices_a_live_guest(self):
        live = self.facility(peer={'bios_mode': 0x12, 'blink': True})
        self.assertTrue(live.await_render(budget_ms=2000, slice_ms=100))

    def test_render_gate_reports_a_guest_that_never_redraws(self):
        static = self.facility(peer={'bios_mode': 0x12})
        self.assertFalse(static.await_render(budget_ms=500, slice_ms=100))

    # ---- DOS prompt profile ----

    def test_command_entry_and_execution_are_separate_observations(self):
        facility = self.facility(peer={'commands': {'VER': ['MS-DOS Version 5.00']}})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('VER', expect_output='MS-DOS Version')
        self.assertTrue(result.succeeded)
        self.assertEqual(result.entered, inp.OBSERVED)
        self.assertTrue(result.prompt_returned)
        self.assertTrue(result.output_matched)

    def test_failed_entry_withholds_enter(self):
        facility = self.facility(peer={'swallow': True})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('VER')
        self.assertFalse(result.succeeded)
        self.assertFalse(result.submitted)
        self.assertIn('Enter withheld', result.detail)
        self.assertNotIn('key down 0x1c', self.peer.requests)

    def test_unreturned_prompt_is_reported_as_unknown_execution(self):
        facility = self.facility(peer={'no_prompt_return': True})
        prompt = profiles.DosPrompt(facility, PROMPT, prompt_timeout_ms=300)
        result = prompt.submit('DIR')
        self.assertTrue(result.submitted)
        self.assertIs(result.prompt_returned, False)
        self.assertFalse(result.succeeded)
        self.assertIn('execution state unknown', result.detail)
        self.assertEqual(self.peer.received, 'DIR')

    def test_expected_output_that_never_appears_is_reported(self):
        facility = self.facility()
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('TYPE NOPE', expect_output='cannot find', timeout_ms=200)
        self.assertTrue(result.prompt_returned)
        self.assertFalse(result.output_matched)
        self.assertFalse(result.succeeded)

    def test_screen_state_profile_recognises_only_captured_states(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        screens = profiles.ScreenStates(facility)
        desktop = screens.capture('desktop')
        with self.assertRaises(profiles.ProfileError):
            screens.expect('menu')
        self.assertTrue(screens.matches('desktop'))
        facility.press(0x44)
        screens.capture('menu')
        self.assertFalse(screens.matches('desktop'))
        transition = screens.transition(0x01, before='menu', after='desktop')
        self.assertEqual(transition.status, inp.OBSERVED)
        self.assertTrue(transition.evidence.observed)
        self.assertEqual(screens.states['desktop'], desktop)

    # ---- protocol primitives and validation ----

    def test_wait_text_reports_match_and_timeout(self):
        facility = self.facility()
        self.assertTrue(facility.client.wait_text('C:\\>', 500)['matched'])
        self.assertFalse(facility.client.wait_text('NOT PRESENT', 250)['matched'])

    def test_wait_memory_compares_expected_bytes(self):
        facility = self.facility()
        self.assertTrue(facility.client.wait_memory(0x480, b'\x1e\x00', 250)['matched'])
        self.assertFalse(facility.client.wait_memory(0x480, b'\xff\xff', 250)['matched'])

    def test_input_validation_precedes_any_wire_mutation(self):
        facility = self.facility()
        before = len(self.peer.requests)
        invalid = [
            lambda: facility.press(0x1C, expect='restore'),
            lambda: facility.press(0x1C, expect='restore', reference={'basis': 'frame', 'digest': 'x'}),
            lambda: facility.type_text('A', anchor=''),
            lambda: facility.type_text('A', anchor='ABSENT'),
            lambda: facility.type_text('A', anchor=PROMPT, occurrence='middle'),
            lambda: facility.press(),
            lambda: facility.press(0x1C, expect='sometimes'),
            lambda: facility.client.wait_text('A\nB', 10),
            lambda: facility.client.wait_text('A', 0),
            lambda: facility.client.wait_memory(0, b'', 10),
            lambda: facility.client.mouse(0, 0, -1),
            lambda: inp.VerifiedInput(facility.client, chunk=0),
            lambda: inp.VerifiedInput(facility.client, max_recoveries=9),
            lambda: inp.VerifiedInput(facility.client, max_bursts=0),
            lambda: facility.await_render(budget_ms=-1),
        ]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()
        sent = [request for request in self.peer.requests
                if request.split()[0] in ('key', 'mouse', 'tablet')]
        self.assertEqual(sent, [])
        self.assertGreaterEqual(len(self.peer.requests), before)

    def test_graphics_mode_refuses_anchor_verification(self):
        facility = self.facility()
        self.peer.bios_mode = 0x12
        with self.assertRaises(ValueError):
            facility.type_text('A', anchor=PROMPT)
        with self.assertRaises(profiles.ProfileError):
            profiles.DosPrompt(facility, PROMPT)

    def test_report_evidence_is_serializable_and_carries_each_layer(self):
        facility = self.facility(chunk=4)
        report = facility.type_text('ABCDE', anchor=PROMPT)
        import json
        payload = json.loads(json.dumps(report.as_dict()))
        self.assertEqual(set(payload['evidence']),
                         {'acknowledged', 'delivered', 'accepted', 'observed'})
        self.assertEqual(len(payload['steps']), report.bursts)
        self.assertNotIn(TOKEN, json.dumps(payload))


if __name__ == '__main__':
    unittest.main()
