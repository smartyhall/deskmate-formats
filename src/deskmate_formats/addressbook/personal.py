"""Schema-aware reader; only four contact fields have controlled UI evidence."""
from dataclasses import dataclass
from pathlib import Path

from deskmate_formats.database import Database, DatabaseError, Row, parse_bytes as parse_database, require

CONTACT_SCHEMA = (('Title', 10, 'K'), ('FirstName', 18, 'K'), ('LastName', 20, 'K'),
                  ('Address', 43, 'K'), ('City', 20, 'K'), ('State', 8, 'K'),
                  ('Zip', 10, 'K'), ('CompanyName', 29, 'K'), ('WorkPhone', 20, 'K'),
                  ('HomePhone', 20, 'K'), ('DateOne', 8, 'D'), ('NoteOne', 12, 'K'),
                  ('DateTwo', 8, 'D'), ('NoteTwo', 12, 'K'), ('Notes', 40, 'K'),
                  ('Christmas', 1, 'K'))
VERIFIED_FIELDS = {'first_name': 'FirstName', 'last_name': 'LastName',
                   'city': 'City', 'work_phone': 'WorkPhone'}


@dataclass(frozen=True)
class Contact:
    """Verified field subset; other schema-named fields must remain opaque."""
    first_name: str
    last_name: str
    city: str = ''
    work_phone: str = ''

    def __post_init__(self):
        for name, width in (('first_name', 18), ('last_name', 20), ('city', 20), ('work_phone', 20)):
            value = getattr(self, name)
            if type(value) is not str or len(value) > width or any(not 32 <= ord(c) < 127 for c in value):
                raise ValueError(f'{name} requires at most {width} printable ASCII characters')
        if not self.first_name or not self.last_name:
            raise ValueError('single-contact experimental profile requires first and last names')


@dataclass(frozen=True)
class ContactRecord:
    row: Row
    raw_fields: tuple[tuple[str, bytes], ...]

    @property
    def record_id(self):
        return self.row.record_id

    @property
    def known_fields(self):
        raw = dict(self.raw_fields)
        return {name: raw[column].decode('ascii') if all(32 <= c < 127 for c in raw[column]) else None
                for name, column in VERIFIED_FIELDS.items()}

    @property
    def opaque_fields(self):
        return {k: v for k, v in self.raw_fields if k not in VERIFIED_FIELDS.values()}

    def to_dict(self):
        return {'storage_record_id': self.record_id, 'offset': self.row.offset,
                'index_offset': self.row.index_offset, 'length': len(self.row.raw),
                'known_fields': self.known_fields,
                'raw_fields_hex': {k: v.hex(' ') for k, v in self.raw_fields},
                'opaque_fields_hex': {k: v.hex(' ') for k, v in self.opaque_fields.items()},
                'raw_hex': self.row.raw.hex(' ')}


@dataclass(frozen=True)
class AddressBook:
    storage: Database
    contacts: tuple[ContactRecord, ...]
    warnings: tuple[str, ...]

    def to_dict(self):
        return {'sha256': self.storage.sha256, 'size': len(self.storage.data),
                'profile': 'addressbook-3.05-single-page', 'contact_count': len(self.contacts),
                'warnings': list(self.warnings), 'contacts': [c.to_dict() for c in self.contacts]}


def parse_bytes(source):
    storage = parse_database(source, max_pages=10)
    require(len(storage.data) == 10240 and storage.data[:4] == b'\x03\0\0\0',
            'unsupported_layout', 'only observed ten-page ADR profile is supported')
    require(tuple(t.name for t in storage.tables) == ('DBCOLS', 'DATA', 'NAMES', 'CONFIG'),
            'unsupported_schema', 'unknown Address Book table set')
    for n, table in enumerate(storage.tables):
        require((table.data_page, table.index_page) == (2 + 2 * n, 3 + 2 * n)
                and all(e.page == table.data_page for e in table.entries),
                'unsupported_layout', 'Address Book additional data/index pages unsupported')
    for name, expected in (
            ('DATA', CONTACT_SCHEMA),
            ('NAMES', (('Internal', 20, 'K'), ('Users', 20, 'K'))),
            ('CONFIG', (('UserId', 10, 'K'), ('LastList', 20, 'K'), ('ConfigInfo', 200, 'K')))):
        require(tuple((c.name, c.width, c.kind) for c in storage.table(name).columns) == expected,
                'unsupported_schema', f'unknown {name} schema')
    table = storage.table('DATA')
    contacts = []
    for row in table.rows:
        require(all(len(value) <= col.width for value, col in zip(row.fields, table.columns, strict=True)),
                'invalid_record', 'contact exceeds declared field width', row.offset)
        contacts.append(ContactRecord(row, tuple((c.name, value) for c, value in zip(table.columns, row.fields))))
    warnings = ['Only FirstName, LastName, City and WorkPhone have controlled populated UI evidence.',
                'Other fields retain schema names and raw bytes; dates/defaults/Christmas semantics are opaque.']
    if len(contacts) > 1:
        warnings.append('Multiple contacts read structurally; native ordering and insertion policy are unverified.')
    return AddressBook(storage, tuple(contacts), tuple(warnings))


def parse_file(path):
    with Path(path).open('rb') as handle:
        data = handle.read(10241)
    return parse_bytes(data)
