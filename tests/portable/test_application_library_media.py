"""Check the application-library FAT12 builder without vendor media."""

import importlib.util
import json
from pathlib import Path
from struct import unpack_from
import tempfile
import unittest
from zipfile import ZipFile


SCRIPT = Path(__file__).resolve().parents[2] / 'tools/experimental/application_library_media.py'
SPEC = importlib.util.spec_from_file_location('application_library_media', SCRIPT)
MEDIA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MEDIA)


class ApplicationLibraryMediaTest(unittest.TestCase):
    def test_directory_source_builds_labelled_disk(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            source = root / 'set'
            (source / 'DOCS').mkdir(parents=True)
            (source / 'INSTALL.EXE').write_bytes(b'not a real installer')
            (source / 'DOCS' / 'README.TXT').write_bytes(b'Synthetic set file.\r\n')
            output = root / 'disk.img'
            receipt = MEDIA.build([source], 'APP_DISK1', '720k', output)
            image = output.read_bytes()
            self.assertEqual(len(image), 737280)
            self.assertEqual(image[21], 0xf9)
            self.assertEqual(image[54:62], b'FAT12   ')
            self.assertEqual(image[3584:3595], b'APP_DISK1  ')
            self.assertEqual(image[3595], 0x08)
            self.assertEqual(receipt['bytes'], 737280)
            self.assertEqual(len(receipt['sha256']), 64)
            names = {member['name'].upper() for member in receipt['members']}
            self.assertEqual(names, {'INSTALL.EXE', 'DOCS/README.TXT'})
            for member in receipt['members']:
                self.assertEqual(len(member['sha256']), 64)
            json.dumps(receipt)

    def test_zip_source_preserves_dates_and_detects_duplicates(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            first = root / 'one.zip'
            second = root / 'two.zip'
            with ZipFile(first, 'w') as archive:
                archive.writestr('CONTROL.DOC', b'first')
            with ZipFile(second, 'w') as archive:
                archive.writestr('CONTROL.DOC', b'second')
            receipt = MEDIA.build([first], 'ZIP_DISK1 ', '360k', root / 'one.img')
            self.assertEqual(receipt['members'][0]['name'], 'CONTROL.DOC')
            self.assertEqual(receipt['bytes'], 368640)
            with self.assertRaises(ValueError):
                MEDIA.build([first, second], 'ZIP_DISK1 ', '360k', root / 'two.img')

    def test_label_and_geometry_validation(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            source = root / 'set'
            source.mkdir()
            (source / 'A.TXT').write_bytes(b'a')
            for label in ('', 'TOO_LONG_LABEL'):
                with self.subTest(label=label):
                    with self.assertRaises(ValueError):
                        MEDIA.build([source], label, '720k', root / 'bad.img')
            with self.assertRaises(ValueError):
                MEDIA.build([source], 'LABEL', '5m', root / 'bad.img')

    def test_nested_directory_entries_are_written(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            source = root / 'set'
            (source / 'FONT').mkdir(parents=True)
            (source / 'FONT' / 'COBB.FF1').write_bytes(b'font bytes' * 4)
            receipt = MEDIA.build([source], 'FONT_DISK', '720k', root / 'disk.img')
            image = (root / 'disk.img').read_bytes()
            entries = [image[index:index + 32] for index in range(3584, 3584 + 32 * 8, 32)]
            names = [entry[:11] for entry in entries if entry[0] not in (0x00, 0xe5)]
            self.assertIn(b'FONT       ', names)
            self.assertEqual(receipt['members'][0]['name'], 'FONT/COBB.FF1')
            font_dir = next(entry for entry in entries if entry[:11] == b'FONT       ')
            self.assertTrue(font_dir[11] & 0x10)
            child = image.find(b'COBB    FF1')
            self.assertGreater(child, 3584)
            self.assertEqual(image[child + 11], 0x20)


if __name__ == '__main__':
    unittest.main()
