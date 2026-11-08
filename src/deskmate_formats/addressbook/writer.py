"""Experimental empty-to-one Address Book writer; never guesses multicontact order."""
from pathlib import Path
import os
import struct
import tempfile

from deskmate_formats.database import DatabaseError
from .personal import Contact, parse_bytes


def create_contact(source, contact):
    """Return new bytes while preserving all unrelated records, pages and tokens.

    Reproduces the A01–A04 insertion profile. Later inserts require native evidence.
    """
    if not isinstance(contact, Contact):
        raise ValueError('expected validated Contact')
    book = parse_bytes(source)
    table = book.storage.table('DATA')
    if table.rows:
        raise DatabaseError('unsupported_layout', 'multiple-contact insertion needs native index evidence')
    if (table.tokens[5] != b'000' or table.next_id_candidate != 16 or table.tokens[8:] != (b'3', b'2')
            or len(table.tokens[4]) != 5 or len(table.tokens[6]) != 5):
        raise DatabaseError('unsupported_layout', 'unknown empty-to-one counter/index profile')
    fields = [b'', contact.first_name.encode('ascii'), contact.last_name.encode('ascii'), b'',
              contact.city.encode('ascii'), b'', b'', b'', contact.work_phone.encode('ascii'),
              b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n']
    row = b'\x80\x10' + b'\x01'.join(fields) + b'\x01\x02'
    if len(row) + 1 > 1024:
        raise DatabaseError('capacity', 'contact requires another page')
    output = bytearray(book.storage.data)
    start, index = table.data_page * 1024, table.index_page * 1024 + 40
    output[start:start + len(row) + 1] = row + b'\x03'
    struct.pack_into('<HHH', output, index, table.data_page, 0, 16)
    for token, value in ((4, b'00001'), (6, b'00017')):
        pos = table.token_offset(token)
        output[pos:pos + 5] = value
    result = bytes(output)
    parsed = parse_bytes(result)
    if len(parsed.contacts) != 1 or parsed.contacts[0].known_fields != {
            'first_name': contact.first_name, 'last_name': contact.last_name,
            'city': contact.city, 'work_phone': contact.work_phone}:
        raise DatabaseError('postcondition', 'contact insertion failed')
    # Exact allowlist independently protects all unknown bytes/unrelated tables.
    allowed = set(range(start, start + len(row) + 1)) | set(range(index, index + 6))
    for token in (4, 6):
        pos = table.token_offset(token)
        allowed.update(range(pos, pos + 5))
    if len(result) != len(book.storage.data) or any(
            a != b and n not in allowed for n, (a, b) in enumerate(zip(book.storage.data, result))):
        raise DatabaseError('postcondition', 'insertion modified unrelated bytes')
    return result


def write_new(path, data):
    """Validated, flushed, atomic hard-link publication; existing paths fail."""
    parse_bytes(data)
    path = Path(path)
    fd, temp = tempfile.mkstemp(prefix='.addressbook-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
    finally:
        os.unlink(temp)
