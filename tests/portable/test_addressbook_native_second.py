"""Actual native pair, independent raw prediction and exact-source writer gate."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest

from deskmate_formats.addressbook.experimental_second import append_second_contact, write_second_contact
from deskmate_formats.addressbook.personal import Contact, parse_bytes
from deskmate_formats.addressbook.writer import create_contact

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/application-generated/addressbook'
CONTACT = Contact('ZULU', 'ALPHA', work_phone='555-0100')


def expected(source, first=b'ZULU', phone=b'555-0100'):
    # Predeclared fixed A01 offsets/defaults, not a production parser/writer.
    row = (b'\x80\x11\x01' + first + b'\x01ALPHA' + b'\x01' * 6 + phone
           + b'\x01\x01\x01Birthday\x01\x01Anniversary\x01\x01n\x01\x02')
    output = bytearray(source)
    output[0x431:0x436] = b'00002'
    output[0x43B:0x440] = b'00018'
    output[0x103D:0x103E + len(row)] = row + b'\x03'
    output[0x1428:0x1434] = bytes.fromhex('04 00 3d 00 11 00 04 00 00 00 10 00')
    return bytes(output)


class NativeSecondContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (FIXTURES / 'a01-historical-match-tool-generated.adr').read_bytes()
        cls.native = (FIXTURES / 'native-two-contact-20261117.adr').read_bytes()

    def test_native_whole_bytes_match_predeclared_prediction_and_generated_fixture(self):
        self.assertEqual(len(self.source), 10240)
        self.assertEqual(sha256(self.source).hexdigest(),
                         '19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8')
        self.assertEqual(self.native, expected(self.source))
        self.assertEqual(sha256(self.native).hexdigest(),
                         'c37c62bf2fb16963f910c4d4c80e395d3a42305b55e954435d30ca0f9d3cdf40')
        self.assertEqual((FIXTURES / 'second-alpha-tool-generated.adr').read_bytes(), self.native)
        self.assertEqual(append_second_contact(self.source, CONTACT, experimental=True), self.native)

    def test_independent_trial_diagnostic_all_checks(self):
        spec = importlib.util.spec_from_file_location('independent_second_trial',
                    ROOT / 'tools/experimental/database_trial_report.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checks = module.addressbook_trial(self.source, self.native)['trial_checks']
        self.assertEqual(checks.pop('unrelated_changed_offsets'), [])
        self.assertTrue(all(value is True for value in checks.values()), checks)

    def test_physical_append_and_last_name_index_are_separate(self):
        self.assertEqual(self.native[4096:4157], self.source[4096:4157])
        self.assertEqual(self.native[4157:4159], b'\x80\x11')
        self.assertEqual(self.native[4213], 3)
        self.assertEqual(struct.unpack_from('<6H', self.native, 5160), (4, 61, 17, 4, 0, 16))
        self.assertEqual(sum(a != b for a, b in zip(self.source, self.native)), 63)
        self.assertEqual([sum(a != b for a, b in zip(self.source[p:p + 1024],
                                                   self.native[p:p + 1024]))
                          for p in range(0, 10240, 1024)], [0, 2, 0, 0, 57, 4, 0, 0, 0, 0])
        self.assertEqual([c.known_fields for c in parse_bytes(self.native).contacts],
                         [dict(first_name='ZULU', last_name='ALPHA', city='', work_phone='555-0100'),
                          dict(first_name='TEST', last_name='USER A', city='', work_phone='202-555-0142')])

    def test_offline_first_name_phone_width_boundaries_and_source_immutability(self):
        for first, phone in (('A', ''), ('Z' * 18, '9' * 20), ('Test Name', '202-555-0142')):
            mutable = bytearray(self.source)
            contact = Contact(first, 'ALPHA', work_phone=phone)
            actual = append_second_contact(mutable, contact, experimental=True)
            self.assertEqual(actual, expected(self.source, first.encode(), phone.encode()))
            self.assertEqual(mutable, self.source)

    def test_explicit_opt_in_and_exact_source_gate_include_adversarial_layouts(self):
        for value in (False, None, 1, 'yes'):
            with self.assertRaises(ValueError):
                append_second_contact(self.source, CONTACT, experimental=value)
        for source in (None, '', self.source[:-1], self.source + b'\0', self.native):
            with self.assertRaises(ValueError):
                append_second_contact(source, CONTACT, experimental=True)
        # Route, pointer ownership/interior target, ID, hole, count, schema and
        # dirty last-slot changes all fail before any output can be published.
        for at in (0x1400, 0x1428, 0x142A, 0x142C, 0x1434, 0x431, 0x802, 0x1518):
            changed = bytearray(self.source); changed[at] ^= 1
            with self.assertRaises(ValueError):
                append_second_contact(changed, CONTACT, experimental=True)
        for contact in (None, Contact('ZULU', 'BETA'), Contact('ZULU', 'ALPHA', city='METRO')):
            with self.assertRaises(ValueError):
                append_second_contact(self.source, contact, experimental=True)
        with self.assertRaises(ValueError):
            create_contact(self.source, CONTACT)  # Original API stays empty-to-one.

    def test_cli_new_file_and_existing_destination_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.adr', Path(folder) / 'output.adr'
            source.write_bytes(self.source)
            result = subprocess.run([sys.executable, str(ROOT / 'tools/experimental/append_addressbook_second.py'),
                                     str(source), str(output), '--experimental'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), self.native)
            with self.assertRaises(FileExistsError):
                write_second_contact(output, self.source, CONTACT, experimental=True)
            self.assertEqual(source.read_bytes(), self.source)
