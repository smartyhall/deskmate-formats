"""Bounded readers for observed DeskMate database structures, not an allocator.

The common profile uses one directory and one index page per table. The
separate Help profile also supports chained indexes and wider live row IDs.
Unknown header bytes, descriptor tokens and field values are retained verbatim.
Packed-12 data chains and four index subdivisions are validated. Application
codecs, general collation and next-ID policy deliberately do not live here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import struct

PAGE_SIZE = 1024
INDEX_HEADER_SIZE = 40
INDEX_HEADER = (b'\xff' * 9 + b'\x00') * 4
INDEX_SENTINEL = INDEX_HEADER[:10]
INDEX_GROUP_BYTES = 246
INDEX_GROUP_CAPACITY = 41
MAX_PAGES = 64
SELF_SCHEMA = (('cname', 80, 'C'), ('owner', 80, 'C'), ('pos', 4, 'N'),
               ('len', 4, 'N'), ('type', 1, 'C'), ('uniq', 1, 'N'))


class DatabaseError(ValueError):
    """Malformed or unsupported structure; offsets are absolute and zero based."""

    def __init__(self, code, message, offset=None):
        self.code, self.offset = code, offset
        where = '' if offset is None else f' at 0x{offset:04X}'
        super().__init__(f'{code}{where}: {message}')


def require(condition, code, message, offset=None):
    if not condition:
        raise DatabaseError(code, message, offset)


def decimal(value, offset):
    require(bool(value) and all(48 <= c <= 57 for c in value),
            'invalid_metadata', 'expected ASCII decimal', offset)
    return int(value)


@dataclass(frozen=True)
class IndexEntry:
    index_offset: int
    page: int
    in_page_offset: int
    record_id: int

    @property
    def address(self):
        return self.page * PAGE_SIZE + self.in_page_offset


@dataclass(frozen=True)
class Column:
    name: str
    width: int
    kind: str
    raw_fields: tuple[bytes, ...]


@dataclass(frozen=True)
class Row:
    offset: int
    record_id: int
    raw: bytes
    fields: tuple[bytes, ...]
    index_offset: int | None
    retired: bool = False

    @property
    def end(self):
        return self.offset + len(self.raw)


@dataclass(frozen=True)
class IndexGroup:
    routing_offset: int
    routing_key: bytes
    entries: tuple[IndexEntry, ...]


@dataclass(frozen=True)
class Table:
    name: str
    descriptor_offset: int
    raw_descriptor: bytes
    tokens: tuple[bytes, ...]
    data_page: int
    index_page: int
    column_count: int
    record_count: int
    next_id_candidate: int
    entries: tuple[IndexEntry, ...] = ()
    columns: tuple[Column, ...] = ()
    rows: tuple[Row, ...] = ()
    retired_rows: tuple[Row, ...] = ()
    index_groups: tuple[IndexGroup, ...] = ()
    data_pages: tuple[int, ...] = ()

    def token_offset(self, index):
        return self.descriptor_offset + sum(len(t) + 1 for t in self.tokens[:index])


@dataclass(frozen=True)
class Database:
    data: bytes
    sha256: str
    tables: tuple[Table, ...]

    def table(self, name):
        for table in self.tables:
            if table.name == name:
                return table
        raise DatabaseError('unsupported_schema', f'missing table {name}')

    @property
    def header(self):
        return self.data[:PAGE_SIZE]


@dataclass(frozen=True)
class HelpDirectory:
    """The observed Help table descriptors and the opaque post-marker bytes."""

    tables: tuple[Table, ...]
    marker_offset: int
    tail: bytes


def _directory(data):
    cursor, limit, result, names = PAGE_SIZE, 2 * PAGE_SIZE, [], set()
    while cursor < limit and data[cursor] != 3:
        end = data.find(b'\x01\x02', cursor, limit)
        require(end >= 0, 'invalid_metadata', 'missing table terminator', cursor)
        tokens = tuple(data[cursor:end].split(b'\x01'))
        require(len(tokens) >= 8 and tokens[0] == b'T', 'unsupported_layout',
                'unknown table descriptor', cursor)
        try:
            name = tokens[1].decode('ascii')
        except UnicodeDecodeError as exc:
            raise DatabaseError('invalid_metadata', 'non-ASCII table name', cursor) from exc
        require(name and name not in names, 'invalid_metadata', 'empty/duplicate table name', cursor)
        names.add(name)
        page, columns, count, next_id, index = (decimal(tokens[i], cursor) for i in (2, 3, 4, 6, 7))
        require(2 <= page < len(data) // PAGE_SIZE and 2 <= index < len(data) // PAGE_SIZE
                and page != index, 'invalid_index', 'invalid table page roles', cursor)
        require(1 <= columns <= 128, 'unsupported_layout', 'unsupported column count', cursor)
        result.append(Table(name, cursor, data[cursor:end + 2], tokens, page, index,
                            columns, count, next_id))
        cursor = end + 2
    require(result and cursor < limit and data[cursor] == 3,
            'unsupported_layout', 'missing directory marker or nonzero tail', cursor)
    return tuple(result), cursor


def page_link(data, page):
    """Read an MSB-first packed-12 link from the bounded header page."""
    at = 0x20 + page + page // 2
    word = int.from_bytes(data[at:at + 2], 'big')
    return word & 0xFFF if page % 2 else word >> 4


def _chain(data, start):
    pages, seen = [], set()
    page = start
    while True:
        require(2 <= page < len(data) // PAGE_SIZE and page not in seen,
                'invalid_chain', 'cyclic or out-of-file page chain', 0x20 + page + page // 2)
        pages.append(page)
        seen.add(page)
        link = page_link(data, page)
        if link == 0xFF8:
            return tuple(pages)
        require(2 <= link < len(data) // PAGE_SIZE, 'invalid_chain',
                'unsupported/free/extent marker inside page chain', 0x20 + page + page // 2)
        page = link


def _index(data, table, index_pages, id_limit):
    last_base = index_pages[-1] * PAGE_SIZE
    entries, groups, ids, targets = [], [], set(), set()
    empty_seen = False
    subdivisions = ((page * PAGE_SIZE, group) for page in index_pages for group in range(4))
    for base, group in subdivisions:
        cursor = base + INDEX_HEADER_SIZE + INDEX_GROUP_BYTES * group
        end = cursor + INDEX_GROUP_BYTES
        live = []
        while cursor < end:
            page, offset, ident = struct.unpack_from('<HHH', data, cursor)
            if (page, offset, ident) == (0, 0, 0):
                require(base == last_base and not any(data[cursor:end]), 'invalid_index',
                        'index holes or nonzero subdivision tail', cursor)
                break
            require(not empty_seen and page in table.data_pages and offset < PAGE_SIZE,
                    'invalid_index', 'index target outside owning chain or nonempty group after gap', cursor)
            require(0x10 <= ident < id_limit, 'unsupported_layout', 'long/unknown record ID framing', cursor)
            entry = IndexEntry(cursor, page, offset, ident)
            require(ident not in ids and entry.address not in targets,
                    'invalid_index', 'duplicate record ID or target', cursor)
            live.append(entry)
            ids.add(ident)
            targets.add(entry.address)
            cursor += 6
        empty_seen |= not live
        routing = base + 10 * group
        key = data[routing:routing + 10]
        require(live or key == INDEX_SENTINEL, 'invalid_index', 'finite route for empty group', routing)
        groups.append(IndexGroup(routing, key, tuple(live)))
        entries.extend(live)
    require(len(entries) == table.record_count, 'invalid_index',
            'count disagrees with index', table.index_page * PAGE_SIZE)
    return tuple(entries), tuple(groups)


def _row(data, start, fields, *, index_offset=None, retired=False, allow_missing_uniq=False, id_limit=0x80):
    limit = (start // PAGE_SIZE + 1) * PAGE_SIZE
    prefix = 0x4400 if retired else 0x8000
    ident = int.from_bytes(data[start:start + 2], 'big') - prefix
    require(start + 2 <= limit and 0x10 <= ident < id_limit,
            'invalid_record', 'unknown row prefix/ID', start)
    end = data.find(b'\x01\x02', start + 2, limit)
    require(end >= 0, 'invalid_record', 'missing page-bounded row terminator', start)
    payload = data[start + 2:end]
    require(not any(c in payload for c in (0, 2, 3)), 'invalid_record', 'reserved byte inside row', start)
    values = tuple(payload.split(b'\x01'))
    legacy = allow_missing_uniq and len(values) == 5 and values[1] != b'DBCOLS'
    require(len(values) == fields or legacy, 'invalid_record', 'field count disagrees with schema', start)
    return Row(start, ident, data[start:end + 2], values, index_offset, retired)


def _rows(data, table, entries, reserved, page_owners, allow_retired, allow_missing_uniq, id_limit):
    targets = {e.address: e for e in entries}
    pages = table.data_pages
    live, retired = {}, []
    for page in pages:
        require(page not in reserved and page not in page_owners,
                'invalid_index', 'data page aliases metadata/index/another table', page * PAGE_SIZE)
        page_owners.add(page)
        cursor, limit = page * PAGE_SIZE, (page + 1) * PAGE_SIZE
        while cursor < limit and data[cursor] != 3:
            entry = targets.get(cursor)
            if entry is not None:
                row = _row(data, cursor, table.column_count, index_offset=entry.index_offset,
                           allow_missing_uniq=allow_missing_uniq, id_limit=id_limit)
                require(row.record_id == entry.record_id, 'invalid_record', 'index/row ID mismatch', cursor)
                live[cursor] = row
            else:
                require(allow_retired and data[cursor] == 0x44, 'unsupported_layout',
                        'unindexed row, overlap or gap; retired rows require opt-in', cursor)
                row = _row(data, cursor, table.column_count, retired=True)
                retired.append(row)
            cursor = row.end
        require(cursor < limit and data[cursor] == 3 and not any(data[cursor + 1:limit]),
                'unsupported_layout', 'missing row-list marker or nonzero tail', cursor)
    require(set(live) == set(targets), 'invalid_index', 'index points inside a row or past list marker')
    return tuple(live[e.address] for e in entries), tuple(retired)


def index_prefix(fields, ordinals):
    """UPD 11C8: at most five fields, ten bytes including final separator."""
    key = bytearray()
    for ordinal in ordinals[:5]:
        room = 9 - len(key)
        if room < 0:
            break
        key.extend(fields[ordinal - 1][:room])
        key.append(1)
    key.extend(bytes(10 - len(key)))
    return bytes(key)


def _routing(table):
    """Finite keys must be the native ten-byte prefix of a group's last row.

    Sentinel groups can remain populated: the native routing path falls back
    to full-row comparison. No inferred balancing or DOS K collation is used.
    """
    finite = [g for g in table.index_groups if g.routing_key != INDEX_SENTINEL]
    if not finite:
        return
    ordinals = tuple(decimal(t, table.descriptor_offset) for t in table.tokens[8:])
    require(1 <= len(ordinals) <= 5 and len(set(ordinals)) == len(ordinals)
            and all(1 <= n <= table.column_count for n in ordinals),
            'unsupported_layout', 'finite routes need bounded sort ordinals', table.descriptor_offset)
    by_address = {r.offset: r for r in table.rows}
    for group in finite:
        fields = by_address[group.entries[-1].address].fields
        key = index_prefix(fields, ordinals)
        require(group.routing_key == key, 'invalid_index',
                'routing prefix disagrees with subdivision endpoint', group.routing_offset)


def parse_bytes(source, *, allow_retired=False, max_pages=MAX_PAGES, allow_legacy_filer_schema=False):
    """Read known framing, preserving opaque content; no universal ID/allocation policy.

    Retired-row scanning follows each validated packed-12 data-page chain.
    Unreferenced pages stay opaque in ``Database.data``; they are not free space.
    """
    return _parse_snapshot(_snapshot(source, max_pages), allow_retired, allow_legacy_filer_schema)


def inspect_help_directory(source):
    """Identify the measured DeskMate Help profile without decoding table rows."""
    data = _snapshot(source, MAX_PAGES)
    tables, marker = _directory(data)
    profile = _help_directory(data, tables, marker)
    _check_header_links(data)
    return profile


def parse_help_bytes(source, *, allow_retired=False, max_pages=MAX_PAGES):
    """Read framed Help tables when covered by the common row and index reader."""
    return _parse_snapshot(_snapshot(source, max_pages), allow_retired, False,
                           directory_check=_help_directory, allow_chained_indexes=True,
                           id_limit=0x200)


def parse_information_center_bytes(source, *, allow_retired=False, max_pages=MAX_PAGES):
    """Read the measured RSX Information Center 3.61 INFOCNTR.DB profile."""
    db = _parse_snapshot(_snapshot(source, max_pages), allow_retired, False,
                         directory_check=_information_center_directory)
    schema = tuple((col.name, col.width, col.kind) for col in db.table('INFO').columns)
    require(schema == (('Type', 1, 'K'), ('Date', 7, 'D'), ('Text', 952, 'K'),
                       ('Phone', 20, 'K'), ('Name', 20, 'K'), ('Time', 8, 'K')),
            'unsupported_schema', 'unknown Information Center INFO schema')
    return db


def _information_center_directory(data, tables, marker):
    roles = tuple((table.name, table.data_page, table.index_page, table.column_count)
                  for table in tables)
    require(data[:4] == b'\x03\x00\x00\x00' and marker == 0x44A
            and data[marker + 1:2 * PAGE_SIZE].rstrip(b'\0') == b'\x02\x03'
            and roles == (('DBCOLS', 2, 3, 6), ('INFO', 4, 5, 6))
            and tuple(table.tokens[8:] for table in tables) == ((b'2', b'3'), (b'1', b'2', b'6')),
            'unsupported_layout', 'unknown Information Center directory profile', marker)


_HELP_TAILS = (b'6\x017\x01\x02\x03', b'\x02\x037\x011\x01\x02\x03',
               b'5\x01\x02\x037\x014\x011\x01\x02\x03')


def _help_directory(data, tables, marker):
    roles = tuple((table.name, table.data_page, table.index_page, table.column_count)
                  for table in tables)
    tail = data[marker + 1:2 * PAGE_SIZE].rstrip(b'\0')
    require(data[:4] == b'\x03FIL' and marker == 0x464 and tail in _HELP_TAILS
            and roles in (
                (('DBCOLS', 2, 3, 6), ('Rules', 4, 5, 8), ('Text', 6, 7, 3)),
                (('DBCOLS', 2, 3, 6), ('Rules', 4, 5, 9), ('Text', 6, 7, 3)),
                (('DBCOLS', 2, 3, 6), ('Rules', 4, 5, 9), ('Text', 6, 7, 4)),
            )
            and tuple(table.tokens[8:] for table in tables) == ((b'2', b'3'), (), ()),
            'unsupported_layout', 'unknown DeskMate Help directory profile', marker)
    return HelpDirectory(tables, marker, tail)


def _snapshot(source, max_pages):
    require(isinstance(source, (bytes, bytearray, memoryview)), 'invalid_input', 'expected byte snapshot')
    require(type(max_pages) is int, 'unsupported_layout', 'page bound must be an integer')
    data = bytes(source)
    require(2 <= max_pages <= MAX_PAGES, 'unsupported_layout', 'invalid page bound')
    require(len(data) >= 6 * PAGE_SIZE, 'truncated_file', 'at least six complete pages required')
    require(len(data) % PAGE_SIZE == 0 and len(data) <= max_pages * PAGE_SIZE,
            'unsupported_layout', 'partial page or file exceeds bounded profile')
    require(data[:4] in (b'\x03FIL', b'\x03\x00\x00\x00'), 'invalid_header', 'unknown database header', 0)
    return data


def _check_header_links(data):
    require(page_link(data, 0) == page_link(data, 1) == 0xFF8
            and page_link(data, len(data) // PAGE_SIZE) == 0xFFF,
            'invalid_chain', 'unsupported header/directory chains or extent marker', 0x20)


def _parse_snapshot(data, allow_retired, allow_legacy_filer_schema, *, directory_check=None,
                    allow_chained_indexes=False, id_limit=0x80):
    from dataclasses import replace
    tables, marker = _directory(data)
    if directory_check is not None:
        directory_check(data, tables, marker)
    else:
        require(not any(data[marker + 1:2 * PAGE_SIZE]),
                'unsupported_layout', 'missing directory marker or nonzero tail', marker)
    _check_header_links(data)
    reserved = {0, 1}
    index_chains = {}
    for table in tables:
        require(table.index_page not in reserved, 'invalid_index', 'shared index page')
        chain = _chain(data, table.index_page)
        require(allow_chained_indexes or len(chain) == 1,
                'unsupported_layout', 'multiple index pages unsupported', table.index_page * PAGE_SIZE)
        require(reserved.isdisjoint(chain), 'invalid_index', 'shared index page')
        index_chains[table.name] = chain
        reserved.update(chain)
    page_owners = set()
    parsed = []
    for table in tables:
        table = replace(table, data_pages=_chain(data, table.data_page))
        entries, groups = _index(data, table, index_chains[table.name], id_limit)
        legacy = (allow_legacy_filer_schema and data[:4] == b'\x03FIL'
                  and table.name == 'DBCOLS' and table.column_count == 6)
        rows, retired = _rows(data, table, entries, reserved, page_owners, allow_retired, legacy, id_limit)
        table = replace(table, entries=entries, rows=rows, retired_rows=retired, index_groups=groups)
        _routing(table)
        parsed.append(table)
    db = Database(data, hashlib.sha256(data).hexdigest(), tuple(parsed))
    schema = db.table('DBCOLS')
    require(schema.column_count == 6 and not schema.retired_rows,
            'unsupported_schema', 'unsupported DBCOLS profile')
    columns = {table.name: {} for table in db.tables}
    for row in schema.rows:
        try:
            name, owner, pos, width, kind, *unique = (v.decode('ascii') for v in row.fields)
        except UnicodeDecodeError as exc:
            raise DatabaseError('invalid_schema', 'non-ASCII column definition', row.offset) from exc
        position, size = decimal(row.fields[2], row.offset), decimal(row.fields[3], row.offset)
        require(owner in columns and position not in columns[owner] and name
                and size > 0 and len(kind) == 1 and unique in ([], ['0']),
                'unsupported_schema', 'unknown/duplicate column definition', row.offset)
        columns[owner][position] = Column(name, size, kind, row.fields)
    result = []
    for table in db.tables:
        cols = columns[table.name]
        require(set(cols) == set(range(1, table.column_count + 1)),
                'invalid_schema', 'missing/out-of-range column positions')
        ordered = tuple(cols[i] for i in range(1, table.column_count + 1))
        require(len({c.name for c in ordered}) == len(ordered), 'invalid_schema', 'duplicate column name')
        result.append(replace(table, columns=ordered))
    db = replace(db, tables=tuple(result))
    require(tuple((c.name, c.width, c.kind) for c in db.table('DBCOLS').columns) == SELF_SCHEMA,
            'unsupported_schema', 'unknown DBCOLS self-schema')
    return db


def parse_file(path, **kwargs):
    with Path(path).open('rb') as handle:
        data = handle.read(MAX_PAGES * PAGE_SIZE + 1)
    return parse_bytes(data, **kwargs)
