"""Inspect captured DeskMate IBM Graphic one-page raster streams."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from


DRAW_PROLOGUE = bytes.fromhex('12 1b3500 1b2d00 1b46')
CARD_PROLOGUE = bytes.fromhex(
    '1b7200 12 1b4900 1b3500 1b4f 1b5801ff 1b4342 12 1b4900 1b2d00 1b46'
)
MAX_BYTES = 2 * 1024 * 1024


def decode(data):
    """Return one page of 120 dpi by 72 dpi dots and a band inventory."""
    profile = next((p for p in (DRAW_PROLOGUE, CARD_PROLOGUE) if data.startswith(p)), None)
    if len(data) > MAX_BYTES or profile is None:
        raise ValueError('unsupported DeskMate IBM Graphic prologue or size')
    width, height = (1020, 792) if profile == CARD_PROLOGUE else (2048, 1208)
    pos, x, vertical = len(profile), 0, 0
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
            if profile == CARD_PROLOGUE and not bands:
                raise ValueError('expected at least one card graphics band')
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
                if not 0 < count <= len(data) - pos or vertical % 3 or x + count > width or vertical // 3 + 8 > height:
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


def render_letter_pdf(pixels, destination):
    """Write decoded dot centers on Letter with an illustrative dot radius."""
    from reportlab.pdfgen import canvas

    page = canvas.Canvas(str(destination), pagesize=(612, 792), invariant=1)
    page.setTitle('DeskMate IBM Graphic raster reconstruction')
    for x, y in sorted(pixels):
        page.circle(x * 0.6, 792 - y, 0.32, stroke=0, fill=1)
    page.showPage()
    page.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--pdf', type=Path, help='reconstruct a Letter card PDF (requires ReportLab)')
    args = parser.parse_args()
    with args.source.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    pixels, bands = decode(data)
    if args.pdf is not None:
        if args.pdf.resolve() == args.source.resolve():
            parser.error('PDF destination must differ from the source stream')
        if not data.startswith(CARD_PROLOGUE):
            parser.error('PDF geometry is qualified only for the Letter card profile')
        render_letter_pdf(pixels, args.pdf)
    print(json.dumps({
        'sha256': sha256(data).hexdigest(), 'size': len(data),
        'dots': len(pixels), 'bands': bands,
        'bounds': [func(point[axis] for point in pixels) for func in (min, max) for axis in (0, 1)]
        if pixels else None,
    }, indent=2))
