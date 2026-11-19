"""Author the four original Draw baseline candidates and a viewport control."""
import argparse
from dataclasses import dataclass
from pathlib import Path
from struct import pack, pack_into

from deskmate_formats import draw


@dataclass(frozen=True)
class Record:
    code: bytes
    bounds: tuple
    tail: bytes
    children: tuple = ()


def line(x0, y0, x1, y1, color=1, style=0, weight=0):
    return Record(bytes((76, style)), (x0, y0, x1, y1), bytes((color, weight)))


def shape(code, bounds, color=1, fill=1, pattern=254, style=0, weight=0, background=0):
    return Record(bytes((ord(code), pattern)), bounds, bytes((color, weight, style, background, fill, 0)))


def path(points, color=1, *, closed=False, pattern=254, fill=1, style=0, weight=0):
    xs, ys = zip(*points)
    x, y = min(xs), min(ys)
    bounds = (x, y, max(xs), max(ys))
    attrs = bytes((color, color, style, weight, pattern, 0, fill, 0))
    flag = 255 if closed else 0
    data = b''.join(pack('<HH', px - x, py - y) for px, py in points)
    tail = attrs + pack('<HHBBH', max(xs) - x, max(ys) - y,
                       flag if pattern != 254 else 0, flag, len(points)) + data
    return Record(b'UP', bounds, pack('<H', 10 + len(tail) // 2) + tail)


def arc(bounds, points, color=1):
    x0, y0, x1, y1 = bounds
    return Record(b'UA', bounds, pack('<H8B8H', 22, color, color, 0, 0, 254, 0, color, 0,
                                      x1 - x0, y1 - y0, *points))


def group(*children):
    xs = [n for child in children for n in child.bounds[::2]]
    ys = [n for child in children for n in child.bounds[1::2]]
    return Record(b'OO', (min(xs), min(ys), max(xs) + 1, max(ys) + 1), b'', children)


def text(template, label, bounds, color):
    payload = bytearray(template.raw[18:100])
    payload[2] = color
    data = label.encode('ascii')
    pack_into('<H', payload, 78, len(data))
    payload.extend(data + b'\0')
    if len(payload) % 2:
        payload.append(0)
    pack_into('<H', payload, 0, 9 + len(payload) // 2)
    return Record(b'Uf', bounds, bytes(payload))


def encode(template, roots):
    listing = bytearray(2 + 4 * len(roots))
    pack_into('<H', listing, 0, len(roots))

    def append(record):
        offset = len(listing)
        listing.extend(record.code)
        for value in record.bounds:
            fixed = round(value * 65536)
            listing.extend(pack('<hH', fixed // 65536, fixed % 65536))
        listing.extend(record.tail)
        if record.children:
            listing.extend(pack('<H', len(record.children)) + bytes(2 * len(record.children)))
            for index in reversed(range(len(record.children))):
                child_offset = append(record.children[index])
                pack_into('<H', listing, offset + 20 + index * 2, child_offset // 2)
        return offset

    for index in reversed(range(len(roots))):
        offset = append(roots[index])
        pack_into('<HH', listing, 2 + 4 * index, offset // 2, index + 1)
    header = bytearray(template.form.header)
    pack_into('<5H', header, 2, len(listing) // 2, 2, len(roots) + 1, 2 * len(roots) + 1, 1)
    pack_into('<H', header, 16, int.from_bytes(header[14:16], 'little') + len(listing))
    palette = bytes(channel for entry in template.palette for channel in entry)
    return (template.page_setup + header + pack('<HH', len(listing), 2) + listing
            + b'\0\0\x10\0' + palette + template.trailer)


def viewport():
    return [
        line(-200, 300, 925, 300, 10),
        line(400, -200, 400, 800, 4),
        line(800, 985, 1200, 985, 1),
        line(1250, 730, 1750, 730, 2),
        line(1263, 780, 1763, 780, 6),
        line(2000.25, 1000.25, 2000.25, 2500.25, 13),
        line(4000.75, 1000.75, 4000.75, 3000.75, 12),
        line(6000, 1000, 6000, 4000, 14),
        line(1200, 4000, 3800, 4000, 11),
        line(7500, 200, 8500, 200, 3),
    ]


def primitives():
    objects = []
    for idx in range(8):
        x = 500 + 875 * idx
        objects.append(line(x, 325, x + 650, 325, 2, idx, idx % 4))
        objects.append(line(x, 480, x + 500, 815, 1, idx))
        objects.append(line(x + 650, 490, x + 650, 830, 10, idx))
        for row in range(2):
            y = 1120 + row * 725
            objects.append(shape('RE'[row], (x, y, x + 690, y + 550),
                                 color=2, fill=10 + idx % 4, pattern=idx + 1))
    objects.extend([
        shape('R', (500, 2710, 1750, 3500), color=2),
        shape('E', (950, 2880, 2010, 3720), color=13, fill=13, pattern=9),
        path([(2300, 3700), (2300, 2710), (3230, 3420), (3470, 2830)], 10, style=1),
        path([(3710, 3020), (4210, 2710), (4820, 2890), (4620, 3550), (3940, 3490)],
             2, closed=True, pattern=9, fill=4),
        arc((5110, 2670, 6160, 3360), (0, 690, 1050, 690, 525, 0)),
        arc((6400, 2850, 7440, 3350), (0, 500, 1040, 500, 520, 0), 10),
        line(-200, 4200, 1400, 4200, 10),
    ])
    for idx in range(16):
        x = 500 + idx * 435
        objects.append(shape('R', (x, 4050, x + 365, 4450), color=2, fill=idx, pattern=1))
    return objects


def technical(font):
    objects = [shape('R', (950, 1050, 6810, 3910)), shape('R', (1025, 1125, 6735, 3835)),
               line(3660.5, 1125, 3660.5, 2560), line(3735.5, 1125, 3735.5, 2560),
               line(3660.5, 3260, 3660.5, 3835), line(3735.5, 3260, 3735.5, 3835),
               line(1025, 2560, 2450, 2560), line(3100, 2560, 3660, 2560),
               line(1025, 2635, 2450, 2635), line(3100, 2635, 3660, 2635),
               line(3736, 3260, 4436, 3260, 4),
               arc((3736, 2560, 4436, 3260), (0, 0, 700, 700, 495, 205), 4),
               line(2450, 2560, 2450, 1910, 4),
               arc((2450, 1910, 3100, 2560), (0, 0, 650, 650, 460, 190), 4)]
    for x in (1400, 4550, 5500):
        objects.extend([shape('R', (x, 1030, x + 750, 1145), 10, 0, 1),
                        line(x, 1087, x + 750, 1087, 10)])
    for x in (950, 3660, 6810):
        objects += [line(x, 3910, x, 4340, 2), line(x - 45, 4290, x + 45, 4200, 2)]
    objects.append(line(950, 4245, 6810, 4245, 2))
    objects += [shape('R', (5150, 1570, 6400, 2080), 10),
                shape('R', (5320, 1660, 6230, 1970), 10)]
    for label, bounds in [
        ('CEDAR WORKSHOP', (960, 425, 3840, 780)), ('STORE', (1390, 1500, 2270, 1800)),
        ('STUDIO', (1240, 3000, 2240, 3290)), ('BENCH BAY', (4570, 2850, 6100, 3140)),
        ('4.0 M', (1800, 4350, 2530, 4600)), ('4.6 M', (4790, 4350, 5520, 4600)),
    ]:
        objects.append(text(font, label, bounds, 2))
    return objects


def landscape():
    objects = [shape('E', (6070, 440, 7070, 1410), 1, 1, 1),
               path([(320, 2590), (1630, 850), (2500, 2080), (3650, 650),
                     (5360, 2640), (7260, 1980), (7460, 4200), (320, 4200)],
                    4, closed=True, pattern=9, fill=4),
               path([(330, 2910), (2150, 2480), (3900, 2920), (5400, 2360),
                     (7460, 2530), (7460, 4390), (330, 4390)], 10, closed=True, pattern=1, fill=14),
               path([(4000, 3680), (5530, 3000), (7440, 2850), (7440, 4470),
                     (2820, 4470)], 4, closed=True, pattern=1, fill=4)]
    for idx in range(5):
        objects.append(line(4320 + 360 * idx, 3400 + 145 * idx, 7110 - 86 * idx, 3400 + 145 * idx, 2))
    windows = group(shape('R', (1920, 2630, 2360, 3100), 2, 4, 1),
                    line(2140, 2630, 2140, 3100, 2), line(1920, 2865, 2360, 2865, 2),
                    shape('R', (3260, 2630, 3670, 3100), 2, 4, 1),
                    line(3470, 2630, 3470, 3100, 2), line(3260, 2865, 3670, 2865, 2))
    objects.append(group(shape('R', (1600, 2230, 3970, 3670), 1, 12, 1),
                         path([(1420, 2340), (2740, 1470), (4160, 2340)], 1,
                              closed=True, pattern=9, fill=6),
                         windows, shape('R', (2540, 2750, 3040, 3670), 1, 3, 1)))
    for x, y, scale in [(800, 3740, 1), (1180, 3980, 0.7), (4690, 2860, 0.65), (5320, 2870, 0.8)]:
        w, h = int(370 * scale), int(950 * scale)
        objects.extend([line(x, y - 180, x, y, 12, weight=2),
                        path([(x - w, y - 180), (x, y - h), (x + w, y - 180)],
                             10, closed=True, pattern=1, fill=14)])
    return objects


def typography(font):
    labels = [
        ('DRAW LETTER STUDY', 600, 560, 3900, 460, 1),
        ('ABCDEFGHIJKLM', 620, 1390, 4800, 350, 2),
        ('NOPQRSTUVWXYZ', 620, 1970, 4800, 350, 10),
        ('0123456789', 620, 2550, 2600, 350, 4),
        ('CLOSE SPACING', 620, 3220, 2100, 290, 13),
        ('WIDE TRACK', 620, 3750, 4150, 410, 1),
    ]
    objects = []
    for label, x, y, width, height, color in labels:
        objects.extend([text(font, label, (x, y, x + width, y + height), color),
                        line(x, y + height + 40, x + width, y + height + 40, 7)])
    return objects


def generate(fixtures, destination):
    base = draw.parse_file(fixtures / 'd01.fig')
    font, = draw.parse_file(fixtures / 'd23.fig').form.elements
    cases = {'PRIM2': primitives(), 'PLAN2': technical(font), 'LAND2': landscape(),
             'TYPE2': typography(font), 'MAP': viewport()}
    for name, objects in cases.items():
        data = encode(base, objects)
        assert len(tuple(draw.parse_bytes(data).form.draw_order())) >= len(objects)
        with (destination / f'{name}.FIG').open('xb') as output:
            output.write(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    generate(args.fixtures, args.destination)
