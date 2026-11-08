"""Independent database scaffolding; structural tests, never native fixtures."""
import struct
from synthetic import allocation

SELF = [('cname', 80, 'C'), ('owner', 80, 'C'), ('pos', 4, 'N'),
        ('len', 4, 'N'), ('type', 1, 'C'), ('uniq', 1, 'N')]
CONTACT = [('Title', 10, 'K'), ('FirstName', 18, 'K'), ('LastName', 20, 'K'),
           ('Address', 43, 'K'), ('City', 20, 'K'), ('State', 8, 'K'),
           ('Zip', 10, 'K'), ('CompanyName', 29, 'K'), ('WorkPhone', 20, 'K'),
           ('HomePhone', 20, 'K'), ('DateOne', 8, 'D'), ('NoteOne', 12, 'K'),
           ('DateTwo', 8, 'D'), ('NoteTwo', 12, 'K'), ('Notes', 40, 'K'),
           ('Christmas', 1, 'K')]


def framed(ident, values):
    return bytes((128, ident)) + b'\x01'.join(values) + b'\x01\x02'


def addressbook(fields=None, *, contact_rows=None):
    """Invented header/config; measured schema names, widths and table roles."""
    d = bytearray(10240)
    d[0] = 3
    d[384:384 + 21] = b'SYNTHETIC ADR HEADER!'
    allocation(d)
    definitions = [('DBCOLS', SELF), ('DATA', CONTACT),
                   ('NAMES', [('Internal', 20, 'K'), ('Users', 20, 'K')]),
                   ('CONFIG', [('UserId', 10, 'K'), ('LastList', 20, 'K'), ('ConfigInfo', 200, 'K')])]
    schemas, ident = [], 16
    for owner, columns in definitions:
        for pos, (name, width, kind) in enumerate(columns, 1):
            schemas.append((ident, framed(ident, [name.encode(), owner.encode(),
                            f'{pos:03d}'.encode(), str(width).encode(), kind.encode(), b'0'])))
            ident += 1
    # The real schema index orders by owner/position, independently of physical order.
    index_order = sorted(schemas, key=lambda pair: pair[1][2:].split(b'\x01')[1:3])
    data_rows = ([] if fields is None else [(16, framed(16, fields))]) if contact_rows is None else [
        (16 + n, framed(16 + n, values)) for n, values in enumerate(contact_rows)]
    rows = [schemas, data_rows,
            [(16, framed(16, [b'Title', b'Synthetic label']))],
            [(16, framed(16, [b'Test', b'All', b'Opaque']))]]
    cursor = 1024
    for n, ((name, columns), records) in enumerate(zip(definitions, rows)):
        page, index = 2 + 2 * n, 3 + 2 * n
        tokens = [b'T', name.encode(), str(page).encode(), f'{len(columns):02d}'.encode(),
                  f'{len(records):05d}'.encode(), b'000',
                  f'{max((i for i, _ in records), default=15) + 1:05d}'.encode(), str(index).encode()]
        tokens += [b'2', b'3'] if n == 0 else [b'3', b'2'] if n == 1 else []
        value = b'\x01'.join(tokens) + b'\x01\x02'
        d[cursor:cursor + len(value)] = value
        cursor += len(value)
        pos, locations = page * 1024, {}
        for rid, value in records:
            locations[rid] = pos - page * 1024
            d[pos:pos + len(value)] = value
            pos += len(value)
        d[pos] = 3
        d[index * 1024:index * 1024 + 40] = (b'\xff' * 9 + b'\0') * 4
        order = index_order if n == 0 else records
        for slot, (rid, _) in enumerate(order):
            struct.pack_into('<HHH', d, index * 1024 + 40 + 6 * slot, page, locations[rid], rid)
    d[cursor] = 3
    return bytes(d)
