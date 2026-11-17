"""Exercise the inspector against exact Form Setup and Filer output."""
from pathlib import Path
from struct import unpack_from
import unittest

from deskmate_formats import database, filer

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/filer'


class FilerNativeTest(unittest.TestCase):
    def test_empty_and_one_record(self):
        empty, saved = (filer.parse_file(FIXTURES / f'qrecord-{state}.fil')
                        for state in ('empty', 'one'))
        for snapshot in (empty, saved):
            self.assertEqual([table.name for table in snapshot.tables], ['DBCOLS', 'DATA', 'LAYOUTS'])
            self.assertEqual(len(snapshot.data), 8192)
            table = snapshot.table('DATA')
            self.assertEqual([(c.name, c.width, c.kind) for c in table.columns], [('FTXT_A', 22, 'K')])
            self.assertEqual((table.data_pages, table.index_page), ((6,), 7))
        self.assertEqual(empty.table('DATA').rows, ())
        self.assertEqual(empty.table('DATA').next_id_candidate, 16)
        table = saved.table('DATA')
        self.assertEqual((table.record_count, table.next_id_candidate), (1, 17))
        row, = table.rows
        self.assertEqual((row.offset, row.record_id, row.fields), (0x1800, 16, (b'F7Q9',)))
        self.assertEqual(saved.data[0x1800:0x1809], b'\x80\x10F7Q9\x01\x02\x03')
        self.assertEqual(unpack_from('<HHH', saved.data, 0x1C28), (6, 0, 16))
        changed = {i for i, (a, b) in enumerate(zip(empty.data, saved.data)) if a != b}
        self.assertEqual(changed, {0x435, 0x43F, *range(0x1800, 0x1809), 0x1C28, 0x1C2C})

    def test_inspection_reports_index_and_values(self):
        result = filer.inspect_file(FIXTURES / 'qrecord-one.fil')
        self.assertEqual(result['data_index'], [{
            'index_offset': 0x1C28, 'page': 6, 'in_page_offset': 0, 'record_id': 16,
        }])
        self.assertEqual(result['data_rows'][0]['fields'], ['F7Q9'])
        self.assertEqual(result['data_rows'][0]['fields_hex'], ['46375139'])
        self.assertEqual(result['retired_data_rows'], [])

    def test_damaged_filer_and_calendar_fail(self):
        raw = bytearray((FIXTURES / 'qrecord-one.fil').read_bytes())
        raw[0x1C2C] = 0x11
        with self.assertRaises(database.DatabaseError):
            filer.parse_bytes(raw)
        calendar = FIXTURES.parent / 'calendar/e02-86box-historical-match.cln'
        with self.assertRaisesRegex(database.DatabaseError, 'expected Filer'):
            filer.parse_file(calendar)
