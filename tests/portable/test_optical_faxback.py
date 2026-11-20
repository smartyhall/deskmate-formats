"""Portable optical and Faxback regressions using independently made controls."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from struct import pack_into
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/archive'))
import faxback_index as fax
import intelligence_extract as extraction
import optical_inventory as optical


def iso_descriptor():
    descriptor = bytearray(2048)
    descriptor[:7] = b'\x01CD001\x01'
    descriptor[40:72] = b'TEST DISC'.ljust(32, b' ')
    descriptor[80:88] = b'\x18\0\0\0\0\0\0\x18'
    descriptor[128:132] = b'\0\x08\x08\0'
    result = bytearray(24 * 2048)
    result[16 * 2048:17 * 2048] = descriptor
    return result


class OpticalTests(unittest.TestCase):
    def test_cooked_and_raw_descriptors(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'media')
            data = iso_descriptor()
            path.write_bytes(data)
            info = extraction.optical_descriptor(path)
            self.assertEqual(info['metadata']['volume'], 'TEST DISC')
            self.assertEqual(extraction.identify(path, 'label.bin'), 'iso9660')
            raw = bytearray(24 * 2352)
            sync = b'\0' + b'\xff' * 10 + b'\0\0\0\0\1'
            raw[16 * 2352:16 * 2352 + 16] = sync
            raw[16 * 2352 + 16:16 * 2352 + 16 + 2048] = data[16 * 2048:17 * 2048]
            path.write_bytes(raw)
            self.assertEqual(extraction.identify(path, 'label.bin'), 'cd-raw')
            path.write_bytes(data[:-1])
            self.assertEqual(extraction.identify(path, 'label.iso'), 'optical-image')

    def test_blank_iso_link_field_is_regular_and_blank_folder_size_is_valid(self):
        listing = ('Type = Iso\n----------\nPath = DIR\nFolder = +\nSize = \n\n'
                   'Path = DIR\\README.TXT\nFolder = -\nSize = 5\nSymbolic Link = \n\n'
                   'Path = LINK\nFolder = -\nSize = 5\nSymbolic Link = TARGET\n')
        kind, rows = extraction._legacy_entries(listing)
        self.assertEqual(kind, 'Iso')
        self.assertEqual(rows, [('DIR', 0, 'directory'), ('DIR\\README.TXT', 5, None),
                                ('LINK', 5, 'non-regular')])

    def test_zip_iso_preserves_nested_hash_and_selected_member(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'input.zip'
            image = iso_descriptor()
            with ZipFile(source, 'w') as archive:
                archive.writestr('nested/disc.iso', image)
            listing = b'Type = Iso\n----------\nPath = README.TXT\nSize = 5\n'
            with (patch.object(optical, '_capture', return_value=(0, listing)),
                  patch.object(optical, '_seven_member', return_value=b'test\n')):
                result, = optical.inspect(source, Path('7z'), root / 'receipt.json', ('readme.txt',))
            self.assertEqual(result['member'], 'nested/disc.iso')
            self.assertEqual(result['sha256'], hashlib.sha256(image).hexdigest())
            self.assertEqual(result['extracted'][0]['text_prefix'], 'test\n')

    def test_ne_ordinal_zero_has_bounds(self):
        specimen = bytearray(160)
        specimen[:2] = b'MZ'
        pack_into('<I', specimen, 0x3c, 64)
        specimen[64:66] = b'NE'
        pack_into('<H', specimen, 64 + 0x26, 64)
        specimen[64 + 0x36] = 2
        specimen[128:136] = b'\x05HELLO\0\0'
        self.assertEqual(optical.executable_header(specimen)['resident_name'], 'HELLO')
        self.assertIsNone(optical.executable_header(specimen[:131])['resident_name'])


class FaxbackTests(unittest.TestCase):
    def test_verified_header_catalog_links_and_repeatable_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp, 'mirror')
            root.mkdir()
            body = b'Example (250-1234)   Catalog Listing   Faxback Doc. # 1234\n1235   Setup\n'
            (root / 'test.txt').write_bytes(body)
            row = {'kind': 'file', 'url': 'https://example.test/01234.txt',
                   'rel': 'tandy1000/faxback/01234.txt', 'local': 'test.txt',
                   'status': 'verified', 'sha256': hashlib.sha256(body).hexdigest(),
                   'bytes': len(body), 'observed': '2026-11-20'}
            db = root.parent / 'private.sqlite'
            with patch.object(fax, 'read_transfer_state', return_value=[row]):
                for _ in range(2):
                    report = fax.index(root, db)
                    self.assertEqual(report['identity_states'], {'body-confirmed': 1})
                    self.assertEqual(report['document_edges'], 1)
            with closing(sqlite3.connect(db)) as connection:
                self.assertEqual(connection.execute('SELECT number FROM document_ref').fetchone(), (1235,))
                self.assertEqual(connection.execute("SELECT count(*) FROM text WHERE text MATCH 'Setup'").fetchone(),
                                 (1,))
                self.assertEqual(connection.execute("SELECT catalog FROM catalog_ref WHERE evidence='title'").fetchone(),
                                 ('250-1234',))


if __name__ == '__main__':
    unittest.main()
