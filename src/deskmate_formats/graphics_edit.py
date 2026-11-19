"""Length-preserving edits to exact shared graphics-form list records."""
from struct import pack, pack_into

from . import graphics


FIXED_ONE = 65536


def _target(form, tag, kind):
    if type(tag) is not int:
        raise graphics.GraphicsFormatError('expected an integer display-list tag')
    offset = next((entry.offset for entry in form.entries if entry.tag == tag), None)
    element = next((element for element in form.elements if element.offset == offset), None)
    if element is None or element.kind != kind or len(element.raw) != graphics.PRIMITIVE_SIZES[kind]:
        raise graphics.GraphicsFormatError(f'edit requires an exact-size top-level {kind} record at tag {tag}')
    return element


def _integer(value):
    if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
        raise graphics.GraphicsFormatError('coordinate outside signed 16.16 range')
    return value


def _coordinates(listing, element, coords):
    result = bytearray(listing)
    for index, value in enumerate(coords):
        whole, fraction = divmod(_integer(value), FIXED_ONE)
        pack_into('<hH', result, element.offset + 2 + index * 4, whole, fraction)
    return bytes(result)


def _fixed(element):
    values = element.coordinates
    return tuple(a * FIXED_ONE + b for a, b in zip(values[::2], values[1::2]))


def _coordinate_bytes(a):
    return pack('<hH', *divmod(_integer(a), FIXED_ONE))


def _color(color):
    if type(color) is not int or not 0 <= color < 16:
        raise graphics.GraphicsFormatError('palette index must be 0 through 15')
    return color


def move_line(form, tag, dx, dy):
    """Return the list with one top-level line moved by exact 16.16 deltas."""
    record = _target(form, tag, 'L')
    dx, dy = _integer(dx), _integer(dy)
    x0, y0, x1, y1 = _fixed(record)
    return _coordinates(form.list_data, record, (x0 + dx, y0 + dy, x1 + dx, y1 + dy))


def recolor_line(form, tag, color):
    """Return the list with one top-level line's palette index changed."""
    record = _target(form, tag, 'L')
    result = bytearray(form.list_data)
    result[record.offset + 18] = _color(color)
    return bytes(result)


def resize_rectangle(form, tag, width, height):
    """Return the list with an ordered rectangle resized about its upper-left."""
    record = _target(form, tag, 'R')
    width, height = _integer(width), _integer(height)
    x0, y0, x1, y1 = _fixed(record)
    if not (width > 0 and height > 0 and x0 <= x1 and y0 <= y1):
        raise graphics.GraphicsFormatError('resize requires positive dimensions and ordered rectangle bounds')
    return _coordinates(form.list_data, record, (x0, y0, x0 + width, y0 + height))


def _record(kind, modifier, coords):
    if len(coords) != 4:
        raise graphics.GraphicsFormatError('expected four exact fixed coordinates')
    return bytes((ord(kind), modifier)) + b''.join(_coordinate_bytes(value) for value in coords)


def line_record(coords, color):
    return _record('L', 0, coords) + bytes((_color(color), 0))


def ellipse_record(coords, color, fill):
    x0, y0, x1, y1 = coords
    if not (x0 < x1 and y0 < y1):
        raise graphics.GraphicsFormatError('ellipse requires positive ordered bounds')
    pattern, foreground = (254, 1) if fill is None else (1, _color(fill))
    return _record('E', pattern, coords) + bytes((_color(color), 0, 0, 0, foreground, 0))


def polyline_record(points, color, closed, fill):
    if type(closed) is not bool or not (2 + closed <= len(points) <= 16_374) or fill is not None and not closed:
        raise graphics.GraphicsFormatError('invalid polyline closure, fill, or point count')
    x_values, y_values = zip(*points)
    if any(type(value) is not int or not -32768 <= value <= 32767 for value in x_values + y_values):
        raise graphics.GraphicsFormatError('polyline points require signed integral world units')
    x0, y0, x1, y1 = min(x_values), min(y_values), max(x_values), max(y_values)
    color = _color(color)
    pattern, foreground = (254, 1) if fill is None else (1, _color(fill))
    attrs = bytes((color, color, 0, 0, pattern, 0, foreground, 0))
    bounds = tuple(n * FIXED_ONE for n in (x0, y0, x1, y1))
    return (_record('U', ord('P'), bounds) + pack('<H', 18 + 2 * len(points)) + attrs
            + pack('<HHBBH', x1 - x0, y1 - y0, 255 if fill is not None else 0, 255 if closed else 0, len(points))
            + b''.join(pack('<HH', x - x0, y - y0) for x, y in points))


def group_header(elements, child_word_offsets):
    """Build the measured OO envelope for a flat sequence of known leaves."""
    bounds = [_fixed(element) for element in elements]
    xs = [value for coords in bounds for value in coords[::2]]
    ys = [value for coords in bounds for value in coords[1::2]]
    coords = (min(xs), min(ys), max(xs) + FIXED_ONE, max(ys) + FIXED_ONE)
    return (_record('O', ord('O'), coords) + pack('<H', len(elements))
            + b''.join(pack('<H', word) for word in child_word_offsets))
