"""Reproduce the Draw byte-to-FF1-slot experiment using a disposable machine."""
import argparse
from itertools import groupby
import json
from pathlib import Path

from deskmate_formats.draw_writer import add_outline_text, new_outline_drawing
from deskmate_formats.ff1 import Glyph, create_resource, dixon_slot, outline_bounds, serialize_resource
from deskmate_formats.ff1_geometric import rectangle
from deskmate_formats.font_resources import GlyphOutline, OutlineFace, parse_glyph_index
from draw_floppy import data_floppy


CODES = (65, 69, 72, 73, 79, 90, 32, *range(128, 256))
POINTS = 29


def origin(position):
    return 165 + position % 15 * 520, 525 + position // 15 * 475


def prepare(output):
    glyphs = []
    for code in range(32, 256):
        contours = (rectangle(0, -480, 78, 0), *(
            rectangle(125 + 120*i, -480, 203 + 120*i, 0) for i in range(8) if code & (1 << i)))
        glyphs.append(Glyph(1100, GlyphOutline(outline_bounds(contours), contours, b'')))
    data = serialize_resource(dixon_slot(create_resource('Dixon', glyphs)))
    index = parse_glyph_index(data)
    # Retain the candidate cache generated before the Draw translation was known.
    # An otherwise identical index with nominal raw-slot lookup supplies that cache.
    class PhysicalSlotFace(OutlineFace):
        draw_entry = OutlineFace.entry

    face = PhysicalSlotFace('Dixon', '', index, data)
    fig = new_outline_drawing(face, 'A', origin(0), point_size=POINTS)
    for position, code in enumerate(CODES[1:], 1):
        label = bytes([code]).decode('cp437')
        fig = add_outline_text(fig, face, label, origin(position), point_size=POINTS)
    for name, contents in [('SLOTMAP.FF1', data), ('SLOTMAP.FIG', fig),
                           ('charset-probe.img', data_floppy({'SLOTMAP.FIL': data, 'SLOTMAP.FIG': fig}))]:
        with (output / name).open('xb') as target:
            target.write(contents)


def read_marks(frame):
    from PIL import Image

    with Image.open(frame) as source:
        if source.size != (640, 480):
            raise ValueError('expected the RSX full framebuffer')
        image = source.convert('RGB')
    result = {}
    for position, code in enumerate(CODES):
        x, y = origin(position)
        row = round(62 + y * 19 / 220 - 8)
        xs = [column for column in range(round(x * .08) - 2, round(x * .08 + 37))
              if image.getpixel((column, row))[0]]
        spans = [[item[1] for item in group] for _, group in
                 groupby(enumerate(xs), lambda item: item[1] - item[0])]
        if not spans:
            raise ValueError(f'no marker at byte {code:#04x}')
        centers = [sum(span) / len(span) for span in spans]
        bits = [round((center - centers[0]) / (POINTS * .08 * 120 / 72)) - 1 for center in centers[1:]]
        if len(set(bits)) != len(bits) or any(i not in range(8) for i in bits):
            raise ValueError(f'ambiguous markers at byte {code:#04x}')
        result[code] = sum(1 << i for i in bits)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--prepare', type=Path)
    choice.add_argument('--decode', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare)
    else:
        print(json.dumps(read_marks(args.decode), indent=2))
