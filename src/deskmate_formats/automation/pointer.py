"""Guest-level pointer delivery, calibration and verification for 86Box.

Layer split, so that application knowledge does not leak into the transport:

* :class:`PointerTransport` sends relative mouse counts and an absolute button
  mask. It knows nothing about pixels, controls or applications.
* :class:`Frame` decodes the emulator's native PNG framebuffer and finds
  changed regions; :class:`FrameCursor` uses that to localise the guest's drawn
  pointer without any guest cooperation.
* :class:`MemoryMouseOracle` reads an independently authored resident guest
  diagnostic that publishes ``INT 33h`` position, buttons and transition
  counters. When present it is the authoritative position source.
* :class:`Pointer` calibrates the guest driver's counts-to-pixels response and
  closes the loop: move, sample, correct. Every operation returns a structured
  receipt separating acknowledgement, delivery, guest-driver state, visible
  cursor and an optional application-visible observation.
* :class:`ScreenState` observes application-visible results in the framebuffer.

Measured properties of the production guest (Tandy 1000 RSX, PS/2 mouse,
Logitech 6.00 driver, DeskMate 3.05) are recorded in
``docs/research/graphical-input-qualification-001.md``. The two that shape this
code: the response is accelerated (about 0.5 px/unit for 4 units up to about
1.9 px/unit at 64), and a single request of 128 units or more delivers nothing.
Neither is guessed here: calibration measures the curve, and every move is
bounded and observed.

Nothing retries a move whose reply was lost. :meth:`Pointer.release_all` is the
only safe follow-up and is idempotent. Evidence attributes are independent:
``acknowledged`` is the socket reply, ``delivered`` the emulated device
acceptance, ``guest`` the driver's own state, ``visible`` the drawn cursor, and
``observed`` is only ever set by a caller-supplied expectation.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import StrEnum
import struct
import zlib

from .client import CommandError, ProtocolError

LEFT = 1
RIGHT = 2
MIDDLE = 4

#: A single relative request of this many units or more delivered nothing in
#: native trials; callers are therefore bounded well below it.
MAX_REQUEST_UNITS = 64


class PointerError(RuntimeError):
    """A pointer operation could not be completed or attributed."""


class Failure(StrEnum):
    """Explicit outcome classes; absence of success is never assumed."""

    UNSUPPORTED = 'unsupported_capability'
    REJECTED = 'command_rejected'
    UNCERTAIN = 'uncertain_delivery'
    NOT_LOCATED = 'cursor_not_located'
    AMBIGUOUS = 'ambiguous_screen'
    BLOCKED = 'clamped_or_blocked'
    NOT_REACHED = 'target_not_reached'
    OUT_OF_RANGE = 'target_outside_framebuffer'
    NO_GUEST_STATE = 'guest_state_unavailable'


@dataclass(frozen=True)
class Box:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def area(self):
        return self.width * self.height

    def contains(self, x, y):
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1

    def as_list(self):
        return [self.x0, self.y0, self.x1, self.y1]


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def decode_png(png):
    """Decode an 8-bit truecolour PNG (with or without alpha) to RGB bytes.

    The emulator emits non-interlaced 8-bit RGB. Anything outside that profile
    is rejected rather than guessed at, so a changed encoder cannot silently
    produce wrong pixels.
    """
    if png[:8] != b'\x89PNG\r\n\x1a\n':
        raise PointerError('not a PNG')
    offset = 8
    width = height = depth = color = interface = None
    compressed = bytearray()
    palette = None
    while offset + 12 <= len(png):
        length = int.from_bytes(png[offset:offset + 4], 'big')
        kind = png[offset + 4:offset + 8]
        data = png[offset + 8:offset + 8 + length]
        crc = int.from_bytes(png[offset + 8 + length:offset + 12 + length], 'big')
        if zlib.crc32(kind + data) != crc:
            raise PointerError('PNG checksum mismatch')
        if kind == b'IHDR':
            width, height, depth, color, _, _, interface = struct.unpack('>IIBBBBB', data)
        elif kind == b'PLTE':
            palette = data
        elif kind == b'IDAT':
            compressed += data
        elif kind == b'IEND':
            break
        offset += 12 + length
    if depth != 8 or color not in (2, 3, 6) or interface != 0 or not width or not height:
        raise PointerError('unsupported PNG profile')
    channels = {2: 3, 3: 1, 6: 4}[color]
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    if len(raw) != (stride + 1) * height:
        raise PointerError('truncated PNG data')
    rows = []
    previous = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind = raw[start]
        line = bytearray(raw[start + 1:start + 1 + stride])
        if kind == 0:
            pass
        elif kind == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                upleft = previous[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, previous[i], upleft)) & 0xFF
        else:
            raise PointerError('unknown PNG filter')
        previous = line
        if color == 3:
            if palette is None:
                raise PointerError('indexed PNG without palette')
            expanded = bytearray(width * 3)
            for x, index in enumerate(line):
                expanded[3 * x:3 * x + 3] = palette[3 * index:3 * index + 3]
            rows.append(bytes(expanded))
        elif color == 6:
            rows.append(bytes(b for x in range(width) for b in line[4 * x:4 * x + 3]))
        else:
            rows.append(bytes(line))
    return width, height, b''.join(rows)


class Frame:
    """A decoded native framebuffer; exactly what the guest displayed."""

    __slots__ = ('width', 'height', 'rgb')

    def __init__(self, width, height, rgb):
        if len(rgb) != width * height * 3:
            raise PointerError('frame size does not match its dimensions')
        self.width = width
        self.height = height
        self.rgb = rgb

    @classmethod
    def from_png(cls, png):
        return cls(*decode_png(png))

    def pixel(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise PointerError('pixel outside the framebuffer')
        i = 3 * (y * self.width + x)
        return tuple(self.rgb[i:i + 3])

    def digest(self, box=None):
        if box is None:
            data = self.rgb
            prefix = b'frame'
        else:
            rows = []
            for y in range(box.y0, box.y1):
                rows.append(self.rgb[3 * (y * self.width + box.x0):3 * (y * self.width + box.x1)])
            data = b''.join(rows)
            prefix = b'region'
        return hashlib.sha256(prefix + data).hexdigest()

    def diff_pixels(self, other, threshold=8):
        """Changed pixel coordinates; identical rows are skipped wholesale."""
        if (self.width, self.height) != (other.width, other.height):
            raise PointerError('frames have different dimensions')
        changed = []
        stride = self.width * 3
        for y in range(self.height):
            start = y * stride
            if self.rgb[start:start + stride] == other.rgb[start:start + stride]:
                continue
            for x in range(self.width):
                i = start + 3 * x
                a = self.rgb[i:i + 3]
                b = other.rgb[i:i + 3]
                if (abs(a[0] - b[0]) > threshold or abs(a[1] - b[1]) > threshold
                        or abs(a[2] - b[2]) > threshold):
                    changed.append((x, y))
        return changed

    def diff_boxes(self, other, threshold=8, min_pixels=1, gap=0):
        """Connected changed regions, largest first.

        ``gap`` merges fragments that are close but not touching. The guest's
        XOR-drawn pointer breaks into several pieces over text or patterned
        backgrounds; the sprite is still one object.
        """
        return components(self.diff_pixels(other, threshold), min_pixels, gap)


def components(points, min_pixels=1, gap=0):
    """Connected components of a coordinate list, largest first."""
    if type(gap) is not int or not 0 <= gap <= 8:
        raise ValueError('invalid component merge gap')
    remaining = set(points)
    boxes = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        x0 = x1 = start[0]
        y0 = y1 = start[1]
        count = 0
        while stack:
            x, y = stack.pop()
            count += 1
            x0, x1 = min(x0, x), max(x1, x)
            y0, y1 = min(y0, y), max(y1, y)
            for dx in range(-gap, gap + 1):
                for dy in range(-gap, gap + 1):
                    neighbour = (x + dx, y + dy)
                    if neighbour in remaining:
                        remaining.remove(neighbour)
                        stack.append(neighbour)
        if count >= min_pixels:
            boxes.append(Box(x0, y0, x1 + 1, y1 + 1))
    boxes.sort(key=lambda b: b.area, reverse=True)
    return boxes


@dataclass(frozen=True)
class Cursor:
    """Top-left pixel of the guest's drawn pointer, with its sprite size."""

    x: int
    y: int
    width: int = 0
    height: int = 0

    @property
    def box(self):
        return Box(self.x, self.y, self.x + self.width, self.y + self.height)

    def as_dict(self):
        return asdict(self)


@dataclass
class PointerReceipt:
    """Independent evidence attributes for one pointer operation."""

    operation: str
    acknowledged: bool = False
    delivered: bool = False
    guest: dict | None = None
    visible: dict | None = None
    target: tuple | None = None
    actual: tuple | None = None
    steps: int = 0
    emulated_ms: int = 0
    observed: bool | None = None
    failure: str | None = None
    detail: str | None = None

    @property
    def ok(self):
        return self.failure is None

    def as_dict(self):
        return asdict(self)


class PointerTransport:
    """Relative motion and absolute button state over the authenticated socket."""

    def __init__(self, client):
        self.client = client
        self.buttons = 0
        self.moves = 0

    def move(self, dx, dy, buttons=None):
        mask = self.buttons if buttons is None else buttons
        reply = self.client.mouse(dx, dy, mask)
        self.buttons = mask
        self.moves += 1
        return reply

    def press(self, button):
        return self.move(0, 0, self.buttons | button)

    def release(self, button):
        return self.move(0, 0, self.buttons & ~button)

    def release_all(self):
        return self.move(0, 0, 0)

    def advance(self, milliseconds, stop=None):
        return self.client.advance(milliseconds, stop=stop)


class FrameCursor:
    """Localise the drawn pointer by differencing consecutive native frames."""

    def __init__(self, client, settle_ms=120, threshold=8, gap=2):
        if settle_ms < 0 or not 0 <= threshold <= 255:
            raise ValueError('invalid settle time or threshold')
        self.client = client
        self.settle_ms = settle_ms
        self.threshold = threshold
        self.gap = gap

    def capture(self):
        png, meta = self.client.framebuffer()
        return Frame.from_png(png), meta, png

    def locate(self, before, after, previous, expected=None):
        """Identify the cursor after one move.

        Returns ``previous`` when the frame did not change (a clamped or
        dropped move) and raises when the delta cannot be attributed to one
        cursor.
        """
        boxes = before.diff_boxes(after, self.threshold, gap=self.gap)
        if not boxes:
            return previous
        if previous is not None:
            for box in boxes:
                if box.x0 == previous.x and box.y0 == previous.y:
                    others = [b for b in boxes if b != box]
                    if len(others) == 1:
                        return Cursor(others[0].x0, others[0].y0,
                                      previous.width or others[0].width,
                                      previous.height or others[0].height)
                    if not others:
                        return previous
                    raise PointerError('more than two changed regions')
        if len(boxes) == 2 and (boxes[0].width, boxes[0].height) == (boxes[1].width, boxes[1].height):
            if expected is not None:
                dx, dy = expected
                reference = previous or Cursor(0, 0)
                def score(b):
                    return (((b.x0 - reference.x) * (1 if dx >= 0 else -1))
                            + ((b.y0 - reference.y) * (1 if dy >= 0 else -1)))
                chosen = max(boxes, key=score)
            else:
                chosen = boxes[0]
            return Cursor(chosen.x0, chosen.y0, chosen.width, chosen.height)
        raise PointerError(f'{len(boxes)} changed regions cannot be attributed to the pointer')


@dataclass
class Calibration:
    """Measured guest response: emulator counts to guest pixels."""

    x_ratio: float
    y_ratio: float
    samples: list = field(default_factory=list)
    spread: float = 0.0
    nonlinear: bool = False
    curve: list = field(default_factory=list)
    skipped: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)

    def units_for(self, pixels, axis='x'):
        """Inverse response: the request that should deliver ``pixels``.

        Interpolates the measured curve; beyond it, extrapolates with the last
        measured ratio. Never returns a request at or above the truncation
        limit.
        """
        if type(pixels) is not int:
            raise ValueError('pixel delta must be an integer')
        if pixels == 0:
            return 0
        sign = 1 if pixels > 0 else -1
        magnitude = abs(pixels)
        ratio = self.x_ratio if axis == 'x' else self.y_ratio
        points = self.curve
        if not points:
            units = int(round(magnitude / ratio))
        elif magnitude <= points[0][1]:
            units = points[0][0]
        else:
            units = None
            for (u0, p0), (u1, p1) in zip(points, points[1:]):
                if magnitude <= p1:
                    if p1 == p0:
                        units = u1
                    else:
                        units = int(round(u0 + (magnitude - p0) * (u1 - u0) / (p1 - p0)))
                    break
            if units is None:
                u_last, p_last = points[-1]
                units = int(round(magnitude * u_last / p_last)) if p_last else int(round(magnitude / ratio))
        units = max(1, min(MAX_REQUEST_UNITS, abs(units)))
        return sign * units


class Pointer:
    """Calibrated aiming and clicking with explicit evidence per operation."""

    def __init__(self, client, oracle=None, settle_ms=120, press_ms=80,
                 double_click_ms=90, threshold=8, max_request=MAX_REQUEST_UNITS):
        if not 1 <= max_request <= MAX_REQUEST_UNITS:
            raise ValueError('max_request must be 1..64; larger requests are dropped')
        self.client = client
        self.oracle = oracle
        self.transport = PointerTransport(client)
        self.cursor = FrameCursor(client, settle_ms=settle_ms, threshold=threshold)
        self.calibration = None
        self.position = None
        self.home_origin = None
        self.settle_ms = settle_ms
        self.press_ms = press_ms
        self.double_click_ms = double_click_ms
        self.max_request = max_request

    # -- observation -----------------------------------------------------
    def _advance(self, milliseconds):
        return self.transport.advance(milliseconds)

    def _frame(self):
        return self.cursor.capture()[0]

    def frame(self):
        """Current native frame and its PNG bytes."""
        frame, _meta, png = self.cursor.capture()
        return frame, png

    def guest_state(self):
        """The guest driver's own position/buttons, or None without the oracle."""
        return self.oracle.read() if self.oracle is not None else None

    def sample_settled(self, min_ticks=2, timeout_ms=3000, step_ms=60):
        """Advance until the guest driver has run and consumed queued motion.

        Measured failure mode: while DeskMate repaints, the driver's timer hook
        does not run, so relative motion accumulates in the device. Reading
        before the driver processes it looks like a dropped move; several
        requests then land together and overshoot. Waiting for two driver ticks
        makes each observation correspond to consumed input.
        """
        if self.oracle is None:
            self._advance(self.settle_ms)
            return None
        first = self.oracle.read()
        elapsed = 0
        while elapsed < timeout_ms:
            self._advance(step_ms)
            elapsed += step_ms
            current = self.oracle.read()
            if current['ticks'] - first['ticks'] >= min_ticks:
                return current
        raise PointerError(f'guest driver did not run within {timeout_ms} ms of emulated time')

    def _settled_position(self):
        if self.oracle is None:
            self._advance(self.settle_ms)
            return self._position_tuple()
        sample = self.sample_settled()
        return sample['x'], sample['y']

    def _position_tuple(self):
        if self.oracle is not None:
            sample = self.oracle.read()
            return sample['x'], sample['y']
        if self.position is None:
            raise PointerError('no tracked position; home first')
        return self.position.x, self.position.y

    # -- calibration -----------------------------------------------------
    def home(self):
        """Drive into the driver's clamp corner and measure the sprite.

        The clamp is the only absolute reference the relative protocol offers.
        Measured clamp corner on this guest is (0, 5), not (0, 0): the driver
        reserves a few scan lines. That value is observed, never assumed.
        """
        if self.oracle is not None:
            self.home_origin = self._clamp(oracle=True)
            return {'origin': list(self.home_origin), 'source': 'guest_oracle'}
        self.home_origin = self._clamp(oracle=False)
        return {'origin': list(self.home_origin), 'source': 'framebuffer'}

    def _clamp(self, oracle):
        """Drive into the clamp corner; a dropped request is not a clamp.

        The guest's clamp corner is (0, 5) on this driver. Reaching the corner
        is required, so an unchanged position only counts as a clamp when it is
        already at the left edge; two unchanged positions elsewhere are a
        blocked pointer, not success.
        """
        previous = None
        quiet = 0
        for _ in range(80):
            if oracle:
                current = self._position_tuple()
                if current[0] <= 2 and current[1] <= 8:
                    previous = current
                    break
                if current == previous:
                    quiet += 1
                    if quiet >= 2:
                        raise PointerError(
                            f'pointer stopped at {current}, away from the clamp corner')
                else:
                    quiet = 0
                previous = current
            before = self._frame()
            self.transport.move(-self.max_request, -self.max_request)
            if oracle:
                self._settled_position()
            else:
                self._advance(self.settle_ms)
            after = self._frame()
            boxes = after.diff_boxes(before, self.cursor.threshold, gap=self.cursor.gap)
            candidates = [b for b in boxes if b.width <= 64 and b.height <= 64]
            if not oracle:
                if not candidates:
                    break
                best = min(candidates, key=lambda b: (b.x0, b.y0))
                if best.x0 <= 1:
                    previous = (best.x0, best.y0)
                    break
                previous = (best.x0, best.y0)
        origin = self._position_tuple() if oracle else previous
        if origin is None:
            raise PointerError('could not establish a clamp origin')
        # Measure the sprite by moving away from the corner.
        before = self._frame()
        self.transport.move(24, 24)
        self._settled_position()
        after = self._frame()
        boxes = [b for b in after.diff_boxes(before, self.cursor.threshold, gap=self.cursor.gap)
                 if b.width <= 64 and b.height <= 64]
        if boxes:
            sprite = min(boxes, key=lambda b: (b.x0, b.y0))
        width = sprite.width if sprite else 12
        height = sprite.height if sprite else 16
        self.position = Cursor(origin[0], origin[1], width, height)
        return origin

    def calibrate(self, sizes=(4, 8, 16, 24, 32, 48, 64)):
        """Measure the accelerated response and build its inverse curve.

        Very small requests fall below the guest driver's dead zone (measured:
        4 units sometimes moved nothing). A size that produces no motion is
        retried once and then skipped; the curve needs at least two usable
        sizes to be meaningful.
        """
        if self.home_origin is None:
            self.home()
        samples = []
        curve = []
        skipped = []
        for size in sizes:
            if size < 1 or size > self.max_request:
                raise ValueError('calibration sizes must be 1..max_request')
            for axis in ('x', 'y'):
                dx, dy = (size, 0) if axis == 'x' else (0, size)
                travelled = 0
                for _attempt in range(2):
                    start = self._position_tuple()
                    self.transport.move(dx, dy)
                    end = self._settled_position()
                    travelled = (end[0] - start[0]) if axis == 'x' else (end[1] - start[1])
                    if travelled:
                        break
                if not travelled:
                    skipped.append({'axis': axis, 'units': size})
                    continue
                samples.append({'axis': axis, 'units': size, 'pixels': travelled,
                                'ratio': travelled / size})
        by_size = {}
        for sample in samples:
            by_size.setdefault(sample['units'], []).append(abs(sample['pixels']))
        for units in sorted(by_size):
            pixels = sum(by_size[units]) / len(by_size[units])
            curve.append((units, pixels))
        if len(curve) < 2:
            raise PointerError('not enough usable calibration samples')
        xs = [s['ratio'] for s in samples if s['axis'] == 'x']
        ys = [s['ratio'] for s in samples if s['axis'] == 'y']
        ratios = xs + ys
        mean = sum(ratios) / len(ratios)
        spread = max(ratios) - min(ratios)
        self.calibration = Calibration(
            x_ratio=sum(xs) / len(xs), y_ratio=sum(ys) / len(ys), samples=samples,
            spread=spread, nonlinear=spread > 0.08 * mean, curve=curve,
            skipped=skipped)
        self.position = Cursor(*self._position_tuple(),
                               self.position.width if self.position else 0,
                               self.position.height if self.position else 0)
        return self.calibration

    # -- movement --------------------------------------------------------
    def move_to(self, x, y, tolerance=2, max_steps=20):
        """Close the loop until the cursor reaches the target pixel."""
        if self.home_origin is None:
            self.home()
        if self.calibration is None:
            self.calibrate()
        frame = self._frame()
        if not (0 <= x < frame.width and 0 <= y < frame.height):
            return PointerReceipt('move_to', target=(x, y), actual=self._position_tuple(),
                                  failure=Failure.OUT_OF_RANGE,
                                  detail=f'framebuffer is {frame.width}x{frame.height}')
        receipt = PointerReceipt('move_to', target=(x, y), acknowledged=True, delivered=True)
        stationary = 0
        for step in range(1, max_steps + 1):
            px, py = self._position_tuple()
            dxp, dyp = x - px, y - py
            if abs(dxp) <= tolerance and abs(dyp) <= tolerance:
                receipt.actual = (px, py)
                receipt.guest = self.guest_state()
                receipt.steps = step - 1
                return receipt
            ux = self.calibration.units_for(dxp, 'x')
            uy = self.calibration.units_for(dyp, 'y')
            try:
                self.transport.move(ux, uy)
            except CommandError as exc:
                receipt.failure = Failure.REJECTED
                receipt.detail = str(exc)
                return receipt
            except ProtocolError as exc:
                receipt.failure = Failure.UNCERTAIN
                receipt.detail = f'{exc}; do not replay the move'
                return receipt
            try:
                nx, ny = self._settled_position()
            except PointerError as exc:
                receipt.failure = Failure.AMBIGUOUS
                receipt.detail = str(exc)
                return receipt
            receipt.steps += 1
            receipt.emulated_ms += self.settle_ms
            if (nx, ny) == (px, py):
                stationary += 1
                if stationary >= 2:
                    receipt.actual = (nx, ny)
                    receipt.guest = self.guest_state()
                    receipt.failure = Failure.BLOCKED
                    receipt.detail = 'two requests produced no cursor change'
                    return receipt
            else:
                stationary = 0
        receipt.actual = self._position_tuple()
        receipt.guest = self.guest_state()
        receipt.failure = Failure.NOT_REACHED
        receipt.detail = f'stopped at {receipt.actual} after {max_steps} steps'
        return receipt

    def move_by(self, dx, dy):
        """Relative move in guest pixels, resolved through the calibration."""
        px, py = self._position_tuple()
        return self.move_to(px + dx, py + dy)

    # -- buttons ---------------------------------------------------------
    def _button_events(self, mask, presses, gap_ms=None):
        receipt = PointerReceipt('button')
        gap = self.settle_ms if gap_ms is None else gap_ms
        before = self.guest_state()
        observed_press = None
        for index in range(presses):
            try:
                self.transport.press(mask)
            except ProtocolError as exc:
                receipt.failure = Failure.UNCERTAIN
                receipt.detail = f'{exc}; button state is uncertain, release explicitly'
                return receipt
            receipt.acknowledged = receipt.delivered = True
            if self.oracle is not None:
                self.sample_settled(min_ticks=1)
            else:
                self._advance(self.press_ms)
            held = self.guest_state()
            if held is not None:
                observed_press = bool(held['buttons'] & mask)
            try:
                self.transport.release(mask)
            except ProtocolError as exc:
                receipt.failure = Failure.UNCERTAIN
                receipt.detail = f'{exc}; release is uncertain'
                return receipt
            if self.oracle is not None:
                self.sample_settled(min_ticks=1)
                if index + 1 < presses:
                    self._advance(gap)
            else:
                self._advance(gap if index + 1 < presses else self.settle_ms)
            receipt.emulated_ms += self.press_ms + self.settle_ms
        after = self.guest_state()
        receipt.actual = self._position_tuple()
        if before is not None and after is not None:
            receipt.guest = {
                'before': {k: before[k] for k in ('buttons', 'presses', 'releases')},
                'pressed': observed_press,
                'after': {k: after[k] for k in ('buttons', 'presses', 'releases')},
                'press_events': after['presses'] - before['presses'],
                'release_events': after['releases'] - before['releases'],
                'expected_events': presses,
            }
            if observed_press is False:
                receipt.failure = Failure.NOT_LOCATED
                receipt.detail = 'guest driver did not report the button down while held'
            elif after['buttons'] != 0:
                receipt.failure = Failure.UNCERTAIN
                receipt.detail = 'guest still reports a button down after release'
        return receipt

    def click(self, button=LEFT):
        """Click at the current position; no aiming is implied."""
        return self._button_events(button, 1)

    def click_at(self, x, y, button=LEFT, tolerance=2):
        receipt = self.move_to(x, y, tolerance=tolerance)
        receipt.operation = 'click_at'
        if not receipt.ok:
            return receipt
        click = self._button_events(button, 1)
        receipt.acknowledged &= click.acknowledged
        receipt.delivered &= click.delivered
        receipt.emulated_ms += click.emulated_ms
        receipt.guest = click.guest or receipt.guest
        if click.failure:
            receipt.failure = click.failure
            receipt.detail = click.detail
        return receipt

    def double_click_at(self, x, y, button=LEFT, interval_ms=None, tolerance=2):
        receipt = self.move_to(x, y, tolerance=tolerance)
        receipt.operation = 'double_click_at'
        if not receipt.ok:
            return receipt
        interval = self.double_click_ms if interval_ms is None else interval_ms
        if type(interval) is not int or not 0 <= interval <= 1000:
            raise ValueError('double-click interval must be 0..1000 emulated ms')
        click = self._button_events(button, 2, gap_ms=interval)
        receipt.acknowledged &= click.acknowledged
        receipt.delivered &= click.delivered
        receipt.emulated_ms += click.emulated_ms
        receipt.guest = click.guest or receipt.guest
        if click.failure:
            receipt.failure = click.failure
            receipt.detail = click.detail
        receipt.detail = f'gap {interval} ms between the release and the second press'
        return receipt

    def drag(self, start, end, button=LEFT, step_pixels=24, tolerance=2, hold_ms=500):
        """Press at ``start``, move in bounded increments, release at ``end``."""
        receipt = self.move_to(*start, tolerance=tolerance)
        receipt.operation = 'drag'
        receipt.target = tuple(end)
        if not receipt.ok:
            return receipt
        try:
            self.transport.press(button)
            receipt.acknowledged = receipt.delivered = True
        except ProtocolError as exc:
            receipt.failure = Failure.UNCERTAIN
            receipt.detail = f'{exc}; button state is uncertain'
            return receipt
        self._advance(self.press_ms)
        x0, y0 = start
        x1, y1 = end
        distance = max(abs(x1 - x0), abs(y1 - y0))
        steps = max(1, (distance + step_pixels - 1) // step_pixels)
        for i in range(1, steps + 1):
            px, py = self._position_tuple()
            target = (int(round(x0 + (x1 - x0) * i / steps)),
                      int(round(y0 + (y1 - y0) * i / steps)))
            dxp, dyp = target[0] - px, target[1] - py
            if abs(dxp) > 1 or abs(dyp) > 1:
                ux = self.calibration.units_for(dxp, 'x')
                uy = self.calibration.units_for(dyp, 'y')
                try:
                    self.transport.move(ux, uy)
                except (CommandError, ProtocolError) as exc:
                    self.release_all()
                    receipt.failure = Failure.UNCERTAIN
                    receipt.detail = f'held move failed: {exc}'
                    return receipt
                self._settled_position()
                receipt.steps += 1
        # Menus highlight the item under the pointer one processing tick late;
        # releasing immediately activates the previously highlighted entry. A
        # brief hold plus a small in-item nudge lets the highlight catch up.
        self._advance(hold_ms)
        try:
            self.transport.move(1, 0)
            self._settled_position()
        except (CommandError, ProtocolError):
            pass
        self._advance(hold_ms)
        try:
            self.transport.release(button)
        except ProtocolError as exc:
            receipt.failure = Failure.UNCERTAIN
            receipt.detail = f'{exc}; release is uncertain'
            return receipt
        self._settled_position()
        receipt.actual = self._position_tuple()
        receipt.guest = self.guest_state()
        return receipt

    def release_all(self):
        """Idempotent recovery: leave every button released."""
        try:
            self.transport.release_all()
            return PointerReceipt('release_all', acknowledged=True, delivered=True,
                                  guest=self.guest_state())
        except (CommandError, ProtocolError) as exc:
            return PointerReceipt('release_all', failure=Failure.UNCERTAIN, detail=str(exc))


class ScreenState:
    """Framebuffer observation for application-visible expectations."""

    def __init__(self, client, step_ms=100):
        self.client = client
        self.step_ms = step_ms

    def capture(self):
        png, meta = self.client.framebuffer()
        return Frame.from_png(png), meta

    def digest(self, box=None):
        return self.capture()[0].digest(box)

    def wait_change(self, before, timeout_ms=3000, box=None):
        """Advance until the frame (or a region) differs from ``before``."""
        frame = None
        elapsed = 0
        while elapsed <= timeout_ms:
            frame, meta = self.capture()
            if frame.digest(box) != before.digest(box):
                return {'changed': True, 'emulated_ms': elapsed, 'status': meta,
                        'frame': frame, 'digest': frame.digest(box)}
            if elapsed == timeout_ms:
                break
            step = min(self.step_ms, timeout_ms - elapsed)
            self.client.advance(step)
            elapsed += step
        return {'changed': False, 'emulated_ms': elapsed, 'frame': frame,
                'digest': frame.digest(box) if frame else None}


# -- optional guest oracle -------------------------------------------------

MDIAG_SIGNATURE = b'MDIAG001'
MDIAG_LAYOUT = struct.Struct('<8sHHHHHHHH')


class MemoryMouseOracle:
    """Read the guest ``INT 33h`` state published by the resident diagnostic.

    The diagnostic is independently authored (``tools/experimental/
    guest_mouse_diag``) and installed by the experiment. Reading it proves the
    guest mouse driver processed motion and buttons, which a socket reply
    cannot. It does not prove an application acted on them.
    """

    def __init__(self, client, segment, offset=0):
        if not 0 <= segment < 0x10000 or not 0 <= offset < 0x10000:
            raise ValueError('invalid diagnostic address')
        self.client = client
        self.address = segment * 16 + offset
        self._last_ticks = None

    @classmethod
    def discover(cls, client, limit=0xA0000, chunk=65536, image=None):
        """Find the resident record by signature in conventional RAM."""
        if not 0x1000 <= limit <= 0xA0000 or not 1024 <= chunk <= 65536:
            raise ValueError('invalid discovery bounds')
        if image is None:
            chunks = []
            for base in range(0, limit, chunk):
                length = min(chunk, limit - base)
                chunks.append((base, client.memory(base, length)))
        else:
            chunks = [(0, image)]
        for base, data in chunks:
            index = data.find(MDIAG_SIGNATURE)
            while index >= 0:
                address = base + index
                if address + MDIAG_LAYOUT.size <= limit:
                    try:
                        cls(client, address >> 4, address & 0xF).read()
                        return cls(client, address >> 4, address & 0xF)
                    except (PointerError, ProtocolError, CommandError):
                        pass
                index = data.find(MDIAG_SIGNATURE, index + 1)
        raise PointerError('guest mouse diagnostic not found in conventional RAM')

    def read(self):
        """One held read; ticks only advance when the caller advances time."""
        data = self.client.memory(self.address, MDIAG_LAYOUT.size)
        (signature, x, y, buttons, presses, releases, ticks,
         version, _reserved) = MDIAG_LAYOUT.unpack(data)
        if signature != MDIAG_SIGNATURE:
            raise PointerError('guest mouse diagnostic signature mismatch')
        if version != 1:
            raise PointerError(f'unsupported guest diagnostic version {version}')
        self._last_ticks = ticks
        return {'x': x, 'y': y, 'buttons': buttons, 'presses': presses,
                'releases': releases, 'ticks': ticks, 'address': self.address}

    def verify_live(self, milliseconds=120):
        """Prove the record is being updated by advancing emulated time."""
        first = self.read()
        self.client.advance(milliseconds)
        second = self.read()
        if second['ticks'] == first['ticks']:
            raise PointerError('guest diagnostic is not advancing; state is unusable')
        return {'ticks_before': first['ticks'], 'ticks_after': second['ticks'],
                'emulated_ms': milliseconds, 'sample': second}
