"""Independent synthetic Address Book framing, preservation and safety controls."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deskmate_formats.addressbook import Contact, parse_bytes, parse_file, create_contact, write_new
from deskmate_formats.addressbook.cli import main, create_main
from deskmate_formats.addressbook.samples import contacts
from deskmate_formats.database import DatabaseError
from database_synthetic import addressbook

FIELDS = [b'', b'TEST', b'USER A', b'', b'', b'', b'', b'', b'202-555-0142',
          b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n']


class AddressBookTests(unittest.TestCase):
    def test_empty_and_single_contact_fields(self):
        self.assertFalse(parse_bytes(addressbook()).contacts)
        row, = parse_bytes(addressbook(FIELDS)).contacts
        self.assertEqual(row.record_id, 16)
        self.assertEqual(row.known_fields, {'first_name': 'TEST', 'last_name': 'USER A',
                                          'city': '', 'work_phone': '202-555-0142'})
        self.assertEqual(row.opaque_fields['Christmas'], b'n')
        self.assertEqual(row.opaque_fields['NoteOne'], b'Birthday')
        self.assertEqual(row.row.offset, 4096)
        self.assertEqual(len(row.row.raw), 61)

    def test_four_independent_field_oracles(self):
        for first, city, phone in (('TEST', '', '202-555-0142'), ('TESTLONG', '', '202-555-0142'),
                                    ('TEST', '', '555-0142'), ('TEST', 'METRO', '202-555-0142')):
            fields = list(FIELDS)
            fields[1], fields[4], fields[8] = first.encode(), city.encode(), phone.encode()
            source = bytearray(addressbook())
            before = bytes(source)
            output = create_contact(source, Contact(first, 'USER A', city, phone))
            self.assertEqual(output, addressbook(fields))
            self.assertEqual(bytes(source), before)
            self.assertEqual(output[:1024], before[:1024])
            self.assertEqual(output[2048:4096], before[2048:4096])
            self.assertEqual(output[6144:], before[6144:])

    def test_variations_widths_and_opaque_fields(self):
        for field, width in ((0, 10), (3, 43), (7, 29), (9, 20), (14, 40)):
            fields = list(FIELDS)
            fields[field] = b'X' * width
            row, = parse_bytes(addressbook(fields)).contacts
            self.assertEqual(row.row.fields[field], fields[field])
            fields[field] += b'X'
            with self.assertRaisesRegex(DatabaseError, 'field width'):
                parse_bytes(addressbook(fields))
        fields = list(FIELDS)
        fields[1] = b'\x82'
        row, = parse_bytes(addressbook(fields)).contacts
        self.assertIsNone(row.known_fields['first_name'])
        self.assertEqual(dict(row.raw_fields)['FirstName'], b'\x82')

    def test_validated_contacts_and_sample_set(self):
        source = addressbook()
        for contact in contacts():
            row, = parse_bytes(create_contact(source, contact)).contacts
            self.assertEqual(row.known_fields['last_name'], contact.last_name)
        self.assertEqual(len(contacts()), 25)
        self.assertEqual(len(set(contacts())), 25)
        original = Contact('Test', 'Example')
        for change in ({'first_name': ''}, {'last_name': 'X' * 21}, {'city': 'X' * 21},
                       {'work_phone': 'X' * 21}, {'first_name': '\x01'}, {'city': 'café'},
                       {'work_phone': 123}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(original, **change)

    def test_multiple_insertion_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(DatabaseError, 'native index evidence'):
            create_contact(addressbook(FIELDS), Contact('Other', 'Example'))
        source = bytearray(addressbook())
        source[0x43B:0x440] = b'00018'
        with self.assertRaisesRegex(DatabaseError, 'counter/index profile'):
            create_contact(source, Contact('Other', 'Example'))

    def test_two_independently_framed_rows_are_read_without_order_claim(self):
        other = list(FIELDS)
        other[1], other[2] = b'OTHER', b'EXAMPLE'
        book = parse_bytes(addressbook(contact_rows=[FIELDS, other]))
        self.assertEqual([r.known_fields['first_name'] for r in book.contacts], ['TEST', 'OTHER'])
        self.assertTrue(any('unverified' in w for w in book.warnings))

    def test_malformed_and_unknown_profiles(self):
        source = addressbook(FIELDS)
        for data in (source[:-1], source + bytes(1024), b'BAD!' + source[4:]):
            with self.assertRaises(DatabaseError):
                parse_bytes(data)
        fields = list(FIELDS)
        fields[1] = b'BAD\x02'
        with self.assertRaises(DatabaseError):
            parse_bytes(addressbook(fields))
        unknown = bytearray(source)
        at = unknown.index(b'FirstName')
        unknown[at:at + 9] = b'OtherName'
        with self.assertRaises(DatabaseError):
            parse_bytes(unknown)

    def test_atomic_publication_and_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output, item = root / 'empty.adr', root / 'new.adr', root / 'contact.json'
            source.write_bytes(addressbook())
            item.write_text(json.dumps({'first_name': 'Test', 'last_name': 'Example',
                                       'city': 'Metro', 'work_phone': '555-0100'}))
            argv = [str(source), str(output), '--contact', str(item)]
            self.assertEqual(create_main(argv), 0)
            self.assertEqual(len(parse_file(output).contacts), 1)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(create_main(argv), 2)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main([str(output)]), 0)
            self.assertEqual(json.loads(out.getvalue())['contact_count'], 1)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                write_new(output, before)
            target = root / 'failed.adr'
            with patch('deskmate_formats.addressbook.writer.os.link', side_effect=OSError('unsupported')):
                with self.assertRaises(OSError):
                    write_new(target, before)
            self.assertFalse(target.exists())
            self.assertFalse(list(root.glob('.addressbook-*')))
            self.assertEqual(source.read_bytes(), addressbook())
