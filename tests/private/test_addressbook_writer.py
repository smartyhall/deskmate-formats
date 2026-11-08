"""Offline writer oracle against independently published native A01–A04 hashes.

Set DESKMATE_ADR_BASELINE to the preserved, empty baseline file, or DOSLAB_ROOT
to the original archive. No emulator, mutation of inputs or new native run.
"""
import hashlib
import os
from pathlib import Path
import unittest

from deskmate_formats.addressbook import Contact, create_contact, parse_bytes

BASELINE = 'cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c'
CASES = (
    ('A01', Contact('TEST', 'USER A', '', '202-555-0142'),
     '19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8'),
    ('A02', Contact('TESTLONG', 'USER A', '', '202-555-0142'),
     'ae216968bce070f7a5d9619b844e20295428dac628984a05d22f203e032d76a6'),
    ('A03', Contact('TEST', 'USER A', '', '555-0142'),
     '81b48761fce08c57cbe43a3bb0a23fc4f7d2faee0cdb800375c9175220787d5d'),
    ('A04', Contact('TEST', 'USER A', 'METRO', '202-555-0142'),
     '2584874c957d74b0c1240ebc0d02a50ac4c886a53b977749cb912e1628cce46f'))


class AddressBookWriterOracles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('DESKMATE_ADR_BASELINE')
        if path is None:
            root = os.environ.get('DOSLAB_ROOT')
            if not root:
                raise unittest.SkipTest('Set DESKMATE_ADR_BASELINE or DOSLAB_ROOT')
            path = Path(root) / 'EXPERIMENTS/ADDRESSBOOK/A00_recon/after/files/DESKMATE/PERSONAL.ADR'
        cls.path = Path(path)
        cls.source = cls.path.read_bytes()
        if hashlib.sha256(cls.source).hexdigest() != BASELINE:
            raise AssertionError('baseline identity mismatch')

    def test_all_four_published_native_hashes(self):
        for name, contact, expected in CASES:
            with self.subTest(case=name):
                data = create_contact(self.source, contact)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected)
                self.assertEqual(len(parse_bytes(data).contacts), 1)
        self.assertEqual(self.path.read_bytes(), self.source)

    def test_unrelated_native_records_preserved(self):
        before = parse_bytes(self.source).storage
        for _, contact, _ in CASES:
            after = parse_bytes(create_contact(self.source, contact)).storage
            for name in ('DBCOLS', 'NAMES', 'CONFIG'):
                self.assertEqual(before.table(name), after.table(name))
            self.assertEqual(before.header, after.header)
