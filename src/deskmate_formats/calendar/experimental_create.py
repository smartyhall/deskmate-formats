"""Exact-month-source, SECOND-only new-file structural reproduction experiment.

Replays the measured 41→20/21 split profile. It is not a general balancer or
proof that creating a calendar triggered the native repartition. No active
calendar selection, rename/delete, arbitrary names, or live save is implemented.
"""
import hashlib
import struct

from deskmate_formats import database
from .experimental_new import _set_link
from .personal import parse_bytes
from .writer import _publish_new


SOURCE_SHA256 = 'd35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106'


def create_second(source, *, name='SECOND', experimental=False):
    """Return a new file for the single observed SECOND creation profile.

    Exact source identity, name and repartition are intentional restrictions.
    The seven column rows, descriptor, config copy, locators, counters and map
    entries are serialized from source structure; no target file is loaded.
    """
    if experimental is not True:
        raise ValueError('explicit experimental=True required')
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected exact month-source byte snapshot')
    source = bytes(source)
    if len(source) != 8192 or hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('requires exact hash-pinned eight-page month source')
    if name != 'SECOND':
        raise ValueError('only exact name SECOND; normalization/other names unqualified')
    db = database.parse_bytes(source)
    calendar = parse_bytes(source, profile='sdk')
    schema, personal = db.table('DBCOLS'), db.table('PERSONAL')
    if (tuple(t.name for t in db.tables) != ('DBCOLS', 'PERSONAL')
            or schema.data_pages != (2,) or personal.data_pages != (4, 6, 7)
            or len(calendar.appointments) != 61 or schema.record_count != 13
            or schema.next_id_candidate != 29 or len(personal.columns) != 7
            or [len(g.entries) for g in personal.index_groups] != [41, 21, 0, 0]
            or any(g.routing_key != database.INDEX_SENTINEL for g in personal.index_groups)
            or schema.retired_rows or personal.retired_rows):
        raise ValueError('source outside observed creation/repartition profile')
    template = [r for r in schema.rows if r.fields[1] == personal.name.encode('ascii')]
    if len(template) != 7:
        raise ValueError('requires all seven PERSONAL schema templates')
    template.sort(key=lambda r: int(r.fields[2]))
    output = bytearray(source + bytes(2048))
    data_page, index_page = len(source) // 1024, len(source) // 1024 + 1
    for page, value in ((data_page, 0xFF8), (index_page, 0xFF8), (index_page + 1, 0xFFF)):
        _set_link(output, page, value)
    output[0x15] = len(db.tables)

    # Append seven schema rows and their six-byte locators in owner/position
    # order. Only this name, after PERSONAL, is qualified by the exact oracle.
    cursor = max(r.end for r in schema.rows)
    slot = schema.entries[-1].index_offset + 6
    data_end = (schema.data_page + 1) * database.PAGE_SIZE
    index_end = schema.index_page * database.PAGE_SIZE + database.INDEX_HEADER_SIZE + database.INDEX_GROUP_BYTES
    ident = schema.next_id_candidate
    for old in template:
        fields = list(old.fields)
        fields[1] = name.encode('ascii')
        row = bytes((0x80, ident)) + b'\x01'.join(fields) + b'\x01\x02'
        if ident >= 0x80 or cursor + len(row) + 3 > data_end or slot + 12 > index_end:
            raise ValueError('schema row/index space or low-ID bound exceeded')
        output[cursor:cursor + len(row) + 1] = row + b'\x03'
        struct.pack_into('<HHH', output, slot, schema.data_page, cursor % 1024, ident)
        ident += 1
        cursor += len(row)
        slot += 6
    for token, value in ((4, schema.record_count + 7), (6, ident)):
        at = schema.token_offset(token)
        output[at:at + 5] = f'{value:05d}'.encode('ascii')

    # New table uses the measured Calendar descriptor profile and a separate
    # source-derived config row. Existing PERSONAL descriptor stays unchanged.
    config = personal.rows[0]
    if config.record_id != 16 or config.raw.hex(' ') != calendar.internal_records[0].raw_hex:
        raise ValueError('unrecognized source configuration template')
    tokens = list(personal.tokens)
    tokens[1], tokens[2], tokens[4] = name.encode('ascii'), str(data_page).encode(), b'00001'
    tokens[6], tokens[7] = f'{config.record_id + 1:05d}'.encode(), str(index_page).encode()
    descriptor = b'\x01'.join(tokens) + b'\x01\x02'
    at = personal.descriptor_offset + len(personal.raw_descriptor)
    if source[at] != 3 or at + len(descriptor) >= 2048:
        raise ValueError('directory capacity exceeded')
    output[at:at + len(descriptor) + 1] = descriptor + b'\x03'
    at = data_page * 1024
    output[at:at + len(config.raw) + 1] = config.raw + b'\x03'
    at = index_page * 1024
    output[at:at + 40] = database.INDEX_HEADER
    struct.pack_into('<HHH', output, at + 40, data_page, 0, config.record_id)

    # Replay only the observed full-first-subdivision split: preserve every
    # logical locator, split 41 at slot 20, shift the prior second group intact.
    # General split selection, propagation, page growth and triggers are absent.
    old_first, old_second = personal.index_groups[:2]
    groups = (old_first.entries[:20], old_first.entries[20:], old_second.entries, ())
    base = personal.index_page * 1024
    output[base + 40:base + 1024] = bytes(984)
    for group, entries in enumerate(groups):
        for n, entry in enumerate(entries):
            struct.pack_into('<HHH', output, base + 40 + 246 * group + 6 * n,
                             entry.page, entry.in_page_offset, entry.record_id)
    rows = {r.offset: r for r in personal.rows}
    terminal = rows[groups[0][-1].address]
    output[base:base + 10] = database.index_prefix(terminal.fields, (1, 2, 4, 5, 7))
    result = bytes(output)
    after = database.parse_bytes(result)
    decoded = parse_bytes(result, profile='sdk')
    if (len(decoded.calendar('PERSONAL').appointments) != 61
            or decoded.calendar('SECOND').appointments
            or len(decoded.calendar('SECOND').internal_records) != 1
            or after.table('PERSONAL').raw_descriptor != personal.raw_descriptor
            or [r.raw for r in after.table('PERSONAL').rows] != [r.raw for r in personal.rows]
            or [(e.page, e.in_page_offset, e.record_id) for e in after.table('PERSONAL').entries] !=
               [(e.page, e.in_page_offset, e.record_id) for e in personal.entries]):
        raise ValueError('creation preservation postcondition failed')
    for page in personal.data_pages:
        if result[page * 1024:(page + 1) * 1024] != source[page * 1024:(page + 1) * 1024]:
            raise ValueError('creation changed PERSONAL data page')
    return result


def write_second(path, source, *, name='SECOND', experimental=False):
    """Create and atomically publish to a new destination only."""
    result = create_second(source, name=name, experimental=experimental)
    _publish_new(path, result)
    return result
