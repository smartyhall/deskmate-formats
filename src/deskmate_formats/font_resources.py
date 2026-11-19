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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resource', type=Path)
    args = parser.parse_args()
    try:
        result = parse_file(args.resource)
    except (OSError, FontResourceError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(asdict(result), default=bytes.hex, indent=2))
