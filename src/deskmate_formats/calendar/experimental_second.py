"""Opt-in first appointment in SECOND, from exact native empty-SECOND A only.

Genuine row/index/counter serialization. No expected-output bytes, patch table,
allocator, splitting, deletion, recurrence, or acceptance of previous outputs.
"""
import hashlib
import struct

from deskmate_formats import database
from .codec import encode_date, encode_time
from .personal import parse_bytes
from .writer import _publish_new, _validate


SOURCE_SHA256 = '338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5'


def append_first_second(source, event, *, calendar='SECOND', experimental=False):
    """Return a new snapshot with one ordinary event; never mutate the source.

    Only SECOND's first appointment is supported, on a fixed single data/index
    page with low IDs and SDK ordinary fields. Other validated event values are
    experimental; only the documented A→B event has a native byte oracle.
    """
    if experimental is not True:
        raise ValueError('explicit experimental=True required')
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected exact native A byte snapshot')
    data = bytes(source)
    if len(data) != 10240 or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('requires exact hash-pinned native empty-SECOND A source')
    if calendar != 'SECOND':
        raise ValueError('only owning calendar SECOND is supported')
    _validate(event, profile='sdk')
    db = database.parse_bytes(data)
    parsed = parse_bytes(data, profile='sdk')
    table = db.table(calendar)
    named = parsed.calendar(calendar)
    if (tuple(t.name for t in db.tables) != ('DBCOLS', 'PERSONAL', 'SECOND')
            or table.data_pages != (table.data_page,)
            or table.record_count != 1 or named.appointments
            or len(named.internal_records) != 1 or table.retired_rows
            or table.tokens[5] != b'000'):
        raise ValueError('requires existing empty SECOND and one configuration row')
    ident = table.next_id_candidate
    if not 0x10 < ident < 0x80 or ident != max(r.record_id for r in table.rows) + 1:
        raise ValueError('unsupported low-ID/next-ID profile')
    groups = table.index_groups
    if (len(groups[0].entries) != 1 or any(g.entries for g in groups[1:])
            or any(g.routing_key != database.INDEX_SENTINEL for g in groups)):
        raise ValueError('unsupported SECOND index subdivision/capacity profile')
    weekday = (event.day.weekday() + 1) % 7 + 1
    fields = (encode_date(event.day), bytes((0x61 + weekday,)), event.duration_raw,
              encode_time(event.start_minutes), encode_time(event.end_minutes),
              event.protected_raw, event.description.encode('ascii'))
    row = bytes((0x80, ident)) + b'\x01'.join(fields) + b'\x01\x02'
    address = max(r.end for r in table.rows)
    page_end = (table.data_page + 1) * database.PAGE_SIZE
    # The native ordinary append guard reserves two additional bytes beyond
    # the serialized row and the required page-local list marker.
    if (data[address] != 3 or any(data[address + 1:page_end])
            or len(row) + 2 > page_end - address - 1):
        raise ValueError('insufficient page space; allocation/packing unsupported')
    index = groups[0].entries[-1].index_offset + 6
    group_end = table.index_page * database.PAGE_SIZE + database.INDEX_HEADER_SIZE + database.INDEX_GROUP_BYTES
    if index + 12 > group_end or any(data[index:group_end]):
        raise ValueError('insufficient index capacity; splitting unsupported')
    output = bytearray(data)
    output[address:address + len(row) + 1] = row + b'\x03'
    struct.pack_into('<HHH', output, index, table.data_page, address % database.PAGE_SIZE, ident)
    for token, value in ((4, table.record_count + 1), (6, ident + 1)):
        old = table.tokens[token]
        encoded = f'{value:05d}'.encode('ascii')
        if len(old) != 5 or len(encoded) != 5:
            raise ValueError('unsupported descriptor counter width/range')
        start = table.token_offset(token)
        output[start:start + 5] = encoded
    result = bytes(output)
    after = database.parse_bytes(result)
    decoded = parse_bytes(result, profile='sdk').calendar(calendar)
    new = after.table(calendar)
    if (len(result) != len(data) or len(decoded.appointments) != 1
            or new.rows[:-1] != table.rows or new.rows[-1].fields != fields
            or new.entries[:-1] != table.entries or new.next_id_candidate != ident + 1):
        raise ValueError('SECOND append postcondition failed')
    for before in db.tables:
        if before.name != calendar and after.table(before.name) != before:
            raise ValueError('append changed an unrelated table')
    # Check preservation beyond decoded contents: unknown header, directory,
    # schema, PERSONAL index and all untouched padding must remain exact.
    allowed = set(range(address, address + len(row) + 1)) | set(range(index, index + 6))
    for token in (4, 6):
        allowed.update(range(table.token_offset(token), table.token_offset(token) + 5))
    if any(a != b and i not in allowed for i, (a, b) in enumerate(zip(data, result, strict=True))):
        raise ValueError('append modified bytes outside row/index/counters')
    return result


def write_first_second(path, source, event, *, calendar='SECOND', experimental=False):
    """Generate and atomically publish a new file, with no overwrite fallback."""
    result = append_first_second(source, event, calendar=calendar, experimental=experimental)
    _publish_new(path, result)
    return result
