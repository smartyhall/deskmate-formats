"""Read-only binary comparisons and explicitly requested candidate index probes.

This is an investigation tool, not a database recognizer. Offsets/counts come
from the caller. JSON may expose proprietary bytes: save results privately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from deskmate_formats.calendar.personal import PAGE_SIZE, INDEX_HEADER


def _span(data: bytes, offset: int, length: int) -> bytes:
    if offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError('requested region is outside the input')
    return data[offset:offset + length]


def compare_regions(left: bytes, right: bytes, left_offset: int,
                    right_offset: int, length: int) -> dict:
    """Compare fixed regions; never heuristically align repetitive padding."""
    a = _span(left, left_offset, length)
    b = _span(right, right_offset, length)
    runs = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            if runs and runs[-1]['end_relative'] == i:
                runs[-1]['end_relative'] = i + 1
            else:
                runs.append({'start_relative': i, 'end_relative': i + 1})
    for run in runs:
        start, end = run['start_relative'], run['end_relative']
        run.update(left_offset=left_offset + start,
                   right_offset=right_offset + start,
                   left_hex=a[start:end].hex(), right_hex=b[start:end].hex())
    return {'left_offset': left_offset, 'right_offset': right_offset,
            'length': length, 'equal': a == b,
            'equal_bytes': length - sum(r['end_relative'] - r['start_relative'] for r in runs),
            'left_sha256': hashlib.sha256(a).hexdigest(),
            'right_sha256': hashlib.sha256(b).hexdigest(),
            'differences': runs, 'range_convention': 'end exclusive'}


def inspect_triples(data: bytes, offset: int, count: int,
                    page_size: int = PAGE_SIZE) -> dict:
    """Probe LE16 triples without claiming they are indexes or decoding rows.

    A zero tuple is reported as such and does not stop inspection. A matching
    80/low-ID prefix is evidence only for the tested one-byte ID range.
    """
    if page_size <= 0 or count < 0:
        raise ValueError('page size must be positive and count nonnegative')
    _span(data, offset, count * 6)
    entries = []
    for slot in range(offset, offset + count * 6, 6):
        page, within, rid = struct.unpack_from('<HHH', data, slot)
        target = page * page_size + within
        bounded = within < page_size and target + 2 <= len(data)
        prefix = data[target:target + 2] if bounded else b''
        entries.append({'slot': slot, 'raw_hex': data[slot:slot + 6].hex(),
                        'page_candidate': page, 'offset_candidate': within,
                        'id_candidate': rid, 'target': target,
                        'zero_tuple': page == within == rid == 0,
                        'target_in_bounds': bounded, 'prefix_hex': prefix.hex(),
                        'low_id_prefix_matches': prefix == bytes((0x80, rid))
                        if bounded and 0x10 <= rid < 0x80 else None})
    return {'page_size_assumption': page_size, 'entries': entries,
            'scope': 'candidate arithmetic only; no row or ID codec validation'}


def block_map(data: bytes, block_size: int = PAGE_SIZE) -> list[dict]:
    if block_size <= 0:
        raise ValueError('block size must be positive')
    result = []
    for offset in range(0, len(data), block_size):
        b = data[offset:offset + block_size]
        result.append({'offset': offset, 'length': len(b),
                       'sha256': hashlib.sha256(b).hexdigest(),
                       'nonzero_bytes': sum(x != 0 for x in b),
                       'calendar_index_header_matches': b.startswith(INDEX_HEADER)})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    number = lambda s: int(s, 0)
    p = sub.add_parser('compare')
    p.add_argument('left', type=Path)
    p.add_argument('right', type=Path)
    p.add_argument('--left-offset', type=number, required=True)
    p.add_argument('--right-offset', type=number, required=True)
    p.add_argument('--length', type=number, required=True)
    p = sub.add_parser('triples')
    p.add_argument('file', type=Path)
    p.add_argument('--offset', type=number, required=True)
    p.add_argument('--count', type=number, required=True)
    p.add_argument('--page-size', type=number, default=PAGE_SIZE)
    p = sub.add_parser('blocks')
    p.add_argument('file', type=Path)
    p.add_argument('--block-size', type=number, default=PAGE_SIZE)
    args = parser.parse_args(argv)
    try:
        if args.command == 'compare':
            a, b = args.left.read_bytes(), args.right.read_bytes()
            result = compare_regions(a, b, args.left_offset, args.right_offset, args.length)
            sources = [a, b]
        else:
            data = args.file.read_bytes()
            sources = [data]
            result = (inspect_triples(data, args.offset, args.count, args.page_size)
                      if args.command == 'triples' else block_map(data, args.block_size))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'inputs': [{'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
                                for b in sources], 'result': result}, indent=2))


if __name__ == '__main__':
    main()
