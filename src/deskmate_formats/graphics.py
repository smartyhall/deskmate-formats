"""Read DeskMate's measured serialized graphics forms and preview their geometry."""
from dataclasses import dataclass
from html import escape
from struct import unpack_from

from .font_resources import FontResourceError, parse_glyph_outline


HEADER_SIZE = 18
PREFIX_SIZE = HEADER_SIZE + 4
MAX_BYTES = PREFIX_SIZE + 2 * 65535 + 1
ELEMENT_SIZE = 18
PRIMITIVE_SIZES = {'L': 20, 'R': 24, 'E': 24}
PREVIEW_KINDS = frozenset((*PRIMITIVE_SIZES, 'UP'))
MAX_PREVIEW_STROKE_POINTS = 100_000
MAX_PREVIEW_OUTLINE_BYTES = 200_000
OUTLINE_INK_INDEX = 1


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


@dataclass(frozen=True)
class ExternalFontRun:
    """Measured Uf descriptor and label bytes; glyph data is external."""

    name: str
    attributes: bytes
    descriptor: bytes
    text_bytes: bytes
    padding: bytes

    @property
    def point_size_word(self):
        return unpack_from('<H', self.descriptor, 0)[0]

    @property
    def width_percent_word(self):
        return unpack_from('<H', self.descriptor, 2)[0]


@dataclass(frozen=True)
class SvgOmission:
    """Location and reason for an element excluded from the geometry preview."""

    offset: int
    kind_hex: str
    reason: str


@dataclass(frozen=True)
class SvgPreview:
    svg: str
    view_box: tuple[float, float, float, float]
    rendered_bounds: tuple[float, float, float, float] | None
    rendered_elements: int
    omissions: tuple[SvgOmission, ...]


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


def _font_run(raw, length):
    if length < 102 or raw[98:100] != b'\0\0':
        return None
    name, terminator, padding = raw[26:56].partition(b'\0')
    count, = unpack_from('<H', raw, 96)
    end = 100 + count
    if (not terminator or not name or any(padding) or any(not 32 <= code <= 126 for code in name)
            or not end <= length <= end + 2 or (length == end + 2 and raw[end:length] != b'\0\0')
            or b'\0' in raw[100:end]):
        return None
    return ExternalFontRun(name.decode('ascii'), raw[20:26], raw[56:96],
                           raw[100:end], raw[end:length])


def external_font_run(element):
    """Inspect a validated Uf record without loading its external resource."""
    if element.kind != 'Uf' or len(element.raw) < 20:
        return None
    size, = unpack_from('<H', element.raw, 18)
    return _font_run(element.raw, 2 * size) if 2 * size <= len(element.raw) else None


def _elements(data, entries, directory_end, *, recover_arc_length=False):
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
    recovered_arc = False
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
            if (recover_arc_length and not recovered_arc and kind == 'UA' and len(raw) == 44
                    and words == 23 and (data[end:end + 1] == b'L' or data[end:end + 2] == b'UP')):
                # The measured native reader draws the fixed UA structure and
                # retains the original size word across Save As.
                recovered_arc = True
            else:
                _require(20 <= words * 2 <= len(raw), 'extended element exceeds its record')
            if kind == 'UP':
                _require(words >= 18, 'truncated polyline header')
                count, = unpack_from('<H', raw, 34)
                _require(words * 2 == 36 + 4 * count, 'polyline point count disagrees with size')
                flat = unpack_from(f'<{2 * count}H', raw, 36)
                points = tuple(zip(flat[::2], flat[1::2]))
            elif kind == 'Uf':
                font = _font_run(raw, 2 * words)
                if font:
                    label, font_name = font.text_bytes, font.name
        elements.append(Element(offset, kind, raw[1], coords, raw, children, points, label, font_name))
    return tuple(elements)


def parse_bytes(source, *, text_picture=False, recover_arc_length=False):
    """Read FORM HEADER, size buffer, list and strokes from a bounded payload.

    Set text_picture for the native Text variant with one extra payload byte.
    The reserved header words and unrecognized records are preserved verbatim.
    The explicit Draw recovery permits one measured legacy arc length mismatch.
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
                _elements(listing, entries, directory_end, recover_arc_length=recover_arc_length), data[end:])


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


def arc_quadratic(element):
    """Return the measured UA geometry as start, control and end in world units."""
    if element.kind != 'UA' or len(element.raw) != 44 or element.raw[18:20] not in (b'\x16\0', b'\x17\0'):
        return None
    x0, y0, x1, y1 = element.bounds
    x_extent, y_extent, ax, ay, bx, by, px, py = unpack_from('<8h', element.raw, 28)
    if x_extent <= 0 or y_extent <= 0 or x1 < x0 or y1 < y0:
        return None
    dx, dy = (x1 - x0) / x_extent, (y1 - y0) / y_extent
    a = (x0 + ax * dx, y0 + ay * dy)
    b = (x0 + bx * dx, y0 + by * dy)
    p = (x0 + px * dx, y0 + py * dy)
    q = (2 * p[0] - (a[0] + b[0]) / 2, 2 * p[1] - (a[1] + b[1]) / 2)
    return a, q, b


def _svg_arc(element, colors, points):
    a, q, b = (' '.join(map(_number, pair)) for pair in points)
    stroke = colors.get(element.raw[20], '#333333')
    return (f'<path d="M {a} Q {q} {b}" fill="none" stroke="{stroke}" '
            'stroke-width="1" vector-effect="non-scaling-stroke"/>')


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


def outline_layout(element, faces, byte_budget):
    """Project the measured unrotated Uf profile into world-space glyph paths.

    Returns (glyph paths, charged bytes, omission reason). Glyph paths are
    independent so ink from adjacent glyphs cannot cancel in overlapping areas.
    """
    run = external_font_run(element)
    if run is None:
        return (), 0, 'invalid_external_font_descriptor'
    face = faces.get(run.name.casefold())
    if face is None:
        return (), 0, 'external_font_reference'
    if (run.attributes[1:] != b'\xff\0\0\0\0'
            or (run.attributes[0] != 1 and face.name.casefold() != 'cobb')
            or run.descriptor[4:28] != b'\0\0\0\0\x0c\0\xff' + bytes(17)
            or run.descriptor[34:36] != b'\x01\0'
            or not run.point_size_word or not run.width_percent_word):
        return (), 0, 'unsupported_external_font_transform_or_style'
    try:
        entries = [face.entry(code) for code in run.text_bytes]
    except FontResourceError as error:
        return (), 0, str(error)
    cost = sum(entry.size for entry in entries)
    if cost > byte_budget:
        return (), 0, 'outline_byte_limit'
    x, y = unpack_from('<hh', run.descriptor, 36)
    sy = run.point_size_word * 1000 / (72 * face.index.units_per_em_word)
    sx = sy * run.width_percent_word / 100
    glyphs = []
    advance = 0
    outlines = {}

    def project(point):
        return x + (advance + point[0]) * sx, y + point[1] * sy

    for entry in entries:
        if entry.code not in outlines:
            try:
                outlines[entry.code] = parse_glyph_outline(face.data, entry)
            except FontResourceError as error:
                return (), cost, str(error)
        outline = outlines[entry.code]
        glyphs.append(tuple(
            (project(contour.start), tuple(tuple(map(project, segment)) for segment in contour.segments))
            for contour in outline.contours if contour.segments
        ))
        advance += entry.advance_word
    return tuple(glyphs), cost, None


def _svg_outline_text(glyphs, colors):
    color = colors.get(OUTLINE_INK_INDEX, '#333333')

    def coordinates(points):
        return ' '.join(_number(value) for point in points for value in point)

    paths = []
    for glyph in glyphs:
        if not glyph:
            continue
        commands = []
        for start, segments in glyph:
            commands.append('M ' + coordinates((start,)))
            for segment in segments:
                commands.append(('L ' if len(segment) == 1 else 'C ') + coordinates(segment))
            commands.append('Z')
        paths.append(f'<path d="{" ".join(commands)}" fill="{color}"/>')
    return ''.join(paths)


def preview_svg(form, palette=(), *, substitute_external_fonts=False, outline_faces=None):
    """Return the geometry preview, dimensions and omitted element locations.

    Palette entries are (index, red, green, blue). Stroke styles and patterned
    fills use solid approximations. Supplied FF1 faces project the supported
    unrotated outline text. Unrotated T text with a complete embedded
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
    outline_budget = MAX_PREVIEW_OUTLINE_BYTES
    shapes, bounds, missing = [], [], []
    substitutions = 0
    for element in leaves:
        if element.kind == 'UP' and len(element.points) < 2:
            missing.append(SvgOmission(element.offset, '5550', 'polyline_has_too_few_points'))
            continue
        if element.kind == 'UA':
            arc = arc_quadratic(element)
            if arc is None:
                missing.append(SvgOmission(element.offset, '5541', 'unsupported_arc_extent'))
                continue
            shape = _svg_arc(element, colors, arc)
        elif element.kind in PREVIEW_KINDS:
            shape = _svg_element(element, colors)
        elif element.kind == 'Uf':
            outlines, cost, reason = outline_layout(element, outline_faces or {}, outline_budget)
            outline_budget -= cost
            if reason is None:
                shape = _svg_outline_text(outlines, colors)
            elif substitute_external_fonts and element.text_bytes:
                x0, y0, x1, y1 = element.bounds
                label = ''.join(c if ord(c) >= 0x20 else '\ufffd' for c in element.text_bytes.decode('cp437'))
                color = colors.get(OUTLINE_INK_INDEX, '#333333')
                shape = (f'<text x="{_number(min(x0, x1))}" y="{_number(max(y0, y1))}" '
                         f'font-size="{_number(max(1, abs(y1-y0)))}" font-family="monospace" '
                         f'fill="{color}">{escape(label)}</text>')
                substitutions += 1
            else:
                missing.append(SvgOmission(element.offset, '5566', reason))
                continue
        elif (element.kind == 'T' and element.text_bytes and element.raw[21] == 0
              and all((element.modifier, code) in glyphs for code in element.text_bytes)):
            cost = sum(point_costs[element.modifier, code] for code in element.text_bytes)
            if cost > point_budget:
                missing.append(SvgOmission(element.offset, '54', 'stroke_point_limit'))
                continue
            point_budget -= cost
            shape = _svg_stroke_text(element, glyphs, colors)
        else:
            reason = {'T': 'unsupported_glyphs_or_rotation', 'Uf': 'external_font_reference'}.get(
                element.kind, 'unsupported_element')
            missing.append(SvgOmission(element.offset, element.kind.encode('latin-1').hex(), reason))
            continue
        shapes.append(shape)
        bounds.append(element.bounds)
    xs = [x for x0, _, x1, _ in bounds for x in (x0, x1)] or [0]
    ys = [y for _, y0, _, y1 in bounds for y in (y0, y1)] or [0]
    pad = max(8, (max(xs) - min(xs)) / 40, (max(ys) - min(ys)) / 40)
    box = (min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2*pad, max(ys) - min(ys) + 2*pad)
    view = ' '.join(map(_number, box))
    description = 'DeskMate geometry preview with approximate fills, stroke styles and text spacing.'
    if substitutions:
        description += f' Generic monospace substitutes for {substitutions} external font runs.'
    if missing:
        kinds = sorted({item.kind_hex for item in missing})
        description += ' Omitted element type bytes (hex) ' + ', '.join(kinds) + '.'
    if colors.get(0):
        background = [f'<rect x="{_number(box[0])}" y="{_number(box[1])}" width="{_number(box[2])}" '
                      f'height="{_number(box[3])}" fill="{colors[0]}"/>']
    else:
        background = []
    svg = '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">',
                     f'<desc>{escape(description)}</desc>', *background, *shapes, '</svg>\n'])
    geometry = (min(xs), min(ys), max(xs), max(ys)) if bounds else None
    return SvgPreview(svg, box, geometry, len(shapes), tuple(missing))


def render_svg(form, palette=(), *, substitute_external_fonts=False, outline_faces=None):
    """Return the stand-alone SVG string for the measured geometry preview."""
    return preview_svg(form, palette, substitute_external_fonts=substitute_external_fonts,
                       outline_faces=outline_faces).svg
