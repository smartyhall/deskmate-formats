"""Check documented Calendar fields against archived application output."""

from datetime import date
from pathlib import Path
import unittest

from deskmate_formats.calendar.personal import parse_file


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'application-generated' / 'calendar'


class CalendarSDKCrosswalkTests(unittest.TestCase):
    def test_alarm_enabled_application_save(self):
        db = parse_file(FIXTURES / 'alarm-on-86box-trial-c.cln')
        event, = db.appointments
        self.assertIs(event.alarm_enabled, True)
        self.assertEqual(event.raw_fields['Protected'], '71')

    def test_configuration_records_preserve_the_recorded_exit_mode(self):
        # Development Guide A-5/A-6. E01 exited from month view and E02 from day view.
        cases = (
            ('e01-86box-historical-match.cln', 2),
            ('e02-86box-historical-match.cln', 4),
        )
        payloads = []
        for name, screen in cases:
            with self.subTest(fixture=name):
                db = parse_file(FIXTURES / name)
                config, = db.internal_records
                self.assertEqual(config.raw_fields['Date'], '20 20 ff')
                self.assertEqual(config.raw_fields['Protected'], '30')
                self.assertTrue(all(config.raw_fields[field] == '' for field in
                                    ('DayOfWeek', 'Duration', 'StartTime', 'EndTime')))
                payload = bytes.fromhex(config.raw_fields['Description'])
                self.assertEqual(len(payload), 25)
                self.assertEqual(payload[0] - 0x61, 8)
                self.assertEqual(payload[1] - 0x61, screen)
                self.assertEqual(payload[2:14], b'a' * 12)
                self.assertEqual(bytes.fromhex(config.raw_hex)[-1], 0x02)
                payloads.append(payload)
        self.assertEqual(payloads[0][2:], payloads[1][2:])

    def test_ordinary_event_matches_documented_bias_and_bit_layout(self):
        # Development Guide A-7. The synthetic UI input was Friday, 09:00 to 10:00, alarm off.
        day = date(2026, 10, 23)
        for name, description in (
            ('e01-86box-historical-match.cln', 'LPHa123'),
            ('e02-86box-historical-match.cln', 'LPHa124'),
        ):
            with self.subTest(fixture=name):
                db = parse_file(FIXTURES / name)
                event, = db.appointments
                raw = {field: bytes.fromhex(value) for field, value in event.raw_fields.items()}
                self.assertEqual(raw['Date'], bytes(0x61 + value for value in
                                                    (day.year - 1980, day.month, day.day)))
                sunday_based_weekday = (day.weekday() + 1) % 7 + 1
                self.assertEqual(raw['DayOfWeek'], bytes([0x61 + sunday_based_weekday]))
                self.assertEqual(raw['Duration'], b'')
                self.assertEqual(raw['StartTime'], bytes([0x80 | (9 << 2)]))
                self.assertEqual(raw['EndTime'], bytes([0x80 | (10 << 2)]))
                self.assertEqual(raw['Protected'], b'1')
                self.assertEqual(raw['Description'], description.encode('ascii'))
                self.assertEqual(bytes.fromhex(event.raw_hex)[-1], 0x02)
