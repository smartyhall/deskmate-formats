"""Bounded readers for observed DeskMate database structures, not an allocator.

One directory page and one index page per table; low-ID, page-local rows only.
Unknown header bytes, descriptor tokens and field values are retained verbatim.
Application codecs and next-ID policy deliberately do not live here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import struct

PAGE_SIZE = 1024
INDEX_HEADER_SIZE = 40
INDEX_HEADER = (b'\xff' * 9 + b'\x00') * 4
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
    require(result and cursor < limit and data[cursor] == 3 and not any(data[cursor + 1:limit]),
            'unsupported_layout', 'missing directory marker or nonzero tail', cursor)
    return result


def _index(data, table):
    base = table.index_page * PAGE_SIZE
    limit = base + PAGE_SIZE
    require(data[base:base + INDEX_HEADER_SIZE] == INDEX_HEADER,
            'unsupported_layout', 'unknown index header', base)
    cursor, entries, ids, targets = base + INDEX_HEADER_SIZE, [], set(), set()
    while cursor + 6 <= limit:
        page, offset, ident = struct.unpack_from('<HHH', data, cursor)
        if (page, offset, ident) == (0, 0, 0):
            break
        require(2 <= page < len(data) // PAGE_SIZE and offset < PAGE_SIZE,
                'invalid_index', 'index target outside file/page', cursor)
        require(0x10 <= ident < 0x80, 'unsupported_layout', 'long/unknown record ID framing', cursor)
        entry = IndexEntry(cursor, page, offset, ident)
        require(ident not in ids and entry.address not in targets,
                'invalid_index', 'duplicate record ID or target', cursor)
        entries.append(entry)
        ids.add(ident)
        targets.add(entry.address)
        cursor += 6
    require(cursor + 6 <= limit and not any(data[cursor:limit]),
            'unsupported_layout', 'missing zero sentinel or index holes/trailing data', cursor)
    require(len(entries) == table.record_count, 'invalid_index', 'count disagrees with index', base)
    return tuple(entries)


def _row(data, start, fields, *, index_offset=None, retired=False):
    limit = (start // PAGE_SIZE + 1) * PAGE_SIZE
    require(start + 2 <= limit and data[start] == (0x44 if retired else 0x80)
            and 0x10 <= data[start + 1] < 0x80,
            'invalid_record', 'unknown row prefix/ID', start)
    end = data.find(b'\x01\x02', start + 2, limit)
    require(end >= 0, 'invalid_record', 'missing page-bounded row terminator', start)
    payload = data[start + 2:end]
    require(not any(c in payload for c in (0, 2, 3)), 'invalid_record', 'reserved byte inside row', start)
    values = tuple(payload.split(b'\x01'))
    require(len(values) == fields, 'invalid_record', 'field count disagrees with schema', start)
    return Row(start, data[start + 1], data[start:end + 2], values, index_offset, retired)


def _rows(data, table, entries, reserved, page_owners, allow_retired):
    targets = {e.address: e for e in entries}
    pages = {table.data_page} | {e.page for e in entries}
    live, retired = {}, []
    for page in sorted(pages):
        require(page not in reserved and page not in page_owners,
                'invalid_index', 'data page aliases metadata/index/another table', page * PAGE_SIZE)
        page_owners.add(page)
        cursor, limit = page * PAGE_SIZE, (page + 1) * PAGE_SIZE
        while cursor < limit and data[cursor] != 3:
            entry = targets.get(cursor)
            if entry is not None:
                row = _row(data, cursor, table.column_count, index_offset=entry.index_offset)
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


def parse_bytes(source, *, allow_retired=False, max_pages=MAX_PAGES):
    """Read known framing, preserving opaque content; no universal ID/allocation policy.

    Retired-row scanning covers only starting and live-index-targeted data pages.
    Unreferenced pages stay opaque in ``Database.data``; they are not free space.
    """
    from dataclasses import replace
    require(isinstance(source, (bytes, bytearray, memoryview)), 'invalid_input', 'expected byte snapshot')
    require(type(max_pages) is int, 'unsupported_layout', 'page bound must be an integer')
    data = bytes(source)
    require(2 <= max_pages <= MAX_PAGES, 'unsupported_layout', 'invalid page bound')
    require(len(data) >= 6 * PAGE_SIZE, 'truncated_file', 'at least six complete pages required')
    require(len(data) % PAGE_SIZE == 0 and len(data) <= max_pages * PAGE_SIZE,
            'unsupported_layout', 'partial page or file exceeds bounded profile')
    require(data[:4] in (b'\x03FIL', b'\x03\x00\x00\x00'), 'invalid_header', 'unknown database header', 0)
    tables = _directory(data)
    reserved = {0, 1}
    for table in tables:
        require(table.index_page not in reserved, 'invalid_index', 'shared index page')
        reserved.add(table.index_page)
    page_owners = set()
    parsed = []
    for table in tables:
        entries = _index(data, table)
        rows, retired = _rows(data, table, entries, reserved, page_owners, allow_retired)
        parsed.append(replace(table, entries=entries, rows=rows, retired_rows=retired))
    db = Database(data, hashlib.sha256(data).hexdigest(), tuple(parsed))
    schema = db.table('DBCOLS')
    require(schema.column_count == 6 and not schema.retired_rows,
            'unsupported_schema', 'unsupported DBCOLS profile')
    columns = {table.name: {} for table in db.tables}
    for row in schema.rows:
        try:
            name, owner, pos, width, kind, unique = (v.decode('ascii') for v in row.fields)
        except UnicodeDecodeError as exc:
            raise DatabaseError('invalid_schema', 'non-ASCII column definition', row.offset) from exc
        position, size = decimal(row.fields[2], row.offset), decimal(row.fields[3], row.offset)
        require(owner in columns and position not in columns[owner] and name
                and size > 0 and len(kind) == 1 and unique == '0',
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
