"""Inspect candidate pair adjustments in a local FF1 resource."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from deskmate_formats.font_resources import MAX_SIZE, parse_glyph_index


def probe(data, labels):
    index = parse_glyph_index(data)
    last = index.entries[-1]
    glyph_end = last.offset + last.size
    pointer, = unpack_from('<I', data, 38)
    result = {'sha256': sha256(data).hexdigest(), 'glyph_end': glyph_end, 'outer_pointer_38': pointer,
              'tail_bytes': len(data) - glyph_end}
    if pointer == 0 and glyph_end == len(data):
        return result
    if pointer != glyph_end or len(data) - pointer < 10:
        raise ValueError('unrecognized FF1 trailing section boundary')
    header = unpack_from('<5H', data, pointer)
    marker, size, field_4, field_6, count = header
    if (marker, field_4, field_6) != (1, 255, 300) or size != len(data) - pointer or size != 10 + 4 * count:
        raise ValueError('unrecognized candidate pair table header')
    rows = tuple(iter_unpack('<BBh', data[pointer + 10:]))
    keys = [row[:2] for row in rows]
    if not rows or any(a >= b for a, b in zip(keys, keys[1:])):
        raise ValueError('candidate pairs must be unique and sorted')
    pairs = {(left, right): value for left, right, value in rows}
    advances = {entry.code: entry.advance_word for entry in index.entries}
    result.update(header=header, pair_count=count, value_range=[min(pairs.values()), max(pairs.values())],
                  probes={})
    for label in labels:
        codes = label.encode('ascii')
        if any(code not in advances for code in codes):
            raise ValueError('probe label contains a code outside the glyph index')
        matches = [[bytes((a, b)).decode('ascii'), pairs[a, b]]
                   for a, b in zip(codes, codes[1:]) if (a, b) in pairs]
        result['probes'][label] = {'nominal_advance_sum': sum(advances[code] for code in codes),
                                  'candidate_pair_adjustments': matches}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resource', type=Path)
    parser.add_argument('labels', nargs='*')
    args = parser.parse_args()
    with args.resource.open('rb') as source:
        data = source.read(MAX_SIZE + 1)
    print(json.dumps(probe(data, args.labels), indent=2))
