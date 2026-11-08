"""Independent positive, boundary and adversarial common-storage controls."""
from pathlib import Path
import struct
import unittest

from deskmate_formats.database import DatabaseError, parse_bytes
from database_synthetic import addressbook
from synthetic import build


class DatabaseTests(unittest.TestCase):
    def test_both_header_profiles_and_schema_order(self):
        for data, counts in ((build('two'), [13, 3]), (addressbook(), [27, 0, 1, 1])):
            db = parse_bytes(data)
            self.assertEqual([t.record_count for t in db.tables], counts)
            self.assertEqual(db.data, data)
            self.assertEqual(db.header, data[:1024])
            self.assertEqual(db.tables[0].columns[0].name, 'cname')
        self.assertEqual(parse_bytes(addressbook()).table('DATA').columns[4].name, 'City')

    def test_native_calendar_fixtures(self):
        root = Path(__file__).parents[1] / 'fixtures/application-generated/calendar'
        for path in root.glob('*.cln'):
            with self.subTest(path=path.name):
                db = parse_bytes(path.read_bytes())
                self.assertEqual(len(db.table('PERSONAL').rows), 2)

    def test_additional_data_page_and_retired_row_opt_in(self):
        data = bytearray(build('two'))
        first_end = 4096 + len(parse_bytes(data).table('PERSONAL').rows[0].raw)
        row = parse_bytes(data).table('PERSONAL').rows[-1]
        data.extend(bytes(1024))
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
