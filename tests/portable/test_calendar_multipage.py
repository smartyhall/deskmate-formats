"""Source-backed small-profile controls; all new outputs remain tool-generated."""
from datetime import date, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from deskmate_formats.calendar.experimental_new import build_new, _set_link
from deskmate_formats.calendar.personal import parse_bytes
from deskmate_formats.calendar.writer import Appointment, append_appointment

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tests/fixtures/application-generated/calendar/e02-86box-historical-match.cln'
TOOLS = ROOT / 'tools/experimental'
MONTH = SOURCE.with_name('sdk-30-days-allocator-tool-generated.cln')
MONTH_SHA256 = 'd35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106'
spec = importlib.util.spec_from_file_location('raw_month_checker', TOOLS / 'check_calendar_multipage.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def expected(events):
    return [{'date': e.day.isoformat(), 'start_minutes': e.start_minutes,
             'end_minutes': e.end_minutes, 'description': e.description,
             'alarm_enabled': e.protected_raw == b'q'} for e in events]


def event(n, length=1):
    return Appointment(date(2028, 1, 1) + timedelta(days=n), 600, 660, 'X' * length)


class MultipageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()

    def test_committed_month_binary_and_expected_listing(self):
        data = MONTH.read_bytes()
        listing = json.loads(MONTH.with_suffix('.expected.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data), 8192)
        self.assertEqual(hashlib.sha256(data).hexdigest(), MONTH_SHA256)
        # This oracle scans physical rows independently of the production reader,
        # verifies every added raw field, all map bytes and index/row relationships.
        report = checker.check(self.source, data, listing['additions'])
        self.assertEqual(report, {key: listing['appointment_count' if key == 'appointments' else key]
                                  for key in report})
        self.assertEqual((report['appointments'], report['distinct_dates'], report['pages']), (61, 30, 8))
        self.assertEqual(report['data_chain'], [4, 6, 7])
        db = parse_bytes(data, profile='sdk')
        actual = [{'date': r.date, 'start_time': r.start_time, 'end_time': r.end_time,
                   'description': r.description, 'alarm_enabled': r.alarm_enabled,
                   'record_id': r.record_id, 'page': r.offset // 1024,
                   'in_page_offset': r.offset % 1024, 'file_offset': r.offset,
                   'row_length': r.length, 'index_offset': r.index_offset}
                  for r in db.appointments]
        self.assertEqual(actual, listing['appointments'])
        self.assertEqual([r['date'] for r in actual], sorted(r['date'] for r in actual))
        self.assertEqual({r['date'] for r in actual},
                         {(date(2026, 10, 23) + timedelta(days=n)).isoformat() for n in range(30)})
        self.assertEqual(actual[0]['description'], 'LPHa124')
        self.assertEqual((actual[0]['start_time'], actual[0]['end_time'], actual[0]['alarm_enabled']),
                         ('09:00', '10:00', False))
        # Connect the static physical-order oracle inputs to the public logical listing.
        by_id = {r['record_id']: r for r in actual}
        for rid, event in enumerate(listing['additions'], 18):
            row = by_id[rid]
            self.assertEqual({key: row[key] for key in ('date', 'description', 'alarm_enabled')},
                             {key: event[key] for key in ('date', 'description', 'alarm_enabled')})
            for field in ('start', 'end'):
                hour, minute = map(int, row[field + '_time'].split(':'))
                self.assertEqual(hour * 60 + minute, event[field + '_minutes'])
        control, = db.internal_records
        self.assertEqual(listing['control_record'],
                         {'record_id': control.record_id, 'page': control.offset // 1024,
                          'in_page_offset': control.offset % 1024, 'index_offset': control.index_offset})
        for usage in listing['page_usage']:
            rows = [r for r in db.records if r.offset // 1024 == usage['page']]
            self.assertEqual((len(rows), min(r.record_id for r in rows), max(r.record_id for r in rows)),
                             (usage['indexed_rows'], usage['first_id'], usage['last_id']))
            marker = max(r.offset + r.length for r in rows)
            self.assertEqual(marker, usage['marker_file_offset'])
            self.assertEqual(data[marker], 3)
            tail = data[marker + 1:(usage['page'] + 1) * 1024]
            self.assertEqual(tail, bytes(usage['zero_tail_bytes']))

    def test_month_regeneration_matches_committed_bytes_and_preserves_prior_fixtures(self):
        spec = importlib.util.spec_from_file_location('month_generator', TOOLS / 'generate_calendar_month.py')
        module = importlib.util.module_from_spec(spec)
        # The experiment CLI imports its adjacent standalone checker.
        sys.path.insert(0, str(TOOLS))
        try:
            spec.loader.exec_module(module)
            regenerated, _ = module.generate(self.source)
        finally:
            sys.path.pop(0)
        self.assertEqual(regenerated, MONTH.read_bytes())
        self.assertEqual(hashlib.sha256(self.source).hexdigest(),
                         '0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9')
        self.assertEqual(hashlib.sha256(SOURCE.with_name('sdk-14-days-tool-generated.cln').read_bytes()).hexdigest(),
                         '85ad05d6bf58540e32349bbb559301d36aced164741b03b09b30d63f22d636ac')

    def test_published_header_transitions_are_exact_not_native_specimens(self):
        header = bytearray(self.source[:1024])
        # Independent published byte deltas. These are never labeled E15/E19 files.
        before = bytes(header)
        for page, value in ((7, 4095), (6, 4088), (4, 6)):
            _set_link(header, page, value)
        self.assertEqual({i: (a, b) for i, (a, b) in enumerate(zip(before, header)) if a != b},
                         {38: (255, 0), 39: (143, 111), 42: (240, 143), 43: (0, 255)})
        before = bytes(header)
        for page, value in ((8, 4095), (7, 4088), (6, 7)):
            _set_link(header, page, value)
        self.assertEqual({i: (a, b) for i, (a, b) in enumerate(zip(before, header)) if a != b},
                         {41: (255, 0), 42: (143, 127), 43: (255, 248), 44: (0, 255), 45: (0, 240)})

    def test_adjacent_nibbles_and_unknown_bytes_preserved(self):
        for page in (4, 5, 6, 7, 8):
            for value in (0, 1, 7, 4088, 4095):
                data = bytearray(b'\xa5' * 1024)
                before_bits = ''.join(f'{b:08b}' for b in data)
                _set_link(data, page, value)
                bits = ''.join(f'{b:08b}' for b in data)
                start = 32 * 8 + 12 * page
                self.assertEqual(bits[:start], before_bits[:start])
                self.assertEqual(bits[start:start + 12], f'{value:012b}')
                self.assertEqual(bits[start + 12:], before_bits[start + 12:])

    def test_fail_closed_source_and_opt_in(self):
        with self.assertRaisesRegex(ValueError, 'experimental=True'):
            build_new(self.source, [event(0)])
        for value in (1, 'yes', None):
            with self.assertRaises(ValueError):
                build_new(self.source, [event(0)], experimental=value)
        for source in (b'', self.source + bytes(1024), self.source[:-1],
                       self.source[:17] + b'\xff' + self.source[18:]):
            with self.assertRaisesRegex(ValueError, 'E02 source'):
                build_new(source, [event(0)], experimental=True)
        made = build_new(self.source, [event(0)], experimental=True)
        with self.assertRaisesRegex(ValueError, 'E02 source'):
            build_new(made, [event(1)], experimental=True)

    def test_source_guard_exact_fit_and_both_sides(self):
        original_end = 4096
        for _ in range(2):
            original_end = self.source.index(b'\x01\x02', original_end + 2, 5120) + 2
        for difference in (-1, 0, 1):
            # Final 18-byte row needs 20 free bytes excluding marker. Construct
            # a preceding used extent of 1003+diff without using writer capacity.
            remaining = 1003 + difference - (original_end - 4096)
            events = []
            while remaining:
                length = min(137, remaining)
                if 0 < remaining - length < 18:
                    length -= 18 - (remaining - length)
                events.append(event(len(events), length - 17))
                remaining -= length
            events.append(event(len(events)))
            data = build_new(self.source, events, experimental=True)
            report = checker.check(self.source, data, expected(events))
            self.assertEqual(report['pages'], 7 if difference == 1 else 6)
            rid = 17 + len(events)
            triples = [struct.unpack_from('<HHH', data, 5160 + 6 * n) for n in range(len(events) + 2)]
            last = next(t for t in triples if t[2] == rid)
            self.assertEqual(last[:2], (6, 0) if difference == 1 else (4, 1003 + difference))

    def test_limits_ties_and_event_validation(self):
        for events, message in (([], 'at least one'),
                                ([event(n) for n in range(101)], 'at most 100'),
                                ([event(0), event(0)], 'tied'),
                                ([event(n, 120) for n in range(30)], 'eight-page')):
            with self.assertRaisesRegex(ValueError, message):
                build_new(self.source, events, experimental=True)
        for e in (Appointment(date(2028, 1, 1), 0, 60, 'Midnight'),
                  Appointment(date(2028, 1, 1), 600, 660, 'A\x01B'),
                  Appointment(date(2028, 1, 1), 600, 660, 'X', protected_raw=b'0')):
            with self.assertRaises(ValueError):
                build_new(self.source, [e], experimental=True)

    def test_second_crossing_threshold_and_unneeded_page(self):
        original_end = 4096
        for _ in range(2):
            original_end = self.source.index(b'\x01\x02', original_end + 2, 5120) + 2
        for difference in (-1, 0, 1):
            events = []

            def fill(remaining):
                while remaining:
                    length = min(137, remaining)
                    if 0 < remaining - length < 18:
                        length -= 18 - (remaining - length)
                    events.append(event(len(events), length - 17))
                    remaining -= length

            fill(1004 - (original_end - 4096))
            events.append(event(len(events)))  # 18 bytes, starts page 6.
            fill(1003 + difference - 18)
            events.append(event(len(events)))
            data = build_new(self.source, events, experimental=True)
            report = checker.check(self.source, data, expected(events))
            self.assertEqual(report['pages'], 8 if difference == 1 else 7)
        events = [event(0)]
        altered = bytearray(build_new(self.source, events, experimental=True))
        altered.extend(b'\x03' + bytes(1023))
        for page, value in ((4, 6), (6, 4088), (7, 4095)):
            _set_link(altered, page, value)
        with self.assertRaisesRegex(ValueError, 'empty/unneeded'):
            checker.check(self.source, altered, expected(events))

    def test_reverse_insertion_and_existing_writer_unchanged(self):
        events = [event(n, 60) for n in reversed(range(30))]
        data = build_new(self.source, events, experimental=True)
        report = checker.check(self.source, data, expected(events))
        self.assertEqual((report['pages'], report['appointments']), (8, 31))
        db = parse_bytes(data, profile='sdk')
        self.assertEqual(len(db.appointments), 31)
        self.assertEqual(SOURCE.read_bytes(), self.source)
        self.assertEqual(data[4096:4096 + 27], self.source[4096:4096 + 27])
        with self.assertRaises(ValueError):
            append_appointment(data, event(31), profile='sdk')
        self.assertEqual(build_new(self.source, [event(0)], experimental=True),
                         append_appointment(self.source, event(0), profile='sdk'))

    def test_independent_checker_rejects_adversarial_bytes(self):
        events = [event(n, 60) for n in range(30)]
        good = build_new(self.source, events, experimental=True)
        # Map, opaque header/directory, schema, original/added row, index header,
        # pointer, count, sentinel and unused tails are all checked independently.
        for at in (0, 31, 38, 41, 1023, 1024, 0x435, 0x43F, 2048, 4097,
                   5120, 5160, 5166, 6143, 6144, 6148, 8191):
            altered = bytearray(good)
            altered[at] ^= 1
            with self.subTest(offset=hex(at)), self.assertRaises(ValueError):
                checker.check(self.source, altered, expected(events))
        altered = bytearray(good)
        altered[5166:5172] = altered[5172:5178]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            checker.check(self.source, altered, expected(events))
        wrong = expected(events)
        wrong[0]['alarm_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'raw fields'):
            checker.check(self.source, good, wrong)

    def test_month_cli_and_standalone_checker_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'candidate.cln'
            command = [sys.executable, str(TOOLS / 'generate_calendar_month.py'), str(SOURCE), str(output)]
            before = (SOURCE.read_bytes(), SOURCE.stat().st_mtime_ns)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            result = subprocess.run(command + ['--experimental-new-pages'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual((receipt['appointments'], receipt['distinct_dates'], receipt['pages']), (61, 30, 8))
            self.assertFalse(receipt['native_opened'])
            self.assertEqual(receipt['output_sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
            expected_path = Path(folder) / 'expected.json'
            expected_path.write_text(result.stdout, encoding='utf-8')
            verified = subprocess.run([sys.executable, str(TOOLS / 'check_calendar_multipage.py'),
                                       str(SOURCE), str(output), str(expected_path)], capture_output=True, text=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(json.loads(verified.stdout)['output_sha256'], receipt['output_sha256'])
            output_before = output.read_bytes()
            repeated = subprocess.run(command + ['--experimental-new-pages'], capture_output=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(output.read_bytes(), output_before)
            self.assertEqual((SOURCE.read_bytes(), SOURCE.stat().st_mtime_ns), before)
            self.assertFalse(list(Path(folder).glob('.calendar-month-*')))
            command[-1] = str(SOURCE)
            self.assertEqual(subprocess.run(command + ['--experimental-new-pages'], capture_output=True).returncode, 2)
            self.assertEqual((SOURCE.read_bytes(), SOURCE.stat().st_mtime_ns), before)
