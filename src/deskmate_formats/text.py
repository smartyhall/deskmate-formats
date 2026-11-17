"""Extract plain text from measured DeskMate 3.05 DOC and To ASCII files."""
import argparse
from pathlib import Path
import sys

FORMATTED_HEADER = bytes.fromhex('0d 44 4f 43 00 01 2b 2d 2d 05 64 2d 2d 05 46 42 3c 00 00 00 00 01')
LAYOUT_COMMANDS = (b'\x03\x21\x00\x00\x04', b'\x03\x00\x00\x00\x04')
ATTRIBUTE_ON = {0x11, 0x13}
ATTRIBUTE_OFF = {0x10: 0x11, 0x12: 0x13}
MAX_BYTES = 1024 * 1024


class TextFormatError(ValueError):
    """Malformed text stream or a format feature outside the measured profiles."""


def extract_bytes(source):
    """Extract text with LF line endings and suppress one native EOF padding space.

    The formatted profile uses the exact observed default header, inline bold
    and underline toggles, and the two measured centering commands. Layout and
    attribute presentation are discarded. Spaces before CRLF are retained.
    """
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise TextFormatError('expected a byte snapshot')
    data = bytes(source)
    if not 2 <= len(data) <= MAX_BYTES or not data.endswith(b'\x1a'):
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
    while cursor < end:
        byte = data[cursor]
        if byte >= 0x20 and byte != 0x7F:
            output.append(byte)
        elif byte == 0x0D and cursor + 1 < end and data[cursor + 1] == 0x0A:
            output.append(0x0A)
            cursor += 1
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
    return output.decode('cp437')


def extract_file(path):
    """Read a bounded file and return the measured plain-text projection."""
    with Path(path).open('rb') as handle:
        return extract_bytes(handle.read(MAX_BYTES + 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(extract_file(args.source))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
