"""Generate the five native-tested flat Draw writer candidates."""
import argparse
from pathlib import Path

from deskmate_formats import draw_writer


def fixed(*values):
    return tuple(int(value * 65536) for value in values)


def generate(fixtures):
    line = (fixtures / 'd01.fig').read_bytes()
    rectangle = (fixtures / 'd04.fig').read_bytes()
    ellipse = draw_writer.add_ellipse(rectangle, fixed(1080.5, 1240.25, 3500, 2720), color=2, fill=4)
    path = draw_writer.add_polyline(line, [(1100, 1600), (1800, 1900), (1350, 2400), (2400, 2750)], color=10)
    return {
        'ADDLINE': draw_writer.add_line(line, fixed(600.25, 1600, 2300.5, 2950), color=10),
        'ADDELL': ellipse,
        'ADDPATH': draw_writer.add_polyline(path, [(2800, 1550), (3650, 1825), (3480, 2600), (2550, 2430)],
                                           color=2, closed=True, fill=13),
        'DELETE': draw_writer.delete(ellipse, 1),
        'ORDER': draw_writer.reorder(ellipse, [2, 1]),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    for name, contents in generate(args.fixtures).items():
        with (args.destination / f'{name}.FIG').open('xb') as file:
            file.write(contents)
