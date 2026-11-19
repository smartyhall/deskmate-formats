"""Generate bounded native-oracle controls for arcs and fill-pattern origins."""
import argparse
from dataclasses import replace
from pathlib import Path
from struct import pack_into

from deskmate_formats import draw

from draw_suite_candidates import arc, encode, line, shape


def arc_controls():
    return [
        arc((400, 500, 1800, 800), (0, 300, 1400, 300, 700, 0), 2),
        arc((2050, 500, 3450, 800), (1400, 300, 0, 300, 700, 0), 2),
        arc((3700, 500, 5250, 1300), (0, 800, 1550, 800, 775, 0), 2),
        arc((5750, 500, 7350, 1750), (0, 1250, 1600, 1250, 800, 0), 2),
        arc((400, 1550, 1850, 2450), (0, 900, 1450, 900, 390, 0), 10),
        arc((2200, 1560, 3650, 2460), (1450, 900, 0, 900, 390, 0), 10),
        arc((4100, 1600, 5650, 2950), (0, 1350, 1550, 350, 625, 0), 10),
        arc((5950, 2000, 7500, 3350), (1550, 350, 0, 1350, 625, 0), 10),
        replace(arc((400, 3200, 2200, 3700), (0, 500, 1800, 500, 900, 0), 13),
                bounds=(400, 3000, 2200, 4450)),
        replace(arc((2800, 3200, 4600, 3700), (0, 500, 1800, 500, 900, 0), 13),
                bounds=(2800, 4450, 4600, 3000)),
        arc((5300, 3630, 7200, 4500), (0, 870, 1900, 870, 950, 870), 13),
    ]


def pattern_controls():
    return [
        shape('R', (x, y, x + 560, y + 650), color=2, fill=10, pattern=pattern, background=3)
        for copy in range(2)
        for pattern in range(16)
        for x, y in [(460 + 905 * (pattern % 8) + 37 * copy, 460 + 905 * (pattern // 8 + 2 * copy) + 29 * copy)]
    ]


def main(base, arc_save, destination):
    base = draw.parse_file(base)
    saved = arc_save.read_bytes()
    drawing = draw.parse_bytes(saved)
    first, next_record = drawing.form.elements
    if first.kind != 'UA' or next_record.kind != 'L' or next_record.offset - first.offset != 44:
        raise ValueError('native arc followed by a distinct line is required')
    position = 44 + first.offset + 18
    if saved[position:position+2] != b'\x16\0':
        raise ValueError('native arc must declare 22 words')
    bad_arc = bytearray(saved)
    pack_into('<H', bad_arc, position, 23)
    data = {
        'ARCSTUD.FIG': encode(base, arc_controls()),
        'PATSTUD.FIG': encode(base, pattern_controls()),
        'ARCBAD.FIG': bad_arc,
        'ARCGOOD.FIG': saved,
        'LINECTRL.FIG': encode(base, [line(1200, 1400, 5425, 1400, 10)]),
    }
    for name, contents in data.items():
        with (destination / name).open('xb') as output:
            output.write(contents)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('template', type=Path)
    parser.add_argument('arc_save', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    main(args.template, args.arc_save, args.destination)
