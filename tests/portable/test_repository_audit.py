"""Keep native DeskMate materials out of both source trees and distributions."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    'audit_repository', Path(__file__).resolve().parents[2] / 'tools/audit_repository.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class RepositoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = audit.ROOT
        audit.ROOT = Path(self.temp.name)

    def tearDown(self):
        audit.ROOT = self.old
        self.temp.cleanup()

    def test_native_extensions_are_blocked_even_for_printable_files(self):
        for suffix in ('.PDM', '.RES', '.R89', '.FIL', '.ADR', '.PCL', '.HLP', '.TUT'):
            p = audit.ROOT / ('native' + suffix)
            p.write_text('synthetic printable content', encoding='utf-8')
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'excluded'):
                audit.audit()
            p.unlink()

    def test_authored_text_remains_allowed(self):
        (audit.ROOT / 'report.md').write_text('Independent findings.\n', encoding='utf-8')
        self.assertEqual(audit.audit()['source_files_checked'], 1)

    def test_mz_signature_is_blocked_under_an_innocent_extension(self):
        (audit.ROOT / 'report.txt').write_bytes(b'MZ synthetic header')
        with self.assertRaisesRegex(ValueError, 'software/database bytes'):
            audit.audit()

    def test_native_extension_in_wheel_is_blocked(self):
        dist = audit.ROOT / 'dist'
        dist.mkdir()
        with zipfile.ZipFile(dist / 'synthetic.whl', 'w') as z:
            z.writestr('example/native.res', 'synthetic resource')
        with self.assertRaisesRegex(ValueError, 'excluded file in archive'):
            audit.audit()
