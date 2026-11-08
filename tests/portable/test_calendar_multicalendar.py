"""Native A, independent structural validator, and unrelated synthetic controls."""
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import date
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from deskmate_formats import database
from deskmate_formats.calendar.cli import main
from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes, parse_file
from deskmate_formats.calendar.writer import append_appointment
from deskmate_formats.calendar.writer import Appointment
from deskmate_formats.calendar.experimental_second import append_first_second, write_first_second
from deskmate_formats.calendar.experimental_create import create_second, write_second
from multicalendar_synthetic import two_calendars


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/application-generated/calendar'
A = FIXTURES / 'native-second-empty-calendar-operator.cln'
SOURCE = FIXTURES / 'sdk-30-days-allocator-tool-generated.cln'
B = FIXTURES / 'native-second-first-event-operator.cln'
GENERATED = FIXTURES / 'second-first-event-tool-generated.cln'
CREATED = FIXTURES / 'second-empty-calendar-tool-generated.cln'
EVENT = Appointment(date(2026, 10, 24), 660, 720, 'SECOND ONLY 001')
EXPECTED_SECOND = dict(date='2026-10-24', start_minutes=660, end_minutes=720,
                       description='SECOND ONLY 001', alarm_enabled=False)
spec = importlib.util.spec_from_file_location('raw_multicalendar_checker',
                                            ROOT / 'tools/experimental/check_calendar_multicalendar.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class MulticalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = A.read_bytes()
        cls.source = SOURCE.read_bytes()
        cls.expected = json.loads(SOURCE.with_suffix('.expected.json').read_text(encoding='utf-8'))
        cls.native_b = B.read_bytes()

    def test_native_b_all_differences_and_table_isolation(self):
        report = checker.check_first_second(self.native, self.native_b)
        self.assertEqual(report['changed_positions'], 38)
        self.assertEqual(report['sha256'], checker.B_SHA256)
        a = parse_bytes(self.native, profile='sdk')
        b = parse_bytes(self.native_b, profile='sdk')
        self.assertEqual(a.calendar('PERSONAL'), b.calendar('PERSONAL'))
        self.assertEqual(a.calendar('SECOND').internal_records, b.calendar('SECOND').internal_records)
        second, = b.calendar('SECOND').appointments
        self.assertEqual((len(b.appointments), len(b.internal_records)), (62, 2))
        self.assertEqual((second.record_id, second.offset, second.index_offset, second.length),
                         (17, 8231, 9262, 32))
        self.assertEqual((second.date, second.start_time, second.end_time, second.alarm_enabled),
                         ('2026-10-24', '11:00', '12:00', False))
        self.assertEqual(second.description, 'SECOND ONLY 001')
        self.assertIn(second.record_id, {r.record_id for r in b.calendar('PERSONAL').appointments})

    def test_writer_matches_actual_native_b_and_committed_generated_bytes(self):
        original = bytearray(self.native)
        made = append_first_second(original, EVENT, experimental=True)
        self.assertEqual(made, self.native_b)
        self.assertEqual(made, GENERATED.read_bytes())
        self.assertEqual(original, self.native)
        report = checker.check_append(self.native, made, EXPECTED_SECOND)
        self.assertEqual((report['changed_positions'], report['row_length']), (38, 32))
        self.assertEqual(report['output_sha256'], checker.B_SHA256)

    def test_creation_exact_native_a_and_end_to_end_native_b(self):
        original = bytearray(self.source)
        made = create_second(original, experimental=True)
        self.assertEqual(original, self.source)
        self.assertEqual(made, self.native)
        self.assertEqual(made, CREATED.read_bytes())
        self.assertEqual(checker.check(self.source, made, self.expected)['sha256'], checker.A_SHA256)
        self.assertEqual(append_first_second(made, EVENT, experimental=True), self.native_b)
        common = database.parse_bytes(made)
        prior = database.parse_bytes(self.source)
        self.assertEqual(common.table('PERSONAL').raw_descriptor, prior.table('PERSONAL').raw_descriptor)
        self.assertEqual(common.table('DBCOLS').rows[:13], prior.table('DBCOLS').rows)
        for n, row in enumerate(common.table('DBCOLS').rows[13:], 1):
            self.assertEqual(row.record_id, 28 + n)
            self.assertEqual(row.fields[1], b'SECOND')
            self.assertEqual(int(row.fields[2]), n)
        self.assertEqual((common.table('SECOND').data_page, common.table('SECOND').index_page), (8, 9))

    def test_creation_exact_source_name_and_no_general_balancer(self):
        for value in (False, 1, 'yes', None):
            with self.subTest(opt_in=value), self.assertRaisesRegex(ValueError, 'experimental=True'):
                create_second(self.source, experimental=value)
        for source in (None, 8192, b'', self.source[:-1], self.source + bytes(1024), self.native, self.native_b):
            with self.subTest(source_type=type(source)), self.assertRaises(ValueError):
                create_second(source, experimental=True)
        for at in (21, 31, 44, 0x418, 0x435, 0x950, 0xC28, 0x1428, 0x151E):
            data = bytearray(self.source)
            data[at] ^= 1
            with self.subTest(offset=at), self.assertRaisesRegex(ValueError, 'hash-pinned'):
                create_second(data, experimental=True)
        for name in ('Second', 'second', 'THIRD', 'SECOND ', '', None):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'exact name SECOND'):
                create_second(self.source, name=name, experimental=True)

    def test_creation_generator_and_new_file_api_preserve_inputs(self):
        tool = ROOT / 'tools/experimental/generate_calendar_second_table.py'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'created.cln'
            source = Path(folder) / 'source.cln'
            expected = Path(folder) / 'listing.json'
            source.write_bytes(self.source)
            expected.write_text(json.dumps(self.expected), encoding='utf-8')
            before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (source, expected)]
            command = [sys.executable, str(tool), str(source), str(expected), str(path)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertFalse(path.exists())
            result = subprocess.run(command + ['--experimental-create-second'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), self.native)
            self.assertEqual(json.loads(result.stdout)['sha256'], checker.A_SHA256)
            self.assertEqual(subprocess.run(command + ['--experimental-create-second'], capture_output=True).returncode, 2)
            self.assertEqual(path.read_bytes(), self.native)
            with self.assertRaises(FileExistsError):
                write_second(path, self.source, experimental=True)
            other = path.with_name('api.cln')
            self.assertEqual(write_second(other, self.source, experimental=True), self.native)
            self.assertEqual(other.read_bytes(), self.native)
            command[-1] = str(source)
            self.assertEqual(subprocess.run(command + ['--experimental-create-second'], capture_output=True).returncode, 2)
            self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in (source, expected)], before)
            self.assertFalse(list(path.parent.glob('.calendar-*')))

    def test_writer_other_encodings_are_independent_offline_controls(self):
        for day, start, end, description, protected in (
                (date(1980, 1, 1), 15, 30, 'X', b'1'),
                (date(2138, 12, 31), 1395, 1425, '~' * 120, b'q'),
                (date(2028, 2, 29), 555, 615, 'AZaz09 ; punctuation', b'1')):
            e = Appointment(day, start, end, description, protected_raw=protected)
            made = append_first_second(self.native, e, experimental=True)
            expected = dict(date=day.isoformat(), start_minutes=start, end_minutes=end,
                            description=description, alarm_enabled=protected == b'q')
            self.assertEqual(checker.check_append(self.native, made, expected)['second_appointments'], 1)
            self.assertNotEqual(hashlib.sha256(made).hexdigest(), checker.B_SHA256)
            self.assertEqual(made[4096:8192], self.native[4096:8192])

    def test_writer_opt_in_source_ownership_and_field_guards(self):
        for value in (False, True + 0, 'yes', None):
            with self.subTest(opt_in=value), self.assertRaisesRegex(ValueError, 'experimental=True'):
                append_first_second(self.native, EVENT, experimental=value)
        for source in (None, 10240, b'', self.native[:-1], self.native + bytes(1024), self.native_b, two_calendars()):
            with self.subTest(source_type=type(source)), self.assertRaises(ValueError):
                append_first_second(source, EVENT, experimental=True)
        # Mutated counts, next-ID ranges, index capacity, row framing, owning
        # chains and unrelated opaque bytes are all rejected by exact-source identity.
        for at, value in ((0x464, 48), (0x46A, 57), (0x46C, 49), (0x242E, 8),
                          (0x2027, 128), (0x2025, 0), (0x2C, 0), (31, 1)):
            data = bytearray(self.native)
            data[at] = value
            with self.subTest(offset=at), self.assertRaisesRegex(ValueError, 'hash-pinned'):
                append_first_second(data, EVENT, experimental=True)
        for name in ('PERSONAL', 'second', '', None):
            with self.subTest(calendar=name), self.assertRaisesRegex(ValueError, 'owning calendar SECOND'):
                append_first_second(self.native, EVENT, calendar=name, experimental=True)
        invalid = [None, replace(EVENT, day='2026-10-24'), replace(EVENT, day=date(1979, 12, 31)),
                   replace(EVENT, day=date(2139, 1, 1)), replace(EVENT, start_minutes=True),
                   replace(EVENT, start_minutes=0), replace(EVENT, end_minutes=1440),
                   replace(EVENT, start_minutes=661), replace(EVENT, end_minutes=660),
                   replace(EVENT, description=''), replace(EVENT, description='X' * 121),
                   replace(EVENT, description='PRIVATE\x01ROW'), replace(EVENT, description='é'),
                   replace(EVENT, duration_raw=b'R'), replace(EVENT, protected_raw=b'p')]
        for e in invalid:
            with self.subTest(event=e), self.assertRaises(ValueError):
                append_first_second(self.native, e, experimental=True)

    def test_independent_append_validator_detects_valid_but_wrong_semantics(self):
        made = append_first_second(self.native, replace(EVENT, protected_raw=b'q'), experimental=True)
        with self.assertRaisesRegex(ValueError, 'expected SECOND event'):
            checker.check_append(self.native, made, EXPECTED_SECOND)
        for at in (0x464, 0x46E, 0x2027, 0x2028, 0x2034, 0x2047, 0x242E, 0x2430, 0x2432, 31):
            data = bytearray(self.native_b)
            data[at] ^= 1
            with self.subTest(at=at), self.assertRaises(ValueError):
                checker.check_append(self.native, data, EXPECTED_SECOND)

    def test_new_file_writer_and_generator_atomic_publication(self):
        tool = ROOT / 'tools/experimental/generate_calendar_second.py'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'candidate.cln'
            source = Path(folder) / 'source.cln'
            source.write_bytes(self.native)
            before = (source.read_bytes(), source.stat().st_mtime_ns)
            command = [sys.executable, str(tool), str(source), str(path)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertFalse(path.exists())
            result = subprocess.run(command + ['--experimental-first-second'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['output_sha256'], checker.B_SHA256)
            self.assertEqual(path.read_bytes(), self.native_b)
            self.assertEqual(subprocess.run(command + ['--experimental-first-second'], capture_output=True).returncode, 2)
            self.assertEqual(path.read_bytes(), self.native_b)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)
            self.assertFalse(list(path.parent.glob('.calendar-*')))
            with self.assertRaises(FileExistsError):
                write_first_second(path, self.native, EVENT, experimental=True)
            other = path.with_name('api.cln')
            self.assertEqual(write_first_second(other, self.native, EVENT, experimental=True), self.native_b)
            self.assertEqual(other.read_bytes(), self.native_b)
            command[-1] = str(source)
            self.assertEqual(subprocess.run(command + ['--experimental-first-second'], capture_output=True).returncode, 2)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)

    def test_native_a_independent_complete_listing_and_byte_preservation(self):
        report = checker.check(self.source, self.native, self.expected)
        self.assertEqual((report['personal_appointments'], report['second_appointments']), (61, 0))
        db = parse_bytes(self.native, profile='sdk')
        self.assertEqual(db.data, self.native)
        self.assertEqual([c.name for c in db.calendars], ['PERSONAL', 'SECOND'])
        self.assertEqual((len(db.records), len(db.appointments), len(db.internal_records)), (63, 61, 2))
        personal, second = db.calendar('PERSONAL'), db.calendar('SECOND')
        self.assertEqual(len(second.appointments), 0)
        self.assertEqual(len(second.internal_records), 1)
        self.assertEqual(personal.internal_records[0].raw_hex, second.internal_records[0].raw_hex)
        self.assertEqual(second.internal_records[0].offset, 8192)
        self.assertEqual([r.calendar_name for r in second.records], ['SECOND'])
        for record, expected in zip(personal.appointments, self.expected['appointments'], strict=True):
            for key in ('date', 'start_time', 'end_time', 'description', 'alarm_enabled',
                        'record_id', 'row_length', 'file_offset'):
                attr = {'row_length': 'length', 'file_offset': 'offset'}.get(key, key)
                self.assertEqual(getattr(record, attr), expected[key])
        common = database.parse_bytes(self.native)
        self.assertEqual(common.data, self.native)
        self.assertEqual(common.sha256, checker.A_SHA256)
        original = database.parse_bytes(self.source).table('PERSONAL')
        now = common.table('PERSONAL')
        self.assertEqual([(e.page, e.in_page_offset, e.record_id) for e in now.entries],
                         [(e.page, e.in_page_offset, e.record_id) for e in original.entries])
        self.assertEqual([r.raw for r in now.rows], [r.raw for r in original.rows])
        self.assertEqual([len(g.entries) for g in now.index_groups], [20, 21, 21, 0])
        self.assertEqual([e.index_offset for e in now.entries],
                         [5120 + 40 + 246 * g + 6 * n
                          for g, count in enumerate((20, 21, 21, 0)) for n in range(count)])
        self.assertEqual(now.index_groups[0].routing_key.hex(), '8f6b80016801b901bd01')
        self.assertEqual([g.routing_key for g in now.index_groups[1:]], [checker.SENTINEL] * 3)

    def test_unrelated_synthetic_appointments_and_ids_are_table_scoped(self):
        data = two_calendars()
        self.assertNotEqual(hashlib.sha256(data).hexdigest(), checker.B_SHA256)
        raw = checker.inspect(data)
        self.assertEqual([len(raw[n]['events']) for n in ('PERSONAL', 'SECOND')], [1, 1])
        db = parse_bytes(data, profile='sdk')
        one, = db.calendar('PERSONAL').appointments
        two, = db.calendar('SECOND').appointments
        self.assertEqual(one.record_id, two.record_id)
        self.assertEqual(two.record_id, 17)
        self.assertEqual((two.date, two.start_time, two.end_time, two.alarm_enabled),
                         ('2030-01-02', '13:00', '14:00', True))
        self.assertEqual(two.description, 'SYNTHETIC SECOND / SCOPED ID')
        self.assertEqual(two.calendar_name, 'SECOND')
        self.assertNotEqual(one.offset, two.offset)
        self.assertEqual(len(db.to_dict()['calendars']), 2)
        with self.assertRaises(CalendarParseError):
            db.calendar('MISSING')

    def assert_both_reject(self, data):
        with self.assertRaises(database.DatabaseError):
            database.parse_bytes(data)
        with self.assertRaises(ValueError):
            checker.inspect(data)

    def test_routing_subdivision_count_and_locator_adversaries(self):
        cases = [(0x1400, b'X'), (0x140A, b'X'), (0x141E, b'X'),
                 (0x1428 + 6, bytes(6)),  # hole within group 0
                 (0x1428 + 20 * 6, b'\x01'),  # dirty group tail
                 (0x151E, struct.pack('<HHH', 8, 0, 16)),  # foreign owning page
                 (0x151E, struct.pack('<HHH', 4, 1, 59)),  # inside row
                 (0x151E, struct.pack('<HHH', 6, 806, 16)),  # duplicate table ID
                 (0x151E, struct.pack('<HHH', 6, 806, 58)),  # wrong row ID
                 (0x435, b'00061'), (0x2025, b'\x00'), (0x27FF, b'X')]
        for at, payload in cases:
            with self.subTest(at=hex(at), payload=payload):
                data = bytearray(self.native)
                data[at:at + len(payload)] = payload
                self.assert_both_reject(data)
        data = bytearray(self.native)
        # An entirely empty middle subdivision cannot hide populated later ones.
        data[0x151E:0x1614] = bytes(246)
        self.assert_both_reject(data)

    def test_chain_cycles_markers_aliases_and_unindexed_rows(self):
        def link(data, page, value):
            bits = list(''.join(f'{b:08b}' for b in data[32:1024]))
            bits[page * 12:(page + 1) * 12] = f'{value:012b}'
            data[32:1024] = int(''.join(bits), 2).to_bytes(992, 'big')
        for page, value in ((0, 0), (1, 0), (4, 4), (6, 4), (7, 6), (4, 0),
                            (4, 0xFFF), (4, 10), (4, 9), (4, 8), (5, 9),
                            (8, 4), (9, 8), (10, 0)):
            with self.subTest(page=page, value=value):
                data = bytearray(self.native)
                link(data, page, value)
                self.assert_both_reject(data)
        # Chain pages are physically scanned even if no live locator targets them.
        data = bytearray(self.native)
        data[0x151E:0x1614] = bytes(246)
        data[0x1614:0x170A] = bytes(246)
        data[0x435:0x43A] = b'00020'
        self.assert_both_reject(data)

    def test_sdk_rejects_calendar_count_schema_and_wrong_sort_order(self):
        for at, payload in ((21, b'\x01'), (0x46F, b'8'), (0x2428, bytes(6))):
            data = bytearray(self.native)
            data[at:at + len(payload)] = payload
            with self.subTest(at=at), self.assertRaises(CalendarParseError):
                parse_bytes(data, profile='sdk')
        # Keep every route/row/locator valid but reverse two later event locators.
        data = bytearray(self.native)
        a, b = 0x151E, 0x1524
        data[a:a + 6], data[b:b + 6] = data[b:b + 6], data[a:a + 6]
        with self.assertRaisesRegex(CalendarParseError, 'index order'):
            parse_bytes(data, profile='sdk')
        with self.assertRaisesRegex(ValueError, 'index ordering'):
            checker.inspect(data)

    def test_cli_and_file_reader_preserve_input_and_report_empty_calendar(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'two.cln'
            path.write_bytes(self.native)
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            self.assertEqual(len(parse_file(path, profile='sdk').calendars), 2)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([str(path), '--profile', 'sdk', '--json']), 0)
            result = json.loads(output.getvalue())
            self.assertEqual([(c['name'], c['appointment_count']) for c in result['calendars']],
                             [('PERSONAL', 61), ('SECOND', 0)])
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        with self.assertRaises(CalendarParseError):
            parse_bytes(self.native)  # Historical default profile stays six-page.
        with self.assertRaisesRegex(ValueError, 'additional-page'):
            append_appointment(self.native, profile='sdk')

    def test_full_subdivision_and_finite_prefix_positive_control(self):
        data = bytearray(self.source)
        # A full first subdivision has no zero locator sentinel of its own.
        table = database.parse_bytes(data).table('PERSONAL')
        self.assertEqual([len(g.entries) for g in table.index_groups], [41, 21, 0, 0])
        terminal = table.rows[40]
        fields = terminal.fields
        data[5120:5130] = checker.prefix(fields, [1, 2, 4, 5, 7])
        self.assertEqual(len(database.parse_bytes(data).table('PERSONAL').rows), 62)
        # Links beyond the extent are deliberately opaque, retained byte-for-byte.
        data[512] = 0xA5
        self.assertEqual(database.parse_bytes(data).data[512], 0xA5)

    def test_no_b_claim_from_a_or_unrelated_synthetic_bytes(self):
        for data in (self.native, two_calendars()):
            with self.assertRaises(ValueError):
                checker.check_first_second(self.native, data)


if __name__ == '__main__':
    unittest.main()
