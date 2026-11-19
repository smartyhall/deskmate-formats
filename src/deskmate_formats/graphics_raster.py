"""Bounded experimental native-resolution graphics profile for the RSX VGA oracle."""
from dataclasses import dataclass
from math import ceil, cos, pi, sin
from struct import unpack_from

from .graphics import MAX_PREVIEW_OUTLINE_BYTES, OUTLINE_INK_INDEX, SvgOmission, arc_quadratic, outline_layout


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
AXIS_STROKES = (
    ('1', '0', '1000', '11100111', '10011100', '10', '1100', '00010000'),
    ('1', '0', '00000011', '1111100011111111', '0000111111100011', '1001', '11100011', '0000011000000000'),
)
# Weight-one dash bits applied to the centers of the 2 x 2 pixel pen.
SQUARE_PEN_DASHES = ('1', '0', '00000010', '1111100001111111', '0000111111000010',
                     '0001', '11000011', '0000010000000000')
# Normal-zoom nib endpoints observed in the forward horizontal controls.
BRUSH_NIBS = {17: ((1, -1), (-2, 2)), 18: ((4, -3), (-3, 4)), 19: ((5, -5), (-6, 6))}


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


def _axis_stroke(image, start, end, rgb, style, weight, vertical):
    major, minor = (1, 0) if vertical else (0, 1)
    length, span = (HEIGHT, WIDTH) if vertical else (WIDTH, HEIGHT)
    first, last, center = start[major], end[major], start[minor]
    lead = max(0, weight - 1)
    trail = weight
    direction = 1 if last >= first else -1
    low = max(0, min(first, last) - (lead if direction > 0 else trail))
    high = min(length - 1, max(first, last) + (trail if direction > 0 else lead))
    pattern = AXIS_STROKES[weight][style] if weight < 2 else '1'
    for step in range(low, high + 1):
        phase = (step - first) * direction
        if pattern[phase % len(pattern)] == '0' or (style == 5 and weight == 1 and phase == 0):
            continue
        for offset in range(max(0, center - lead), min(span - 1, center + trail) + 1):
            x, y = (offset, step) if vertical else (step, offset)
            index = 3 * (y * WIDTH + x)
            image[index:index + 3] = rgb


def _square_pen_stroke(image, start, end, rgb, style, weight):
    """Sweep the measured VGA pen over a line in the original dash phase."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    vertical = abs(dy) > abs(dx)
    major, minor = (1, 0) if vertical else (0, 1)
    length, run = abs(end[major] - start[major]), abs(end[minor] - start[minor])
    direction = 1 if end[major] >= start[major] else -1
    transverse = 1 if end[minor] >= start[minor] else -1
    lead = max(0, weight - 1)
    extent = HEIGHT if vertical else WIDTH
    low, high = -weight, extent - 1 + lead
    distances = sorted(((low - start[major]) * direction, (high - start[major]) * direction))
    pattern = '1' if weight >= 2 else (SQUARE_PEN_DASHES if weight else AXIS_STROKES[0])[style]
    for step in range(max(0, distances[0]), min(length, distances[1]) + 1):
        if pattern[step % len(pattern)] == '0':
            continue
        # At a half-pixel tie, choose the step nearest the lower major coordinate.
        offset = (2 * step * run + length - (direction > 0)) // (2 * length) if length else 0
        position = start[major] + direction * step
        cross = start[minor] + transverse * offset
        x, y = (cross, position) if vertical else (position, cross)
        first, last = max(0, x - lead), min(WIDTH, x + weight + 1)
        if first < last:
            pixels = rgb * (last - first)
            for row in range(max(0, y - lead), min(HEIGHT, y + weight + 1)):
                at = 3 * (row * WIDTH + first)
                image[at:at + len(pixels)] = pixels


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


def _brush_segment(image, start, end, rgb, nib):
    """Approximate the native slanted brush polygon and inclusive edges."""
    (u, v), (s, t) = nib
    a, b = start
    c, d = end
    vertices = [(a + u, b + v), (c + u, d + v), (c + s, d + t), (a + s, b + t)]
    edges = _segments(vertices, True)
    first = min(b, d) + min(v, t)
    last = max(b, d) + max(v, t)
    for y in range(max(0, first), min(HEIGHT - 1, last) + 1):
        crossings = []
        for (x0, y0), (x1, y1) in edges:
            if min(y0, y1) <= y <= max(y0, y1):
                if y0 == y1:
                    crossings.extend((x0, x1))
                else:
                    crossings.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
        _fill_span(image, round(min(crossings)), round(max(crossings)) + (b != d), y, TILES[1], rgb, rgb)
    for start_edge, end_edge in edges:
        _line(image, start_edge, end_edge, rgb)


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


def _glyph_edges(glyph):
    def project(point):
        return point[0] * 2 / 25, point[1] * 19 / 220

    edges = []
    for start, segments in glyph:
        previous = project(start)
        for segment in segments:
            points = tuple(map(project, segment))
            if len(points) == 1:
                edges.append((previous, points[0]))
            else:
                a, b, c = points
                length = sum(max(abs(q[0]-p[0]), abs(q[1]-p[1]))
                             for p, q in zip((previous, a, b), points))
                count = min(32, max(2, ceil(length / 2)))
                point = previous
                for i in range(1, count + 1):
                    t = i / count
                    u = 1 - t
                    next_point = tuple(u**3*p + 3*u*u*t*v + 3*u*t*t*w + t**3*q
                                       for p, v, w, q in zip(previous, a, b, c))
                    edges.append((point, next_point))
                    point = next_point
            previous = points[-1]
    return edges


def _fill_glyph(image, edges, rows, color):
    for y in rows:
        sample_y = y + .5
        crossings = []
        for (x0, y0), (x1, y1) in edges:
            if min(y0, y1) <= sample_y < max(y0, y1):
                x = x0 + (x1 - x0) * (sample_y - y0) / (y1 - y0)
                crossings.append((x, 1 if y1 > y0 else -1))
        winding = 0
        start = 0
        for x, delta in sorted(crossings):
            if winding == 0:
                start = max(0, ceil(x - .5))
            winding += delta
            if winding == 0:
                end = min(WIDTH, ceil(x - .5))
                if start < end:
                    offset = 3 * (y * WIDTH + start)
                    image[offset:offset + 3 * (end - start)] = color * (end - start)


def _raster_outlines(image, glyphs, color, budget):
    prepared = []
    cost = 0
    for glyph in glyphs:
        if not glyph:
            continue
        edges = _glyph_edges(glyph)
        ys = [y for edge in edges for _, y in edge]
        rows = range(max(0, ceil(min(ys) - .5)), min(HEIGHT, ceil(max(ys) - .5)))
        cost += len(edges) * (1 + len(rows)) + WIDTH * len(rows)
        if cost > budget:
            return None
        prepared.append((edges, rows))
    for edges, rows in prepared:
        _fill_glyph(image, edges, rows, color)
    return cost


def preview_rsx(form, palette, *, outline_faces=None):
    """Render the Normal-zoom RSX drawing crop with the measured fill profiles.

    Uses measured line pens, dash masks and screen-phase fill tiles, with
    approximate brush, ellipse, curve and polygon rasterization. Other
    outlines use a one-pixel solid approximation. Supplied
    FF1 base faces use an unhinted, pixel-center contour fill.
    """
    colors = {index: bytes((channel >> 2) * 255 // 63 for channel in rgb) for index, *rgb in palette}
    background = colors.get(0, b'\0\0\x81')
    image = bytearray(background * (WIDTH * HEIGHT))
    rendered, omitted, budget = 0, [], MAX_WORK
    outline_budget = MAX_PREVIEW_OUTLINE_BYTES
    for record in form.draw_order():
        if record.kind == 'Uf' and outline_faces and budget > 0:
            glyphs, cost, reason = outline_layout(record, outline_faces, outline_budget)
            outline_budget -= cost
            if reason is None:
                cost = _raster_outlines(image, glyphs, colors.get(OUTLINE_INK_INDEX, bytes(3)), budget)
                if cost is not None:
                    budget -= cost
                    rendered += 1
                    continue
                reason = 'raster_work_limit'
            omitted.append(SvgOmission(record.offset, '5566', reason))
            continue
        shape = _shape(record) if budget > 0 else None
        if shape is None:
            reason = 'raster_work_limit' if budget <= 0 else 'unsupported_rsx_raster_element'
            omitted.append(SvgOmission(record.offset, record.kind.encode('latin-1').hex(), reason))
            continue
        points, closed, color_index, fill = shape
        min_y, max_y = min(y for x, y in points), max(y for x, y in points)
        rows = max(0, min(HEIGHT, max_y + 1) - max(0, min_y))
        cost = len(points) * (640 + rows)
        nib = BRUSH_NIBS.get(record.raw[23]) if record.kind == 'UP' and record.raw[24] == 254 else None
        if nib:
            cost += len(points) * (4 * HEIGHT + 12 * WIDTH)
        if cost > budget:
            omitted.append(SvgOmission(record.offset, record.kind.encode('latin-1').hex(), 'raster_work_limit'))
            continue
        budget -= cost
        edges = _segments(points, closed)
        if closed and fill and 0 <= fill[0] < len(TILES):
            tile, fg, bg = TILES[fill[0]], colors.get(fill[1], bytes(3)), colors.get(fill[2], background)
            _fill_polygon(image, edges, min_y, max_y, tile, fg, bg)
        outline = colors.get(color_index, bytes(3))
        x0, y0, x1, y1 = record.bounds
        if record.kind == 'L' and record.modifier < 8 and record.raw[19] < 4:
            if x0 == x1 or y0 == y1:
                _axis_stroke(image, *points, outline, record.modifier, record.raw[19], vertical=x0 == x1)
            else:
                _square_pen_stroke(image, *points, outline, record.modifier, record.raw[19])
        elif nib:
            for a, b in edges:
                _brush_segment(image, a, b, outline, nib)
        else:
            for a, b in edges:
                _line(image, a, b, outline)
        rendered += 1
    return RasterPreview(WIDTH, HEIGHT, bytes(image), rendered, tuple(omitted), tuple(background))
