"""Original adversarial parser checks, now using independent synthetic bytes."""
import struct
import unittest
from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes
from synthetic import build

class MutationTests(unittest.TestCase):
    def setUp(self):
        self.data = bytearray(build('two'))

    def fails(self, code=None):
        with self.assertRaises(CalendarParseError) as caught:
            parse_bytes(self.data)
        if code:
            self.assertEqual(caught.exception.code, code, str(caught.exception))
        self.assertTrue(str(caught.exception))

    def replace_rows_in_memory(self, field_changes=None, order=(0x10, 0x11, 0x12),
                               index_order=(0x10, 0x11, 0x12)):
        """Construct synthetic bytes for tests only. No file writes or public writer."""
        rows = {}
        for at in (0x1428, 0x142E, 0x1434):
            page, off, ident = struct.unpack_from('<HHH', self.data, at)
            start = page*1024 + off
            end = self.data.index(b'\x01\x02', start+2)
            values = bytes(self.data[start+2:end]).split(b'\x01')
            for number, value in (field_changes or {}).get(ident, {}).items():
                values[number] = value
            rows[ident] = bytes((0x80, ident)) + b'\x01'.join(values) + b'\x01\x02'
        self.data[0x1000:0x1400] = b'\x00'*1024
        cursor, offsets = 0x1000, {}
        for ident in order:
            offsets[ident] = cursor - 0x1000
            row = rows[ident]
            self.data[cursor:cursor+len(row)] = row
            cursor += len(row)
        self.data[cursor] = 3
        self.data[0x1428:] = b'\x00'*(6144-0x1428)
        for slot, ident in enumerate(index_order):
            struct.pack_into('<HHH', self.data, 0x1428+slot*6, 4, offsets[ident], ident)
        self.data[0x435:0x43A] = f'{len(index_order):05d}'.encode('ascii')

    def test_relocated_records_and_permuted_index(self):
        self.replace_rows_in_memory(order=(0x12, 0x10, 0x11), index_order=(0x11, 0x12, 0x10))
        before = bytes(self.data)
        db = parse_bytes(self.data)
        by_id = {r.record_id:r for r in db.records}
        self.assertEqual((by_id[0x11].offset, by_id[0x12].offset), (0x103F, 0x1000))
        self.assertEqual((by_id[0x11].description, by_id[0x12].description), ('LPHa124', 'BETA456'))
        self.assertEqual(by_id[0x10].kind, 'internal/control')
        self.assertEqual(bytes(self.data), before)

    def test_truncated_files(self):
        for size in (0, 3, 1024, 4096, 5120, 6143):
            with self.subTest(size=size), self.assertRaisesRegex(CalendarParseError, 'truncated_file'):
                parse_bytes(self.data[:size])

    def test_additional_pages_rejected(self):
        self.data += b'\x00'*1024
        self.fails('unsupported_layout')

    def test_bad_magic(self):
        self.data[:4] = b'\x03BAD'
        self.fails('invalid_header')

    def test_out_of_file_index_page(self):
        struct.pack_into('<H', self.data, 0x142E, 999)
        self.fails('invalid_index')

    def test_out_of_page_index_offset(self):
        struct.pack_into('<H', self.data, 0x1430, 1024)
        self.fails('invalid_index')

    def test_index_points_into_wrong_page(self):
        struct.pack_into('<H', self.data, 0x142E, 2)
        self.fails('unsupported_layout')

    def test_index_points_into_middle_of_row(self):
        struct.pack_into('<H', self.data, 0x1430, 0x28)
        self.fails('invalid_record')

    def test_duplicate_index_id(self):
        struct.pack_into('<H', self.data, 0x1438, 0x11)
        self.fails('invalid_index')

    def test_duplicate_index_address(self):
        struct.pack_into('<H', self.data, 0x1436, 0x27)
        self.fails('invalid_index')

    def test_index_hole_with_hidden_record(self):
        self.data[0x142E:0x1434] = b'\x00'*6
        self.fails('unsupported_layout')

    def test_index_count_mismatch(self):
        self.data[0x439] = ord('4')
        self.fails('invalid_index')

    def test_unknown_next_id_relation(self):
        self.data[0x443] = ord('8')
        self.fails('unsupported_layout')

    def test_long_id_encoding_rejected(self):
        struct.pack_into('<H', self.data, 0x1432, 0x111)
        self.fails('unsupported_layout')

    def test_unknown_index_header(self):
        self.data[0x1400] = 0
        self.fails('unsupported_layout')

    def test_unknown_table_descriptor(self):
        at = self.data.index(b'PERSONAL')
        self.data[at] = ord('X')
        self.fails('unsupported_layout')

    def test_bad_metadata_decimal(self):
        self.data[0x439] = ord('X')
        self.fails('invalid_metadata')

    def test_changed_schema(self):
        at = self.data.index(b'Date\x01PERSONAL')
        self.data[at] = ord('X')
        self.fails('unsupported_schema')

    def test_invalid_schema_index(self):
        struct.pack_into('<H', self.data, 0xC28, 99)
        self.fails('invalid_index')

    def test_row_id_disagrees_with_index(self):
        self.data[0x1028] = 0x12
        self.fails('invalid_record')

    def test_missing_row_terminator(self):
        self.data[0x1056] = 0
        self.fails('invalid_record')

    def test_malformed_field_count(self):
        self.data[0x102C] = 0x7E
        self.fails('invalid_record')

    def test_bad_field_width(self):
        self.replace_rows_in_memory({0x11:{0:b'\x90\x6c'}})
        self.fails('invalid_record')

    def test_missing_list_marker(self):
        self.data[0x1057] = 0
        self.fails('unsupported_layout')

    def test_unindexed_data_in_padding(self):
        self.data[0x1100] = 0x80
        self.fails('unsupported_layout')

    def test_invalid_calendar_date(self):
        self.data[0x102B] = 0x61
        self.fails('invalid_date')

    def test_stored_weekday_inconsistent(self):
        self.data[0x102D] = 0x62
        self.fails('inconsistent_weekday')

    def test_unknown_valid_date_retained_without_extrapolation(self):
        self.data[0x1029] = 0x91
        row = parse_bytes(self.data).appointments[0]
        self.assertIsNone(row.date)
        self.assertEqual(row.undecoded_fields['Date'], '91 6c 62')
        self.assertTrue(any('outside' in w for w in row.warnings))

    def test_unmeasured_time_retained_without_extrapolation(self):
        self.data[0x1030] = 0xA6
        row = parse_bytes(self.data).appointments[0]
        self.assertIsNone(row.start_time)
        self.assertEqual(row.undecoded_fields['StartTime'], 'a6')

    def test_unknown_weekday_retained(self):
        self.data[0x102D] = 0x64
        row = parse_bytes(self.data).appointments[0]
        self.assertIsNone(row.day_of_week)
        self.assertEqual(row.undecoded_fields['DayOfWeek'], '64')

    def test_empty_time_retained(self):
        self.replace_rows_in_memory({0x11:{3:b''}})
        row = parse_bytes(self.data).appointments[0]
        self.assertIsNone(row.start_time)
        self.assertEqual(row.undecoded_fields['StartTime'], '')

    def test_duration_protected_and_non_ascii_description_retained(self):
        self.replace_rows_in_memory({0x11:{2:b'Q',5:b'9',6:b'\xc4PHa124'}})
        row = parse_bytes(self.data).appointments[0]
        self.assertIsNone(row.description)
        self.assertEqual(row.undecoded_fields['Duration'], '51')
        self.assertEqual(row.undecoded_fields['Protected'], '39')
        self.assertEqual(row.undecoded_fields['Description'], 'c4 50 48 61 31 32 34')
        self.assertNotIn('alarm', row.to_dict())

    def test_reversed_times_unsupported(self):
        self.data[0x1030] = 0xB0
        self.fails('unsupported_time_order')

    def test_unknown_internal_signature_not_hidden(self):
        self.data[0x100D] = ord('f')
        self.fails('unsupported_record')

    def test_bad_date_not_misclassified_as_internal(self):
        self.data[0x1029:0x102C] = b'  \xff'
        self.fails('invalid_date')

    def test_missing_internal_row_unsupported(self):
        self.replace_rows_in_memory(order=(0x11,0x12), index_order=(0x11,0x12))
        self.fails('unsupported_record')

    def test_unknown_header_bytes_preserved(self):
        self.data[200] = 0x77
        result = parse_bytes(self.data)
        self.assertEqual(bytes.fromhex(result.metadata['header_page_raw_hex'])[200], 0x77)
