"""Verify the actual Calendar, Address Book, and Text cross-release specimens."""

from pathlib import Path
import unittest

from deskmate_formats import database, text
from deskmate_formats.addressbook import personal as addressbook
from deskmate_formats.calendar import personal as calendar


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated'


class DeskMateReleaseComparisonTest(unittest.TestCase):
    def test_calendar_native_stages(self):
        directory = FIXTURES / 'calendar'
        for stage, expected in (('default', []), ('added', ['LPHa123']),
                                ('edited', ['LPHa124']), ('removed', [])):
            with self.subTest(stage=stage):
                content = (directory / f'303-native-{stage}.cal').read_bytes()
                appointments = calendar.parse_bytes(content).appointments
                self.assertEqual([appointment.description for appointment in appointments], expected)
                for appointment in appointments:
                    self.assertEqual((appointment.date, appointment.start_time, appointment.end_time),
                                     ('2026-10-23', '09:00', '10:00'))

        added = (directory / '303-native-added.cal').read_bytes()
        historical = (directory / 'e01-86box-historical-match.cln').read_bytes()
        self.assertEqual(added[:0x100d] + b'c' + added[0x100e:], historical)
        self.assertEqual((directory / '303-native-edited.cal').read_bytes(),
                         (directory / 'e02-86box-historical-match.cln').read_bytes())
        early = (directory / '302-native-added.cal').read_bytes()
        self.assertEqual(early[:0x18] + b'W' + early[0x19:], added)
        self.assertEqual(calendar.parse_bytes(early).appointments[0].description, 'LPHa123')

    def test_address_book_metadata_and_contact_rows(self):
        directory = FIXTURES / 'addressbook'
        for stage, names in (('default', []), ('added', ['TEST']), ('edited', ['TESTLONG']),
                             ('cross-save', ['ZULUX', 'TEST'])):
            with self.subTest(stage=stage):
                book = addressbook.parse_file(directory / f'303-native-{stage}.adr')
                self.assertEqual([contact.known_fields['first_name'] for contact in book.contacts], names)
                config, = book.storage.table('CONFIG').rows
                self.assertEqual(bool(config.fields[2]), stage in ('edited', 'cross-save'))
                for contact in book.contacts:
                    fields = contact.known_fields
                    self.assertEqual(fields['last_name'], 'ALPHA' if fields['first_name'] == 'ZULUX' else 'USER A')
                    self.assertEqual(fields['work_phone'],
                                     '555-0100' if fields['first_name'] == 'ZULUX' else '202-555-0142')

    def test_302_address_book_declares_narrower_fields(self):
        path = FIXTURES / 'addressbook/302-native-added.adr'
        blob = path.read_bytes()
        table = database.parse_bytes(blob, max_pages=10).table('DATA')
        columns = {column.name: column.width for column in table.columns}
        self.assertEqual((columns['Title'], columns['Address']), (5, 38))
        row, = table.rows
        later, = addressbook.parse_file(path.with_name('303-native-added.adr')).contacts
        self.assertEqual(row.raw, later.row.raw)
        with self.assertRaisesRegex(database.DatabaseError, 'unsupported_schema'):
            addressbook.parse_bytes(blob)

    def test_plain_text_saved_bytes_and_logical_text(self):
        path = FIXTURES / 'text/303-native-match.doc'
        self.assertEqual(path.read_bytes(), b'ALPHA\r\nBETA \x1a')
        self.assertEqual(text.extract_file(path), 'ALPHA\nBETA')
