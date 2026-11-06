"""Publication audit tests for application-generated synthetic-data specimens."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from tools import audit_repository


class FixtureAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / 'tests/fixtures/application-generated'
        self.base.mkdir(parents=True)

    def manifest(self, items):
        (self.base / 'manifest.json').write_text(
            json.dumps({'fixtures': items}), encoding='utf-8')

    @staticmethod
    def entry(name, data):
        return {'path': name, 'sha256': hashlib.sha256(data).hexdigest(),
                'size': len(data), 'origin': 'DeskMate 3.05 controlled experiment',
                'synthetic_data': True}

    def audit(self):
        with patch.object(audit_repository, 'ROOT', self.root):
            return audit_repository.audit()

    def test_generated_fil_database_accepted(self):
        data = b'\x03FIL' + b'\x00' * 24
        path = self.base / 'calendar/E02.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/E02.cln', data)])
        self.assertEqual(self.audit()['application_generated_fixtures_checked'], 1)

    def test_tampering_rejected(self):
        data = b'\x03FIL' + b'\x00' * 24
        path = self.base / 'addressbook/A01.adr'
        path.parent.mkdir()
        path.write_bytes(data + b'!')
        self.manifest([self.entry('addressbook/A01.adr', data)])
        with self.assertRaisesRegex(ValueError, 'digest or size mismatch'):
            self.audit()

    def test_unlisted_binary_rejected(self):
        self.manifest([])
        (self.base / 'unlisted.cln').write_bytes(b'\x03FIL')
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_missing_declared_binary_rejected(self):
        self.manifest([self.entry('calendar/E02.cln', b'data')])
        with self.assertRaisesRegex(ValueError, 'missing declared fixtures'):
            self.audit()

    def test_executable_outside_rejected(self):
        self.manifest([])
        (self.root / 'installer.com').write_bytes(b'MZ')
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_disguised_executable_rejected(self):
        data = b'MZ' + b'\x00' * 16
        path = self.base / 'calendar/fake.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/fake.cln', data)])
        with self.assertRaisesRegex(ValueError, 'executable disguised'):
            self.audit()

    def test_traversal_rejected(self):
        self.manifest([self.entry('../outside.cln', b'data')])
        with self.assertRaisesRegex(ValueError, 'unsafe fixture path'):
            self.audit()

    def test_manifested_binary_with_access_token_rejected(self):
        data = b'\x03FIL\x00' + (b'https://example.invalid/?access_' + b'token=EXAMPLE12345678')
        path = self.base / 'calendar/E03.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/E03.cln', data)])
        with self.assertRaisesRegex(ValueError, 'archive access query'):
            self.audit()

    def test_manifested_binary_with_private_host_path_rejected(self):
        data = b'\x03FIL\x00C:\\Users\\example\\Secrets'
        path = self.base / 'calendar/E04.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/E04.cln', data)])
        with self.assertRaisesRegex(ValueError, 'host Windows user path'):
            self.audit()

    def test_source_distribution_with_omitted_binary_is_auditable(self):
        self.manifest([self.entry('calendar/E02.cln', b'private-test-file')])
        (self.root / 'PKG-INFO').write_text('Metadata-Version: 2.4\n')
        self.assertEqual(self.audit()['status'], 'passed')

    def test_private_observatory_spool_rejected_in_checkout_and_archive(self):
        self.manifest([])
        journal = self.root / 'events.jsonl'
        journal.write_bytes(b'{"summary":"fictional private content"}\n')
        with self.assertRaisesRegex(ValueError, 'private Observatory spool file'):
            self.audit()
        journal.unlink()
        dist = self.root / 'dist'
        dist.mkdir()
        with ZipFile(dist / 'test.whl', 'w') as wheel:
            wheel.writestr('data/writer.lock', b'')
        with self.assertRaisesRegex(ValueError, 'private Observatory spool file in archive'):
            self.audit()


if __name__ == '__main__':
    unittest.main()
