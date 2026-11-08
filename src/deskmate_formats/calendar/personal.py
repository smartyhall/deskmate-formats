"""Read-only observed six-page profile and explicit bounded SDK named calendars.

No fixture hashes or appointment addresses are used by the parser. Unknown value
semantics remain raw; unknown structural layouts are rejected. See README_PARSER.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
import hashlib
import struct

PAGE_SIZE = 1024
FILE_SIZE = 6 * PAGE_SIZE
INDEX_HEADER_SIZE = 0x28
INDEX_HEADER = (b'\xff' * 9 + b'\x00') * 4
FIELD_NAMES = ('Date', 'DayOfWeek', 'Duration', 'StartTime', 'EndTime',
               'Protected', 'Description')
PERSONAL_SCHEMA = tuple(zip(FIELD_NAMES, (3, 1, 1, 1, 1, 1, 120),
                            ('C', 'C', 'C', 'C', 'C', 'C', 'K')))
DBCOLS_SCHEMA = tuple(zip(('cname', 'owner', 'pos', 'len', 'type', 'uniq'),
                         (80, 80, 4, 4, 1, 1), ('C', 'C', 'N', 'N', 'C', 'N')))
OBSERVED_DATES = {(2026, 10, 23), (2026, 10, 24), (2026, 11, 1), (2027, 11, 1)}
OBSERVED_WEEKDAYS = {1: 'Sunday', 2: 'Monday', 6: 'Friday', 7: 'Saturday'}
OBSERVED_TIMES = {0xA4, 0xA5, 0xA8, 0xA9, 0xAC, 0xB0}
SCOPE = 'Observed six-page, single-data/index-page tables; E00–E08 value mappings'


class CalendarParseError(ValueError):
    """Malformed or unsupported input, with a stable code and optional offset."""

    def __init__(self, code: str, message: str, offset: int | None = None):
        self.code, self.offset = code, offset
        where = '' if offset is None else f' at 0x{offset:04X}'
        super().__init__(f'{code}{where}: {message}')


def _require(condition: bool, code: str, message: str, offset=None):
    if not condition:
        raise CalendarParseError(code, message, offset)


@dataclass(frozen=True)
class IndexEntry:
    index_offset: int
    page: int
    in_page_offset: int
    record_id: int

    @property
    def address(self) -> int:
        return self.page * PAGE_SIZE + self.in_page_offset


@dataclass(frozen=True)
class Record:
    kind: str
    record_id: int
    offset: int
    length: int
    index_offset: int
    raw_hex: str
    raw_fields: dict[str, str]
    undecoded_fields: dict[str, str]
    warnings: tuple[str, ...]
    date: str | None = None
    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    description: str | None = None
    alarm_enabled: bool | None = None
    calendar_name: str = 'PERSONAL'

    def to_dict(self) -> dict:
        result = asdict(self)
        result['offset_hex'] = f'0x{self.offset:04X}'
        result['record_id_hex'] = f'0x{self.record_id:02X}'
        result['index_offset_hex'] = f'0x{self.index_offset:04X}'
        return result


@dataclass(frozen=True)
class NamedCalendar:
    name: str
    records: tuple[Record, ...]

    @property
    def appointments(self) -> tuple[Record, ...]:
        return tuple(r for r in self.records if r.kind == 'appointment')

    @property
    def internal_records(self) -> tuple[Record, ...]:
        return tuple(r for r in self.records if r.kind == 'internal/control')


@dataclass(frozen=True)
class CalendarDatabase:
    source: str | None
    sha256: str
    size: int
    metadata: dict
    records: tuple[Record, ...]
    warnings: tuple[str, ...]
    calendars: tuple[NamedCalendar, ...] = ()
    data: bytes = b''

    def calendar(self, name: str) -> NamedCalendar:
        for calendar in self.calendars or (NamedCalendar('PERSONAL', self.records),):
            if calendar.name == name:
                return calendar
        raise CalendarParseError('unsupported_schema', f'missing calendar {name}')

    @property
    def appointments(self) -> tuple[Record, ...]:
        return tuple(r for r in self.records if r.kind == 'appointment')

    @property
    def internal_records(self) -> tuple[Record, ...]:
        return tuple(r for r in self.records if r.kind == 'internal/control')

    def to_dict(self) -> dict:
        return {'source': self.source, 'sha256': self.sha256, 'size': self.size,
                'scope': ('SDK ordinary codecs; bounded multipage/multicalendar reading' if self.metadata.get('codec_profile') == 'sdk' else SCOPE), 'metadata': self.metadata,
                'warnings': list(self.warnings),
                'appointment_count': len(self.appointments),
                'appointments': [r.to_dict() for r in self.appointments],
                'internal_records': [r.to_dict() for r in self.internal_records],
                'calendars': [{'name': c.name, 'appointment_count': len(c.appointments),
                               'appointments': [r.to_dict() for r in c.appointments],
                               'internal_records': [r.to_dict() for r in c.internal_records]}
                              for c in self.calendars or (NamedCalendar('PERSONAL', self.records),)]}


def _decimal(raw: bytes, label: str, offset: int) -> int:
    _require(bool(raw) and all(48 <= x <= 57 for x in raw),
             'invalid_metadata', f'{label} must be ASCII decimal', offset)
    return int(raw)


def _tables(data: bytes) -> dict[str, dict]:
    """Recognize the observed metadata page, keeping uninterpreted tokens raw."""
    cursor, limit, tables = PAGE_SIZE, PAGE_SIZE * 2, {}
    for expected_name, token_count in (('DBCOLS', 10), ('PERSONAL', 13)):
        end = data.find(b'\x01\x02', cursor, limit)
        _require(end >= 0, 'invalid_metadata', 'missing table terminator', cursor)
        tokens = data[cursor:end].split(b'\x01')
        _require(len(tokens) == token_count and tokens[:2] ==
                 [b'T', expected_name.encode('ascii')], 'unsupported_layout',
                 f'expected observed {expected_name} table descriptor', cursor)
        data_page = _decimal(tokens[2], 'data-page candidate', cursor)
        columns = _decimal(tokens[3], 'column count', cursor)
        count = _decimal(tokens[4], 'record count', cursor)
        next_id = _decimal(tokens[6], 'next-ID candidate', cursor)
        index_page = _decimal(tokens[7], 'index-page candidate', cursor)
        expected_pages = (2, 3) if expected_name == 'DBCOLS' else (4, 5)
        _require((data_page, index_page) == expected_pages,
                 'unsupported_layout', 'only the observed table page roles are supported', cursor)
        _require(columns == (6 if expected_name == 'DBCOLS' else 7) and
                 len(tokens[4]) == len(tokens[6]) == 5 and tokens[5] == b'000',
                 'unsupported_layout', 'unrecognized table descriptor values', cursor)
        tail = [b'2', b'3'] if expected_name == 'DBCOLS' else [b'1', b'2', b'4', b'5', b'7']
        _require(tokens[8:] == tail, 'unsupported_layout',
                 'unrecognized trailing table descriptor tokens', cursor)
        tables[expected_name] = {'data_page': data_page, 'index_page': index_page,
                                'column_count': columns, 'record_count': count,
                                'next_id_candidate': next_id,
                                'raw_tokens_hex': [t.hex(' ') for t in tokens]}
        cursor = end + 2
    _require(data[cursor:cursor + 1] == b'\x03' and not any(data[cursor + 1:limit]),
             'unsupported_layout', 'metadata list marker/padding differs', cursor)
    return tables


def _index(data: bytes, table: dict) -> tuple[IndexEntry, ...]:
    base, page_end = table['index_page'] * PAGE_SIZE, (table['index_page'] + 1) * PAGE_SIZE
    _require(data[base:base + INDEX_HEADER_SIZE] == INDEX_HEADER,
             'unsupported_layout', 'unknown index-page header', base)
    entries, ids, targets = [], set(), set()
    cursor = base + INDEX_HEADER_SIZE
    while cursor + 6 <= page_end:
        page, offset, row_id = struct.unpack_from('<HHH', data, cursor)
        if (page, offset, row_id) == (0, 0, 0):
            break
        _require(page < len(data) // PAGE_SIZE and offset < PAGE_SIZE,
                 'invalid_index', 'page/offset is outside file boundaries', cursor)
        _require(page == table['data_page'], 'unsupported_layout',
                 'index target is outside the recognized data page', cursor)
        _require(0x10 <= row_id < 0x80, 'unsupported_layout',
                 'only observed 80 + low-ID row framing is supported', cursor)
        entry = IndexEntry(cursor, page, offset, row_id)
        _require(row_id not in ids and entry.address not in targets,
                 'invalid_index', 'duplicate record ID or target', cursor)
        ids.add(row_id)
        targets.add(entry.address)
        entries.append(entry)
        cursor += 6
    _require(cursor + 6 <= page_end and not any(data[cursor:page_end]),
             'unsupported_layout', 'index has no zero tail or has holes/trailing data', cursor)
    _require(len(entries) == table['record_count'], 'invalid_index',
             'index entry count disagrees with table record count', base)
    _require(bool(entries), 'unsupported_layout', 'observed tables include at least one row', base)
    _require(table['next_id_candidate'] == max(ids) + 1, 'unsupported_layout',
             'candidate next-ID differs from the observed max-ID + 1 relation', base)
    return tuple(entries)


def _rows(data: bytes, table: dict, entries: tuple[IndexEntry, ...], fields: int):
    page_start, page_end = table['data_page'] * PAGE_SIZE, (table['data_page'] + 1) * PAGE_SIZE
    rows = {}
    for entry in entries:
        start = entry.address
        _require(start + 2 <= page_end and data[start:start + 2] ==
                 bytes((0x80, entry.record_id)), 'invalid_record',
                 'row prefix/ID does not match its index entry', start)
        end = data.find(b'\x01\x02', start + 2, page_end)
        _require(end >= 0, 'invalid_record', 'missing bounded row terminator', start)
        payload = data[start + 2:end]
        _require(not any(x in payload for x in (b'\x00', b'\x02', b'\x03')),
                 'invalid_record', 'unexpected control/list marker inside row', start)
        values = payload.split(b'\x01')
        _require(len(values) == fields, 'invalid_record',
                 f'expected {fields} delimited fields, got {len(values)}', start)
        rows[start] = (entry, end + 2, values)
    cursor = page_start
    for start, (_, end, _) in sorted(rows.items()):
        _require(start == cursor, 'unsupported_layout',
                 'data rows overlap or contain an unindexed gap/row', start)
        cursor = end
    _require(cursor < page_end and data[cursor] == 3 and not any(data[cursor + 1:page_end]),
             'unsupported_layout', 'missing row-list marker or nonzero page tail', cursor)
    return rows


def _schema(data: bytes, table: dict):
    entries = _index(data, table)
    rows = _rows(data, table, entries, 6)
    columns = {'DBCOLS': {}, 'PERSONAL': {}}
    for entry in entries:
        _, _, values = rows[entry.address]
        try:
            name, owner, position, length, kind, unique = (v.decode('ascii') for v in values)
        except UnicodeDecodeError as exc:
            raise CalendarParseError('invalid_schema', 'non-ASCII schema token', entry.address) from exc
        _require(owner in columns and position.isascii() and position.isdecimal() and
                 length.isascii() and length.isdecimal() and unique == '0',
                 'invalid_schema', 'unrecognized schema token', entry.address)
        pos = int(position)
        _require(pos not in columns[owner], 'invalid_schema', 'duplicate column position', entry.address)
        columns[owner][pos] = (name, int(length), kind)
    for owner, expected in (('DBCOLS', DBCOLS_SCHEMA), ('PERSONAL', PERSONAL_SCHEMA)):
        _require(set(columns[owner]) == set(range(1, len(expected) + 1)) and
                 tuple(columns[owner][i] for i in range(1, len(expected) + 1)) == expected,
                 'unsupported_schema', f'{owner} columns differ from observed schema')
    return tuple(columns['PERSONAL'][i][0] for i in range(1, 8))


def _decode(data: bytes, entry: IndexEntry, end: int, values: list[bytes], names, *, sdk=False) -> Record:
    raw = dict(zip(names, values))
    fields = {k: v.hex(' ') for k, v in raw.items()}
    common = dict(record_id=entry.record_id, offset=entry.address, length=end - entry.address,
                  index_offset=entry.index_offset, raw_hex=data[entry.address:end].hex(' '),
                  raw_fields=fields)
    internal_description = b'i' + raw['Description'][1:2] + b'a' * 12 + b'@PaSsWoRd@='
    is_internal = (values[:6] == [b'  \xff', b'', b'', b'', b'', b'0'] and
                   raw['Description'][1:2] in (b'c', b'e') and
                   raw['Description'] == internal_description)
    if is_internal:
        _require(entry.record_id == 0x10, 'unsupported_record',
                 'internal signature under an unobserved ID', entry.address)
        return Record(kind='internal/control', undecoded_fields=fields,
                      warnings=('Observed internal/control signature; all field semantics remain opaque.',),
                      **common)
    _require(entry.record_id != 0x10, 'unsupported_record',
             'ID 0x10 does not match the observed internal/control signature', entry.address)
    _require(len(raw['Date']) == 3 and all(len(raw[n]) <= 1 for n in names[1:6]),
             'invalid_record', 'field widths disagree with PERSONAL schema', entry.address)
    _require(len(raw['Description']) <= 120, 'unsupported_record',
             'description exceeds declared schema limit', entry.address)
    # Keep the complete Protected byte in the existing raw output.
    unknown = {n: fields[n] for n in ('Duration', 'Protected')}
    warnings = []
    decoded_date = None
    components = (1980 + raw['Date'][0] - 0x61, raw['Date'][1] - 0x61, raw['Date'][2] - 0x61)
    try:
        candidate_date = date(*components)
    except ValueError as exc:
        raise CalendarParseError('invalid_date', 'date components do not form a calendar date', entry.address) from exc
    if sdk and not 1980 <= candidate_date.year <= 2138:
        raise CalendarParseError('invalid_date', 'outside ordinary SDK representable year range', entry.address)
    if sdk or components in OBSERVED_DATES:
        decoded_date = candidate_date.isoformat()
    else:
        unknown['Date'] = fields['Date']
        warnings.append('Date is outside the four observed date mappings; not decoded.')
    weekday = None
    weekdays = dict(enumerate(('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'), 1)) if sdk else OBSERVED_WEEKDAYS
    if len(raw['DayOfWeek']) == 1 and raw['DayOfWeek'][0] - 0x61 in weekdays:
        number = raw['DayOfWeek'][0] - 0x61
        weekday = weekdays[number]
        if decoded_date is not None:
            _require(number == (candidate_date.weekday() + 1) % 7 + 1,
                     'inconsistent_weekday', 'stored weekday disagrees with decoded date', entry.address)
    else:
        unknown['DayOfWeek'] = fields['DayOfWeek']
        warnings.append('Weekday is empty or outside observed mappings; not decoded.')
    times = {}
    for name in ('StartTime', 'EndTime'):
        value = raw[name]
        times[name] = None
        if len(value) == 1 and value[0] in (range(0x81, 0xE0) if sdk else OBSERVED_TIMES):
            minutes = 15 * (value[0] - 0x80)
            times[name] = f'{minutes // 60:02d}:{minutes % 60:02d}'
        else:
            unknown[name] = fields[name]
            warnings.append(f'{name} is empty or outside observed time mappings; not decoded.')
    if all(times.values()):
        _require(times['StartTime'] < times['EndTime'], 'unsupported_time_order',
                 'reversed, zero-length or overnight event is outside the observed subset', entry.address)
    alarm_enabled = None
    if decoded_date is not None and weekday is not None and all(times.values()) and not raw['Duration']:
        alarm_enabled = {b'1': False, b'q': True}.get(raw['Protected'])
    if alarm_enabled is None:
        warnings.append('Alarm state is outside the observed ordinary appointment profile.')
    description = None
    if all(0x20 <= x < 0x7F for x in raw['Description']):
        description = raw['Description'].decode('ascii')
    else:
        unknown['Description'] = fields['Description']
        warnings.append('Non-printable/non-ASCII description retained raw; encoding/escaping unknown.')
    return Record(kind='appointment', date=decoded_date, day_of_week=weekday,
                  start_time=times['StartTime'], end_time=times['EndTime'],
                  description=description, alarm_enabled=alarm_enabled, undecoded_fields=unknown,
                  warnings=tuple(warnings), **common)


def parse_bytes(source: bytes, *, source_name: str | None = None, profile='observed') -> CalendarDatabase:
    """Parse an immutable byte snapshot; never writes input or accesses an emulator."""
    if profile == 'sdk':
        return _parse_sdk(source, source_name=source_name)
    _require(profile == 'observed', 'unsupported_layout', 'unknown Calendar profile')
    data = bytes(source)
    _require(len(data) >= FILE_SIZE, 'truncated_file',
             f'observed layout requires {FILE_SIZE} bytes, got {len(data)}')
    _require(len(data) == FILE_SIZE, 'unsupported_layout',
             'only the observed six-page file size is supported')
    _require(data[:4] == b'\x03FIL', 'invalid_header', 'expected observed 03 46 49 4C header', 0)
    tables = _tables(data)
    names = _schema(data, tables['DBCOLS'])
    entries = _index(data, tables['PERSONAL'])
    rows = _rows(data, tables['PERSONAL'], entries, len(names))
    records = tuple(_decode(data, entry, rows[entry.address][1], rows[entry.address][2], names)
                    for entry in entries)
    _require(sum(r.kind == 'internal/control' for r in records) == 1,
             'unsupported_record', 'expected exactly one observed internal/control row')
    metadata = {'page_size': PAGE_SIZE, 'page_count': 6, 'tables': tables,
                'header_page_raw_hex': data[:PAGE_SIZE].hex(' ')}
    return CalendarDatabase(source_name, hashlib.sha256(data).hexdigest(), len(data), metadata,
                            records, ('Header fields beyond magic and page/table token semantics remain partly unknown.',
                                      'Structural acceptance does not validate untested codecs, page growth or deletion.'),
                            data=data)


def _parse_sdk(source, *, source_name=None):
    """Explicit SDK ordinary codecs and bounded extra pages; never allocates."""
    from deskmate_formats import database
    try:
        db = database.parse_bytes(source, allow_retired=True)
    except database.DatabaseError as exc:
        raise CalendarParseError(exc.code, str(exc), exc.offset) from exc
    _require(db.data[:4] == b'\x03FIL', 'invalid_header', 'expected Calendar FIL header', 0)
    _require(len(db.tables) >= 2 and db.tables[0].name == 'DBCOLS'
             and db.tables[1].name == 'PERSONAL',
             'unsupported_layout', 'expected DBCOLS then PERSONAL and named calendars')
    _require(db.data[0x15] == len(db.tables) - 1,
             'invalid_metadata', 'named-calendar count disagrees with directory', 0x15)
    tables = {}
    for table in db.tables:
        is_schema = table.name == 'DBCOLS'
        expected = DBCOLS_SCHEMA if is_schema else PERSONAL_SCHEMA
        tail = (b'2', b'3') if is_schema else (b'1', b'2', b'4', b'5', b'7')
        pages = (2, 3) if is_schema else (4, 5) if table.name == 'PERSONAL' else None
        _require((pages is None or (table.data_page, table.index_page) == pages)
                 and table.tokens[8:] == tail
                 and len(table.tokens[4]) == len(table.tokens[6]) == 5
                 and table.tokens[5] in (b'000', b'001'),
                 'unsupported_layout', 'unknown Calendar table profile')
        _require(tuple((c.name, c.width, c.kind) for c in table.columns) == expected,
                 'unsupported_schema', 'unrecognized Calendar schema')
        tables[table.name] = {'data_page': table.data_page, 'index_page': table.index_page,
                             'data_pages': list(table.data_pages),
                             'column_count': table.column_count, 'record_count': table.record_count,
                             'next_id_candidate': table.next_id_candidate,
                             'raw_descriptor_hex': table.raw_descriptor.hex(' '),
                             'raw_tokens_hex': [t.hex(' ') for t in table.tokens],
                             'index_groups': [{'routing_offset': g.routing_offset,
                                               'routing_key_hex': g.routing_key.hex(' '),
                                               'entry_count': len(g.entries)}
                                              for g in table.index_groups]}
    calendars = []
    for table in db.tables[1:]:
        records = tuple(replace(_decode(db.data, entry, row.end, list(row.fields), FIELD_NAMES, sdk=True),
                                calendar_name=table.name)
                        for entry, row in zip(table.entries, table.rows, strict=True))
        _require(sum(r.kind == 'internal/control' for r in records) == 1
                 and records[0].kind == 'internal/control',
                 'unsupported_record', 'expected one leading internal/control row per calendar')
        # The first four sort fields are C, whose reader comparison folds ASCII
        # lowercase. K description collation (the fifth field) remains opaque.
        keys = [tuple(row.fields[i].upper() for i in (0, 1, 3, 4)) for row in table.rows]
        _require(keys == sorted(keys), 'invalid_index', 'Calendar index order disagrees with C sort fields',
                 table.index_page * PAGE_SIZE)
        calendars.append(NamedCalendar(table.name, records))
    records = tuple(r for calendar in calendars for r in calendar.records)
    metadata = {'page_size': PAGE_SIZE, 'page_count': len(db.data) // PAGE_SIZE,
                'codec_profile': 'sdk', 'tables': tables,
                'header_page_raw_hex': db.header.hex(' '),
                'retired_rows': [{'offset': r.offset, 'record_id': r.record_id,
                                  'raw_hex': r.raw.hex(' '), 'calendar_name': t.name}
                                 for t in db.tables[1:] for r in t.retired_rows]}
    return CalendarDatabase(source_name, db.sha256, len(db.data), metadata, records,
                            ('SDK-derived ordinary codecs; new combinations are not native-verified.',
                             'Unreferenced pages, K collation and nonstructural metadata remain opaque.'),
                            tuple(calendars), db.data)


def parse_file(path: str | Path, *, profile='observed') -> CalendarDatabase:
    """Open input strictly in rb mode, bounded to supported size plus one byte."""
    path = Path(path)
    with path.open('rb') as handle:
        data = handle.read((64 * PAGE_SIZE if profile == 'sdk' else FILE_SIZE) + 1)
    return parse_bytes(data, source_name=str(path), profile=profile)
