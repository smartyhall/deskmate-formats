"""Versioning, strict validation, explicit loss and semantic round-trip controls."""
from copy import deepcopy
from datetime import date
import unittest

from deskmate_formats import interchange as api
from deskmate_formats.calendar.personal import parse_bytes as calendar
from deskmate_formats.calendar.writer import Appointment, append_appointment
from deskmate_formats.addressbook import Contact, parse_bytes as addressbook
from database_synthetic import addressbook as adr
from synthetic import build, assemble, INTERNAL, event
from multicalendar_synthetic import two_calendars


class InterchangeTests(unittest.TestCase):
    def test_multicalendar_export_refuses_to_flatten_table_scoped_ids(self):
        from pathlib import Path
        fixtures = Path(__file__).parents[1] / 'fixtures/application-generated/calendar'
        sources = [two_calendars()] + [(fixtures / name).read_bytes() for name in (
            'native-second-empty-calendar-operator.cln', 'native-second-first-event-operator.cln')]
        for source in sources:
            db = calendar(source, profile='sdk')
            for lossy in (False, True):
                with self.subTest(sha256=db.sha256, lossy=lossy), self.assertRaises(api.InterchangeError) as caught:
                    api.export_calendar(db, lossy=lossy)
                self.assertEqual(caught.exception.code, 'unsupported_calendars')
                self.assertEqual(caught.exception.path, '$.native.calendars')

    def test_calendar_semantic_round_trip_and_snapshot_identity(self):
        data = append_appointment(build('empty'), Appointment(date(2028, 2, 29), 795, 855, 'Leap', protected_raw=b'q'), profile='sdk')
        result = api.export_calendar(calendar(data, profile='sdk'))
        self.assertEqual(result.issues, ())
        imported, = api.load_document(result.document)
        self.assertEqual(imported.appointment.day, date(2028, 2, 29))
        self.assertEqual(imported.appointment.protected_raw, b'q')
        self.assertEqual(imported.storage_record_id, 17)
        self.assertEqual(api.calendar_document([imported], source_sha256=result.document['source_sha256']), result.document)

    def test_contact_round_trip(self):
        contact = Contact('Alex', 'Example', 'Metro', '555-0100')
        document = api.addressbook_document([api.ContactItem(contact)])
        self.assertEqual(api.load_document(document), (api.ContactItem(contact),))
        self.assertNotIn('storage_record_id', document['items'][0])

    def test_strict_versions_properties_values_and_ties(self):
        original = api.calendar_document([api.CalendarItem(Appointment(date(2026, 11, 3), 795, 855, 'Test'))])
        cases = []
        for key, value in (('version', 2), ('version', True), ('kind', 'other'), ('timezone', 'UTC'),
                           ('source_sha256', 'wrong')):
            doc = deepcopy(original)
            doc[key] = value
            cases.append(doc)
        for key, value in (('rrule', 'DAILY'), ('uid', 'invented'), ('alarm_enabled', 1),
                           ('date', '2026-02-29'), ('date', '20261103'), ('description', 'bad\n'),
                           ('start_minutes', 0), ('end_minutes', 1426), ('storage_record_id', True)):
            doc = deepcopy(original)
            doc['items'][0][key] = value
            cases.append(doc)
        doc = deepcopy(original)
        doc['items'] *= 2
        cases.append(doc)
        for n, document in enumerate(cases):
            with self.subTest(n=n), self.assertRaises(api.InterchangeError) as caught:
                api.load_document(document)
            self.assertTrue(caught.exception.code)
            self.assertTrue(caught.exception.path.startswith('$'))

    def test_calendar_loss_is_explicit(self):
        data = assemble([(16, INTERNAL), (17, event(17, 'UNSUPPORTED', duration=b'Q'))], [16, 17])
        with self.assertRaises(api.InterchangeError):
            api.export_calendar(calendar(data))
        result = api.export_calendar(calendar(data), lossy=True)
        self.assertEqual(result.document['items'], [])
        self.assertEqual(result.issues[0].code, 'skipped_record')

    def test_opaque_contact_loss_requires_opt_in(self):
        fields = [b'', b'Alex', b'Example', b'1 Test Street', b'Metro', b'', b'', b'', b'555-0100',
                  b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n']
        book = addressbook(adr(fields))
        with self.assertRaises(api.InterchangeError) as caught:
            api.export_addressbook(book)
        self.assertEqual(caught.exception.code, 'unsupported_fields')
        result = api.export_addressbook(book, lossy=True)
        self.assertEqual(result.issues[0].code, 'omitted_opaque_fields')
        self.assertEqual(api.load_document(result.document)[0].contact.city, 'Metro')
        self.assertEqual(book.contacts[0].opaque_fields['Address'], b'1 Test Street')

    def test_python_api_cannot_silently_drop_duration(self):
        item = api.CalendarItem(Appointment(date(2026, 11, 3), 795, 855, 'Test', duration_raw=b'Q'))
        with self.assertRaises(ValueError):
            api.calendar_document([item])

    def test_versioned_examples_are_valid_and_have_exact_counts(self):
        import json
        from pathlib import Path
        root = Path(__file__).parents[2] / 'examples'
        for name, count in (('calendar-14-days.v1.json', 29), ('contacts-25.v1.json', 25)):
            document = json.loads((root / name).read_text(encoding='utf-8'))
            self.assertEqual(len(api.load_document(document)), count)
