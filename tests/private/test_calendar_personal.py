"""Fixture regression and in-memory adversarial tests; never rewrite CLN files."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import mock_open, patch

from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes, parse_file
from deskmate_formats.calendar.cli import main

LAB = Path(os.environ['DOSLAB_ROOT'])  # Explicit private fixture opt-in; no fallback.
ROOT = LAB / 'EXPERIMENTS/PHASE2'
FIXTURES = [
    ('E00_default', None),
    ('E01_one_event', ('2026-10-23', 'Friday', '09:00', '10:00', 'LPHa123')),
    ('E02_description_change', ('2026-10-23', 'Friday', '09:00', '10:00', 'LPHa124')),
    ('E03_start_0915', ('2026-10-23', 'Friday', '09:15', '10:00', 'LPHa124')),
    ('E04_end_1015', ('2026-10-23', 'Friday', '09:15', '10:15', 'LPHa124')),
    ('E05_date_20261024', ('2026-10-24', 'Saturday', '09:15', '10:15', 'LPHa124')),
    ('E06_date_20261101', ('2026-11-01', 'Sunday', '09:15', '10:15', 'LPHa124')),
    ('E07_date_20271101', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124')),
    ('E08_two_events', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124')),
    ('E09_delete_beta456', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124')),
    ('E10_reuse_gamma45', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124')),
    ('E11_description_growth', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124XYZ')),
    ('E12_delete_gamma45', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124XYZ')),
    ('E13_description_shrink', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124')),
    ('E14_interior_shrink', ('2027-11-01', 'Monday', '09:15', '10:15', 'LPHa124XYZ')),
]


def fixture_path(name):
    return ROOT / name / 'files/DESKMATE/PERSONAL.CLN'


class FixtureTests(unittest.TestCase):
    def test_e14_nontrailing_shrink_compacts_following_row_without_renumbering(self):
        old=parse_file(fixture_path('E11_description_growth'))
        path=fixture_path('E14_interior_shrink')
        new=parse_file(path)
        before={r.description:r for r in old.appointments}
        after={r.description:r for r in new.appointments}
        self.assertEqual(set(after),{'LPHa124XYZ','GAMM'})
        prior_gamma,gamma=before['GAMMA45'],after['GAMM']
        prior_lpha,lpha=before['LPHa124XYZ'],after['LPHa124XYZ']
        self.assertEqual((gamma.record_id,gamma.offset,gamma.index_offset),
                         (prior_gamma.record_id,prior_gamma.offset,prior_gamma.index_offset))
        self.assertEqual(gamma.length,prior_gamma.length-3)
        self.assertEqual(lpha.offset,prior_lpha.offset-3)
        self.assertEqual(lpha.offset,gamma.offset+gamma.length)
        self.assertEqual((lpha.record_id,lpha.index_offset,lpha.length,lpha.raw_hex),
                         (prior_lpha.record_id,prior_lpha.index_offset,prior_lpha.length,prior_lpha.raw_hex))
        old_raw,new_raw=bytes.fromhex(prior_gamma.raw_hex),bytes.fromhex(gamma.raw_hex)
        self.assertEqual(new_raw[:-2],old_raw[:-5])
        self.assertEqual(new_raw[-2:],old_raw[-2:])
        for key in gamma.raw_fields:
            if key!='Description':self.assertEqual(gamma.raw_fields[key],prior_gamma.raw_fields[key])
        self.assertEqual(old.internal_records[0].raw_hex,new.internal_records[0].raw_hex)
        self.assertEqual(old.metadata,new.metadata)
        self.assertEqual([r.record_id for r in sorted(old.records,key=lambda r:r.offset)],
                         [r.record_id for r in sorted(new.records,key=lambda r:r.offset)])
        raw=path.read_bytes()
        for row in new.records:
            page,offset,ident=struct.unpack_from('<HHH',raw,row.index_offset)
            self.assertEqual((page*1024+offset,ident),(row.offset,row.record_id))
        marker=lpha.offset+lpha.length
        self.assertEqual(raw[marker],3)
        self.assertFalse(any(raw[marker+1:((lpha.offset//1024)+1)*1024]))
        self.assertEqual(raw.count(bytes.fromhex(lpha.raw_hex)),1)
        self.assertNotIn(old_raw,raw)
        self.assertEqual(len(raw),fixture_path('E11_description_growth').stat().st_size)
        old_marker=prior_lpha.offset+prior_lpha.length
        self.assertEqual(old_marker-marker,3)
        self.assertEqual(raw[marker+1:old_marker+1],bytes(3))

    def test_e13_shrinkage_restores_independent_baselines(self):
        before_path=fixture_path('E12_delete_gamma45')
        path=fixture_path('E13_description_shrink')
        before,after=before_path.read_bytes(),path.read_bytes()
        old,new=parse_file(before_path),parse_file(path)
        self.assertEqual(len(new.appointments),1)
        prior,row=old.appointments[0],new.appointments[0]
        self.assertEqual((row.record_id,row.offset,row.index_offset),
                         (prior.record_id,prior.offset,prior.index_offset))
        self.assertEqual(row.length,prior.length-3)
        self.assertEqual(row.description,'LPHa124')
        prior_raw,row_raw=bytes.fromhex(prior.raw_hex),bytes.fromhex(row.raw_hex)
        self.assertEqual(row_raw[:-2],prior_raw[:-5])
        self.assertEqual(row_raw[-2:],prior_raw[-2:])
        for key in prior.raw_fields:
            if key!='Description':self.assertEqual(row.raw_fields[key],prior.raw_fields[key])
        self.assertEqual(new.internal_records[0].raw_hex,old.internal_records[0].raw_hex)
        self.assertEqual(new.metadata,old.metadata)
        marker=row.offset+row.length
        self.assertEqual(after[marker],3)
        page_end=((row.offset//1024)+1)*1024
        self.assertFalse(any(after[marker+1:page_end]))
        first_change=row.offset+len(row_raw)-2
        self.assertEqual([i for i,(a,b) in enumerate(zip(before,after)) if a!=b],
                         list(range(first_change,prior.offset+prior.length+1)))
        self.assertEqual(before[first_change:first_change+6],b'XYZ\x01\x02\x03')
        self.assertEqual(after[first_change:first_change+6],b'\x01\x02\x03\x00\x00\x00')
        for baseline in ('E07_date_20271101','E09_delete_beta456'):
            with self.subTest(baseline=baseline):self.assertEqual(after,fixture_path(baseline).read_bytes())

    def test_e12_interior_deletion_compacts_and_renumbers_survivor(self):
        old = parse_file(fixture_path('E11_description_growth'))
        path = fixture_path('E12_delete_gamma45')
        new = parse_file(path)
        previous = {r.description:r for r in old.appointments}
        self.assertEqual(len(new.appointments), 1)
        survivor = new.appointments[0]
        prior, deleted = previous['LPHa124XYZ'], previous['GAMMA45']
        self.assertEqual(survivor.description, prior.description)
        self.assertEqual(survivor.offset, deleted.offset)
        self.assertEqual(prior.offset-survivor.offset, deleted.length)
        self.assertEqual(survivor.record_id, prior.record_id-1)
        self.assertEqual(survivor.record_id, deleted.record_id)
        self.assertEqual(survivor.length, prior.length)
        self.assertEqual(survivor.index_offset, prior.index_offset)
        self.assertEqual(bytes.fromhex(survivor.raw_hex)[2:], bytes.fromhex(prior.raw_hex)[2:])
        self.assertEqual((survivor.date,survivor.day_of_week,survivor.start_time,survivor.end_time,survivor.undecoded_fields),
                         (prior.date,prior.day_of_week,prior.start_time,prior.end_time,prior.undecoded_fields))
        internal = new.internal_records[0]
        self.assertEqual(internal.raw_hex, old.internal_records[0].raw_hex)
        self.assertEqual(survivor.offset, internal.offset+internal.length)
        raw = path.read_bytes()
        page, offset, ident = struct.unpack_from('<HHH', raw, survivor.index_offset)
        self.assertEqual((page*1024+offset, ident), (survivor.offset,survivor.record_id))
        self.assertEqual(raw[deleted.index_offset:deleted.index_offset+6], bytes(6))
        marker = survivor.offset+survivor.length
        self.assertEqual(raw[marker], 3)
        self.assertFalse(any(raw[marker+1:(page+1)*1024]))
        self.assertNotIn(b'GAMMA45', raw)
        self.assertNotIn(bytes.fromhex(prior.raw_hex), raw)
        self.assertEqual(len(raw), fixture_path('E11_description_growth').stat().st_size)
        for field in ('record_count','next_id_candidate'):
            self.assertEqual(new.metadata['tables']['PERSONAL'][field],old.metadata['tables']['PERSONAL'][field]-1)

    def test_e11_growth_relocates_events_and_reassigns_ids(self):
        old = parse_file(fixture_path('E10_reuse_gamma45'))
        new = parse_file(fixture_path('E11_description_growth'))
        previous = {r.description:r for r in old.appointments}
        current = {r.description:r for r in new.appointments}
        first, gamma = current['LPHa124XYZ'], current['GAMMA45']
        self.assertEqual((first.record_id,first.offset,first.length,first.index_offset),
                         (0x12,0x103F,27,0x142E))
        self.assertEqual((gamma.record_id,gamma.offset,gamma.length,gamma.index_offset),
                         (0x11,0x1027,24,0x1434))
        for before,after in ((previous['LPHa124'],first),(previous['GAMMA45'],gamma)):
            self.assertEqual((before.date,before.day_of_week,before.start_time,before.end_time,before.undecoded_fields),
                             (after.date,after.day_of_week,after.start_time,after.end_time,after.undecoded_fields))
            self.assertNotEqual(before.record_id,after.record_id)
            self.assertNotEqual(before.offset,after.offset)
        old_gamma,new_gamma=bytes.fromhex(previous['GAMMA45'].raw_hex),bytes.fromhex(gamma.raw_hex)
        self.assertEqual(old_gamma[2:],new_gamma[2:])
        old_first,new_first=bytes.fromhex(previous['LPHa124'].raw_hex),bytes.fromhex(first.raw_hex)
        self.assertEqual(old_first[2:15],new_first[2:15])
        self.assertEqual(old_first[15:-2]+b'XYZ',new_first[15:-2])
        self.assertEqual(old.internal_records[0].raw_hex,new.internal_records[0].raw_hex)
        raw=fixture_path('E11_description_growth').read_bytes()
        self.assertEqual(raw[0x142E:0x143A],bytes.fromhex('04 00 3f 00 12 00 04 00 27 00 11 00'))
        self.assertEqual(raw[0x105A],3)
        self.assertFalse(any(raw[0x105B:0x1400]))
        self.assertEqual(raw[0x1000:0x1400].count(new_gamma[2:]),1)
        self.assertEqual(raw[0x1000:0x1400].count(new_first[2:]),1)
        self.assertNotIn(old_first,raw[0x1000:0x1400])

    def test_e10_reuses_id_and_tail_with_description_only_e08_delta(self):
        e08 = fixture_path('E08_two_events').read_bytes()
        e09 = fixture_path('E09_delete_beta456').read_bytes()
        e10 = fixture_path('E10_reuse_gamma45').read_bytes()
        self.assertEqual(len(e10), 6144)
        self.assertEqual([i for i,(a,b) in enumerate(zip(e08,e10)) if a != b], list(range(0x104E,0x1055)))
        self.assertEqual(e10[0x104E:0x1055], b'GAMMA45')
        self.assertEqual(e10[0x103F:0x1041], b'\x80\x12')
        self.assertEqual(e10[0x1434:0x143A], bytes.fromhex('04 00 3f 00 12 00'))
        self.assertEqual(e10[0x1000:0x103F], e09[0x1000:0x103F])
        self.assertEqual(e10[0x435:0x43A], b'00003')
        self.assertEqual(e10[0x43F:0x444], b'00019')
        db = parse_file(fixture_path('E10_reuse_gamma45'))
        self.assertEqual([r.description for r in db.appointments], ['LPHa124', 'GAMMA45'])
        replacement = db.appointments[1]
        self.assertEqual((replacement.record_id,replacement.offset,replacement.index_offset,replacement.length),
                         (0x12,0x103F,0x1434,24))

    def test_e09_trailing_deletion_restores_e07(self):
        e07 = fixture_path('E07_date_20271101').read_bytes()
        e08 = fixture_path('E08_two_events').read_bytes()
        e09 = fixture_path('E09_delete_beta456').read_bytes()
        self.assertEqual(e09, e07)
        self.assertEqual(e09[0x1000:0x103F], e08[0x1000:0x103F])
        self.assertEqual(e09[0x103F:0x1058], b'\x03' + b'\x00'*24)
        self.assertEqual(e09[0x1434:0x143A], b'\x00'*6)
        db = parse_file(fixture_path('E09_delete_beta456'))
        self.assertEqual([r.record_id for r in db.records], [0x10, 0x11])
        self.assertEqual([r.description for r in db.appointments], ['LPHa124'])
        self.assertEqual(db.metadata['tables']['PERSONAL']['record_count'], 2)
        self.assertEqual(db.metadata['tables']['PERSONAL']['next_id_candidate'], 18)

    def test_all_documented_appointments_and_input_integrity(self):
        for name, expected in FIXTURES:
            with self.subTest(experiment=name):
                path = fixture_path(name)
                manifest = json.loads((ROOT/name/'manifest.json').read_text())
                entry = next(e for e in manifest['files'] if e['path'].replace('\\', '/') == 'DESKMATE/PERSONAL.CLN')
                before, stat = path.read_bytes(), path.stat()
                self.assertEqual(hashlib.sha256(before).hexdigest(), entry['sha256'])
                db = parse_file(path)
                self.assertEqual(len(db.appointments), 0 if expected is None else 2 if name.startswith(('E08','E10','E11','E14')) else 1)
                self.assertEqual(len(db.internal_records), 1)
                self.assertEqual(db.internal_records[0].record_id, 0x10)
                self.assertIsNone(db.internal_records[0].date)
                self.assertEqual(len(db.internal_records[0].undecoded_fields), 7)
                if expected:
                    first = next(r for r in db.appointments if r.description == expected[4])
                    self.assertEqual((first.date, first.day_of_week, first.start_time, first.end_time, first.description), expected)
                    self.assertEqual((first.record_id,first.length), (0x12,27) if name.startswith(('E11','E14')) else (0x11,27) if name.startswith('E12') else (0x11,24))
                    self.assertEqual(first.undecoded_fields, {'Duration': '', 'Protected': '31'})
                if name.startswith(('E08','E10','E11','E14')):
                    second_description = 'BETA456' if name.startswith('E08') else 'GAMM' if name.startswith('E14') else 'GAMMA45'
                    second = next(r for r in db.appointments if r.description == second_description)
                    self.assertEqual((second.date, second.day_of_week, second.start_time, second.end_time, second.description),
                                     ('2027-11-01', 'Monday', '11:00', '12:00', second_description))
                    self.assertEqual((second.record_id,second.offset,second.length),
                                     (0x11,0x1027,21) if name.startswith('E14') else (0x11,0x1027,24) if name.startswith('E11') else (0x12,0x103F,24))
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(path.stat().st_mtime_ns, stat.st_mtime_ns)

    def test_file_api_opens_binary_read_only_and_bounds_read(self):
        content = fixture_path('E08_two_events').read_bytes()
        opener = mock_open(read_data=content)
        with patch('pathlib.Path.open', opener):
            self.assertEqual(len(parse_file('evidence.cln').appointments), 2)
        opener.assert_called_once_with('rb')
        opener().read.assert_called_once_with(6145)
        self.assertFalse(opener().write.called)


class MutationTests(unittest.TestCase):
    def setUp(self):
        self.data = bytearray(fixture_path('E08_two_events').read_bytes())

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


class CLITests(unittest.TestCase):
    def test_e14_cli_reports_both_preserved_events(self):
        for flags in ([],['--json']):
            with self.subTest(flags=flags):
                out=io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main([str(fixture_path('E14_interior_shrink'))]+flags),0)
                self.assertIn('LPHa124XYZ',out.getvalue())
                self.assertIn('GAMM',out.getvalue())
                self.assertNotIn('GAMMA45',out.getvalue())
                if flags:
                    result=json.loads(out.getvalue())
                    self.assertEqual(result['appointment_count'],2)
                    self.assertEqual(len(result['internal_records']),1)
                    rows={r['description']:r for r in result['appointments']}
                    for desc,ident,length,start,end in [('LPHa124XYZ',0x12,27,'09:15','10:15'),('GAMM',0x11,21,'11:00','12:00')]:
                        row=rows[desc]
                        self.assertEqual((row['record_id'],row['length'],row['date'],row['day_of_week'],row['start_time'],row['end_time']),
                                         (ident,length,'2027-11-01','Monday',start,end))
                else:self.assertIn('2 user appointment(s)',out.getvalue())

    def test_e13_cli_reports_restored_one_appointment(self):
        for flags in ([],['--json']):
            with self.subTest(flags=flags):
                out=io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main([str(fixture_path('E13_description_shrink'))]+flags),0)
                self.assertIn('LPHa124',out.getvalue())
                self.assertNotIn('LPHa124XYZ',out.getvalue())
                self.assertNotIn('GAMMA45',out.getvalue())
                if flags:
                    result=json.loads(out.getvalue())
                    self.assertEqual(result['appointment_count'],1)
                    self.assertEqual(len(result['internal_records']),1)
                    row=result['appointments'][0]
                    self.assertEqual((row['description'],row['date'],row['day_of_week'],row['start_time'],row['end_time'],row['record_id'],row['length']),
                                     ('LPHa124','2027-11-01','Monday','09:15','10:15',0x11,24))
                else:self.assertIn('1 user appointment(s)',out.getvalue())

    def test_e12_cli_lists_only_preserved_survivor(self):
        for options in ([], ['--json']):
            with self.subTest(options=options):
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(main([str(fixture_path('E12_delete_gamma45'))]+options), 0)
                self.assertIn('LPHa124XYZ', out.getvalue())
                self.assertNotIn('GAMMA45', out.getvalue())
                if options:
                    result = json.loads(out.getvalue())
                    self.assertEqual(result['appointment_count'],1)
                    self.assertEqual(len(result['internal_records']),1)
                    row = result['appointments'][0]
                    self.assertEqual((row['record_id'],row['length'],row['date'],row['start_time'],row['end_time']),
                                     (0x11,27,'2027-11-01','09:15','10:15'))
                else:
                    self.assertIn('1 user appointment(s)',out.getvalue())

    def test_e11_json_reports_relocated_records_from_index(self):
        out=io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([str(fixture_path('E11_description_growth')),'--json']),0)
        result=json.loads(out.getvalue())
        self.assertEqual(result['appointment_count'],2)
        by_description={r['description']:r for r in result['appointments']}
        first,gamma=by_description['LPHa124XYZ'],by_description['GAMMA45']
        self.assertEqual((first['record_id'],first['length'],first['start_time'],first['end_time']),
                         (0x12,27,'09:15','10:15'))
        self.assertEqual((gamma['record_id'],gamma['start_time'],gamma['end_time']),
                         (0x11,'11:00','12:00'))
        self.assertEqual(len(result['internal_records']),1)

    def test_e10_listing_has_replacement_without_deleted_description(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([str(fixture_path('E10_reuse_gamma45'))]), 0)
        for value in ('2 user appointment(s)', 'LPHa124', 'GAMMA45', 'ID 0x12', '11:00 - 12:00'):
            self.assertIn(value, out.getvalue())
        self.assertNotIn('BETA456', out.getvalue())

    def test_e09_listing_excludes_deleted_event(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([str(fixture_path('E09_delete_beta456'))]), 0)
        self.assertIn('1 user appointment(s)', out.getvalue())
        self.assertIn('LPHa124', out.getvalue())
        self.assertNotIn('BETA456', out.getvalue())
        self.assertNotIn('ID 0x12', out.getvalue())

    def test_human_listing(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([str(fixture_path('E08_two_events'))]), 0)
        for value in ('2 user appointment(s)', 'LPHa124', 'BETA456', '11:00 - 12:00',
                      'Internal/control ID 0x10', 'Undecoded Protected'):
            self.assertIn(value, out.getvalue())

    def test_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([str(fixture_path('E08_two_events')), '--json']), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result['appointment_count'], 2)
        self.assertEqual(len(result['internal_records']), 1)
        self.assertEqual(result['appointments'][1]['description'], 'BETA456')

    def test_cli_input_error_has_exit_code_and_no_partial_listing(self):
        out, err = io.StringIO(), io.StringIO()
        with patch('deskmate_formats.calendar.cli.parse_file', side_effect=CalendarParseError('truncated_file', 'test')), redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main(['bad.cln', '--json']), 2)
        self.assertEqual(out.getvalue(), '')
        self.assertIn('truncated_file', err.getvalue())

    def test_cli_os_error(self):
        err = io.StringIO()
        with patch('deskmate_formats.calendar.cli.parse_file', side_effect=FileNotFoundError('not found')), redirect_stderr(err):
            self.assertEqual(main(['absent.cln']), 2)
        self.assertIn('not found', err.getvalue())


if __name__ == '__main__':
    unittest.main()
