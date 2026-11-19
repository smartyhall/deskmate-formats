"""Author isolated line and brush FIG candidates for the private RSX lab."""
import argparse
from pathlib import Path

from deskmate_formats.draw import parse_file
from draw_suite_candidates import encode, line, path


LINE_VECTORS = {
    'LINEX': (600, 0), 'LINEY': (0, 600),
    'LINESP': (600, 240), 'LINESN': (600, -240),
    'LINETP': (265, 600), 'LINETN': (-265, 600),
    'LINEDI': (650, 602), 'LINEFR': (600, 240),
}
BRUSH_VECTORS = {'BRUSHX': (600, 0), 'BRUSHY': (0, 600), 'BRUSHD': (550, 400)}
BRUSH_WIDTHS = (0, 1, 2, 3, 16, 17, 18, 19)


def endpoints(column, row, vector, *, reverse=False, fractional=False):
    x, y = 100 + 975 * column, 600 + 1040 * row
    if fractional:
        x += .75
        y += .5
    dx, dy = vector
    a, b = (x + max(0, -dx), y + max(0, -dy)), (x + max(0, dx), y + max(0, dy))
    return (b, a) if reverse else (a, b)


def candidates(template):
    for name, vector in LINE_VECTORS.items():
        controls = [
            line(*a, *b, style=style, weight=weight)
            for weight in range(4) for style in range(8)
            for a, b in (endpoints(style, weight, vector, fractional=name == 'LINEFR'),)
        ]
        yield name + '.FIG', encode(template, controls)
        if name in ('LINESP', 'LINETP', 'LINEDI'):
            controls = [
                line(*a, *b, style=style, weight=weight)
                for weight in range(4) for style in range(8)
                for a, b in (endpoints(style, weight, vector, reverse=True),)
            ]
            yield name + 'R.FIG', encode(template, controls)
    for name, vector in BRUSH_VECTORS.items():
        controls = [
            path((a, b), style=style, weight=width)
            for row, (style, reverse) in enumerate(((0, False), (1, False), (0, True), (1, True)))
            for col, width in enumerate(BRUSH_WIDTHS)
            for a, b in (endpoints(col, row, vector, reverse=reverse),)
        ]
        yield name + '.FIG', encode(template, controls)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('template', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    for name, content in candidates(parse_file(args.template)):
        with (args.destination / name).open('xb') as output:
            output.write(content)
