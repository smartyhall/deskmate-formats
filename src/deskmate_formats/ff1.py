"""Lossless editing and independent construction of the measured FF1 profile."""
from dataclasses import dataclass, replace
from struct import error as StructError, pack, pack_into, unpack_from

from .font_resources import (
    DIRECTORY_OFFSET, MAX_SIZE, RECORD_SIZE, Contour, FontResourceError, GlyphOutline,
    parse_bytes, parse_glyph_index, parse_glyph_outline,
)


FIRST_CODE = 32
CODE_COUNT = 224
UNITS_PER_EM = 1000


@dataclass(frozen=True)
class Glyph:
    advance: int
    outline: GlyphOutline


@dataclass(frozen=True)
class Resource:
    """Parsed glyphs and separately retained directory and opaque sections."""

    header: bytes
    descriptors: tuple[bytes, ...]
    bridge: bytes
    inner_header: bytes
    inner_padding: bytes
    glyphs: tuple[Glyph, ...]
    trailing: bytes

    @property
    def family(self):
        return self.descriptors[0][:32].split(b'\0', 1)[0].decode('ascii')

    @property
    def first_code(self):
        return unpack_from('<H', self.inner_header, 14)[0]

    @property
    def units_per_em(self):
        return unpack_from('<H', self.inner_header, 12)[0]


def parse_resource(data):
    directory = parse_bytes(data)
    index = parse_glyph_index(data)
    end = DIRECTORY_OFFSET + len(directory.variants) * RECORD_SIZE
    inner = end + 4
    widths, = unpack_from('<H', data, end + 2)
    glyph_end = index.entries[-1].offset + index.entries[-1].size
    return Resource(
        data[:DIRECTORY_OFFSET],
        tuple(data[v.offset:v.offset + RECORD_SIZE] for v in directory.variants),
        data[end:inner], data[inner:inner + 48], data[inner + 48:inner + widths],
        tuple(Glyph(entry.advance_word, parse_glyph_outline(data, entry)) for entry in index.entries),
        data[glyph_end:],
    )


def outline_bounds(contours):
    points = [point for contour in contours
              for point in (contour.start, *(p for segment in contour.segments for p in segment))]
    if not points:
        return 0, 0, 0, 0
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def _encode_outline(outline):
    commands = bytearray()
    for contour in outline.contours:
        commands.extend(pack('<Bhh', 0, *contour.start))
        if len(commands) > 65535:
            raise FontResourceError('FF1 contour stream exceeds its length word')
        if contour.segments and contour.segments[-1][-1:] != (contour.start,):
            raise FontResourceError('open FF1 contour')
        for segment in contour.segments:
            if len(segment) == 1:
                commands.extend(pack('<Bhh', 1, *segment[0]))
            elif len(segment) == 3 and all(len(point) == 2 for point in segment):
                commands.extend(pack('<B6h', 2, *(value for point in segment for value in point)))
            else:
                raise FontResourceError('FF1 segment must be a line or cubic')
            if len(commands) > 65535:
                raise FontResourceError('FF1 contour stream exceeds its length word')
    left, top, right, bottom = outline.bounds
    if left > right or top > bottom:
        raise FontResourceError('inverted FF1 glyph bounds')
    return (pack('<H4h2H', 1, left, top, right, bottom, len(commands), len(outline.auxiliary))
            + commands + outline.auxiliary)


def serialize_resource(resource):
    """Rebuild commands and lengths. Keep opaque fields and padding verbatim."""
    if (len(resource.header) != DIRECTORY_OFFSET or len(resource.bridge) != 4
            or len(resource.inner_header) != 48 or not 1 <= len(resource.descriptors) <= 64
            or any(len(item) != RECORD_SIZE for item in resource.descriptors)):
        raise FontResourceError('invalid FF1 model section sizes')
    header, bridge, inner = map(bytearray, (resource.header, resource.bridge, resource.inner_header))
    count = len(resource.glyphs)
    if not 0 < count <= 256 - resource.first_code:
        raise FontResourceError('invalid FF1 character range')
    widths_at = len(inner) + len(resource.inner_padding)
    offsets_at = widths_at + 2 * count
    cursor = offsets_at + 4 * count
    inner_at = DIRECTORY_OFFSET + RECORD_SIZE * len(resource.descriptors) + len(bridge)
    widths, offsets, outlines = bytearray(), bytearray(), bytearray()
    if inner_at + cursor + len(resource.trailing) > MAX_SIZE:
        raise FontResourceError('FF1 resource exceeds snapshot limit')
    try:
        for code, glyph in enumerate(resource.glyphs, resource.first_code):
            try:
                widths.extend(pack('<H', glyph.advance))
                encoded = _encode_outline(glyph.outline)
            except (StructError, FontResourceError) as error:
                raise FontResourceError(f'invalid glyph {code}: {error}') from error
            offsets.extend(pack('<I', cursor))
            cursor += len(encoded)
            if inner_at + cursor + len(resource.trailing) > MAX_SIZE:
                raise FontResourceError('FF1 resource exceeds snapshot limit')
            outlines.extend(encoded)
        original_end = (DIRECTORY_OFFSET + RECORD_SIZE * unpack_from('<H', header, 10)[0]
                        + 4 + unpack_from('<I', inner, 4)[0])
        pair_at, = unpack_from('<I', header, 38)
        if pair_at and cursor + inner_at != original_end:
            if pair_at != original_end:
                raise FontResourceError('cannot relocate an unrecognized FF1 section pointer')
            pack_into('<I', header, 38, cursor + inner_at)
        if inner_at != original_end - unpack_from('<I', inner, 4)[0]:
            outer_index, = unpack_from('<H', header, 34)
            if outer_index != original_end - unpack_from('<I', inner, 4)[0] - 16:
                raise FontResourceError('cannot relocate an unrecognized FF1 directory pointer')
            pack_into('<H', header, 34, inner_at - 16)
        pack_into('<H', header, 10, len(resource.descriptors))
        pack_into('<H', header, 16, count)
        pack_into('<H', bridge, 2, widths_at)
        pack_into('<I', inner, 4, cursor)
        pack_into('<H', inner, 16, count)
        pack_into('<H', inner, 46, offsets_at)
    except StructError as error:
        raise FontResourceError(f'FF1 integer field overflow: {error}') from error
    data = bytes(header + b''.join(resource.descriptors) + bridge + inner
                 + resource.inner_padding + widths + offsets + outlines + resource.trailing)
    parse_glyph_index(data)
    return data


def _name_field(name):
    if not 1 <= len(name) <= 31 or any(not 32 <= ord(char) <= 126 for char in name):
        raise FontResourceError('FF1 name must contain 1 to 31 printable ASCII characters')
    return name.encode('ascii').ljust(32, b'\0')


def create_resource(family, glyphs, *, face_id=50, family_id=2, optional_metrics=True):
    """Build an independent single-variant 32–255/1000-em candidate.

    The outer descriptor style defaults and inner constants are inferred from
    the measured base profile. Auxiliary rows and pair data are optional inputs
    to the model and are not synthesized.
    """
    glyphs = tuple(glyphs)
    if len(glyphs) != CODE_COUNT or not all(1 <= ident <= 255 for ident in (face_id, family_id)):
        raise FontResourceError('expected 224 glyphs and IDs in 1–255')
    descriptor_name = _name_field(family)
    present = [glyph.outline.bounds for glyph in glyphs if glyph.outline.contours]
    bounds = (min((b[0] for b in present), default=0), min((b[1] for b in present), default=0),
              max((b[2] for b in present), default=0), max((b[3] for b in present), default=0))
    advance = max(glyph.advance for glyph in glyphs)
    header = bytearray(DIRECTORY_OFFSET)
    header[:5] = b'\xbd\x7a\0\x01\x01'
    inner = bytearray(48)
    inner[:4] = b'\x1e\xf3\x01\x01'
    style = bytes.fromhex('0f 05 f8 1e 14 00 00')
    try:
        pack_into('<5H4h6H', header, 8, UNITS_PER_EM, 1, 1, FIRST_CODE, CODE_COUNT,
                  *bounds, 0x578f, 0x104, 54, RECORD_SIZE, DIRECTORY_OFFSET + RECORD_SIZE + 4 - 16, 16)
        header[54:66] = pack('<HBBB', family_id, 0, 100, 0) + style
        descriptor = descriptor_name + pack('<HHBBB', 0, face_id, 1, 85, 0) + style
        pack_into('<7H4h4hH', inner, 8, 1, 0, UNITS_PER_EM, FIRST_CODE, CODE_COUNT,
                  0x104, 0x578f, *bounds, -250, min(advance, 32767), 0, min(advance, 32767),
                  76 if optional_metrics else 48)
        padding = bytes(16) + pack('<H4hH', 3, -700, bounds[1], bounds[3], 32767, 0)
    except StructError as error:
        raise FontResourceError(f'FF1 construction field overflow: {error}') from error
    return Resource(bytes(header), (descriptor,), bytes(4), bytes(inner),
                    padding if optional_metrics else b'', glyphs, b'')


def polygon(*points):
    """Construct a polygon with an explicit closing line."""
    return Contour(points[0], tuple((point,) for point in (*points[1:], points[0])))


def dixon_slot(resource):
    """Use the measured Dixon directory structure around an independent bank."""
    if (resource.family != 'Dixon' or len(resource.descriptors) != 1
            or unpack_from('<H', resource.header, 54)[0] != 2
            or unpack_from('<H', resource.descriptors[0], 34)[0] != 50):
        raise FontResourceError('Dixon slot requires family Dixon and IDs 2 and 50')
    settings = (
        ('Thin', 126, 2, 75, 0),
        ('Condensed', 3, 4, 125, 0),
        ('Wide', 4, 8, 150, 0),
        ('Expanded', 54, 16, 100, 1),
        ('Hollow', 5, 17, 85, 1),
        ('Hol-Thin', 58, 18, 75, 1),
        ('Hol-Cond', 6, 20, 125, 1),
        ('Hol-Wide', 55, 24, 150, 1),
    )
    descriptors = [_name_field('Dixon ' + name) + pack('<HHBBB', 0, ident, mode, width, variant)
                   + resource.descriptors[0][39:] for name, ident, mode, width, variant in settings]
    descriptors.append(_name_field('Dixon Hol-Exp') + pack('<HHBB', 0, 1, 18, 2) + bytes(8))
    return replace(resource, descriptors=(*resource.descriptors, *descriptors))
