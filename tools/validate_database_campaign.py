"""Independent fixed-profile experiment checker; imports no production codecs.

Checks the campaign's archived outputs and receipts, not arbitrary DeskMate files.
Supply an explicit private archive and empty ADR source. Prints derived metadata.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def table(data, name):
    marker = b'T\x01' + name.encode() + b'\x01'
    start = data.index(marker, 1024, 2048)
    end = data.index(b'\x01\x02', start, 2048)
    tokens = data[start:end].split(b'\x01')
    check(all(t.isdigit() for t in (tokens[2], tokens[3], tokens[4], tokens[6], tokens[7])), 'invalid decimal')
    return start, tokens


def rows_and_index(data, name):
    start, tokens = table(data, name)
    page, columns, count, next_id, index = (int(tokens[i]) for i in (2, 3, 4, 6, 7))
    cursor, rows = page * 1024, {}
    while cursor < (page + 1) * 1024 and data[cursor] != 3:
        check(data[cursor] == 128, 'unexpected live row prefix')
        end = data.index(b'\x01\x02', cursor + 2, (page + 1) * 1024) + 2
        values = data[cursor + 2:end - 2].split(b'\x01')
        check(len(values) == columns, 'wrong field count')
        check(data[cursor + 1] not in rows, 'duplicate physical ID')
        rows[data[cursor + 1]] = (cursor, end, values)
        cursor = end
    check(cursor < (page + 1) * 1024 and data[cursor] == 3, 'missing row marker')
    check(not any(data[cursor + 1:(page + 1) * 1024]), 'nonzero data tail')
    base = index * 1024
    check(data[base:base + 40] == (b'\xff' * 9 + b'\0') * 4, 'index header differs')
    triples = [struct.unpack_from('<HHH', data, base + 40 + n * 6) for n in range(count)]
    check(len(triples) == len(rows) and len({t[2] for t in triples}) == count, 'count/ID mismatch')
    for target, within, ident in triples:
        check(target == page and within < 1024 and ident in rows, 'invalid index target')
        check(target * 1024 + within == rows[ident][0], 'pointer disagrees with physical row')
    check(not any(data[base + 40 + 6 * count:base + 1024]), 'nonzero index tail')
    check(next_id == max(rows) + 1, 'next ID differs from this experiment profile')
    return start, tokens, rows, triples


def calendar(data, source, expected):
    check(len(data) == 6144 and data[:4] == b'\x03FIL', 'wrong Calendar profile')
    _, _, rows, triples = rows_and_index(data, 'PERSONAL')
    _, _, old, _ = rows_and_index(source, 'PERSONAL')
    check(len(rows) - 1 == expected['total_appointments'], 'appointment count differs')
    check(data[:1024] == source[:1024] and data[2048:4096] == source[2048:4096], 'header/schema changed')
    for ident, (start, end, _) in old.items():
        check(rows[ident][:2] == (start, end) and data[start:end] == source[start:end], 'old row modified/moved')
    keys, days = [], set()
    for _, _, ident in triples:
        _, _, values = rows[ident]
        if ident == 16:
            check(values[0] == b'  \xff' and values[5] == b'0', 'config signature differs')
            continue
        day = date(1980 + values[0][0] - 97, values[0][1] - 97, values[0][2] - 97)
        check(values[1] == bytes((98 + (day.weekday() + 1) % 7,)), 'weekday mismatch')
        # Use SDK hour/quarter bitfields independently of production's biased arithmetic.
        times = [((v[0] >> 2) & 31) * 60 + (v[0] & 3) * 15 for v in (values[3], values[4])]
        check(all(15 <= t <= 1425 for t in times) and times[0] < times[1], 'invalid ordinary time')
        check(values[2] == b'' and values[5] in (b'1', b'q'), 'nonordinary profile')
        check(1 <= len(values[6]) <= 120 and all(32 <= c <= 126 for c in values[6]), 'non-ASCII description')
        keys.append((day, times[0]))
        days.add(day)
    check(keys == sorted(set(keys)), 'chronological uniqueness failed')
    check(len(days) == expected['distinct_dates'], 'day count differs')
    check(digest(data) == expected['output_sha256'], 'Calendar receipt hash mismatch')
    return {'appointments': len(keys), 'distinct_dates': len(days), 'sha256': digest(data)}


def contact(data, source, expected):
    check(len(data) == 10240 and data[:4] == b'\x03\0\0\0', 'wrong ADR profile')
    start, tokens, rows, triples = rows_and_index(data, 'DATA')
    check(list(rows) == [16] and triples == [(4, 0, 16)], 'not observed one-contact index')
    begin, end, values = rows[16]
    check(len(values) == 16 and values[0] == values[3] == values[5] == values[6] == values[7] == b'', 'unexpected optional field')
    check(values[9:] == [b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n'], 'opaque defaults differ')
    check([values[i].decode('ascii') for i in (1, 2, 4, 8)] == [expected['contact'][k]
          for k in ('first_name', 'last_name', 'city', 'work_phone')], 'contact values differ')
    allowed = set(range(begin, end + 1)) | set(range(5160, 5166))
    for token in (4, 6):
        pos = start + sum(len(t) + 1 for t in tokens[:token])
        allowed.update(range(pos, pos + 5))
    check(all(a == b or n in allowed for n, (a, b) in enumerate(zip(source, data))), 'unrelated ADR bytes changed')
    check(digest(data) == expected['sha256'], 'ADR manifest hash mismatch')
    return {'name': expected['name'], 'contacts': 1, 'sha256': digest(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--calendar-source', type=Path, required=True)
    parser.add_argument('--addressbook-source', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.archive / 'calendar-14-days-receipt.json').read_text(encoding='utf-8'))
    baseline = args.addressbook_source.read_bytes()
    check(digest(baseline) == 'cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c', 'wrong ADR baseline')
    source = args.calendar_source.read_bytes()
    check(digest(source) == receipt['source_sha256'], 'wrong Calendar source')
    result = calendar((args.archive / 'calendar-14-days.cln').read_bytes(), source, receipt)
    manifest = json.loads((args.archive / 'contacts-25/manifest.json').read_text(encoding='utf-8'))
    check(manifest['file_count'] == 25 and len(manifest['files']) == 25, 'unexpected contact batch')
    contacts = [contact((args.archive / 'contacts-25' / item['name']).read_bytes(), baseline, item)
                for item in manifest['files']]
    print(json.dumps({'checker_sha256': digest(Path(__file__).read_bytes()),
                      'evidence_class': 'independent offline fixed-profile structural checks',
                      'calendar': result, 'contact_files': contacts, 'native_opened': False}, indent=2))


if __name__ == '__main__':
    main()
