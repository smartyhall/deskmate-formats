"""Inspect the measured DeskMate FF1 family directory in user-supplied resources."""
import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from


MAX_SIZE = 128 * 1024
DIRECTORY_OFFSET = 0x42
RECORD_SIZE = 46


class FontResourceError(ValueError):
    """Resource lies outside the measured FF1 directory profile."""


@dataclass(frozen=True)
class FontVariant:
    name: str
    offset: int
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
        variants.append(FontVariant(label, offset, raw[32:]))
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
