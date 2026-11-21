"""Independent positive, boundary and adversarial common-storage controls."""
from pathlib import Path
import struct
import unittest

from deskmate_formats.database import DatabaseError, inspect_help_directory, parse_bytes, parse_help_bytes
from database_synthetic import SELF, addressbook, framed
from synthetic import allocation, build


def help_database(tail, *, chained=False):
    # Use invented fields and records with independently assembled framing.
    data = bytearray(10240 if chained else 8192)
    data[:4] = b'\x03FIL'
    allocation(data, ((6, 8), (7, 9)) if chained else ())
    definitions = [('DBCOLS', SELF),
                   ('Rules', [(f'r{i}', 12, 'C') for i in range(8)]),
                   ('Text', [(f't{i}', 24, 'C') for i in range(3)])]
    schema = [
        (column.encode(), owner.encode(), str(position).encode(), str(width).encode(), kind.encode(), b'0')
        for owner, columns in definitions for position, (column, width, kind) in enumerate(columns, 1)
    ]
    directory = bytearray()
    text_rows = [(b'X', b'Y', b'')] * 165 if chained else [(b'Topic', b'Body', b'')]
    for number, ((owner, columns), fields) in enumerate(zip(definitions, [schema, [], text_rows])):
        page, index = 2 + number * 2, 3 + number * 2
        descriptor = ['T', owner, str(page), f'{len(columns):02d}', f'{len(fields):05d}', '000',
                      f'{16 + len(fields):05d}', str(index)]
        if number == 0:
            descriptor.extend(['2', '3'])
        directory.extend('\x01'.join(descriptor).encode() + b'\x01\x02')
        cursor = page * 1024
        index_start = index * 1024
        data[index_start:index_start + 40] = (b'\xff' * 9 + b'\0') * 4
        for slot, record in enumerate(fields):
            rid = (0x90 if chained and owner == 'Text' else 16) + slot
            row = (0x8000 + rid).to_bytes(2, 'big') + framed(16, record)[2:]
            if cursor % 1024 + len(row) >= 1024:
                assert chained and owner == 'Text' and cursor // 1024 == 6
                data[cursor] = 3
                cursor = 8192
            if slot == 164:
                index_start = 9216
                data[index_start:index_start + 40] = (b'\xff' * 9 + b'\0') * 4
            data[cursor:cursor + len(row)] = row
            struct.pack_into('<HHH', data, index_start + 40 + 6 * (slot % 164),
                             cursor // 1024, cursor % 1024, rid)
            cursor += len(row)
        data[cursor] = 3
    assert len(directory) == 0x64
    directory.extend(b'\x03' + tail)
    data[0x400:0x400 + len(directory)] = directory
    return bytes(data)


class DatabaseTests(unittest.TestCase):
    def test_both_header_profiles_and_schema_order(self):
        for data, counts in ((build('two'), [13, 3]), (addressbook(), [27, 0, 1, 1])):
            db = parse_bytes(data)
            self.assertEqual([t.record_count for t in db.tables], counts)
            self.assertEqual(db.data, data)
            self.assertEqual(db.header, data[:1024])
            self.assertEqual(db.tables[0].columns[0].name, 'cname')
        self.assertEqual(parse_bytes(addressbook()).table('DATA').columns[4].name, 'City')

    def test_help_directory_is_recognized_separately(self):
        tail = b'6\x017\x01\x02\x03'
        data = help_database(tail)
        directory = inspect_help_directory(data)
        self.assertEqual(([table.name for table in directory.tables], directory.marker_offset, directory.tail),
                         (['DBCOLS', 'Rules', 'Text'], 0x464, tail))
        with self.assertRaisesRegex(DatabaseError, 'nonzero tail'):
            parse_bytes(data)
        parsed = parse_help_bytes(data)
        self.assertEqual(parsed.data, data)
        self.assertEqual(parsed.table('Text').rows[0].fields, (b'Topic', b'Body', b''))

    def test_help_profile_does_not_mask_unknown_tails_or_bad_rows(self):
        with self.assertRaisesRegex(DatabaseError, 'unknown DeskMate Help directory'):
            parse_help_bytes(help_database(b'6\x018\x01\x02\x03'))
        with self.assertRaisesRegex(DatabaseError, 'unknown DeskMate Help directory'):
            inspect_help_directory(help_database(b'6\x017\x01\x02\x03').replace(b'Text\x016', b'Fake\x016', 1))
        data = bytearray(help_database(b'6\x017\x01\x02\x03'))
        data[6 * 1024] = 0xFF
        inspect_help_directory(data)
        with self.assertRaises(DatabaseError):
            parse_help_bytes(data)

    def test_help_index_chain_and_wider_row_identifiers(self):
        data = help_database(b'6\x017\x01\x02\x03', chained=True)
        text = parse_help_bytes(data).table('Text')
        self.assertEqual([row.record_id for row in text.rows], list(range(0x90, 0x90 + 165)))
        self.assertEqual([len(group.entries) for group in text.index_groups], [41] * 4 + [1, 0, 0, 0])
        self.assertEqual(text.data_pages, (6, 8))
        self.assertEqual(text.rows[-1].raw[:2], (0x8000 + text.rows[-1].record_id).to_bytes(2, 'big'))

        invalid = bytearray(data)
        invalid[text.rows[-1].offset] = 0x80
        with self.assertRaisesRegex(DatabaseError, 'index/row ID mismatch'):
            parse_help_bytes(invalid)
        invalid = bytearray(data)
        invalid[7 * 1024 + 40:7 * 1024 + 46] = bytes(6)
        with self.assertRaisesRegex(DatabaseError, 'index holes'):
            parse_help_bytes(invalid)

    def test_native_calendar_fixtures(self):
        root = Path(__file__).parents[1] / 'fixtures/application-generated/calendar'
        # This legacy positive test covers exactly the observed one-calendar
        # six-page specimens; it is not a test of every native CLN layout.
        for name in ('e01-86box-historical-match.cln',
                     'e02-86box-historical-match.cln',
                     'alarm-on-86box-trial-c.cln'):
            with self.subTest(path=name):
                db = parse_bytes((root / name).read_bytes())
                self.assertEqual(len(db.table('PERSONAL').rows), 2)

    def test_native_second_calendar_fixture_is_pinned_and_parses(self):
        import hashlib
        root = Path(__file__).parents[1] / 'fixtures/application-generated/calendar'
        native = (root / 'native-second-empty-calendar-operator.cln').read_bytes()
        source = (root / 'sdk-30-days-allocator-tool-generated.cln').read_bytes()
        self.assertEqual(len(native), 10240)
        self.assertEqual(hashlib.sha256(native).hexdigest(),
                         '338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5')
        self.assertEqual(len(source), 8192)
        # 61 PERSONAL appointments retain their exact raw data pages.
        for page in (4, 6, 7):
            self.assertEqual(native[page*1024:(page+1)*1024],
                             source[page*1024:(page+1)*1024])
        db = parse_bytes(native)
        self.assertEqual([t.name for t in db.tables], ['DBCOLS', 'PERSONAL', 'SECOND'])
        self.assertEqual([len(t.rows) for t in db.tables], [20, 62, 1])
        self.assertEqual([len(g.entries) for g in db.table('PERSONAL').index_groups], [20, 21, 21, 0])
        self.assertEqual(db.table('PERSONAL').data_pages, (4, 6, 7))
        self.assertEqual(db.table('SECOND').data_pages, (8,))
        self.assertEqual(db.data, native)

    def test_tool_generated_calendar_candidate(self):
        root = Path(__file__).parents[1] / 'fixtures/application-generated/calendar'
        path = root / 'sdk-14-days-tool-generated.cln'
        db = parse_bytes(path.read_bytes())
        self.assertEqual(db.sha256,
                         '85ad05d6bf58540e32349bbb559301d36aced164741b03b09b30d63f22d636ac')
        self.assertEqual(len(db.data), 6144)
        self.assertEqual(len(db.table('PERSONAL').rows), 30)
        self.assertEqual(len(db.table('PERSONAL').entries), 30)

    def test_additional_data_page_and_retired_row_opt_in(self):
        data = bytearray(build('two'))
        first_end = 4096 + len(parse_bytes(data).table('PERSONAL').rows[0].raw)
        row = parse_bytes(data).table('PERSONAL').rows[-1]
        data.extend(bytes(1024))
        allocation(data, ((4, 6),))
        data[6144:6144 + len(row.raw)] = row.raw
        data[6144 + len(row.raw)] = 3
        data[row.offset:5120] = b'\x03' + bytes(5120 - row.offset - 1)
        struct.pack_into('<HHH', data, row.index_offset, 6, 0, row.record_id)
        db = parse_bytes(data)
        self.assertEqual(db.table('PERSONAL').rows[-1].offset, 6144)
        self.assertLess(first_end, row.offset)
        # Retire first appointment without reclaiming its bytes or next-ID token.
        data[first_end] = 0x44
        data[5166:5172] = data[5172:5178]
        data[5172:5178] = bytes(6)
        data[0x435:0x43A] = b'00002'
        with self.assertRaises(DatabaseError):
            parse_bytes(data)
        table = parse_bytes(data, allow_retired=True).table('PERSONAL')
        self.assertEqual(len(table.rows), 2)
        self.assertEqual(table.retired_rows[0].offset, first_end)
        self.assertEqual(table.next_id_candidate, 19)

    def test_next_id_is_not_a_universal_max_plus_one(self):
        data = bytearray(build())
        data[0x418:0x41D] = b'00022'
        self.assertEqual(parse_bytes(data).table('DBCOLS').next_id_candidate, 22)

    def test_malformed_inputs(self):
        cases = []
        def mutate(at, value):
            data = bytearray(build('two'))
            data[at:at + len(value)] = value
            return data
        cases += [b'', build()[:-1], build() + bytes(1), mutate(0, b'BAD!'),
                  mutate(3072, b'X'), mutate(0x142E, struct.pack('<H', 99)),
                  mutate(0x1430, struct.pack('<H', 1024)),
                  mutate(0x1436, struct.pack('<H', 39)),
                  mutate(0x1438, struct.pack('<H', 17)),
                  mutate(0x142E, bytes(6)), mutate(0x103F, b'X'),
                  mutate(0x435, b'00004'), mutate(0x103D, b'\x03')]
        for n, data in enumerate(cases):
            with self.subTest(case=n), self.assertRaises(DatabaseError):
                parse_bytes(data)

    def test_page_alias_and_missing_schema_rejected(self):
        for at, value in ((0x142E, struct.pack('<H', 3)), (0x402, b'UNKNOWN'),
                          (0x800 + 2, b'other')):
            data = bytearray(build('two'))
            data[at:at + len(value)] = value
            with self.subTest(at=at), self.assertRaises(DatabaseError):
                parse_bytes(data)

    def test_input_types_and_bounds_are_checked_before_copying(self):
        for source in (None, 65536, 'not bytes'):
            with self.subTest(source=source), self.assertRaises(DatabaseError):
                parse_bytes(source)
        for bound in (True, 10.0, 1, 65):
            with self.subTest(bound=bound), self.assertRaises(DatabaseError):
                parse_bytes(build(), max_pages=bound)
