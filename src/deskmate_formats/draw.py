"""Inspect or preview native DeskMate 3.05 Draw FIG files."""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from struct import unpack_from
import sys

from . import graphics


PAGE_SETUP_SIZE = 22
PALETTE_SIZE = 64
MAX_BYTES = PAGE_SETUP_SIZE + graphics.MAX_BYTES + PALETTE_SIZE + 3


@dataclass(frozen=True)
class Drawing:
    page_setup: bytes
    form: graphics.Form
    palette_offset: int
    palette: tuple[tuple[int, int, int, int], ...]
    trailer: bytes


def parse_bytes(source):
    """Read the measured 0x14 FIG profile, retaining all serialized sections."""
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise graphics.GraphicsFormatError('expected a byte snapshot')
    if not 113 <= memoryview(source).nbytes <= MAX_BYTES:
        raise graphics.GraphicsFormatError('invalid FIG file size')
    data = bytes(source)
    if data[:4] != b'\x14FIG':
        raise graphics.GraphicsFormatError('unsupported FIG signature')
    form_offset = PAGE_SETUP_SIZE + graphics.PREFIX_SIZE
    list_bytes, stroke_bytes = unpack_from('<HH', data, form_offset - 4)
    form_end = form_offset + list_bytes + stroke_bytes
    palette_offset = form_end + 2
    palette_end = palette_offset + PALETTE_SIZE
    if len(data) != palette_end + 1 or data[form_end:palette_offset] != b'\x10\x00':
        raise graphics.GraphicsFormatError('inconsistent FIG form or palette extent')
    palette = tuple(unpack_from('<4B', data, i) for i in range(palette_offset, palette_end, 4))
    if {entry[0] for entry in palette} != set(range(16)):
        raise graphics.GraphicsFormatError('invalid FIG palette indices')
    form = graphics.parse_bytes(data[PAGE_SETUP_SIZE:form_end])
    return Drawing(data[:PAGE_SETUP_SIZE], form, palette_offset, palette, data[palette_end:])


def parse_file(path):
    with Path(path).open('rb') as handle:
        return parse_bytes(handle.read(MAX_BYTES + 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--svg', action='store_true', help='write an SVG geometry preview to stdout')
    args = parser.parse_args(argv)
    try:
        drawing = parse_file(args.source)
        if args.svg:
            sys.stdout.write(graphics.render_svg(drawing.form, drawing.palette))
        else:
            print(json.dumps(asdict(drawing), default=bytes.hex, indent=2))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
