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
                 commands=None, prompt='C:\\>', no_prompt_return=False, stale=None,
                 instrumented=False, cursor_offset_after=0, hold_last=None,
                 regress_at=None, regress_to=0, mutate_after=None, clear_on=(),
                 leave_text_on=(), long_history=False, discard_at=None):
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
        self.cursor_offset_after = cursor_offset_after
        self.hold_last = hold_last
        self.regress_at = regress_at
        self.regress_to = regress_to
        self.regressed = False
        self.mutate_after = mutate_after
        self.mutated = False
        self.discard_at = discard_at
        self.discarded = False
        self.clear_on = set(clear_on)
        self.leave_text_on = set(leave_text_on)
        self.delay_steps = delay_steps
        self.delay_left = 0
        self.deferred = ''
        self.prompt = prompt
        self.lines = [prompt + 'VER', 'MS-DOS Version 5.00'] if history else []
        if long_history:
            self.lines = [f'HISTORY LINE {index:02d}' for index in range(30)]
        self.typed = ''
        self.received = ''
        self.commands = dict(commands or {})
        self.no_prompt_return = no_prompt_return
        self.stale = stale
        # A guest event between two observations can leave the caret somewhere
        # other than the end of the text, or shift the row the anchor is on.
        self.indent = 0
        self.caret = None
        self.menu = False
        self.shift = False
        self.head = 0x1E
        self.tail = 0x1E
        # An instrumented build announces capabilities and reports its own
        # automation queue and event counters; a stock build announces nothing.
        self.instrumented = instrumented
        self.seq = 0
        self.accepted = 0
        self.forwarded = 0
        self.dropped = 0
        self.sent_dx = 0
        self.sent_dy = 0
        self.sent_buttons = 0
        # A build that lies about completion: reports events still queued.
        self.completion_queue = 0
        self.stopped_next = False
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
        live = ' ' * self.indent + self.prompt + self.typed
        body = self.lines + [live + ((self.stale or '') if self.typed else '')]
        body = body[-ROWS:]
        rows = [' ' * COLS] * (ROWS - len(body)) + [row[:COLS].ljust(COLS) for row in body]
        return rows[-ROWS:]

    def _depth(self):
        return ((self.tail - self.head) % 0x20) // 2

    def _cursor(self):
        rows = self._screen()
        row = len(rows) - 1
        offset = self.cursor_offset
        if self.typed:
            offset += self.cursor_offset_after
        column = self.indent + len(self.prompt) + len(self.typed) + offset
        if self.caret is not None:
            column = self.caret
        return [row, max(0, min(COLS - 1, column))]

    def _memory(self):
        data = bytearray(0x10000)
        # A malformed ring stays malformed: the guest never wrote plausible
        # extents or pointers, and stepping the machine does not repair that.
        head = 0x90 if self.ring == 'malformed' else self.head
        data[0x41A:0x41C] = struct.pack('<H', head)
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
        if (self.mutate_after is not None and not self.mutated
                and len(self.received) >= self.mutate_after):
            # A second row that also carries the anchor makes the location
            # ambiguous, exactly as a relocated input field would.
            self.lines.append(self.prompt)
            self.mutated = True

    def _key(self, request):
        parts = request.split()
        down = parts[1] == 'down'
        self.seq += 1
        events = len(parts) - 2
        lost = 0
        if (self.discard_at is not None and not self.discarded
                and len(self.received) >= self.discard_at):
            # The interface accepted an event and then discarded it: an empty
            # queue afterwards must not read as full delivery.
            self.dropped += 1
            lost = 1
            self.discarded = True
        self.accepted += events
        self.forwarded += events - lost
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
        reply = {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True}
        if self.stopped_next:
            # A key command ended by the debugger leaves events pending.
            self.stopped_next = False
            reply.update({'events': len(parts) - 2, 'seq': self.seq,
                          'stopped': 'debugger'})
            return reply
        if self.instrumented:
            reply.update({'events': len(parts) - 2, 'seq': self.seq,
                          'queue': self.completion_queue, 'replaced': 0,
                          'accepted': self.accepted, 'forwarded': self.forwarded,
                          'dropped': self.dropped, 'pending': 0, 'generation': 0})
        return reply

    def _submit(self):
        if self.no_prompt_return:
            return
        line = self.typed
        upper = line.strip().upper()
        if upper in self.leave_text_on:
            self.bios_mode = 0x12
            return
        if upper in self.clear_on:
            self.lines = []
        self.lines.append(self.prompt + line)
        output = self.commands.get(upper)
        if output:
            self.lines.extend(output)
        self.typed = ''

    def _step(self, amount):
        self.ms += amount
        if self.drain and not (self.hold_last is not None
                               and len(self.received) >= self.hold_last):
            self.head = self.tail
        if (self.regress_at is not None and not self.regressed
                and len(self.received) >= self.regress_at):
            # Previously verified text disappears while the queue is empty.
            self.typed = self.typed[:self.regress_to]
            self.regressed = True
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
            reply = {'ok': True, 'protocol': 1, 'version': 'SYNTHETIC-PEER', 'ms': self.ms,
                     'frames': self.frames, 'held': True, 'paused': False, 'ff': False,
                     'w': 1, 'h': 1, 'bios_mode': self.bios_mode, 'quantum_ms': 1}
            if self.instrumented:
                reply['caps'] = ['input_queue', 'event_seq', 'wait_queue', 'video_meta',
                                 'mouse_state', 'keyboard_held', 'input_accounting',
                                 'queue_pump', 'key_cancel']
                # The interface forwards each event immediately here, so its own
                # queue is empty and every accepted event is forwarded. The BIOS
                # ring depth is a different queue and lives in guest memory.
                reply['input'] = {'queue': 0, 'capacity': 64, 'pending': 0, 'seq': self.seq,
                                  'accepted': self.accepted, 'forwarded': self.forwarded,
                                  'dropped': self.dropped, 'generation': 0,
                                  'accounting': True, 'held_keys': 0, 'gap_ms': 2}
            return reply
        if parts == ['video']:
            text = self.bios_mode in inp.TEXT_MODES
            return {'ok': True, 'bios_mode': self.bios_mode, 'text': text,
                    'cols': COLS if text else 0, 'rows': ROWS if text else 0,
                    'cursor': self._cursor() if text else [-1, -1], 'w': 1, 'h': 1}
        if parts == ['mouse', 'state']:
            return {'ok': True, 'sent_dx': self.sent_dx, 'sent_dy': self.sent_dy,
                    'buttons': self.sent_buttons, 'mode': 0}
        if parts[:2] == ['wait', 'queue']:
            budget = int(parts[2], 0)
            if self.drain:
                self.head = self.tail
            matched = self._depth() == 0
            self.ms += 0 if matched else budget
            return {'ok': True, 'ms': self.ms, 'frames': self.frames, 'held': True,
                    'matched': matched, 'queue': self._depth()}
        if parts == ['info']:
            return {'ok': True, 'version': 'SYNTHETIC-PEER', 'machine': 'SYNTHETIC',
                    'hard_resets': 1, 'soft_resets': 1, 'last_reset_ms': 0}
        if verb == 'step':
            return self._step(int(parts[1], 0))
        if verb in ('hold', 'release'):
            return {'ok': True, 'ms': self.ms, 'held': True}
        if parts == ['key', 'cancel']:
            cancelled = self._depth()
            self.head = self.tail
            # These were counted as forwarded when the request arrived; the
            # cancellation moves them to dropped, so the identity still holds.
            self.forwarded -= cancelled
            self.dropped += cancelled
            return {'ok': True, 'cancelled': cancelled, 'dropped': self.dropped,
                    'generation': 0, 'ms': self.ms, 'frames': self.frames,
                    'held': True}
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
            self.sent_dx += int(parts[1], 0)
            self.sent_dy += int(parts[2], 0)
            self.sent_buttons = int(parts[3], 0)
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
        # This peer does queue each keystroke before draining it, so the ring is
        # seen holding input and then empty: affirmative acceptance evidence.
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
        # The burst landed only partly, so the suffix is a recovery and spends
        # the allowance even though it succeeds.
        self.assertEqual((report.bursts, report.recoveries), (2, 1))
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
        # Nothing was ever seen queued, so there is no affirmative acceptance
        # evidence even though the ring reads empty.
        self.assertIsNone(report.evidence.accepted)
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

    def test_partial_burst_spends_a_recovery_even_though_it_progressed(self):
        facility = self.facility(peer={'drop': (7,)}, chunk=8, max_recoveries=1)
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertEqual((report.bursts, report.recoveries), (2, 1))
        self.assertEqual(self.peer.typed, 'ABCDEFGH')
        self.assertEqual(report.steps[0]['expected'], 'ABCDEFGH')
        self.assertEqual(report.steps[0]['observed'], 'ABCDEFG')

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
        facility = self.facility(peer={'cursor_offset_after': -2}, chunk=4)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(report.recoveries, 0)
        self.assertEqual(report.bursts, 1)

    def test_cursor_ahead_of_the_echoed_text_is_ambiguous(self):
        facility = self.facility(peer={'cursor_offset_after': 2}, chunk=4)
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

    def test_pointer_equal_to_the_exclusive_end_is_out_of_range(self):
        facility = self.facility()
        self.peer.tail = 0x3E          # the end offset itself, not a valid pointer
        state = facility.bios_keyboard_queue()
        self.assertFalse(state['valid'])
        self.assertEqual(state['reason'], 'pointer outside extents')

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
        # An unreadable ring cannot satisfy a prerequisite, so nothing is sent.
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.WITHHELD)
        self.assertIn('keyboard ring unreadable', report.detail)
        self.assertIsNone(report.evidence.accepted)
        self.assertEqual([r for r in self.peer.requests if r.split()[0] == 'key'], [])

    def test_bypass_profile_observes_without_claiming_translation(self):
        # The qualified alternative for a guest that hooks INT 09h: the ring is
        # meaningless, so the limitation is recorded and acceptance is unknown.
        facility = self.facility(peer={'ring': 'malformed'},
                                 keyboard=inp.KEYBOARD_BYPASS)
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertIsNone(report.evidence.accepted)
        self.assertIsNone(report.evidence.translated)
        self.assertIn('bios_keyboard_ring_bypassed', report.evidence.limitations)
        self.assertIs(report.evidence.observed, True)

    def test_bypass_profile_refuses_recovery_it_cannot_qualify(self):
        facility = self.facility(peer={'drop': (3,), 'ring': 'malformed'}, chunk=4,
                                 keyboard=inp.KEYBOARD_BYPASS, max_recoveries=1)
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.recoveries, 0)
        self.assertIn('cannot be excluded', report.steps[0]['gate']['reason'])

    def test_ring_drain_steps_until_empty(self):
        facility = self.facility(peer={'queue_only': True})
        facility.client.type_ascii('AB')
        self.assertEqual(facility.bios_keyboard_queue()['depth'], 2)
        self.assertEqual(facility.wait_drained(timeout_ms=200)['depth'], 0)

    # ---- insertion point, completion and recovery re-gating ----

    def test_wrong_initial_cursor_withholds_all_input(self):
        facility = self.facility(peer={'cursor_offset': 1})
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.WITHHELD)
        self.assertEqual(report.detail, 'cursor is not at the anchor end')
        self.assertEqual(report.bursts, 0)
        self.assertEqual([r for r in self.peer.requests if r.split()[0] == 'key'], [])

    def test_text_beside_the_anchor_is_not_an_insertion_point(self):
        # An empty region after the anchor says nothing about the cursor; text
        # already sitting there makes the position unknown, so nothing is sent.
        facility = self.facility()
        self.peer.typed = 'OLD'
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.WITHHELD)
        self.assertIn('not followed by an empty input position', report.detail)
        self.assertEqual(self.peer.received, '')

    def test_pending_input_after_matching_text_is_not_observed(self):
        facility = self.facility(peer={'hold_last': 4}, chunk=4)
        report = facility.type_text('ABCD', anchor=PROMPT)
        # The screen reads exactly the requested text, but the ring still owes a
        # keystroke: a late arrival could change the row, so this is pending.
        self.assertEqual(report.status, inp.PENDING)
        self.assertEqual(report.observed, 'ABCD')
        self.assertIs(report.evidence.observed, False)
        self.assertIn('completion', report.steps[-1])

    def test_completion_refuses_a_row_that_changed_after_observation(self):
        facility = self.facility()
        before, _, _ = facility._insertion_point(PROMPT, 'only')
        start_col = before['col'] + len(PROMPT)
        facility.client.type_ascii('ABC')
        self.peer.typed = 'AB'
        completion = facility._completion(PROMPT, 'only', before, start_col, 'ABC')
        self.assertFalse(completion['ok'])
        self.assertIn('changed between observation and completion', completion['reason'])

    def test_completion_refuses_when_the_ring_still_holds_input(self):
        facility = self.facility()
        before, _, _ = facility._insertion_point(PROMPT, 'only')
        start_col = before['col'] + len(PROMPT)
        facility.client.type_ascii('ABC')
        self.peer.hold_last = 0        # the ring never drains from here
        completion = facility._completion(PROMPT, 'only', before, start_col, 'ABC')
        self.assertFalse(completion['ok'])
        self.assertTrue(completion['pending'])

    def test_recovery_gate_refuses_a_second_anchor(self):
        facility = self.facility()
        info, _, reason = facility._insertion_point(PROMPT, 'only')
        self.assertIsNone(reason)
        start_col = info['col'] + len(PROMPT)
        facility.client.type_ascii('ABC')
        self.peer.lines.append(PROMPT)
        allowed, gate = facility._recovery_gate(PROMPT, 'only', info, start_col, 'ABC')
        self.assertFalse(allowed)
        self.assertIn('anchor', gate['reason'])

    def test_recovery_gate_refuses_pending_input(self):
        facility = self.facility()
        info, _, _ = facility._insertion_point(PROMPT, 'only')
        start_col = info['col'] + len(PROMPT)
        facility.client.type_ascii('ABC')
        self.peer.head = self.peer.tail - 2
        self.peer.drain = False
        allowed, gate = facility._recovery_gate(PROMPT, 'only', info, start_col, 'ABC')
        self.assertFalse(allowed)
        self.assertTrue(gate['pending'])

    def test_recovery_gate_refuses_a_different_insertion_point(self):
        facility = self.facility()
        info, _, _ = facility._insertion_point(PROMPT, 'only')
        start_col = info['col'] + len(PROMPT)
        facility.client.type_ascii('ABC')
        self.peer.typed = 'AB'
        allowed, gate = facility._recovery_gate(PROMPT, 'only', info, start_col, 'ABC')
        self.assertFalse(allowed)
        self.assertIn('verified prefix', gate['reason'])

    def test_previously_verified_prefix_cannot_regress_into_a_replay(self):
        facility = self.facility(peer={'drop': (3,), 'regress_at': 6, 'regress_to': 2},
                                 chunk=4, max_recoveries=2)
        report = facility.type_text('ABCDEF', anchor=PROMPT)
        # ABC had been verified; the row now shows AB. Resending DEF would
        # duplicate C if it were only a display lag, so no replay is allowed.
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.detail, 'previously verified text regressed')
        self.assertEqual(report.recoveries, 1)

    # ---- prerequisites for every further burst, not only a recovery ----

    def between_bursts(self, facility, mutate, *, after=1, settle=True):
        """Apply a guest event just after the `after`-th observation returns.

        Between two observations the guest can move the caret, print, lose text
        or deliver a late keystroke. Reproducing that exact moment keeps the test
        independent of how many reads an observation happens to make.
        """
        observe = facility._observe
        seen = []

        def observing(anchor, occurrence, start_col):
            result = observe(anchor, occurrence, start_col)
            seen.append(result)
            if len(seen) == after:
                if settle:
                    facility.client.step(facility.settle_step_ms)
                mutate()
            return result

        facility._observe = observing

    def test_row_info_counts_occurrences_within_a_single_row(self):
        facility = self.facility()
        self.peer.lines = ['AB one AB two']
        first = facility.row_info('AB', 'first')
        last = facility.row_info('AB', 'last')
        self.assertEqual((first['row'], first['col']), (ROWS - 2, 0))
        self.assertTrue(first['after'].startswith(' one AB two'))
        self.assertEqual((last['row'], last['col']), (ROWS - 2, 7))
        self.assertEqual(last['after'].strip(' '), 'two')
        with self.assertRaises(ValueError) as caught:
            facility.row_info('AB', 'only')
        self.assertIn('2 positions', str(caught.exception))

    def test_same_row_duplicate_anchor_refuses_an_occurrence_only_request(self):
        # One row with the anchor twice is as ambiguous as two rows, and no
        # input may be sent against a silently chosen occurrence.
        facility = self.facility()
        self.peer.lines = ['AB one AB two']
        with self.assertRaises(ValueError):
            facility.type_text('X', anchor='AB')
        self.assertEqual(self.peer.received, '')
        self.assertEqual([r for r in self.peer.requests if r.split()[0] == 'key'], [])

    def test_cursor_relocated_after_a_complete_burst_stops_further_input(self):
        # The first burst landed completely and was verified. The guest then
        # moves the caret to column 3, so the next burst has no insertion point
        # it can justify: nothing more may be sent.
        facility = self.facility(chunk=4)
        self.between_bursts(facility, lambda: setattr(self.peer, 'caret', 3))
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertIn('insertion point', report.detail)
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')
        self.assertIn('next', report.steps[-1])
        self.assertFalse(report.steps[-1]['next']['ok'])

    def test_late_input_between_bursts_prevents_the_next_burst(self):
        # A keystroke arrives after the observation returned: the row now holds
        # more than the verified prefix, so the next burst is not justified.
        facility = self.facility(chunk=4)
        self.between_bursts(facility, lambda: setattr(self.peer, 'typed', 'ABCDZ'))
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertIn('after the verified prefix', report.detail)
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_anchor_duplicated_between_bursts_stops_input(self):
        facility = self.facility(chunk=4)
        self.between_bursts(facility, lambda: self.peer.lines.append(PROMPT))
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertIn('ambiguous', report.detail)
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_anchor_relocated_between_bursts_stops_input(self):
        facility = self.facility(chunk=4)
        self.between_bursts(facility, lambda: setattr(self.peer, 'indent', 2))
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertIn('anchor moved', report.detail)
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_verified_prefix_regression_between_bursts_is_ambiguous(self):
        facility = self.facility(chunk=4)
        self.between_bursts(facility, lambda: setattr(self.peer, 'typed', 'AB'))
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertEqual(report.detail, 'previously verified prefix regressed')
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_unreadable_ring_between_bursts_withholds_further_input(self):
        facility = self.facility(chunk=4)
        self.between_bursts(facility, lambda: setattr(self.peer, 'ring', 'malformed'))
        report = facility.type_text('ABCDEFGH', anchor=PROMPT)
        # The queue evidence itself became unusable, so nothing further is sent
        # and the outcome is a refusal rather than a pending wait.
        self.assertEqual(report.status, inp.WITHHELD)
        self.assertIn('unreadable', report.detail)
        self.assertEqual(report.bursts, 1)
        self.assertEqual(self.peer.received, 'ABCD')

    def test_bypass_profile_continues_without_queue_evidence_and_says_so(self):
        facility = self.facility(peer={'ring': 'malformed'},
                                 keyboard=inp.KEYBOARD_BYPASS, chunk=2)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertEqual(report.bursts, 2)
        self.assertIn('pending_input_not_excluded_between_bursts',
                      report.evidence.limitations)

    # ---- menus, pointer and render gates ----

    def test_menu_open_and_restore_are_observed_against_a_reference(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        start = facility.snapshot()
        self.assertEqual(start['basis'], 'frame')
        opened = facility.press(0x44, expect='changed')
        self.assertEqual(opened.status, 'changed')
        self.assertIsNone(opened.evidence.observed)
        self.assertIsNone(opened.evidence.accepted)
        closed = facility.press(0x01, expect='state', reference=start)
        self.assertEqual(closed.status, inp.OBSERVED)

    def test_a_press_without_an_expectation_never_claims_observation(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.press(0x44)
        self.assertEqual(report.status, 'changed')
        self.assertIsNone(report.evidence.observed)

    def test_requested_change_is_still_not_success(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.press(0x44, expect='changed')
        self.assertEqual(report.status, 'changed')
        self.assertIsNone(report.evidence.observed)
        self.assertNotEqual(report.status, inp.OBSERVED)

    def test_text_basis_ignores_a_blinking_cursor(self):
        facility = self.facility(peer={'blink': True})
        first = facility.frame_digest()[0]
        facility.client.step(600)
        self.assertNotEqual(first, facility.frame_digest()[0])
        report = facility.press(0x44, expect='changed')
        self.assertEqual(report.status, inp.UNCHANGED)
        self.assertEqual(report.steps[0]['basis'], 'text')

    def test_unexpected_no_change_is_reported_not_hidden(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.press(0x01, expect='changed')
        self.assertEqual(report.status, inp.UNCHANGED)

    def test_pointer_motion_is_delivered_and_visible(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.pointer(5, -3, 1, expect='changed')
        self.assertEqual(report.status, 'changed')
        self.assertIsNone(report.evidence.observed)
        self.assertIn('mouse 5 -3 1', self.peer.requests)

    def test_pointer_click_without_change_is_not_success(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        report = facility.pointer(0, 0, 1, expect='changed')
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

    def test_output_already_in_history_does_not_count(self):
        # The screen already shows the string from an earlier command; a command
        # that prints nothing must not be credited with producing it.
        facility = self.facility(peer={'history': True})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('NOOP', expect_output='MS-DOS Version', timeout_ms=300)
        self.assertTrue(result.prompt_returned)
        self.assertFalse(result.output_matched)
        self.assertFalse(result.succeeded)

    def test_output_in_a_new_row_counts_even_if_it_repeats_history(self):
        facility = self.facility(peer={'history': True,
                                       'commands': {'NOOP': ['MS-DOS Version 5.00']}})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('NOOP', expect_output='MS-DOS Version')
        self.assertTrue(result.output_matched)
        self.assertTrue(result.prompt_returned)

    def test_expected_output_that_never_appears_is_reported(self):
        facility = self.facility()
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('TYPE NOPE', expect_output='cannot find', timeout_ms=200)
        self.assertTrue(result.prompt_returned)
        self.assertFalse(result.output_matched)
        self.assertFalse(result.succeeded)

    def test_command_echo_is_not_credited_as_output(self):
        # The command text is on screen before Enter; finding it after Enter
        # proves nothing about what the command printed.
        facility = self.facility()
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('VER', expect_output='VER', timeout_ms=200)
        self.assertTrue(result.prompt_returned)
        self.assertFalse(result.output_matched)
        self.assertFalse(result.succeeded)

    def test_pre_enter_reference_is_captured_after_entry(self):
        facility = self.facility(peer={'commands': {'VER': ['MS-DOS Version 5.00']}})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('VER')
        self.assertIsNotNone(result.pre_enter)
        self.assertEqual(result.pre_enter['rows'], ROWS)
        stages = [step['stage'] for step in result.steps]
        self.assertEqual(stages[:3], ['entry', 'pre-enter', 'submit'])

    def test_scrolled_history_is_not_credited_as_new_output(self):
        # A full screen scrolls: old rows move up. A common-prefix comparison
        # would call almost all of that fresh; the shift model must not.
        facility = self.facility(peer={'long_history': True})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('NOOP', expect_output='HISTORY LINE 29', timeout_ms=200)
        self.assertTrue(result.prompt_returned)
        self.assertFalse(result.output_matched)
        self.assertEqual(result.output['shift'], 1)

    def test_cleared_screen_output_is_fresh_and_old_history_is_gone(self):
        facility = self.facility(peer={'history': True, 'clear_on': ('CLS',),
                                       'commands': {'CLS': ['Screen cleared']}})
        prompt = profiles.DosPrompt(facility, PROMPT)
        result = prompt.submit('CLS', expect_output='Screen cleared')
        self.assertTrue(result.output_matched)
        self.assertTrue(result.succeeded)

    def test_command_that_leaves_text_mode_is_reported_unknown(self):
        facility = self.facility(peer={'leave_text_on': ('WIN',)})
        prompt = profiles.DosPrompt(facility, PROMPT, prompt_timeout_ms=300)
        result = prompt.submit('WIN')
        self.assertTrue(result.submitted)
        self.assertIsNone(result.prompt_returned)
        self.assertTrue(result.left_text)
        self.assertFalse(result.succeeded)
        self.assertIn('left the text screen', result.detail)

    def test_prompt_return_is_corroborated_by_screen_quiet(self):
        facility = self.facility(peer={'commands': {'VER': ['MS-DOS Version 5.00']}})
        prompt = profiles.DosPrompt(facility, PROMPT, quiet_ms=100)
        result = prompt.submit('VER', expect_output='MS-DOS Version')
        self.assertTrue(result.prompt_returned)
        self.assertTrue(result.settled)

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

    def test_transition_withholds_input_when_the_start_state_is_wrong(self):
        facility = self.facility(peer={'bios_mode': 0x12})
        screens = profiles.ScreenStates(facility)
        screens.capture('desktop')
        facility.press(0x44)
        screens.capture('menu')
        facility.press(0x01)                        # back to the desktop
        before = len(self.peer.requests)
        report = screens.transition(0x150, before='menu', after='desktop')
        self.assertEqual(report.detail['action'], 'withheld')
        self.assertFalse(report.evidence.delivered)
        sent = [r for r in self.peer.requests[before:] if r.split()[0] == 'key']
        self.assertEqual(sent, [])

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

    # ---- instrumented-build negotiation ----

    def test_stock_build_announces_no_instrumentation(self):
        facility = self.facility()
        self.assertEqual(facility.client.capabilities(), [])
        self.assertFalse(facility.client.supports('wait_queue'))
        self.assertIsNone(facility.automation_queue())
        self.assertIsNone(facility.wait_queue(10))
        for operation in (lambda: facility.client.wait_queue(10),
                          lambda: facility.client.video(),
                          lambda: facility.client.mouse_state()):
            with self.assertRaises(box.FeatureUnavailable):
                operation()

    def test_discarded_events_are_not_reported_as_success(self):
        facility = self.facility(peer={'instrumented': True, 'discard_at': 2}, chunk=8)
        report = facility.type_text('ABCD', anchor=PROMPT)
        self.assertEqual(report.status, inp.AMBIGUOUS)
        self.assertIn('discarded', report.detail)

    def test_instrumented_build_reports_queue_sequence_and_counters(self):
        facility = self.facility(peer={'instrumented': True})
        self.assertTrue(facility.client.supports('input_queue'))
        state = facility.automation_queue()
        self.assertEqual((state['queue'], state['capacity'], state['seq']), (0, 64, 0))
        report = facility.type_text('AB', anchor=PROMPT)
        self.assertEqual(report.status, inp.OBSERVED)
        self.assertTrue(report.steps[0]['automation']['matched'])
        state = facility.automation_queue()
        self.assertGreater(state['seq'], 0)
        self.assertEqual((state['accepted'], state['forwarded'], state['dropped']),
                         (8, 8, 0))

    def test_key_completion_is_verified_when_the_build_reports_it(self):
        facility = self.facility(peer={'instrumented': True})
        facility.client.tap(0x0F)
        facility.client.tap(0x10)
        self.assertEqual(facility.client.last_key_seq, 4)
        self.peer.completion_queue = 1
        with self.assertRaises(box.ProtocolError):
            facility.client.tap(0x11)

    def test_input_accounting_balances_across_a_request(self):
        facility = self.facility(peer={'instrumented': True})
        facility.client.type_ascii('AB')
        state = facility.automation_queue()
        self.assertTrue(state['accounting'])
        self.assertEqual(state['accepted'],
                         state['forwarded'] + state['dropped'] + state['pending'])
        self.assertEqual(facility.client.last_dropped_delta, 0)

    def test_cancel_discards_pending_events_with_accounting(self):
        facility = self.facility(peer={'instrumented': True, 'queue_only': True,
                                       'drain': False})
        facility.client.type_ascii('AB')
        result = facility.client.cancel_keys()
        self.assertEqual(result['cancelled'], 2)
        state = facility.automation_queue()
        self.assertEqual(state['queue'], 0)
        self.assertEqual(state['dropped'], 2)
        self.assertEqual(state['accepted'],
                         state['forwarded'] + state['dropped'] + state['pending'])

    def test_a_stopped_key_request_is_an_interrupted_delivery(self):
        facility = self.facility(peer={'instrumented': True})
        self.peer.stopped_next = True
        with self.assertRaises(box.ProtocolError):
            facility.client.tap(0x0F)

    def test_wait_queue_is_bounded_when_the_queue_never_drains(self):
        facility = self.facility(peer={'instrumented': True, 'queue_only': True, 'drain': False})
        facility.client.type_ascii('A')
        result = facility.client.wait_queue(40)
        self.assertFalse(result['matched'])
        self.assertGreater(result['queue'], 0)

    def test_video_metadata_matches_the_text_cursor(self):
        facility = self.facility(peer={'instrumented': True})
        video = facility.client.video()
        self.assertEqual((video['bios_mode'], video['text'], video['cols'], video['rows']),
                         (3, True, COLS, ROWS))
        facility.client.type_ascii('VER')
        self.assertEqual(facility.client.video()['cursor'], facility.client.text()['cursor'])
        self.peer.bios_mode = 0x12
        graphics = facility.client.video()
        self.assertFalse(graphics['text'])
        self.assertEqual(graphics['cursor'], [-1, -1])

    def test_mouse_state_reports_cumulative_delivery(self):
        facility = self.facility(peer={'instrumented': True, 'bios_mode': 0x12})
        facility.pointer(4, -2, 1)
        facility.pointer(1, 3, 0)
        state = facility.client.mouse_state()
        self.assertEqual((state['sent_dx'], state['sent_dy'], state['buttons']), (5, 1, 0))

    def test_forwarding_queue_blocks_observation_and_resend(self):
        facility = self.facility(peer={'instrumented': True, 'queue_only': True, 'drain': False})
        report = facility.type_text('ABC', anchor=PROMPT)
        self.assertEqual(report.status, inp.PENDING)
        self.assertIn('automation queue still forwarding', report.detail)
        self.assertEqual((report.bursts, len(report.steps)), (1, 1))
        self.assertEqual(report.steps[0]['automation']['matched'], False)

    def test_report_evidence_is_serializable_and_carries_each_layer(self):
        facility = self.facility(chunk=4)
        report = facility.type_text('ABCDE', anchor=PROMPT)
        import json
        payload = json.loads(json.dumps(report.as_dict()))
        self.assertEqual(set(payload['evidence']),
                         {'acknowledged', 'delivered', 'accepted', 'translated',
                          'observed', 'limitations'})
        self.assertEqual(payload['evidence']['translated'],
                         payload['evidence']['accepted'])
        self.assertEqual(len(payload['steps']), report.bursts)
        self.assertNotIn(TOKEN, json.dumps(payload))


class FreshRegionTests(unittest.TestCase):
    """The output-region model, independent of any peer or emulator."""

    def test_unchanged_screen_has_no_fresh_text(self):
        rows = ['A', 'B']
        self.assertEqual(profiles.fresh_text(rows, list(rows)), '')

    def test_appended_row_is_fresh(self):
        self.assertEqual(profiles.fresh_text(['A'], ['A', 'B']), 'B')

    def test_rewritten_row_is_fresh(self):
        self.assertEqual(profiles.fresh_text(['A', 'B'], ['A', 'C']), 'C')

    def test_scrolled_row_is_not_fresh(self):
        before = ['OLD1', 'OLD2', 'OLD3']
        after = ['OLD2', 'OLD3', 'NEW']
        region = profiles.fresh_region(before, after)
        self.assertEqual((region['shift'], region['rows']), (1, ['NEW']))

    def test_scrolled_history_does_not_match_a_needle(self):
        before = ['OLD1', 'OLD2', 'OLD3']
        after = ['OLD2', 'OLD3', 'NEW']
        self.assertNotIn('OLD1', profiles.fresh_text(before, after))

    def test_a_blank_screen_makes_every_drawn_row_fresh(self):
        before = [' ' * 8] * 3
        self.assertEqual(profiles.fresh_text(before, [' ' * 8, ' ' * 8, 'HELLO']), 'HELLO')

    def test_rows_of_different_length_are_rejected(self):
        with self.assertRaises(TypeError):
            profiles.fresh_region('rows', ['A'])


if __name__ == '__main__':
    unittest.main()
