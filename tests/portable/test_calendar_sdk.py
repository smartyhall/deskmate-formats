"""SDK ordinary codecs and independent raw-byte/structural output controls."""
from datetime import date, timedelta
from pathlib import Path
import struct
import tempfile
import unittest

from deskmate_formats.calendar.codec import encode_date, decode_date, encode_time, decode_time
from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes, parse_file
from deskmate_formats.calendar.writer import Appointment, append_appointment, capacity, write_new
from deskmate_formats.calendar.samples import schedule
from synthetic import build, assemble, INTERNAL, event


class SDKCalendarTests(unittest.TestCase):
    def test_literal_date_and_time_vectors(self):
        # SDK bitfields and published native E03/E07/E19 bytes, not writer output.
        for day, raw in ((date(1980, 1, 1), '616262'), (date(2000, 2, 29), '75637e'),
                         (date(2027, 11, 1), '906c62'), (date(2026, 11, 14), '8f6c6f'),
                         (date(2138, 12, 31), 'ff6d80')):
            self.assertEqual(encode_date(day), bytes.fromhex(raw))
            self.assertEqual(decode_date(bytes.fromhex(raw)), day)
        for minutes, raw in ((15, '81'), (555, 'a5'), (615, 'a9'),
                             (780, 'b4'), (855, 'b9'), (1425, 'df')):
            self.assertEqual(encode_time(minutes), bytes.fromhex(raw))
            self.assertEqual(decode_time(bytes.fromhex(raw)), minutes)

    def test_calendar_boundaries_and_invalid_values(self):
        for day in (date(1979, 12, 31), date(2139, 1, 1), '2026-11-01'):
            with self.assertRaises(ValueError):
                encode_date(day)
        for raw in ('', '6163', '61637f', '606262', '8f6e62'):
            with self.assertRaises(ValueError):
                decode_date(bytes.fromhex(raw))
        for minutes in (0, 1, 14, 1440, 1500, True, 540.0):
            with self.assertRaises(ValueError):
                encode_time(minutes)
        for raw in (b'', b'\x80', b'\xe0', b'\xf0', b'\xa4\xa5'):
            with self.assertRaises(ValueError):
                decode_time(raw)

    def test_default_profile_is_preserved(self):
        new = Appointment(date(2028, 2, 29), 780, 825, 'Leap')
        with self.assertRaises(ValueError):
            append_appointment(build('empty'), new)
        data = append_appointment(build('empty'), new, profile='sdk')
        self.assertIsNone(parse_bytes(data).appointments[0].date)
        row, = parse_bytes(data, profile='sdk').appointments
        self.assertEqual((row.date, row.day_of_week, row.start_time), ('2028-02-29', 'Tuesday', '13:00'))
        self.assertEqual(bytes.fromhex(row.raw_fields['Date']), bytes.fromhex('91637e'))

    def test_all_weekdays_and_quarters(self):
        for n, name in enumerate(('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')):
            day = date(2026, 11, 1) + timedelta(days=n)
            data = append_appointment(build('empty'), Appointment(day, 780 + n * 15, 900, name), profile='sdk')
            row, = parse_bytes(data, profile='sdk').appointments
            self.assertEqual(row.day_of_week, name)
            self.assertEqual(row.raw_fields['DayOfWeek'], f'{0x62 + n:02x}')
        bad = assemble([(16, INTERNAL), (17, event(17, 'BAD', weekday=b'd'))], [16, 17])
        with self.assertRaisesRegex(CalendarParseError, 'inconsistent_weekday'):
            parse_bytes(bad, profile='sdk')

    def test_two_weeks_and_original_bytes(self):
        source = (Path(__file__).parents[1] / 'fixtures/application-generated/calendar/e02-86box-historical-match.cln').read_bytes()
        original = parse_bytes(source)
        data = source
        # Reverse insert order independently exercises physical versus index order.
        for item in reversed(schedule()):
            data = append_appointment(data, item, profile='sdk')
        db = parse_bytes(data, profile='sdk')
        self.assertEqual(len(db.appointments), 29)
        self.assertEqual(len({r.date for r in db.appointments}), 14)
        self.assertEqual((db.appointments[0].date, db.appointments[-1].date), ('2026-10-23', '2026-11-05'))
        self.assertEqual(len(data), 6144)
        self.assertEqual(data[:1024], source[:1024])
        self.assertEqual(data[2048:4096], source[2048:4096])
        self.assertGreater(capacity(data, profile='sdk')['data_bytes'], 0)
        by_id = {r.record_id: r for r in db.records}
        for row in original.records:
            self.assertEqual(by_id[row.record_id].raw_hex, row.raw_hex)
            self.assertEqual(by_id[row.record_id].offset, row.offset)
        # Independent LE16 slot walk and delimiter scan, without parser addresses.
        triples = [struct.unpack_from('<HHH', data, 5160 + 6 * n) for n in range(30)]
        self.assertEqual(len({t[2] for t in triples}), 30)
        self.assertEqual(data[5160 + 180:6144], bytes(804))
        raw_keys = []
        for page, offset, rid in triples[1:]:
            address = page * 1024 + offset
            self.assertEqual(data[address:address + 2], bytes((128, rid)))
            end = data.index(b'\x01\x02', address + 2, (page + 1) * 1024)
            fields = data[address + 2:end].split(b'\x01')
            raw_keys.append((fields[0], fields[3]))
        self.assertEqual(raw_keys, sorted(set(raw_keys)))

    def test_month_capacity_failure_and_atomic_no_overwrite(self):
        data = build('empty')
        count = 0
        for item in schedule(days=30):
            try:
                data = append_appointment(data, item, profile='sdk')
                count += 1
            except ValueError as exc:
                self.assertIn('additional data/index page required', str(exc))
                break
        self.assertGreaterEqual(count, 28)
        self.assertLess(count, 60)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'new.cln'
            write_new(path, data, profile='sdk')
            self.assertEqual(parse_file(path, profile='sdk').size, 6144)
            with self.assertRaises(FileExistsError):
                write_new(path, data, profile='sdk')
            self.assertEqual(path.read_bytes(), data)

    def test_multipage_reading_does_not_enable_writing(self):
        data = bytearray(build('two'))
        row = parse_bytes(data).appointments[-1]
        raw = bytes.fromhex(row.raw_hex)
        data.extend(raw + b'\x03' + bytes(1024 - len(raw) - 1))
        data[row.offset:5120] = b'\x03' + bytes(5120 - row.offset - 1)
        struct.pack_into('<HHH', data, row.index_offset, 6, 0, row.record_id)
        self.assertEqual(parse_bytes(data, profile='sdk').appointments[-1].offset, 6144)
        with self.assertRaises(CalendarParseError):
            parse_bytes(data)
        with self.assertRaisesRegex(ValueError, 'additional-page'):
            append_appointment(data, profile='sdk')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'additional-page'):
                write_new(Path(temp) / 'new.cln', data, profile='sdk')
