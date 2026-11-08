"""Independent raw-byte oracle for the E02-only experimental new-file builder.

No production parser, writer, map codec or date/time codec imports. Inputs are
bounded; output is JSON on stdout. Success is offline consistency, not native
acceptance. Expected JSON contains an 'additions' array in physical input order.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(source, data, additions):
    require(len(source) == 6144 and hashlib.sha256(source).hexdigest() ==
            '0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9', 'source identity')
    require(len(data) in (6144, 7168, 8192), 'file size')
    require(type(additions) is list and 1 <= len(additions) <= 100, 'expected additions')
    require(data[:32] == source[:32], 'opaque header prefix')
    pages = len(data) // 1024
    # Independent bitstream model, rather than the writer's byte/nibble setter.
    links = [4088] * 6 + [4095] + [0] * 654
    if pages > 6:
        links[4], links[6], links[7] = 6, 4088, 4095
    if pages > 7:
        links[6], links[7], links[8] = 7, 4088, 4095
    expected_map = int(''.join(format(n, '012b') for n in links) + '0000', 2).to_bytes(992, 'big')
    require(data[32:1024] == expected_map, 'page chain/map or adjacent bits')
    directory = bytearray(data[1024:2048])
    directory[0x35:0x3A] = source[0x435:0x43A]
    directory[0x3F:0x44] = source[0x43F:0x444]
    require(directory == source[1024:2048], 'unrelated directory bytes')
    require(data[2048:4096] == source[2048:4096], 'schema preservation')
    require(data[5120:5160] == source[5120:5160], 'index header preservation')
    count = len(additions) + 2
    require(count <= 112, 'low ID bound')
    require(data[0x435:0x43A] == f'{count:05d}'.encode(), 'record counter')
    require(data[0x43F:0x444] == f'{count + 16:05d}'.encode(), 'next ID counter')
    require(data[5160 + 6 * count:6144] == bytes(984 - 6 * count), 'index sentinel/tail')
    triples = [struct.unpack_from('<HHH', data, 5160 + 6 * n) for n in range(count)]
    require(len({t[2] for t in triples}) == count, 'duplicate IDs')
    require(len({t[:2] for t in triples}) == count, 'duplicate pointers')
    require(triples[0] == (4, 0, 16), 'control first')
    physical = []
    lengths = {}
    # Walk all supported data pages physically; discover rows independently of
    # index targets and require a unique page-local 03 followed only by zeros.
    for page in [4] + list(range(6, pages)):
        cursor, limit = page * 1024, (page + 1) * 1024
        require(data[cursor] == 128, 'empty/unneeded data page')
        while cursor < limit and data[cursor] != 3:
            require(data[cursor] == 128 and cursor + 2 < limit, 'row prefix/bounds')
            end = data.find(b'\x01\x02', cursor + 2, limit)
            require(end >= 0, 'row terminator')
            require(data[cursor + 1] == 16 + len(physical), 'physical sequential ID')
            fields = data[cursor + 2:end].split(b'\x01')
            require(len(fields) == 7, 'field count')
            physical.append((page, cursor % 1024, data[cursor + 1], fields))
            lengths[data[cursor + 1]] = end + 2 - cursor
            cursor = end + 2
        require(cursor < limit and data[cursor] == 3, 'page marker')
        require(data[cursor + 1:limit] == bytes(limit - cursor - 1), 'page tail')
    require(len(physical) == count, 'physical/index count')
    require({t[:3] for t in physical} == set(triples), 'index/physical correspondence')
    # Original rows are independently delimited in E02 and kept at their offsets.
    original_end = 4096
    for _ in range(2):
        original_end = source.index(b'\x01\x02', original_end + 2, 5120) + 2
    require(data[4096:original_end] == source[4096:original_end], 'original rows')
    prior = physical[1]
    logical_keys = {17: (prior[3][0], prior[3][3])}
    for n, item in enumerate(additions, 18):
        require(type(item) is dict and set(item) ==
                {'date', 'start_minutes', 'end_minutes', 'description', 'alarm_enabled'}, 'expected event keys')
        day = date.fromisoformat(item['date'])
        start, end = item['start_minutes'], item['end_minutes']
        require(type(start) is int and type(end) is int and
                0 < start < end < 1440 and start % 15 == end % 15 == 0, 'ordinary time')
        text = item['description']
        require(type(text) is str and 1 <= len(text) <= 120 and
                all(32 <= ord(c) < 127 for c in text), 'ordinary description')
        require(type(item['alarm_enabled']) is bool, 'alarm type')
        expected = [bytes([day.year - 1980 + 97, day.month + 97, day.day + 97]),
                    bytes([((day.weekday() + 1) % 7) + 98]), b'',
                    bytes([128 | ((start // 60) << 2) | ((start % 60) // 15)]),
                    bytes([128 | ((end // 60) << 2) | ((end % 60) // 15)]),
                    b'q' if item['alarm_enabled'] else b'1', text.encode('ascii')]
        page, offset, rid, fields = physical[n - 16]
        require(fields == expected, 'expected raw fields')
        previous_page, previous_offset, previous_id, _ = physical[n - 17]
        previous_end = previous_offset + lengths[previous_id]
        # Independent exact-fit/shortage checks: no skipped usable tail or
        # premature page extension; match the source-derived two-byte headroom.
        fits = lengths[rid] + 2 <= 1023 - previous_end
        require((page == previous_page and offset == previous_end) if fits else
                (page == (6 if previous_page == 4 else previous_page + 1) and offset == 0),
                'physical append/space threshold')
        logical_keys[rid] = (fields[0], fields[3])
    ordered_keys = [logical_keys[rid] for _, _, rid in triples[1:]]
    require(ordered_keys == sorted(set(ordered_keys)), 'chronological unique index')
    return {'evidence_class': 'tool-generated; independently checked offline; native acceptance pending',
            'source_sha256': hashlib.sha256(source).hexdigest(),
            'output_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'pages': pages, 'appointments': count - 1,
            'distinct_dates': len({key[0] for key in ordered_keys}),
            'data_chain': [4] + list(range(6, pages)),
            'original_rows_preserved': True, 'unknown_source_bytes_preserved': True,
            'native_opened': False, 'native_saved': False}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('candidate', type=Path)
    cli.add_argument('expected', type=Path)
    args = cli.parse_args()
    with args.source.open('rb') as handle:
        source = handle.read(6145)
    with args.candidate.open('rb') as handle:
        data = handle.read(8193)
    with args.expected.open('rb') as handle:
        raw = handle.read(65537)
    require(len(raw) <= 65536, 'expected JSON size')
    print(json.dumps(check(source, data, json.loads(raw)['additions']), indent=2))


if __name__ == '__main__':
    main()
