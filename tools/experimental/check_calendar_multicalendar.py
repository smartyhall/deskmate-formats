"""Independent offline validator for the native A/B multicalendar experiment.

No production parser/writer imports. ``inspect`` checks structure without using
an input digest; ``check`` additionally pins the native input and prior listing.
Optional B must be original supplied bytes with the documented digest. This
tool never creates a database, mutates input, or claims native execution.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path


A_SHA256 = '338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5'
B_SHA256 = 'b9c9a4cae3cffac1bc337f7b378ea25df74efd3b6771e117c6e0fc3f81b77084'
SOURCE_SHA256 = 'd35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106'
SENTINEL = bytes.fromhex('ff ff ff ff ff ff ff ff ff 00')
CALENDAR_SCHEMA = [('Date', 3, 'C'), ('DayOfWeek', 1, 'C'), ('Duration', 1, 'C'),
                   ('StartTime', 1, 'C'), ('EndTime', 1, 'C'), ('Protected', 1, 'C'),
                   ('Description', 120, 'K')]
SELF_SCHEMA = [('cname', 80, 'C'), ('owner', 80, 'C'), ('pos', 4, 'N'),
               ('len', 4, 'N'), ('type', 1, 'C'), ('uniq', 1, 'N')]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def number(raw):
    require(raw and all(48 <= b <= 57 for b in raw), 'ASCII decimal')
    return int(raw)


def locators(page):
    groups = []
    for start in range(40, 1024, 246):
        block = page[start:start + 246]
        triples = []
        for pos in range(0, 246, 6):
            triple = tuple(int.from_bytes(block[pos + i:pos + i + 2], 'little') for i in (0, 2, 4))
            if triple == (0, 0, 0):
                require(not any(block[pos:]), 'subdivision holes/tail')
                break
            triples.append(triple)
        groups.append(triples)
    require(all(groups[i - 1] for i in range(1, 4) if groups[i]), 'nonempty subdivision after gap')
    return groups


def prefix(fields, ordinals):
    # Independent concatenation/truncation model of UPD's ten-byte prefix.
    full = b'\x01'.join(fields[i - 1] for i in ordinals[:5]) + b'\x01'
    return full[:9] + b'\x01' if len(full) >= 10 else full.ljust(10, b'\0')


def inspect(data):
    """Validate the bounded three-table campaign layout, without a hash gate."""
    require(len(data) == 10240 and data[:4] == b'\x03FIL', 'ten-page Calendar header')
    # Bitstream decoding is deliberately independent of the production nibble codec.
    bits = ''.join(f'{b:08b}' for b in data[32:1024])
    links = [int(bits[12 * i:12 * i + 12], 2) for i in range(11)]
    require(links[:2] == [4088, 4088] and links[10] == 4095, 'header/extent links')
    directory = data[1024:2048]
    marker = directory.find(b'\x03')
    require(marker >= 0 and not any(directory[marker + 1:]), 'directory tail')
    chunks = directory[:marker].split(b'\x01\x02')
    require(chunks[-1] == b'' and len(chunks) == 4 and data[21] == 2, 'table/calendar count')
    tables = {}
    for chunk in chunks[:-1]:
        tokens = chunk.split(b'\x01')
        require(len(tokens) >= 8 and tokens[0] == b'T', 'descriptor')
        name = tokens[1].decode('ascii')
        require(name not in tables, 'duplicate table')
        page, columns, count, next_id, index = [number(tokens[i]) for i in (2, 3, 4, 6, 7)]
        require(2 <= page < 10 and 2 <= index < 10 and page != index, 'table page roles')
        ordinals = [number(t) for t in tokens[8:]]
        require(ordinals == ([2, 3] if name == 'DBCOLS' else [1, 2, 4, 5, 7]), 'sort ordinals')
        tables[name] = dict(page=page, columns=columns, count=count, next_id=next_id,
                            index=index, ordinals=ordinals)
    require(list(tables) == ['DBCOLS', 'PERSONAL', 'SECOND'], 'table names/order')
    reserved = {0, 1}
    for t in tables.values():
        require(t['index'] not in reserved and links[t['index']] == 4088, 'index chain/ownership')
        reserved.add(t['index'])
    owners = set(reserved)
    for name, t in tables.items():
        chain, page = [], t['page']
        while True:
            require(2 <= page < 10 and page not in owners, 'cyclic/cross-table page chain')
            chain.append(page)
            owners.add(page)
            following = links[page]
            if following == 4088:
                break
            page = following
        physical = {}
        for page in chain:
            block = data[page * 1024:(page + 1) * 1024]
            cursor = 0
            while cursor < 1024 and block[cursor] != 3:
                require(cursor + 2 < 1024 and block[cursor] == 128
                        and 16 <= block[cursor + 1] < 128, 'row prefix/ID')
                end = block.find(b'\x01\x02', cursor + 2)
                require(end >= 0, 'page-local row terminator')
                payload = block[cursor + 2:end]
                require(not any(b in payload for b in (0, 2, 3)), 'reserved row byte')
                fields = payload.split(b'\x01')
                require(len(fields) == t['columns'], 'row field count')
                physical[(page, cursor)] = (block[cursor + 1], fields)
                cursor = end + 2
            require(cursor < 1024 and block[cursor] == 3 and not any(block[cursor + 1:]), 'row marker/tail')
        block = data[t['index'] * 1024:(t['index'] + 1) * 1024]
        groups = locators(block)
        triples = [entry for group in groups for entry in group]
        require(len(triples) == t['count'] == len(physical), 'row/index/descriptor count')
        require(len({entry[2] for entry in triples}) == len(triples), 'duplicate table-scoped ID')
        require({entry[:2] for entry in triples} == set(physical)
                and len(triples) == len({entry[:2] for entry in triples}), 'locator ownership/boundary')
        for p, offset, rid in triples:
            require(physical[(p, offset)][0] == rid, 'locator ID mismatch')
        for n, group in enumerate(groups):
            route = block[n * 10:(n + 1) * 10]
            if route != SENTINEL:
                require(group, 'finite route on empty group')
                last = physical[group[-1][:2]][1]
                require(route == prefix(last, t['ordinals']), 'routing endpoint mismatch')
        t.update(chain=chain, groups=groups, triples=triples, physical=physical)
    definitions = {name: {} for name in tables}
    for _, fields in tables['DBCOLS']['physical'].values():
        column, owner, position, width, kind, unique = fields
        owner = owner.decode('ascii')
        pos = number(position)
        require(owner in definitions and pos not in definitions[owner] and unique == b'0', 'schema owner/position')
        definitions[owner][pos] = (column.decode('ascii'), number(width), kind.decode('ascii'))
    for name, t in tables.items():
        expected = SELF_SCHEMA if name == 'DBCOLS' else CALENDAR_SCHEMA
        require(sorted(definitions[name]) == list(range(1, len(expected) + 1))
                and [definitions[name][n] for n in sorted(definitions[name])] == expected, 'schema definitions')
        if name == 'DBCOLS':
            continue
        events, controls, keys = [], [], []
        for page, offset, rid in t['triples']:
            fields = t['physical'][(page, offset)][1]
            raw_date, weekday, duration, start, end, alarm, description = fields
            if rid == 16:
                require(fields[:6] == [b'  \xff', b'', b'', b'', b'', b'0'] and
                        description in (b'ie' + b'a' * 12 + b'@PaSsWoRd@=',
                                        b'ic' + b'a' * 12 + b'@PaSsWoRd@='), 'configuration signature')
                controls.append((page, offset, rid))
            else:
                require(len(raw_date) == 3 and len(weekday) == len(start) == len(end) == 1
                        and not duration and alarm in (b'1', b'q'), 'ordinary appointment fields')
                day = date(raw_date[0] - 97 + 1980, raw_date[1] - 97, raw_date[2] - 97)
                require(1980 <= day.year <= 2138 and weekday[0] == (day.weekday() + 1) % 7 + 98,
                        'date/weekday')
                require(128 < start[0] < end[0] < 224 and 1 <= len(description) <= 120
                        and all(32 <= b < 127 for b in description), 'ordinary time/description')
                events.append(dict(date=day.isoformat(), start_time=clock(start[0]), end_time=clock(end[0]),
                                   description=description.decode('ascii'), alarm_enabled=alarm == b'q',
                                   record_id=rid, page=page, in_page_offset=offset))
            keys.append(tuple(fields[i].upper() for i in (0, 1, 3, 4)))
        require(len(controls) == 1 and t['triples'][0] == controls[0], 'leading per-calendar configuration')
        require(keys == sorted(keys), 'Calendar index ordering')
        t.update(events=events, controls=controls)
    return tables


def clock(raw):
    minutes = 15 * (raw - 128)
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def check(source, data, expected):
    tables = inspect(data)
    require(len(source) == 8192 and digest(source) == SOURCE_SHA256, 'source identity')
    require(digest(data) == A_SHA256, 'native A identity')
    require([tables[n]['count'] for n in tables] == [20, 62, 1], 'A record counts')
    require([len(g) for g in tables['PERSONAL']['groups']] == [20, 21, 21, 0], 'A subdivision counts')
    for page in (4, 6, 7):
        require(data[page * 1024:(page + 1) * 1024] == source[page * 1024:(page + 1) * 1024], 'PERSONAL physical preservation')
    original = [entry for group in locators(source[5120:6144]) for entry in group]
    require(tables['PERSONAL']['triples'] == original, 'all 62 PERSONAL locators preserved')
    require(tables['PERSONAL']['chain'] == [4, 6, 7] and tables['SECOND']['chain'] == [8], 'A data chains')
    actual = tables['PERSONAL']['events']
    require(len(actual) == len(expected['appointments']) == 61, 'expected appointment count')
    require(actual == [{key: row[key] for key in actual[0]} for row in expected['appointments']], 'all PERSONAL fields/alarms/locations')
    require(not tables['SECOND']['events'] and tables['SECOND']['controls'] == [(8, 0, 16)], 'empty SECOND')
    require(tables['PERSONAL']['physical'][(4, 0)] == tables['SECOND']['physical'][(8, 0)], 'separate matching config rows')
    return dict(evidence_class='native A bytes independently validated; creation operator-reported',
                sha256=digest(data), bytes=len(data), database_tables=3, named_calendars=2,
                personal_appointments=61, second_appointments=0, configuration_records=2,
                personal_index_groups=[20, 21, 21, 0], personal_locators=62,
                source_sha256=digest(source))


def check_first_second(a, b):
    """Compare actual original B only; its digest is never used as generated bytes."""
    before, after = inspect(a), inspect(b)
    require(digest(a) == A_SHA256 and digest(b) == B_SHA256, 'original A/B identities')
    changed = [i for i, (x, y) in enumerate(zip(a, b, strict=True)) if x != y]
    require(changed == [0x464, 0x46E] + list(range(0x2027, 0x2048)) + [0x242E, 0x2430, 0x2432], '38 exact changed positions')
    for name in ('DBCOLS', 'PERSONAL'):
        require(before[name] == after[name], 'unrelated table unchanged')
    t = after['SECOND']
    require((t['count'], t['next_id']) == (2, 18) and
            (before['SECOND']['count'], before['SECOND']['next_id']) == (1, 17), 'SECOND counters')
    require(t['triples'] == [(8, 0, 16), (8, 39, 17)] and
            t['groups'][1:] == [[], [], []] and t['chain'] == [8], 'SECOND locator/no allocation')
    require(t['events'] == [dict(date='2026-10-24', start_time='11:00', end_time='12:00',
                               description='SECOND ONLY 001', alarm_enabled=False,
                               record_id=17, page=8, in_page_offset=39)], 'SECOND event')
    require(b[0x2027:0x2029] == b'\x80\x11' and b[0x2045:0x2048] == b'\x01\x02\x03', '32-byte physical append')
    require(before['SECOND']['physical'][(8, 0)] == t['physical'][(8, 0)], 'SECOND configuration preserved')
    return dict(sha256=digest(b), bytes=len(b), changed_positions=len(changed),
                personal_appointments=61, second_appointments=1, original_b_verified=True)


def check_append(a, candidate, expected):
    """Independently check a tool-generated first SECOND append, without B bytes."""
    before, after = inspect(a), inspect(candidate)
    require(digest(a) == A_SHA256, 'exact empty-SECOND source identity')
    require(type(expected) is dict and set(expected) ==
            {'date', 'start_minutes', 'end_minutes', 'description', 'alarm_enabled'}, 'expected event keys')
    start, end = expected['start_minutes'], expected['end_minutes']
    require(type(start) is int and type(end) is int and 0 < start < end < 1440
            and start % 15 == end % 15 == 0 and type(expected['alarm_enabled']) is bool, 'expected times/alarm')
    day = date.fromisoformat(expected['date'])
    require(1980 <= day.year <= 2138, 'expected ordinary year')
    text = expected['description']
    require(type(text) is str and 1 <= len(text) <= 120 and all(32 <= ord(c) < 127 for c in text), 'expected description')
    t = after['SECOND']
    require(t['events'] == [dict(date=day.isoformat(), start_time=f'{start // 60:02d}:{start % 60:02d}',
                               end_time=f'{end // 60:02d}:{end % 60:02d}', description=text,
                               alarm_enabled=expected['alarm_enabled'], record_id=17, page=8, in_page_offset=39)], 'expected SECOND event')
    require((t['count'], t['next_id']) == (2, 18) and t['chain'] == [8]
            and t['triples'] == [(8, 0, 16), (8, 39, 17)], 'append counters/locator/chain')
    require(before['SECOND']['physical'][(8, 0)] == t['physical'][(8, 0)], 'existing SECOND configuration')
    require(all(before[name] == after[name] for name in ('DBCOLS', 'PERSONAL')), 'unrelated tables')
    # Known source A's independently delimited descriptor and row placement.
    row_end = candidate.find(b'\x01\x02', 0x2029, 0x2400) + 2
    require(row_end > 0x2029 and candidate[row_end] == 3, 'appended row marker')
    allowed = {*range(0x460, 0x465), *range(0x46A, 0x46F),
               *range(0x2027, row_end + 1), *range(0x242E, 0x2434)}
    changed = [i for i, (x, y) in enumerate(zip(a, candidate, strict=True)) if x != y]
    require(set(changed) <= allowed, 'unknown/unrelated bytes changed')
    return dict(evidence_class='tool-generated, independently checked offline; not application-produced or native-accepted',
                source_sha256=digest(a), output_sha256=digest(candidate), bytes=len(candidate),
                personal_appointments=61, second_appointments=1, configuration_records=2,
                changed_positions=len(changed), row_length=row_end - 0x2027,
                expected_second_appointment=expected, native_opened=False, native_saved=False)


def read(path, bound):
    with path.open('rb') as handle:
        result = handle.read(bound + 1)
    require(len(result) <= bound, 'input exceeds bound')
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('native_a', type=Path)
    cli.add_argument('expected', type=Path)
    cli.add_argument('--first-second', type=Path, help='Original supplied B only; optional, read-only')
    args = cli.parse_args()
    source, a = read(args.source, 8192), read(args.native_a, 10240)
    report = check(source, a, json.loads(read(args.expected, 131072)))
    if args.first_second:
        report['first_second'] = check_first_second(a, read(args.first_second, 10240))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
