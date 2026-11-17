"""Opt-in same-length edits and the two measured month-index split profiles.

Native evidence covers 59/61 appointments, one PERSONAL table, three data pages
and a full first index group. This is not a general DMDB rebalancer or updater.
"""
import struct

from deskmate_formats import database
from .personal import parse_bytes
from .writer import _publish_new


def _profile(source, experimental):
    if experimental is not True:
        raise ValueError('explicit experimental=True required')
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected Calendar byte snapshot')
    source = bytes(source)
    if len(source) != 8192:
        raise ValueError('requires measured eight-page month profile')
    raw = database.parse_bytes(source)
    calendar = parse_bytes(source, profile='sdk')
    if tuple(t.name for t in raw.tables) != ('DBCOLS', 'PERSONAL'):
        raise ValueError('only single-calendar PERSONAL maintenance supported')
    table = raw.table('PERSONAL')
    schema = raw.table('DBCOLS')
    if (table.data_pages != (4, 6, 7) or table.index_page != 5
            or table.record_count not in (60, 62) or table.retired_rows
            or schema.data_pages != (2,) or schema.index_page != 3
            or schema.record_count != 13 or schema.next_id_candidate != 29
            or schema.retired_rows or table.tokens[5] != b'000'
            or table.tokens[8:] != (b'1', b'2', b'4', b'5', b'7')
            or table.next_id_candidate != max(r.record_id for r in table.rows) + 1
            or len(calendar.internal_records) != 1
            or calendar.internal_records[0].record_id != 16):
        raise ValueError('source outside measured month maintenance profile')
    keys = []
    for event in calendar.appointments:
        if (None in (event.date, event.start_time, event.end_time, event.description)
                or event.undecoded_fields not in ({'Duration': '', 'Protected': '31'},
                                                 {'Duration': '', 'Protected': '71'})):
            raise ValueError('unsupported existing appointment fields')
        keys.append((event.date, event.start_time))
    if len(keys) != len(set(keys)):
        raise ValueError('tied date/start keys unsupported for maintenance')
    groups = table.index_groups
    counts = tuple(len(g.entries) for g in groups)
    tail = table.record_count - 41
    if counts == (41, tail, 0, 0):
        if any(g.routing_key != database.INDEX_SENTINEL for g in groups):
            raise ValueError('unsplit profile requires all sentinel routes')
        split = False
    elif counts == (20, 21, tail, 0):
        # Generic parsing already checks the finite route against its last row.
        if (groups[0].routing_key == database.INDEX_SENTINEL
                or any(g.routing_key != database.INDEX_SENTINEL for g in groups[1:])):
            raise ValueError('split profile requires only first finite route')
        split = True
    else:
        raise ValueError('unsupported subdivision occupancy; no general balancing')
    return source, raw, calendar, table, split


def normalize_index(source, *, experimental=False):
    """Return native-measured 20/21/tail layout; preserve every other byte.

    Accepted occupancies are 41/19 and 41/21, or their already split forms.
    Counts include the config row. Idempotent on the supported split layout.
    Unmeasured counts, routes, full later groups and multicalendar sources fail.
    """
    source, raw, _, table, split = _profile(source, experimental)
    if split:
        return source
    first, second = table.index_groups[:2]
    groups = (first.entries[:20], first.entries[20:], second.entries, ())
    base = table.index_page * 1024
    output = bytearray(source)
    output[base + 40:base + 1024] = bytes(984)
    for group, entries in enumerate(groups):
        for n, entry in enumerate(entries):
            struct.pack_into('<HHH', output, base + 40 + group * 246 + n * 6,
                             entry.page, entry.in_page_offset, entry.record_id)
    endpoint = next(r for r in table.rows if r.offset == groups[0][-1].address)
    output[base:base + 10] = database.index_prefix(endpoint.fields, (1, 2, 4, 5, 7))
    result = bytes(output)
    _, after, _, updated, is_split = _profile(result, True)
    if (not is_split or updated.raw_descriptor != table.raw_descriptor
            or [r.raw for r in updated.rows] != [r.raw for r in table.rows]
            or [(e.page, e.in_page_offset, e.record_id) for e in updated.entries] !=
               [(e.page, e.in_page_offset, e.record_id) for e in table.entries]
            or after.header != raw.header
            or result[:base] != source[:base]
            or result[base + 1024:] != source[base + 1024:]):
        raise ValueError('index normalization preservation check failed')
    return result


def replace_description(source, record_id, description, *, normalize=False,
                        experimental=False):
    """Replace one appointment's same-length printable-ASCII description.

    Row address/length, every other payload and the existing index are exact.
    Optional normalize=True also applies the measured index split. Date/time,
    IDs, config, alarm, variable-length edits and arbitrary layouts are excluded.
    """
    source, _, calendar, table, _ = _profile(source, experimental)
    if type(normalize) is not bool:
        raise ValueError('normalize must be bool')
    if type(record_id) is not int:
        raise ValueError('record_id must be an appointment integer ID')
    event = next((e for e in calendar.appointments if e.record_id == record_id), None)
    if event is None:
        raise ValueError('record_id is not an existing PERSONAL appointment')
    if (type(description) is not str or not 1 <= len(description) <= 120
            or any(not 0x20 <= ord(c) <= 0x7E for c in description)):
        raise ValueError('description requires 1..120 printable ASCII characters')
    row = next(r for r in table.rows if r.record_id == record_id)
    replacement = description.encode('ascii')
    if len(replacement) != len(row.fields[6]):
        raise ValueError('only same-length description replacement supported')
    # The ordinary row's first four sort fields fill its routing prefix before
    # Description. Unique date/start keys prove the unchanged index order.
    new_fields = row.fields[:6] + (replacement,)
    if database.index_prefix(new_fields, (1, 2, 4, 5, 7)) != database.index_prefix(row.fields, (1, 2, 4, 5, 7)):
        raise ValueError('description would change index routing prefix')
    at = row.offset + 2 + sum(len(field) + 1 for field in row.fields[:6])
    output = bytearray(source)
    output[at:at + len(replacement)] = replacement
    result = bytes(output)
    _, _, _, updated, _ = _profile(result, True)
    for before, after in zip(table.rows, updated.rows, strict=True):
        if (before.offset != after.offset or len(before.raw) != len(after.raw)
                or before.record_id != after.record_id
                or after.fields != (new_fields if before.record_id == record_id else before.fields)):
            raise ValueError('description preservation check failed')
    if result[:at] != source[:at] or result[at + len(replacement):] != source[at + len(replacement):]:
        raise ValueError('description edit escaped target bytes')
    return normalize_index(result, experimental=True) if normalize else result


def write_description(path, source, record_id, description, *, normalize=False,
                      experimental=False):
    """Publish only to a new destination; source is always an immutable snapshot."""
    result = replace_description(source, record_id, description, normalize=normalize,
                                 experimental=experimental)
    _publish_new(path, result)
    return result
