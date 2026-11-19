"""Inspect DeskMate FF1 directories and outlines in user-supplied resources."""
import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from


MAX_SIZE = 128 * 1024
DIRECTORY_OFFSET = 0x42
RECORD_SIZE = 46
DRAW_EXTENDED_OUTLINE_SLOTS = bytes((
    180, 207, 197, 192, 204, 200, 212, 181, 193, 205, 201, 221, 209, 217, 216, 208,
    220, 215, 211, 194, 206, 202, 195, 203, 239, 218, 219, 191, 187, 188, 186, 190,
    196, 213, 198, 199, 183, 182, 249, 250, 185, 128, 129, 130, 131, 184, 251, 253,
    226, 234, 210, 214, 241, 240, 161, 225, 233, 189, 244, 243, 242, 168, 169, 170,
    160, 255, 176, 252, 246, 245, 179, 224, 162, 163, 164, 165, 230, 229, 166, 167,
    232, 231, 223, 235, 236, 173, 237, 174, 238, 222, 247, 248, 254, 175, 227, 228,
))


def draw_outline_slot(code):
    """Translate an input byte in the measured Draw base-outline mode."""
    if code < 128:
        return code
    if code < 224:
        return DRAW_EXTENDED_OUTLINE_SLOTS[code - 128]
    return 32


class FontResourceError(ValueError):
    """Resource lies outside the measured FF1 directory profile."""


@dataclass(frozen=True)
class FontVariant:
    name: str
    # Name offset within the original snapshot.
    offset: int
    # Native record's twelve leading and two trailing bytes.
    attributes: bytes


@dataclass(frozen=True)
class FontResource:
    size: int
    sha256: str
    first_code_word: int
    code_count_word: int
    variants: tuple[FontVariant, ...]


@dataclass(frozen=True)
class GlyphEntry:
    code: int
    advance_word: int
    offset: int
    size: int


@dataclass(frozen=True)
class GlyphIndex:
    units_per_em_word: int
    entries: tuple[GlyphEntry, ...]


Point = tuple[int, int]


@dataclass(frozen=True)
class Contour:
    start: Point
    # Line endpoints and cubic triples, in stream order.
    segments: tuple[tuple[Point, ...], ...]


@dataclass(frozen=True)
class GlyphOutline:
    bounds: tuple[int, int, int, int]
    contours: tuple[Contour, ...]
    auxiliary: bytes


def parse_glyph_outline(data, entry):
    """Read one contour stream, retaining the auxiliary bytes verbatim."""
    offset = entry.offset
    prefix_size = 14
    if offset < 0 or entry.size < prefix_size or offset + entry.size > len(data):
        raise FontResourceError(f'invalid FF1 glyph extent for code {entry.code}')
    marker, left, top, right, bottom, size, auxiliary_size = unpack_from('<H4h2H', data, offset)
    if marker != 1 or prefix_size + size + auxiliary_size != entry.size or left > right or top > bottom:
        raise FontResourceError(f'unsupported FF1 glyph header for code {entry.code}')
    start = None
    segments = []
    contours = []
    pos, end = offset + prefix_size, offset + prefix_size + size
    while pos < end:
        opcode = data[pos]
        if opcode > 2:
            raise FontResourceError(f'unknown FF1 opcode {opcode:#04x} for code {entry.code} at glyph byte {pos-offset}')
        following = pos + (13 if opcode == 2 else 5)
        if following > end:
            raise FontResourceError(f'truncated FF1 command for code {entry.code} at glyph byte {pos-offset}')
        points = tuple(iter_unpack('<hh', data[pos+1:following]))
        if opcode == 0:
            if start is not None:
                contours.append(Contour(start, tuple(segments)))
            start, segments = points[0], []
        elif start is None:
            raise FontResourceError(f'FF1 contour lacks a move for code {entry.code}')
        else:
            segments.append(points)
        pos = following
    if start is not None:
        contours.append(Contour(start, tuple(segments)))
    if any(c.segments and c.segments[-1][-1] != c.start for c in contours):
        raise FontResourceError(f'open FF1 contour for code {entry.code}')
    return GlyphOutline((left, top, right, bottom), tuple(contours), data[end:offset + entry.size])


@dataclass(frozen=True)
class OutlineFace:
    """Base face of a local FF1 snapshot, keyed by its resource name."""

    name: str
    sha256: str
    index: GlyphIndex
    data: bytes

    def entry(self, code):
        position = code - self.index.entries[0].code
        if not 0 <= position < len(self.index.entries):
            raise FontResourceError(f'code {code} is outside the {self.name} glyph index')
        return self.index.entries[position]

    def draw_entry(self, code):
        if (self.index.units_per_em_word == 1000 and len(self.index.entries) == 224
                and self.index.entries[0].code == 32):
            code = draw_outline_slot(code)
        return self.entry(code)


def load_outline_faces(paths):
    """Load explicitly supplied base faces and reject ambiguous family names."""
    faces = {}
    for path in paths:
        with Path(path).open('rb') as handle:
            data = handle.read(MAX_SIZE + 1)
        resource = parse_bytes(data)
        index = parse_glyph_index(data)
        name = resource.variants[0].name
        key = name.casefold()
        if key in faces and faces[key].sha256 != resource.sha256:
            raise FontResourceError(f'conflicting FF1 resources for {name}')
        faces[key] = OutlineFace(name, resource.sha256, index, data)
    return faces


def parse_bytes(data):
    """Read names and descriptor bytes without interpreting resource glyphs."""
    if not isinstance(data, bytes) or not DIRECTORY_OFFSET <= len(data) <= MAX_SIZE:
        raise FontResourceError('invalid FF1 snapshot size')
    if data[:5] != b'\xbd\x7a\x00\x01\x01' or data[32:34] != b'\x2e\0':
        raise FontResourceError('unsupported FF1 directory profile')
    count, = unpack_from('<H', data, 10)
    first, codes = unpack_from('<HH', data, 14)
    if (not 1 <= count <= 64 or DIRECTORY_OFFSET + count * RECORD_SIZE > len(data)
            or not 0 < codes <= 256 - first):
        raise FontResourceError('invalid FF1 directory extent')
    names = set()
    variants = []
    for offset in range(DIRECTORY_OFFSET, DIRECTORY_OFFSET + count * RECORD_SIZE, RECORD_SIZE):
        raw = data[offset:offset + RECORD_SIZE]
        name, terminator, _ = raw[:32].partition(b'\0')
        if not name or not terminator or any(not 32 <= code <= 126 for code in name):
            raise FontResourceError('invalid FF1 variant name')
        label = name.decode('ascii')
        if label.casefold() in names:
            raise FontResourceError('duplicate FF1 variant name')
        names.add(label.casefold())
        variants.append(FontVariant(label, offset, data[offset-12:offset] + raw[32:34]))
    return FontResource(len(data), sha256(data).hexdigest(), first, codes, tuple(variants))


def parse_file(path):
    with Path(path).open('rb') as file:
        return parse_bytes(file.read(MAX_SIZE + 1))


def parse_glyph_index(data):
    """Read the verified code-to-glyph extent table and nominal advance words."""
    resource = parse_bytes(data)
    outer_end = DIRECTORY_OFFSET + len(resource.variants) * RECORD_SIZE
    inner = outer_end + 4
    if inner + 48 > len(data) or data[inner:inner+4] != b'\x1e\xf3\x01\x01':
        raise FontResourceError('unsupported FF1 inner glyph index profile')
    declared_size, = unpack_from('<I', data, inner + 4)
    units, first, count = unpack_from('<HHH', data, inner + 12)
    widths_rel, = unpack_from('<H', data, outer_end + 2)
    index_rel, = unpack_from('<H', data, inner + 46)
    if (declared_size > len(data) - inner or not units
            or (first, count) != (resource.first_code_word, resource.code_count_word)
            or widths_rel < 48 or widths_rel + 2 * count != index_rel
            or index_rel + 4 * count >= declared_size):
        raise FontResourceError('inconsistent FF1 inner glyph index extent')
    widths = unpack_from(f'<{count}H', data, inner + widths_rel)
    offsets = (*unpack_from(f'<{count}I', data, inner + index_rel), declared_size)
    if offsets[0] != index_rel + 4 * count or any(a >= b for a, b in zip(offsets, offsets[1:])):
        raise FontResourceError('overlapping or unordered FF1 glyph extents')
    entries = tuple(GlyphEntry(first + i, width, inner + a, b - a)
                    for i, (width, a, b) in enumerate(zip(widths, offsets, offsets[1:])))
    return GlyphIndex(units, entries)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resource', type=Path)
    parser.add_argument('--glyph-index', action='store_true', help='read nominal advances and verified glyph extents')
    args = parser.parse_args()
    try:
        with args.resource.open('rb') as source:
            data = source.read(MAX_SIZE + 1)
        result = parse_glyph_index(data) if args.glyph_index else parse_bytes(data)
    except (OSError, FontResourceError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(asdict(result), default=bytes.hex, indent=2))
