"""Portable parameterized checks for the programmatic Calendar corpus."""
import struct
import unittest

from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes
from deskmate_formats.calendar.writer import Appointment, append_appointment, capacity

from calendar_corpus import DATES, TIMES, Case, probes, specimen_cases
from synthetic import INTERNAL


def clock(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def check_case(test, case, data):
    db = parse_bytes(data)
    test.assertEqual(len(db.appointments), len(case.events))
    test.assertEqual(len(db.internal_records), 1)
    table = db.metadata['tables']['PERSONAL']
    test.assertEqual(table['record_count'], len(case.events) + 1)
    test.assertEqual(table['next_id_candidate'], len(case.events) + 17)
    internal, = db.internal_records
    test.assertEqual((internal.record_id, internal.offset, internal.raw_hex),
                     (16, 4096, INTERNAL.hex(' ')))

    keys = [(record.date, record.start_time) for record in db.appointments]
    test.assertEqual(keys, sorted(set(keys)))
    for record, physical in zip(db.appointments, case.index_order, strict=True):
        event = case.events[physical]
        day, weekday, _, _ = DATES[event.day]
        test.assertEqual((record.date, record.day_of_week, record.start_time,
                          record.end_time, record.description, record.undecoded_fields),
                         (day.isoformat(), weekday, clock(TIMES[event.start]),
                          clock(TIMES[event.end]), event.description,
                          {'Duration': '', 'Protected': '31'}))
        test.assertEqual(record.record_id, 17 + physical)

    cursor = 4096
    for record in sorted(db.records, key=lambda row: row.record_id):
        test.assertEqual(record.offset, cursor)
        cursor += record.length
    test.assertEqual(data[cursor], 3)
    for slot, record in enumerate(db.records):
        index_offset = 5160 + 6 * slot
        test.assertEqual(record.index_offset, index_offset)
        test.assertEqual(struct.unpack_from('<HHH', data, index_offset),
                         (4, record.offset - 4096, record.record_id))



def check_writer(test, case, data):
    if case.events:
        prefix = Case(case.name, case.events[:-1], case.category).build()
        last = case.events[-1]
        appointment = Appointment(DATES[last.day][0], TIMES[last.start], TIMES[last.end],
                                  last.description)
        # Full-byte equality also checks the unrelated pages and all existing rows.
        source = bytearray(prefix)
        test.assertEqual(append_appointment(source, appointment), data)
        test.assertEqual(source, prefix)
    if case.category == 'exact-fit':
        test.assertEqual(capacity(data)['data_bytes'], 0)
        with test.assertRaisesRegex(ValueError, 'additional data/index page required'):
            append_appointment(prefix, Appointment(appointment.day, appointment.start_minutes,
                                                   appointment.end_minutes, last.description + '~'))


def check_probe(test, probe, data):
    if probe.error:
        with test.assertRaises(CalendarParseError) as caught:
            parse_bytes(data)
        test.assertEqual(caught.exception.code, probe.error)
    else:
        appointment, = parse_bytes(data).appointments
        test.assertIsNone(appointment.description)
        test.assertEqual(appointment.undecoded_fields['Description'], '82')
        test.assertEqual(appointment.raw_fields['Description'], '82')


class CalendarCorpusTests(unittest.TestCase):
    def test_valid_corpus(self):
        seen = set()
        for case in specimen_cases():
            with self.subTest(case=case.name):
                data = case.build()
                self.assertNotIn(data, seen)
                seen.add(data)
                check_case(self, case, data)
                check_writer(self, case, data)


    def test_parser_probes(self):
        for probe in probes():
            with self.subTest(probe=probe.name):
                check_probe(self, probe, probe.data)
