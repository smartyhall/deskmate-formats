"""Read DeskMate's measured serialized graphics forms and preview their geometry."""
from dataclasses import dataclass
from html import escape
from struct import unpack_from


HEADER_SIZE = 18
PREFIX_SIZE = HEADER_SIZE + 4
MAX_BYTES = PREFIX_SIZE + 2 * 65535 + 1
ELEMENT_SIZE = 18
PRIMITIVE_SIZES = {'L': 20, 'R': 24, 'E': 24}
PREVIEW_KINDS = frozenset((*PRIMITIVE_SIZES, 'UP'))
MAX_PREVIEW_STROKE_POINTS = 100_000


class GraphicsFormatError(ValueError):
    """Malformed form data or a structure outside the measured profile."""


@dataclass(frozen=True)
class Entry:
    """Display-order reference to a byte offset relative to the form list."""

    offset: int
    tag: int


@dataclass(frozen=True)
class Element:
    """An element extent, modifier and original bounded record bytes."""

    offset: int
    kind: str
    modifier: int
    coordinates: tuple[int, ...]
    raw: bytes
    children: tuple[int, ...] = ()
    points: tuple[tuple[int, int], ...] = ()
    text_bytes: bytes | None = None
    font_name: str | None = None

    @property
    def bounds(self):
        """Project stored integer/fraction pairs as 16.16 world coordinates."""
        return tuple(i + f / 65536 for i, f in zip(self.coordinates[::2], self.coordinates[1::2]))


@dataclass(frozen=True)
class Form:
    """A serialized display list, stroke bytes and optional Text payload suffix."""

    header: bytes
    list_data: bytes
    strokes: bytes
    entries: tuple[Entry, ...]
    elements: tuple[Element, ...]
    trailer: bytes

    def draw_order(self):
        """Yield leaf elements in display order, descending through group parts."""
        by_offset = {element.offset: element for element in self.elements}
        pending = [entry.offset for entry in reversed(self.entries)]
        while pending:
            element = by_offset[pending.pop()]
            if element.children:
                pending.extend(reversed(element.children))
            elif element.kind != 'OO':
                yield element


@dataclass(frozen=True)
class StrokeGlyph:
    """One font and character from a form's embedded stroke bank."""

    font: int
    code: int
    paths: tuple[tuple[tuple[int, int], ...], ...]


def _require(condition, message):
    if not condition:
        raise GraphicsFormatError(message)


def parse_strokes(source):
    """Read the measured embedded stroke bank with a zero-size end word."""
    _require(isinstance(source, (bytes, bytearray, memoryview)), 'expected stroke bytes')
    _require(memoryview(source).nbytes <= 65535, 'stroke bank exceeds word-size bound')
    data = bytes(source)
    if not data:
        return ()
    limit = len(data) - 2
    _require(data[limit:] == b'\x00\x00', 'missing stroke bank terminator')
    glyphs = {}
    cursor = 0
    while cursor < limit:
        _require(cursor + 4 <= limit, 'truncated glyph header')
        size, font, code = unpack_from('<HBB', data, cursor)
        end = cursor + size
        _require(size >= 4 and end <= limit, 'invalid glyph size')
        paths = []
        for raw in data[cursor + 4:end].split(b'\x00'):
            if not raw:
                continue
            _require(len(raw) >= 4 and len(raw) % 2 == 0 and max(raw) <= 128,
                     'invalid glyph coordinates')
            paths.append(tuple(zip(raw[::2], raw[1::2])))
        key = (font, code)
        _require(key not in glyphs, 'duplicate embedded glyph')
        glyphs[key] = StrokeGlyph(font, code, tuple(paths))
        cursor = end
    return tuple(glyphs.values())


def _elements(data, entries, directory_end):
    pending = [entry.offset for entry in entries]
    offsets = set(pending)
    _require(len(offsets) == len(entries), 'duplicate display-list element')
    groups = {}
    for offset in pending:
        _require(directory_end <= offset <= len(data) - ELEMENT_SIZE,
                 f'element reference outside form list at {offset}')
        if data[offset:offset + 2] != b'OO':
            continue
        _require(offset + 20 <= len(data), 'truncated group header')
        count, = unpack_from('<H', data, offset + 18)
        _require(offset + 20 + 2 * count <= len(data), 'truncated group references')
        children = tuple(word * 2 for word in unpack_from(f'<{count}H', data, offset + 20))
        unique = set(children)
        _require(len(unique) == count and offsets.isdisjoint(unique),
                 'duplicate or cyclic group reference')
        offsets.update(unique)
        pending.extend(children)
        groups[offset] = children

    boundaries = sorted(offsets) + [len(data)]
    elements = []
    for offset, end in zip(boundaries, boundaries[1:]):
        raw = data[offset:end]
        _require(len(raw) >= ELEMENT_SIZE, 'overlapping element records')
        kind = raw[:2].decode('latin-1') if raw[0] == ord('U') or offset in groups else chr(raw[0])
        coords = unpack_from('<hHhHhHhH', raw, 2)
        children = groups.get(offset, ())
        points = ()
        label = font_name = None
        if kind in PRIMITIVE_SIZES:
            _require(len(raw) >= PRIMITIVE_SIZES[kind], f'truncated {kind} element')
        elif kind == 'OO':
            _require(len(raw) >= 20 + 2 * len(children), 'group references overlap an element')
        elif kind == 'T':
            _require(len(raw) >= 22 and 22 + raw[20] <= len(raw), 'truncated text element')
            label = raw[22:22 + raw[20]]
        elif kind.startswith('U'):
            _require(len(raw) >= 20, 'truncated extended element')
            words, = unpack_from('<H', raw, 18)
            _require(20 <= words * 2 <= len(raw), 'extended element exceeds its record')
            if kind == 'UP':
                _require(words >= 18, 'truncated polyline header')
                count, = unpack_from('<H', raw, 34)
                _require(words * 2 == 36 + 4 * count, 'polyline point count disagrees with size')
                flat = unpack_from(f'<{2 * count}H', raw, 36)
                points = tuple(zip(flat[::2], flat[1::2]))
            elif kind == 'Uf' and words >= 51 and raw[26:31] == b'Cobb\x00':
                count, = unpack_from('<H', raw, 96)
                text_end = 100 + count
                if raw[98:100] == b'\x00\x00' and text_end < words * 2 and raw[text_end] == 0:
                    label, font_name = raw[100:text_end], 'Cobb'
        elements.append(Element(offset, kind, raw[1], coords, raw, children, points, label, font_name))
    return tuple(elements)


def parse_bytes(source, *, text_picture=False):
    """Read FORM HEADER, size buffer, list and strokes from a bounded payload.

    Set text_picture for the native Text variant with one extra payload byte.
    The reserved header words and unrecognized records are preserved verbatim.
    """
    _require(isinstance(source, (bytes, bytearray, memoryview)), 'expected a byte snapshot')
    _require(PREFIX_SIZE <= memoryview(source).nbytes <= MAX_BYTES, 'invalid form payload size')
    data = bytes(source)
    _require(data[0] == 1 and data[1] in (0, 1), 'unsupported form flags')
    words, stroke_bytes = unpack_from('<HH', data, 2)
    list_bytes, stored_strokes = unpack_from('<HH', data, HEADER_SIZE)
    list_end = PREFIX_SIZE + list_bytes
    end = list_end + stroke_bytes
    _require(list_bytes == 2 * words and list_bytes >= 2 and stroke_bytes == stored_strokes
             and len(data) == end + int(text_picture), 'inconsistent form size fields')
    listing = data[PREFIX_SIZE:list_end]
    count, = unpack_from('<H', listing)
    directory_end = 2 + 4 * count
    _require(directory_end <= list_bytes, 'form directory exceeds list')
    entries = tuple(Entry(2 * word, tag) for word, tag in
                    (unpack_from('<HH', listing, i) for i in range(2, directory_end, 4)))
    _require(len({entry.tag for entry in entries}) == count, 'duplicate display-list tag')
    return Form(data[:HEADER_SIZE], listing, data[list_end:end], entries,
                _elements(listing, entries, directory_end), data[end:])


def _number(value):
    return format(value, '.9g')


def _polyline(element, palette, style):
    x0, y0, x1, y1 = element.bounds
    x_extent, y_extent = unpack_from('<HH', element.raw, 28)
    sx = (x1 - x0) / x_extent if x_extent else 0
    sy = (y1 - y0) / y_extent if y_extent else 0
    points = ' '.join(f'{_number(x0 + x*sx)},{_number(y0 + y*sy)}' for x, y in element.points)
    fill = palette.get(element.raw[26], '#b0b0b0') if element.raw[32] and element.raw[24] != 0xFE else 'none'
    tag = 'polygon' if element.raw[32] or element.raw[33] else 'polyline'
    return f'<{tag} points="{points}" fill="{fill}" {style}/>'


def _svg_element(element, palette):
    x0, y0, x1, y1 = element.bounds
    x, y = min(x0, x1), min(y0, y1)
    width, height = abs(x1 - x0), abs(y1 - y0)
    color = element.raw[20] if element.kind == 'UP' else element.raw[18]
    style = f'stroke="{palette.get(color, "#333333")}" stroke-width="1" vector-effect="non-scaling-stroke"'
    if element.kind == 'L':
        return (f'<line x1="{_number(x0)}" y1="{_number(y0)}" x2="{_number(x1)}" '
                f'y2="{_number(y1)}" {style}/>')
    if element.kind == 'UP':
        return _polyline(element, palette, style)
    fill = palette.get(element.raw[22], '#b0b0b0') if element.modifier != 0xFE else 'none'
    if element.kind == 'R':
        return (f'<rect x="{_number(x)}" y="{_number(y)}" width="{_number(width)}" '
                f'height="{_number(height)}" fill="{fill}" {style}/>')
    return (f'<ellipse cx="{_number(x + width/2)}" cy="{_number(y + height/2)}" '
            f'rx="{_number(width/2)}" ry="{_number(height/2)}" fill="{fill}" {style}/>')


def _svg_stroke_text(element, glyphs, colors):
    x0, y0, x1, y1 = element.bounds
    advance = (x1 - x0) / len(element.text_bytes)
    height = y1 - y0
    paths = []
    for position, code in enumerate(element.text_bytes):
        for path in glyphs[element.modifier, code].paths:
            points = ' '.join(f'{_number(x0 + advance * (position + x / 128))},{_number(y0 + height * y / 128)}'
                              for x, y in path)
            paths.append(f'<polyline points="{points}" vector-effect="non-scaling-stroke"/>')
    color = colors.get(element.raw[19], '#333333')
    label = ''.join(c if ord(c) >= 0x20 else '\ufffd' for c in element.text_bytes.decode('cp437'))
    return (f'<g aria-label="{escape(label, quote=True)}" '
            f'fill="none" stroke="{color}" stroke-width="1">' + ''.join(paths) + '</g>')


def render_svg(form, palette=()):
    """Return a geometry preview of lines, rectangles, ellipses and polylines.

    Palette entries are (index, red, green, blue). Stroke styles and patterned
    fills use solid approximations. Unrotated T text with a complete embedded
    glyph bank uses fixed cell advances. Unsupported records are listed in the
    SVG description and remain available on the original Form.
    """
    colors = {i: f'#{r:02x}{g:02x}{b:02x}' for i, r, g, b in palette}
    leaves = tuple(form.draw_order())
    glyphs = {}
    if any(element.kind == 'T' for element in leaves):
        try:
            glyphs = {(glyph.font, glyph.code): glyph for glyph in parse_strokes(form.strokes)}
        except GraphicsFormatError:
            pass
    point_costs = {key: sum(map(len, glyph.paths)) for key, glyph in glyphs.items()}
    point_budget = MAX_PREVIEW_STROKE_POINTS
    shapes, bounds, missing = [], [], set()
    for element in leaves:
        if element.kind in PREVIEW_KINDS:
            shape = _svg_element(element, colors)
        elif (element.kind == 'T' and element.text_bytes and element.raw[21] == 0
              and all((element.modifier, code) in glyphs for code in element.text_bytes)):
            cost = sum(point_costs[element.modifier, code] for code in element.text_bytes)
            if cost > point_budget:
                missing.add('54')
                continue
            point_budget -= cost
            shape = _svg_stroke_text(element, glyphs, colors)
        else:
            missing.add(element.kind.encode('latin-1').hex())
            continue
        shapes.append(shape)
        bounds.append(element.bounds)
    xs = [x for x0, _, x1, _ in bounds for x in (x0, x1)] or [0]
    ys = [y for _, y0, _, y1 in bounds for y in (y0, y1)] or [0]
    pad = max(8, (max(xs) - min(xs)) / 40, (max(ys) - min(ys)) / 40)
    box = (min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2*pad, max(ys) - min(ys) + 2*pad)
    view = ' '.join(map(_number, box))
    description = 'DeskMate geometry preview with approximate fills, stroke styles and text spacing.'
    if missing:
        description += ' Omitted element type bytes (hex) ' + ', '.join(sorted(missing)) + '.'
    if colors.get(0):
        background = [f'<rect x="{_number(box[0])}" y="{_number(box[1])}" width="{_number(box[2])}" '
                      f'height="{_number(box[3])}" fill="{colors[0]}"/>']
    else:
        background = []
    return '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">',
                      f'<desc>{escape(description)}</desc>', *background, *shapes, '</svg>\n'])
