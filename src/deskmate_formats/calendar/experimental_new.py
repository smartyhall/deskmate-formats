"""Opt-in E02-only new-file builder; source-backed chains, no native acceptance.

Never pass an existing multipage database. The six-page append APIs are separate.
See docs/research/dmdb-page-allocator.md for static evidence and strict limits.
"""
import hashlib
import struct

from .personal import parse_bytes
from .writer import _validate

E02_SHA256 = '0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9'
MAX_PAGES = 8


def _set_link(data, page, value):
    """UPD 1978: MSB-first packed-12 entry, preserving the adjacent nibble."""
    at = 0x20 + page + page // 2
    if page % 2:
        data[at] = (data[at] & 0xF0) | (value >> 8)
        data[at + 1] = value & 255
    else:
        data[at] = value >> 4
        data[at + 1] = (data[at + 1] & 15) | ((value & 15) << 4)


def build_new(source, events, *, experimental=False):
    """Build all additions in memory from exact E02; return bytes, never overwrite.

    Requires experimental=True. At most 100 ordinary SDK appointments may be
    added, subject to low-ID, fixed-index and eight-page bounds. Input order is
    physical insertion order; the index is sorted, with tied starts rejected.
    Native-file growth/reuse and accepting a prior tool output are unsupported.
    """
    if experimental is not True:
        raise ValueError('explicit experimental=True required')
    source = bytes(source)
    if len(source) != 6144 or hashlib.sha256(source).hexdigest() != E02_SHA256:
        raise ValueError('requires exact hash-pinned six-page E02 source')
    # Bound consumption even for an unbounded iterable.
    additions = []
    for event in events:
        if len(additions) == 100:
            raise ValueError('at most 100 additions')
        _validate(event, profile='sdk')
        additions.append(event)
    if not additions:
        raise ValueError('at least one addition required')
    db = parse_bytes(source, profile='sdk')
    output = bytearray(source)
    page = 4
    cursor = max(r.offset + r.length for r in db.records)
    keys = {(r.date, r.start_time) for r in db.appointments}
    entries = [(r.date, r.start_time, r.offset, r.record_id) for r in db.appointments]
    ident = db.metadata['tables']['PERSONAL']['next_id_candidate']
    for event in additions:
        key = (event.day.isoformat(), f'{event.start_minutes // 60:02d}:{event.start_minutes % 60:02d}')
        if key in keys:
            raise ValueError('tied date/start index keys unsupported')
        if ident >= 0x80:
            raise ValueError('long record ID unsupported')
        keys.add(key)
        weekday = (event.day.weekday() + 1) % 7 + 1
        fields = [bytes((0x61 + event.day.year - 1980, 0x61 + event.day.month, 0x61 + event.day.day)),
                  bytes((0x61 + weekday,)), b'', bytes((0x80 + event.start_minutes // 15,)),
                  bytes((0x80 + event.end_minutes // 15,)), event.protected_raw,
                  event.description.encode('ascii')]
        row = bytes((0x80, ident)) + b'\x01'.join(fields) + b'\x01\x02'
        # UPD 12DB..12F6 requires payload length +4, i.e. row length +2.
        if len(row) + 2 > (page + 1) * 1024 - cursor - 1:
            new_page = len(output) // 1024
            if new_page >= MAX_PAGES:
                raise ValueError('experimental eight-page ceiling exceeded')
            _set_link(output, new_page + 1, 0xFFF)
            _set_link(output, new_page, 0xFF8)
            _set_link(output, page, new_page)
            output.extend(bytes(1024))
            page = new_page
            cursor = page * 1024
        output[cursor:cursor + len(row) + 1] = row + b'\x03'
        entries.append((*key, cursor, ident))
        cursor += len(row)
        ident += 1
    ordered = [(r.offset, r.record_id) for r in db.internal_records]
    ordered += [(address, rid) for _, _, address, rid in sorted(entries)]
    if len(ordered) > 163:
        raise ValueError('index growth unsupported')
    for n, (address, rid) in enumerate(ordered):
        struct.pack_into('<HHH', output, 0x1428 + n * 6, address // 1024, address % 1024, rid)
    output[0x435:0x43A] = f'{len(ordered):05d}'.encode('ascii')
    output[0x43F:0x444] = f'{ident:05d}'.encode('ascii')
    result = bytes(output)
    checked = parse_bytes(result, profile='sdk')
    if len(checked.records) != len(ordered):
        raise ValueError('experimental build postcondition failed')
    return result
