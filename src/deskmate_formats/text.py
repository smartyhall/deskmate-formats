"""Read measured DeskMate 3.05 DOC text streams and picture envelopes."""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from struct import unpack_from
import sys

FORMATTED_HEADER = bytes.fromhex('0d 44 4f 43 00 01 2b 2d 2d 05 64 2d 2d 05 46 42 3c 00 00 00 00 01')
LAYOUT_COMMANDS = (b'\x03\x21\x00\x00\x04', b'\x03\x00\x00\x00\x04')
ATTRIBUTE_ON = {0x11, 0x13}
ATTRIBUTE_OFF = {0x10: 0x11, 0x12: 0x13}
MAX_BYTES = 1024 * 1024


class TextFormatError(ValueError):
    """Malformed text stream or a format feature outside the measured profiles."""


@dataclass(frozen=True)
class Picture:
    """An embedded picture envelope with absolute offsets and unmodified payload."""

    offset: int
    payload_offset: int
    end_offset: int
    column: int
    text_offset: int
    payload: bytes


@dataclass(frozen=True)
class Document:
    """The ordinary text projection and ordered pictures in a measured stream."""

    header: bytes
    text: str
    pictures: tuple[Picture, ...]


def _picture(data, offset, end, text_offset):
    if end - offset < 8:
        raise TextFormatError(f'truncated picture envelope at 0x{offset:04X}')
    length, column = unpack_from('<HH', data, offset + 1)
    start = offset + 5
    limit = start + length
    if not length or limit + 3 > end:
        raise TextFormatError(f'invalid picture length at 0x{offset:04X}')
    if unpack_from('<H', data, limit)[0] != length or data[limit + 2] != 0x02:
        raise TextFormatError(f'invalid picture trailer at 0x{limit:04X}')
    return Picture(offset, start, limit + 3, column, text_offset, data[start:limit])


def parse_bytes(source):
    """Inspect a measured DOC stream without interpreting the graphics payloads.

    Text has LF line endings and one native EOF padding space is suppressed.
    Picture text offsets index the decoded text string, which omits the picture
    paragraphs. File offsets are absolute and end offsets are exclusive.
    """
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise TextFormatError('expected a byte snapshot')
    if not 2 <= memoryview(source).nbytes <= MAX_BYTES:
        raise TextFormatError('expected a bounded file ending in DOS EOF (0x1A)')
    data = bytes(source)
    if not data.endswith(b'\x1a'):
        raise TextFormatError('expected a bounded file ending in DOS EOF (0x1A)')

    formatted = data.startswith(b'\rDOC')
    if formatted and not data.startswith(FORMATTED_HEADER):
        raise TextFormatError('unsupported formatted DOC header')
    cursor = len(FORMATTED_HEADER) if formatted else 0
    end = len(data) - 1
    if data[cursor:end].endswith(b' '):
        end -= 1

    active = set()
    output = bytearray()
    pictures = []
    picture_allowed = formatted
    while cursor < end:
        byte = data[cursor]
        if formatted and byte == 0x01 and picture_allowed and not active:
            picture = _picture(data, cursor, end, len(output))
            pictures.append(picture)
            cursor = picture.end_offset
            continue
        picture_allowed = False
        if byte >= 0x20 and byte != 0x7F:
            output.append(byte)
        elif byte == 0x0D and cursor + 1 < end and data[cursor + 1] == 0x0A:
            output.append(0x0A)
            cursor += 1
            picture_allowed = True
        elif formatted and byte in ATTRIBUTE_ON and byte not in active:
            active.add(byte)
        elif formatted and ATTRIBUTE_OFF.get(byte) in active:
            active.remove(ATTRIBUTE_OFF[byte])
        elif formatted and byte == 0x03 and data[cursor:cursor + 5] in LAYOUT_COMMANDS:
            cursor += 4
        else:
            raise TextFormatError(f'unsupported byte or control 0x{byte:02X} at 0x{cursor:04X}')
        cursor += 1
    if active:
        raise TextFormatError('unterminated character attribute')
    return Document(FORMATTED_HEADER if formatted else b'', output.decode('cp437'), tuple(pictures))


def extract_bytes(source):
    """Return the plain-text projection of a measured picture-free file."""
    document = parse_bytes(source)
    if document.pictures:
        raise TextFormatError('document contains pictures; use the structured Text reader')
    return document.text


def parse_file(path):
    """Read a bounded file and preserve its picture envelopes and text."""
    with Path(path).open('rb') as handle:
        return parse_bytes(handle.read(MAX_BYTES + 1))


def extract_file(path):
    """Read a bounded file and return the measured plain-text projection."""
    with Path(path).open('rb') as handle:
        return extract_bytes(handle.read(MAX_BYTES + 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true', help='include picture offsets and payloads as JSON')
    parser.add_argument('source')
    args = parser.parse_args(argv)
    try:
        if args.inspect:
            document = asdict(parse_file(args.source))
            print(json.dumps(document, default=bytes.hex, indent=2))
        else:
            sys.stdout.write(extract_file(args.source))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
