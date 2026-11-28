"""Portable pointer tests: synthetic guest with the measured response curve.

No ROMs, no emulator and no DeskMate media are needed. The fake guest models
the behaviour measured natively in campaign graphical-input-qualification-001:
requests under 128 counts are scaled by an accelerated curve, the driver only
consumes motion on its 18.2 Hz tick, and the clamp corner is (0, 5).
"""
import io
import struct
import unittest
import zlib

from deskmate_formats.automation.pointer import (
    MDIAG_LAYOUT, MDIAG_SIGNATURE, Calibration, Failure, MemoryMouseOracle,
    Pointer, PointerError, PointerReceipt,
)

CURVE = ((4, 2), (8, 10), (16, 26), (24, 42), (32, 58), (48, 90), (64, 122))
CLAMP = (0, 5)
SIZE = (640, 480)


def _chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data
            + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))


def png(width, height, cursor=None):
    """Minimal RGB PNG with an optional 12x16 cursor block."""
    rows = []
    for y in range(height):
        row = bytearray(b'\x00')
        for x in range(width):
            inside = (cursor is not None
                      and cursor[0] <= x < cursor[0] + 12
                      and cursor[1] <= y < cursor[1] + 16)
            row.extend(b'\x00\x00\x00' if inside else b'\xc0\xc0\xc0')
        rows.append(bytes(row))
    raw = zlib.compress(b''.join(rows), 1)
    return (b'\x89PNG\r\n\x1a\n'
            + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + _chunk(b'IDAT', raw) + _chunk(b'IEND', b''))


def deliver(units):
    """Apply the measured curve to one axis, as the guest driver would."""
    if abs(units) >= 128:
        return 0
    sign = 1 if units >= 0 else -1
    magnitude = abs(units)
    if magnitude < CURVE[0][0]:
        return sign * 1
    for (u0, p0), (u1, p1) in zip(CURVE, CURVE[1:]):
        if magnitude <= u1:
            return sign * int(round(p0 + (magnitude - u0) * (p1 - p0) / (u1 - u0)))
    return sign * int(round(magnitude * CURVE[-1][1] / CURVE[-1][0]))


class FakeGuest:
    RECORD_ADDRESS = 0x49A * 16

    """Synthetic guest driver with a clock, a pending accumulator and buttons."""

    def __init__(self, width=640, height=480, period_ms=55, dead=()):
        self.width = width
        self.height = height
        self.period_ms = period_ms
        self.dead = set(dead)
        self.x, self.y = 320, 100
        self.buttons = 0
        self.presses = 0
        self.releases = 0
        self.ticks = 0
        self.pending = [0, 0]
        self.clock = 0
        self.frozen = False
        self.silent = False
        self.commands = []
        self.shown = (self.x, self.y)

    # -- socket surface -------------------------------------------------
    def mouse(self, dx, dy, buttons):
        self.commands.append(('mouse', dx, dy, buttons))
        if dx == 0 and dy == 0:
            for down, mask in ((buttons & 1, 1), (buttons & 2, 2)):
                was = bool(self.buttons & mask)
                if down and not was:
                    self.presses += 1
                if not down and was:
                    self.releases += 1
        self.buttons = buttons
        self.pending[0] += dx
        self.pending[1] += dy
        return {'ok': True}

    def advance(self, milliseconds, stop=None):
        self.commands.append(('advance', milliseconds))
        remaining = milliseconds
        while remaining >= self.period_ms:
            remaining -= self.period_ms
            self.clock += self.period_ms
            self._tick()
        self.clock += remaining
        return {'ok': True}

    def framebuffer(self):
        return png(self.width, self.height, (self.shown[0], self.shown[1])), {'w': self.width}

    def memory(self, address, length):
        record = MDIAG_LAYOUT.pack(MDIAG_SIGNATURE, self.x, self.y, self.buttons,
                                  self.presses, self.releases, self.ticks, 1, 0)
        buf = bytearray(length)
        start = self.RECORD_ADDRESS - address
        for index, value in enumerate(record):
            position = start + index
            if 0 <= position < length:
                buf[position] = value
        return bytes(buf)

    # -- driver model ---------------------------------------------------
    def _tick(self):
        if self.silent:
            return
        self.ticks = (self.ticks + 1) & 0xFFFF
        if self.frozen:
            self.pending = [0, 0]
            return
        dx, dy = self.pending
        self.pending = [0, 0]
        if dx and abs(dx) not in self.dead:
            self.x = self._axis(self.x + deliver(dx), self.width)
        if dy and abs(dy) not in self.dead:
            self.y = self._axis(self.y + deliver(dy), self.height)
        self.x = max(CLAMP[0], min(self.width - 1, self.x))
        self.y = max(CLAMP[1], min(self.height - 1, self.y))
        self.shown = (self.x, self.y)

    @staticmethod
    def _axis(value, extent):
        return max(0, min(extent - 1, value))


def oracle_for(guest):
    return MemoryMouseOracle(guest, 0x49A)


def make_pointer(guest, **kwargs):
    return Pointer(guest, oracle=oracle_for(guest), **kwargs)


class CalibrationTests(unittest.TestCase):
    def test_inverse_curve_matches_measured_response(self):
        curve = [(4, 2.0), (8, 10.0), (16, 26.0), (24, 42.0), (32, 58.0),
                 (48, 90.0), (64, 122.0)]
        calibration = Calibration(x_ratio=1.9, y_ratio=1.9, curve=curve)
        for units, pixels in curve:
            self.assertEqual(pixels, deliver(calibration.units_for(int(pixels))))

    def test_requests_never_reach_the_truncation_limit(self):
        calibration = Calibration(x_ratio=1.9, y_ratio=1.9, curve=list(map(tuple, CURVE)))
        for delta in (1, 5, 200, 5000, -5000):
            self.assertLess(abs(calibration.units_for(delta)), 128)

    def test_dead_zone_size_is_skipped_not_fatal(self):
        guest = FakeGuest(dead=(4,))
        pointer = make_pointer(guest)
        calibration = pointer.calibrate()
        self.assertTrue(calibration.skipped)
        self.assertGreaterEqual(len(calibration.curve), 2)
        self.assertIsNone(pointer.move_to(300, 200).failure)


class MovementTests(unittest.TestCase):
    def test_move_to_reaches_target(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        receipt = pointer.move_to(120, 90)
        self.assertIsNone(receipt.failure)
        self.assertLessEqual(abs(receipt.actual[0] - 120), 2)
        self.assertLessEqual(abs(receipt.actual[1] - 90), 2)
        self.assertGreater(receipt.steps, 0)

    def test_move_to_out_of_range_is_classified(self):
        guest = FakeGuest()
        receipt = make_pointer(guest).move_to(700, 90)
        self.assertEqual(Failure.OUT_OF_RANGE, receipt.failure)
        self.assertFalse(receipt.ok)

    def test_stalled_driver_is_reported_as_blocked(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        pointer.home()
        pointer.calibrate()
        guest.frozen = True
        receipt = pointer.move_to(40, 300)
        self.assertIn(receipt.failure, (Failure.BLOCKED, Failure.AMBIGUOUS))
        self.assertFalse(receipt.ok)

    def test_queued_motion_waits_for_the_driver_tick(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        pointer.home()
        before = guest.ticks
        pointer.sample_settled(min_ticks=2)
        self.assertGreaterEqual(guest.ticks - before, 2)

    def test_silent_driver_raises_instead_of_guessing(self):
        guest = FakeGuest()
        pointer = make_pointer(guest, settle_ms=20)
        guest.mouse(8, 0, 0)
        guest.silent = True
        with self.assertRaises(PointerError):
            pointer.sample_settled(min_ticks=2, timeout_ms=200)


class ButtonTests(unittest.TestCase):
    def test_click_delivers_one_press_and_one_release(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        receipt = pointer.click_at(200, 200)
        self.assertIsNone(receipt.failure)
        self.assertEqual(1, guest.presses)
        self.assertEqual(1, guest.releases)
        self.assertEqual(0, guest.buttons)

    def test_release_all_clears_a_stuck_button(self):
        guest = FakeGuest()
        guest.mouse(0, 0, 1)
        pointer = make_pointer(guest)
        receipt = pointer.release_all()
        self.assertTrue(receipt.ok)
        self.assertEqual(0, guest.buttons)

    def test_double_click_records_two_press_release_pairs(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        receipt = pointer.double_click_at(120, 120)
        self.assertEqual(2, guest.presses)
        self.assertEqual(2, guest.releases)
        self.assertIn('gap', receipt.detail or '')


class DragTests(unittest.TestCase):
    def test_drag_presses_moves_and_releases(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        receipt = pointer.drag((80, 60), (200, 300), step_pixels=16)
        self.assertIsNone(receipt.failure)
        self.assertLessEqual(abs(receipt.actual[1] - 300), 2)
        self.assertEqual(1, guest.presses)
        self.assertEqual(1, guest.releases)
        self.assertEqual(0, guest.buttons)

    def test_drag_holds_the_button_across_intermediate_moves(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        pointer.drag((80, 60), (300, 300), step_pixels=20)
        presses = [i for i, c in enumerate(guest.commands)
                   if c[0] == 'mouse' and c[3] == 1 and not (c[1], c[2]) == (0, 0)]
        releases = [i for i, c in enumerate(guest.commands) if c[0] == 'mouse' and c[3] == 0]
        self.assertTrue(presses and releases)
        after = guest.commands[presses[0]:releases[-1]]
        moves = [c for c in after if c[0] == 'mouse' and (c[1] or c[2])]
        self.assertTrue(moves)
        self.assertTrue(all(c[3] == 1 for c in moves))


class OracleTests(unittest.TestCase):
    def test_signature_mismatch_is_rejected(self):
        guest = FakeGuest()
        oracle = oracle_for(guest)
        original = guest.memory

        def blank(address, length):
            return b'\x00' * length

        guest.memory = blank
        with self.assertRaises(PointerError):
            oracle.read()
        guest.memory = original
        self.assertEqual(guest.y, oracle.read()['y'])

    def test_live_check_reports_tick_progress(self):
        guest = FakeGuest()
        oracle = oracle_for(guest)
        result = oracle.verify_live()
        self.assertGreater(result['ticks_after'], result['ticks_before'])

    def test_receipt_serialises_without_dataclass_objects(self):
        guest = FakeGuest()
        pointer = make_pointer(guest)
        payload = pointer.move_to(150, 150).as_dict()
        self.assertEqual('move_to', payload['operation'])
        self.assertIsInstance(payload['target'], tuple)
        self.assertIsInstance(payload['guest'], dict)


if __name__ == '__main__':
    unittest.main()
