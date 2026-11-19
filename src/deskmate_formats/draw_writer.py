"""Conservative FIG serialization around length-preserving graphics-form edits."""
from fractions import Fraction
from math import ceil, floor
from struct import error as StructError, pack, pack_into, unpack_from

from . import draw, graphics, graphics_edit
from .font_resources import FontResourceError, parse_glyph_outline


LIST_START = draw.PAGE_SETUP_SIZE + graphics.PREFIX_SIZE
_DEFAULT_PAGE_SETUP = bytes.fromhex('1446494700002a2828006e2d2d0050423c0000000100')
_DEFAULT_PALETTE = (
    (0, 0, 128), (192, 192, 0), (192, 192, 192), (128, 0, 0),
    (0, 128, 128), (0, 0, 192), (192, 0, 0), (128, 128, 128),
    (64, 64, 64), (0, 128, 128), (0, 192, 0), (128, 0, 128),
    (128, 128, 0), (192, 0, 192), (0, 128, 0), (0, 0, 0),
)


def _snapshot(source):
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise graphics.GraphicsFormatError('expected a byte snapshot')
    if memoryview(source).nbytes > draw.MAX_BYTES:
        raise graphics.GraphicsFormatError('FIG exceeds the supported file size')
    return bytes(source)


def exact_copy(source, *, recover_arc_length=False):
    """Return the validated FIG snapshot, preserving every byte."""
    data = _snapshot(source)
    draw.parse_bytes(data, recover_arc_length=recover_arc_length)
    return data


def _rewrite(source, edit, *args):
    data = _snapshot(source)
    form = draw.parse_bytes(data).form
    listing = edit(form, *args)
    if len(listing) != len(form.list_data):
        raise graphics.GraphicsFormatError('FIG edit changed the form length')
    return data[:LIST_START] + listing + data[LIST_START + len(listing):]


def move_line(source, tag, dx, dy):
    """Translate one top-level line by exact signed 16.16 deltas."""
    return _rewrite(source, graphics_edit.move_line, tag, dx, dy)


def recolor_line(source, tag, color):
    """Change one top-level line's palette index."""
    return _rewrite(source, graphics_edit.recolor_line, tag, color)


def resize_rectangle(source, tag, width, height):
    """Resize one ordered top-level rectangle about its upper-left corner."""
    return _rewrite(source, graphics_edit.resize_rectangle, tag, width, height)


def reorder(source, tags):
    """Set top-level display order while preserving all physical record bytes."""
    data = _snapshot(source)
    form = draw.parse_bytes(data).form
    offsets = {entry.tag: entry.offset for entry in form.entries}
    if any(type(tag) is not int for tag in tags) or len(tags) != len(offsets) or set(tags) != set(offsets):
        raise graphics.GraphicsFormatError('display order must contain each top-level tag exactly once')
    result = bytearray(data)
    for i, tag in enumerate(tags):
        pack_into('<HH', result, LIST_START + 2 + 4 * i, offsets[tag] // 2, tag)
    return bytes(result)


def _packed(source):
    data = _snapshot(source)
    form = draw.parse_bytes(data).form
    count = len(form.entries)
    capacity, index_words, tag_hint = unpack_from('<HHH', form.header, 6)
    first, last = unpack_from('<HH', form.header, 14)
    if ((capacity, index_words) != (count + 1, 2 * count + 1)
            or last - first != len(form.list_data) or form.strokes != b'\0\0'
            or not form.elements or form.elements[0].offset != 2 + 4 * count):
        raise graphics.GraphicsFormatError('structural edit requires a packed Draw list')
    return data, form, first, tag_hint


def _known_leaves(elements):
    for element in elements:
        expected = graphics.PRIMITIVE_SIZES.get(element.kind)
        if element.kind in ('UA', 'UP'):
            expected = 2 * unpack_from('<H', element.raw, 18)[0]
        if element.kind == 'Uf' and graphics.external_font_run(element) is not None:
            expected = 2 * unpack_from('<H', element.raw, 18)[0]
        if len(element.raw) != expected or (element.kind == 'UA' and expected != 44):
            raise graphics.GraphicsFormatError('structural edit would relocate an unsupported record')


def _rebuild_listing(ordered, first):
    count = len(ordered)
    if count == 0:
        raise graphics.GraphicsFormatError('native Draw has no qualified empty-file representation')
    listing = bytearray(2 + 4 * count)
    pack_into('<H', listing, 0, count)
    for i in reversed(range(count)):
        tag, raw = ordered[i]
        pack_into('<HH', listing, 2 + 4 * i, len(listing) // 2, tag)
        listing.extend(raw)
        if len(listing) > 65535 - first:
            raise graphics.GraphicsFormatError('rebuilt Draw list exceeds the measured allocation bound')
    return listing


def _wrap(data, form, listing, first, tag_hint):
    if len(listing) > 65535 - first:
        raise graphics.GraphicsFormatError('rebuilt Draw list exceeds the measured allocation bound')
    count, = unpack_from('<H', listing)
    header = bytearray(data[:LIST_START])
    pack_into('<H', header, 24, len(listing) // 2)
    pack_into('<HHH', header, 28, count + 1, 2 * count + 1, tag_hint)
    pack_into('<HH', header, 38, first + len(listing), len(listing))
    result = bytes(header) + bytes(listing) + data[LIST_START + len(form.list_data):]
    draw.parse_bytes(result)
    return result


def _new_tag(form, hint, added=1):
    tag = max(hint, *(entry.tag for entry in form.entries)) + added
    if tag > 65535:
        raise graphics.GraphicsFormatError('Draw tag space exhausted')
    return tag


def _rebuild_flat(source, *, new=None, remove=None):
    data, form, first, tag_hint = _packed(source)
    records = {element.offset: element for element in form.elements}
    if len(records) != len(form.entries):
        raise graphics.GraphicsFormatError('structural edit requires a packed flat Draw list')
    _known_leaves(form.elements)
    if remove is not None and (type(remove) is not int or remove not in {e.tag for e in form.entries}):
        raise graphics.GraphicsFormatError('the requested top-level delete tag does not exist')
    ordered = [(entry.tag, records[entry.offset].raw) for entry in form.entries if entry.tag != remove]
    if new is not None:
        tag_hint = _new_tag(form, tag_hint)
        ordered.append((tag_hint, new))
    listing = _rebuild_listing(ordered, first)
    return _wrap(data, form, listing, first, tag_hint)


def add_line(source, coords, *, color=1):
    """Append a plain line with exact fixed coordinates to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.line_record(coords, color))


def add_ellipse(source, coords, *, color=1, fill=None):
    """Append an ellipse with ordered exact fixed bounds to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.ellipse_record(coords, color, fill))


def add_rectangle(source, coords, *, color=1, fill=None):
    """Append a rectangle with ordered exact fixed bounds to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.rectangle_record(coords, color, fill))


def add_polyline(source, points, *, color=1, closed=False, fill=None):
    """Append an integral polyline or polygon to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.polyline_record(points, color, closed, fill))


def new_drawing(kind, geometry, *, color=1, fill=None):
    """Construct a new single-primitive FIG using the measured default profile."""
    if kind == 'L' and fill is None:
        record = graphics_edit.line_record(geometry, color)
    elif kind == 'E':
        record = graphics_edit.ellipse_record(geometry, color, fill)
    elif kind == 'R':
        record = graphics_edit.rectangle_record(geometry, color, fill)
    elif kind in ('polyline', 'polygon'):
        record = graphics_edit.polyline_record(geometry, color, kind == 'polygon', fill)
    else:
        raise graphics.GraphicsFormatError('unsupported first primitive')
    return _new_with_record(record)


def _new_with_record(record):
    first = 0x1C78
    listing = _rebuild_listing([(1, record)], first)
    palette = b''.join(bytes((index, *rgb)) for index, rgb in enumerate(_DEFAULT_PALETTE))
    header = pack('<BB8H', 1, 1, len(listing) // 2, 2, 2, 3, 1, 0, first, first + len(listing))
    data = _DEFAULT_PAGE_SETUP + header + pack('<HH', len(listing), 2) + listing + b'\0\0\x10\0' + palette + b'\0'
    draw.parse_bytes(data)
    return data


def outline_text_record(face, label, origin, *, point_size=24, width_percent=100):
    """Construct a left-justified filled Uf with nominal, ink-enclosing cache."""
    try:
        name = face.name.encode('ascii')
        text = label.encode('cp437')
        x, y = origin
        if (not 1 <= len(name) <= 29 or any(not 32 <= n <= 126 for n in name)
                or not 1 <= len(text) <= 255 or any(n < 32 or n == 127 for n in text)
                or any(type(n) is not int for n in (x, y, point_size, width_percent))
                or not 1 <= point_size <= 255 or not 1 <= width_percent <= 255):
            raise graphics.GraphicsFormatError('unsupported outline text name, label, origin, size or width')
        sy = Fraction(point_size * 1000, 72 * face.index.units_per_em_word)
        sx = sy * Fraction(width_percent, 100)
        cursor = left = right = top = bottom = 0
        for code in text:
            entry = face.draw_entry(code)
            glyph = parse_glyph_outline(face.data, entry)
            if glyph.contours:
                gx, gy, gr, gb = glyph.bounds
                left, right = min(left, cursor + gx), max(right, cursor + gr)
                top, bottom = min(top, gy), max(bottom, gb)
            cursor += entry.advance_word
        l, r = floor(left * sx), max(1, ceil(max(cursor, right) * sx))
        t, b = min(-1, floor(top * sy)), max(1, ceil(bottom * sy))
        raw = bytearray(100)
        raw[:2] = b'Uf'
        for i, coordinate in enumerate((x + l, y + t, x + r, y + b)):
            pack_into('<hH', raw, 2 + 4 * i, coordinate, 0)
        raw[20:22] = b'\x01\xff'
        raw[26:26 + len(name)] = name
        pack_into('<6H', raw, 56, point_size, width_percent, 0, 0, 12, 255)
        pack_into('<4H2hH', raw, 84, b - t, -t, r - l, 1, x, y, len(text))
        raw.extend(text + bytes(2 - len(text) % 2))
        pack_into('<H', raw, 18, len(raw) // 2)
    except (UnicodeError, StructError, FontResourceError) as error:
        raise graphics.GraphicsFormatError(f'cannot encode outline text ({error})') from error
    return bytes(raw)


def new_outline_drawing(face, label, origin, **options):
    """Construct a single-run FIG in the measured packed form."""
    return _new_with_record(outline_text_record(face, label, origin, **options))


def add_outline_text(source, face, label, origin, **options):
    """Append an outline run, retaining all other supported leaf bytes."""
    return _rebuild_flat(source, new=outline_text_record(face, label, origin, **options))


def delete(source, tag):
    """Delete a top-level element from a supported flat, nonempty FIG."""
    return _rebuild_flat(source, remove=tag)


def group_all(source):
    """Wrap a packed flat figure's known top-level elements in one OO."""
    data, form, first, tag_hint = _packed(source)
    if len(form.entries) < 2 or len(form.entries) != len(form.elements):
        raise graphics.GraphicsFormatError('grouping requires at least two flat top-level elements')
    _known_leaves(form.elements)
    elements = tuple(form.draw_order())
    tag = _new_tag(form, tag_hint)
    count = len(elements)
    body = bytearray()
    offsets = [0] * count
    head_end = 6 + 20 + 2 * count
    for i in reversed(range(count)):
        offsets[i] = (head_end + len(body)) // 2
        body.extend(elements[i].raw)
    listing = pack('<HHH', 1, 3, tag) + graphics_edit.group_header(elements, offsets) + body
    return _wrap(data, form, listing, first, tag)


def ungroup_all(source):
    """Flatten a single known group, allocating tags for its saved leaves."""
    data, form, first, tag_hint = _packed(source)
    root = next((item for item in form.elements if item.offset == form.entries[0].offset), None)
    if (len(form.entries) != 1 or root is None or root.kind != 'OO' or len(root.children) < 2
            or len(root.raw) != 20 + 2 * len(root.children) or len(form.elements) != len(root.children) + 1):
        raise graphics.GraphicsFormatError('ungrouping requires one flat group containing only leaves')
    elements = tuple(form.draw_order())
    if len(elements) != len(root.children):
        raise graphics.GraphicsFormatError('ungrouping would relocate a nested or unsupported group')
    _known_leaves(elements)
    end_tag = _new_tag(form, tag_hint, len(elements))
    first_tag = end_tag - len(elements) + 1
    listing = _rebuild_listing([(first_tag+i, item.raw) for i, item in enumerate(elements)], first)
    return _wrap(data, form, listing, first, end_tag)


def replace_palette_color(source, index, rgb):
    """Change the RGB channels of an existing palette entry without moving it."""
    data = _snapshot(source)
    drawing = draw.parse_bytes(data)
    if type(index) is not int or not 0 <= index <= 15:
        raise graphics.GraphicsFormatError('palette index must be 0 through 15')
    if len(rgb) != 3 or any(type(value) is not int or not 0 <= value <= 255 for value in rgb):
        raise graphics.GraphicsFormatError('palette channels require three byte values')
    row, = (position for position, entry in enumerate(drawing.palette) if entry[0] == index)
    offset = drawing.palette_offset + 4 * row + 1
    return data[:offset] + bytes(rgb) + data[offset+3:]


def permute_outline_label(source, tag, ascii_label):
    """Reorder the same ASCII letters in a qualified outline-font text run."""
    data = _snapshot(source)
    form = draw.parse_bytes(data).form
    offset = next((entry.offset for entry in form.entries if entry.tag == tag and type(tag) is int), None)
    item = next((element for element in form.elements if element.offset == offset), None)
    ref = graphics.external_font_run(item) if item else None
    if (ref is None or ref.name not in ('Cobb', 'Dixon', 'Marin')
            or len(item.raw) != 2 * unpack_from('<H', item.raw, 18)[0]
            or any(not 32 <= code <= 126 for code in ref.text_bytes)):
        raise graphics.GraphicsFormatError('text edit requires a resolved top-level ASCII outline-font run')
    if not isinstance(ascii_label, bytes) or sorted(ascii_label) != sorted(ref.text_bytes):
        raise graphics.GraphicsFormatError('this edit requires a permutation of the original ASCII label')
    start = LIST_START + item.offset + 100
    return data[:start] + ascii_label + data[start+len(ascii_label):]
