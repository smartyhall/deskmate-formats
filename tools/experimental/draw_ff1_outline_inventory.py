"""Summarize a local FF1 outline corpus without exporting glyph geometry."""
import argparse
from collections import Counter
import json
from pathlib import Path
from struct import unpack_from

from deskmate_formats.font_resources import MAX_SIZE, parse_bytes, parse_glyph_index, parse_glyph_outline


def inventory(data):
    resource = parse_bytes(data)
    index = parse_glyph_index(data)
    moves = lines = cubics = empty = bounds_matches = 0
    topology = Counter()
    auxiliary = Counter()
    for entry in index.entries:
        outline = parse_glyph_outline(data, entry)
        empty += not outline.contours
        moves += len(outline.contours)
        topology[len(outline.contours)] += 1
        points = []
        for contour in outline.contours:
            points.append(contour.start)
            for segment in contour.segments:
                lines += len(segment) == 1
                cubics += len(segment) == 3
                points.extend(segment)
        if points:
            x, y = zip(*points)
            bounds_matches += outline.bounds == (min(x), min(y), max(x), max(y))
        tail = outline.auxiliary
        if len(tail) >= 6:
            marker, first_count, second_count = unpack_from('<3H', tail)
            label = 'marker-2-six-byte-rows' if marker == 2 and len(tail) == 6 * (1 + first_count + second_count) else 'other'
        else:
            label = 'other' if tail else 'absent'
        auxiliary[label] += 1
    return dict(family=resource.variants[0].name, sha256=resource.sha256,
                glyph_records=len(index.entries), units_per_em_word=index.units_per_em_word,
                moves=moves, lines=lines, cubic_commands=cubics, empty_streams=empty,
                nonempty_control_bounds_matches=bounds_matches,
                contour_counts=dict(sorted(topology.items())), auxiliary_profiles=dict(sorted(auxiliary.items())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resources', nargs='+', type=Path)
    results = []
    for path in parser.parse_args().resources:
        with path.open('rb') as handle:
            results.append(inventory(handle.read(MAX_SIZE + 1)))
    print(json.dumps(results, indent=2))
