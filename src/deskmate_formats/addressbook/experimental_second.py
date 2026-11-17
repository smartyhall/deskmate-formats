"""Exact-A01, ALPHA-only second contact; no general name collation or growth."""
from hashlib import sha256
import struct

from .personal import Contact, parse_bytes
from .writer import write_new

A01_SHA256 = '19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8'


def append_second_contact(source, contact, *, experimental=False):
    """Append an ALPHA contact to exact A01 and index it before USER A.

    Native evidence is ZULU/ALPHA, blank City, Work Phone 555-0100. Other first
    names/phones within Contact's established ASCII widths are offline-tested
    variants. Exact LastName ALPHA and blank City are deliberate restrictions;
    arbitrary K ordering, secondary keys, ties and third inserts are unsupported.
    """
    if experimental is not True:
        raise ValueError('explicit experimental=True required')
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected exact A01 byte snapshot')
    source = bytes(source)
    if len(source) != 10240 or sha256(source).hexdigest() != A01_SHA256:
        raise ValueError('requires exact hash-pinned one-contact A01 source')
    if not isinstance(contact, Contact) or contact.last_name != 'ALPHA' or contact.city:
        raise ValueError('only ALPHA second contact with blank City supported')
    book = parse_bytes(source)
    table = book.storage.table('DATA')
    old, = table.rows
    if (old.offset != 0x1000 or len(old.raw) != 61 or old.record_id != 16
            or table.record_count != 1 or table.next_id_candidate != 17
            or table.tokens[8:] != (b'3', b'2')):
        raise ValueError('A01 structure outside measured second-contact profile')
    fields = [b'', contact.first_name.encode('ascii'), b'ALPHA', b'', b'', b'',
              b'', b'', contact.work_phone.encode('ascii'), b'', b'', b'Birthday',
              b'', b'Anniversary', b'', b'n']
    row = b'\x80\x11' + b'\x01'.join(fields) + b'\x01\x02'
    at, index = old.end, table.index_page * 1024 + 40
    # Preserve the native two-byte headroom, marker and original physical row.
    if len(row) + 3 > (table.data_page + 1) * 1024 - at:
        raise ValueError('second contact needs unsupported data-page growth')
    output = bytearray(source)
    output[at:at + len(row) + 1] = row + b'\x03'
    struct.pack_into('<6H', output, index, 4, at % 1024, 17, 4, 0, 16)
    allowed = set(range(at, at + len(row) + 1)) | set(range(index, index + 12))
    for token, value in ((4, b'00002'), (6, b'00018')):
        pos = table.token_offset(token)
        output[pos:pos + 5] = value
        allowed.update(range(pos, pos + 5))
    result = bytes(output)
    after = parse_bytes(result)
    if (len(result) != len(source) or len(after.contacts) != 2
            or [r.record_id for r in after.contacts] != [17, 16]
            or after.contacts[1].row.raw != old.raw
            or after.contacts[0].known_fields != dict(first_name=contact.first_name,
                    last_name='ALPHA', city='', work_phone=contact.work_phone)
            or any(a != b and n not in allowed for n, (a, b) in enumerate(zip(source, result)))):
        raise ValueError('second-contact preservation postcondition failed')
    return result


def write_second_contact(path, source, contact, *, experimental=False):
    """Create only a new destination; source and existing outputs stay unchanged."""
    result = append_second_contact(source, contact, experimental=experimental)
    write_new(path, result)
    return result
