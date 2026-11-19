"""Bounded experimental native-resolution graphics profile for the RSX VGA oracle."""
from dataclasses import dataclass
from math import cos, pi, sin
from struct import unpack_from

from .graphics import SvgOmission, arc_quadratic


WIDTH, HEIGHT = 640, 418
FRAMEBUFFER_TOP = 62
MAX_WORK = 12_000_000

# Observed framebuffer phases on the RSX internal VGA at Normal and Two
# times zoom. A set bit selects the fill foreground. Bit zero is leftmost.
_PATTERN_ROWS = (
    (1, '0'), (1, '1'),
    (16, 'cccc49243333cccc924a33334924cccc3333924acccc49243333cccc924a33334924cccc3333'),
    (4, '5285252852852852528'),
    (4, '1000100010001000100'),
    (4, '3000300030003000300'),
    (16, '0000020000000008000020000000008000001000000800000200400000200000040000000002'),
    (4, '3'),
    (1, '1001010010010010100'),
    (8, '603038180c060381c0e06030180c06070381c0'),
    (8, '03060e0c183060c0818303060c18307060c081'),
    (16, 'fffffefffc7ff83ff01fe00fc00780030001000000018003c007e00ff01ff83ffc7ffeffffff'),
    (8, '0303030303030303ff030303030303030303ff'),
    (16, 'fff30000fff3ffd3ffb3ff7300f200f200f200f200f200f200f200f200f200f200f200f200f2'),
    (16, 'ffff80018001800180018001800180018001ffff018001800180018001800180018001800180'),
    (16, '0003000300030003000300030003e01c3ff0030003000300030003000300030003001ce0f03f'),
)


def _tile(width, encoded):
    stride = (width + 3) // 4
    return width, tuple(int(encoded[i:i + stride], 16) for i in range(0, len(encoded), stride))


TILES = tuple(_tile(*pattern) for pattern in _PATTERN_ROWS)


@dataclass(frozen=True)
class RasterPreview:
    width: int
    height: int
    rgb: bytes
    rendered_elements: int
    omissions: tuple[SvgOmission, ...]
    background: tuple[int, int, int]


def _point(x, y):
    return int(x * 2 / 25), int(y * 19 / 220)


def _clip(start, end):
    x0, y0 = start
    dx, dy = end[0] - x0, end[1] - y0
    lower, upper = 0, 1
    for p, q in ((-dx, x0), (dx, WIDTH - 1 - x0), (-dy, y0), (dy, HEIGHT - 1 - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        value = q / p
        if p < 0:
            lower = max(lower, value)
        else:
            upper = min(upper, value)
        if lower > upper:
            return None
    return (round(x0 + lower * dx), round(y0 + lower * dy),
            round(x0 + upper * dx), round(y0 + upper * dy))


def _line(image, start, end, rgb):
    clipped = _clip(start, end)
    if clipped is None:
        return
    x, y, x1, y1 = clipped
    dx, dy = abs(x1 - x), -abs(y1 - y)
    sx, sy = (1 if x < x1 else -1), (1 if y < y1 else -1)
    error = dx + dy
    while True:
        offset = 3 * (y * WIDTH + x)
        image[offset:offset + 3] = rgb
        if x == x1 and y == y1:
            break
        double = 2 * error
        if double >= dy:
            error += dy
            x += sx
        if double <= dx:
            error += dx
            y += sy


def _fill_span(image, x0, x1, y, tile, fg, bg):
    start, end = max(0, x0), min(WIDTH - 1, x1)
    if not 0 <= y < HEIGHT or start > end:
        return
    width, rows = tile
    bits = rows[(y + FRAMEBUFFER_TOP) % len(rows)]
    tile_row = b''.join(fg if bits & (1 << x) else bg for x in range(width))
    phase = start % width
    repeated = tile_row * ((end - start + phase) // width + 1)
    p, q = 3 * (y * WIDTH + start), 3 * (y * WIDTH + end + 1)
    image[p:q] = repeated[3 * phase:3 * phase + q - p]


def _segments(points, closed):
    return list(zip(points, points[1:] + points[:1] if closed else points[1:]))


def _fill_polygon(image, edges, min_y, max_y, tile, fg, bg):
    for y in range(max(0, min_y), min(HEIGHT, max_y + 1)):
        intersections = []
        for (x0, y0), (x1, y1) in edges:
            if min(y0, y1) <= y < max(y0, y1):
                intersections.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
        intersections.sort()
        for a, b in zip(intersections[::2], intersections[1::2]):
            _fill_span(image, round(a), round(b), y, tile, fg, bg)


def _shape(element):
    a, b, c, d = element.bounds
    el, raw = element.kind, element.raw
    if el == 'L':
        return [_point(a, b), _point(c, d)], False, raw[18], None
    if el == 'R':
        points = [_point(a, b), _point(c, b), _point(c, d), _point(a, d)]
        return points, True, raw[18], (raw[1], raw[22], raw[21])
    if el == 'E':
        # The contour sampler approximates the native integer ellipse walk.
        points = [_point((a + c + (c - a) * cos(t * pi / 180)) / 2,
                         (b + d + (d - b) * sin(t * pi / 180)) / 2) for t in range(360)]
        return points, True, raw[18], (raw[1], raw[22], raw[21])
    if el == 'UA':
        quadratic = arc_quadratic(element)
        if quadratic is not None:
            p0, q, p1 = quadratic
            points = [_point(*((1-t)**2*v0 + 2*(1-t)*t*vq + t*t*v1 for v0, vq, v1 in zip(p0, q, p1)))
                      for i in range(257) for t in (i / 256,)]
            return points, False, raw[20], None
    if el == 'UP' and len(element.points) >= 2:
        sx, sy = unpack_from('<HH', raw, 28)
        points = [_point(a + (x * (c-a) / sx if sx else 0), b + (y * (d-b) / sy if sy else 0))
                  for x, y in element.points]
        return points, bool(raw[32] or raw[33]), raw[20], ((raw[24], raw[26], raw[25]) if raw[32] else None)
    return None


def preview_rsx(form, palette):
    """Render the Normal-zoom RSX drawing crop with the measured fill profiles.

    Uses one-pixel solid outlines, measured screen-phase fill tiles and
    approximate ellipse/curve stepping and polygon scan conversion. Stroke
    widths, patterned strokes and text are outside this first raster profile.
    """
    colors = {index: bytes((channel >> 2) * 255 // 63 for channel in rgb) for index, *rgb in palette}
    background = colors.get(0, b'\0\0\x81')
    image = bytearray(background * (WIDTH * HEIGHT))
    rendered, omitted, budget = 0, [], MAX_WORK
    for record in form.draw_order():
        shape = _shape(record) if budget > 0 else None
        if shape is None:
            reason = 'raster_work_limit' if budget <= 0 else 'unsupported_rsx_raster_element'
            omitted.append(SvgOmission(record.offset, record.kind.encode('latin-1').hex(), reason))
            continue
        points, closed, color_index, fill = shape
        min_y, max_y = min(y for x, y in points), max(y for x, y in points)
        rows = max(0, min(HEIGHT, max_y + 1) - max(0, min_y))
        cost = len(points) * (640 + rows)
        if cost > budget:
            omitted.append(SvgOmission(record.offset, record.kind.encode('latin-1').hex(), 'raster_work_limit'))
            continue
        budget -= cost
        edges = _segments(points, closed)
        if closed and fill and 0 <= fill[0] < len(TILES):
            tile, fg, bg = TILES[fill[0]], colors.get(fill[1], bytes(3)), colors.get(fill[2], background)
            _fill_polygon(image, edges, min_y, max_y, tile, fg, bg)
        outline = colors.get(color_index, bytes(3))
        for a, b in edges:
            _line(image, a, b, outline)
        rendered += 1
    return RasterPreview(WIDTH, HEIGHT, bytes(image), rendered, tuple(omitted), tuple(background))
