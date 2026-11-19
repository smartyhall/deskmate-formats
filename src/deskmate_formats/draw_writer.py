"""Conservative FIG serialization around length-preserving graphics-form edits."""
from struct import pack_into, unpack_from

from . import draw, graphics, graphics_edit


LIST_START = draw.PAGE_SETUP_SIZE + graphics.PREFIX_SIZE


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


def _rebuild_flat(source, *, new=None, remove=None):
    data = _snapshot(source)
    form = draw.parse_bytes(data).form
    records = {element.offset: element for element in form.elements}
    count = len(form.entries)
    capacity, index_words, tag_hint = unpack_from('<HHH', form.header, 6)
    first, last = unpack_from('<HH', form.header, 14)
    if (count != len(records) or (capacity, index_words) != (count + 1, 2 * count + 1)
            or last - first != len(form.list_data) or form.strokes != b'\0\0'
            or not form.elements or form.elements[0].offset != 2 + 4 * count):
        raise graphics.GraphicsFormatError('structural edit requires a packed flat Draw list')
    for element in form.elements:
        expected = graphics.PRIMITIVE_SIZES.get(element.kind)
        if element.kind in ('UA', 'UP'):
            expected = 2 * unpack_from('<H', element.raw, 18)[0]
        if len(element.raw) != expected or (element.kind == 'UA' and expected != 44):
            raise graphics.GraphicsFormatError('structural edit would relocate an unsupported record')
    if remove is not None and (type(remove) is not int or remove not in {e.tag for e in form.entries}):
        raise graphics.GraphicsFormatError('the requested top-level delete tag does not exist')
    ordered = [(entry.tag, records[entry.offset].raw) for entry in form.entries if entry.tag != remove]
    if new is not None:
        tag_hint = max(tag_hint, *(tag for tag, _ in ordered)) + 1
        if tag_hint > 65535:
            raise graphics.GraphicsFormatError('Draw tag space exhausted')
        ordered.append((tag_hint, new))
    count = len(ordered)
    if count == 0:
        raise graphics.GraphicsFormatError('native Draw has no qualified empty-file representation')
    listing = bytearray(2 + 4 * count)
    pack_into('<H', listing, 0, count)
    for i in reversed(range(count)):
        tag, raw = ordered[i]
        if len(listing) + len(raw) > 65535 - first:
            raise graphics.GraphicsFormatError('rebuilt Draw list exceeds the measured allocation bound')
        pack_into('<HH', listing, 2 + 4 * i, len(listing) // 2, tag)
        listing.extend(raw)
    header = bytearray(data[:LIST_START])
    pack_into('<H', header, 24, len(listing) // 2)
    pack_into('<HHH', header, 28, count + 1, 2 * count + 1, tag_hint)
    pack_into('<HH', header, 38, first + len(listing), len(listing))
    result = bytes(header) + bytes(listing) + data[LIST_START + len(form.list_data):]
    draw.parse_bytes(result)
    return result


def add_line(source, coords, *, color=1):
    """Append a plain line with exact fixed coordinates to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.line_record(coords, color))


def add_ellipse(source, coords, *, color=1, fill=None):
    """Append an ellipse with ordered exact fixed bounds to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.ellipse_record(coords, color, fill))


def add_polyline(source, points, *, color=1, closed=False, fill=None):
    """Append an integral polyline or polygon to a supported flat FIG."""
    return _rebuild_flat(source, new=graphics_edit.polyline_record(points, color, closed, fill))


def delete(source, tag):
    """Delete a top-level element from a supported flat, nonempty FIG."""
    return _rebuild_flat(source, remove=tag)
