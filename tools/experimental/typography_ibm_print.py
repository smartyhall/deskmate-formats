"""Decode the captured DeskMate IBM Graphics print-to-file profile."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from


def decode(data):
    """Return one page of 120 dpi by 72 dpi dots and a band inventory."""
    if not 0 < len(data) <= 2 * 1024 * 1024 or not data.startswith(b'\x12\x1b5\0\x1b-\0\x1bF'):
        raise ValueError('unsupported DeskMate IBM Graphics prologue')
    pos, x, vertical = 9, 0, 0
    bands = []
    pixels = set()
    while pos < len(data):
        value = data[pos]
        pos += 1
        if value == 0x0d:
            x = 0
        elif value == 0x0a:
            vertical += 36
        elif value == 0x20:
            x += 12
        elif value == 0x0c and pos == len(data):
            return pixels, bands
        elif value == 0x1b and pos + 2 <= len(data):
            command = data[pos]
            pos += 1
            if command == ord('J'):
                vertical += data[pos]
                pos += 1
            elif command == ord('L') and pos + 2 <= len(data):
                count, = unpack_from('<H', data, pos)
                pos += 2
                if not 0 < count <= len(data) - pos or vertical % 3 or x + count > 2048 or vertical > 3600:
                    raise ValueError('graphics band falls outside the measured page')
                y = vertical // 3
                bands.append((x, y, count))
                for column, marks in enumerate(data[pos:pos + count], x):
                    pixels.update((column, y + bit) for bit in range(8) if marks & (128 >> bit))
                x += count
                pos += count
            else:
                raise ValueError(f'unsupported escape command at {pos - 2}')
        else:
            raise ValueError(f'unsupported IBM print byte at {pos - 1}')
    raise ValueError('expected a final form-feed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    with args.source.open('rb') as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    pixels, bands = decode(data)
    print(json.dumps({
        'sha256': sha256(data).hexdigest(), 'size': len(data),
        'dots': len(pixels), 'bands': bands,
        'bounds': [func(point[axis] for point in pixels) for func in (min, max) for axis in (0, 1)]
        if pixels else None,
    }, indent=2))
