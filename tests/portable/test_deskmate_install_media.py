"""Check disposable FAT12 geometry and hierarchy without vendor media."""

import importlib.util
from pathlib import Path
from struct import unpack_from
import unittest
from zipfile import ZipInfo


SCRIPT = Path(__file__).resolve().parents[2] / 'tools/experimental/deskmate_install_media.py'
SPEC = importlib.util.spec_from_file_location('deskmate_install_media', SCRIPT)
MEDIA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MEDIA)


class InstallMediaTest(unittest.TestCase):
    def test_geometry_and_redundant_fats(self):
        for geometry, length, root, media in (
            ('360k', 368640, 2560, 0xfd),
            ('720k', 737280, 3584, 0xf9),
            ('1440k', 1474560, 9728, 0xf0),
        ):
            with self.subTest(geometry=geometry):
                disk = MEDIA.floppy([(ZipInfo('CONTROL.DOC'), b'')], b'DESKMATE_1 ', geometry)
                self.assertEqual(len(disk), length)
                self.assertEqual(disk[21], media)
                half = (512 + root) // 2
                self.assertEqual(disk[512:half], disk[half:root])
                self.assertEqual(disk[root:root + 12], b'DESKMATE_1 \x08')
                self.assertEqual(disk[root + 32:root + 43], b'CONTROL DOC')
                self.assertEqual(unpack_from('<HI', disk, root + 58), (0, 0))

    def test_nested_documents_and_parent_links(self):
        blob = b'Synthetic document bytes' * 40
        disk = MEDIA.floppy([(ZipInfo('DOCUMENT/ILLSTRTN/A-B.FIG'), blob)], b'DESKMATE_4 ', '1440k')
        self.assertEqual(disk[9760:9772], b'DOCUMENT   \x10')
        self.assertEqual(unpack_from('<H', disk, 9786)[0], 2)
        self.assertEqual(disk[16896 + 64:16896 + 76], b'ILLSTRTN   \x10')
        self.assertEqual(unpack_from('<H', disk, 16896 + 64 + 26)[0], 3)
        directory = 16896 + 512
        self.assertEqual(unpack_from('<H', disk, directory + 32 + 26)[0], 2)
        self.assertEqual(disk[directory + 64:directory + 75], b'A-B     FIG')
        self.assertEqual(unpack_from('<HI', disk, directory + 64 + 26), (4, len(blob)))
        self.assertEqual(disk[directory + 512:directory + 512 + len(blob)], blob)

    def test_rejects_path_traversal_and_directory_collision(self):
        for names in (('../BAD.DOC',), ('FOLDER', 'FOLDER/CONTROL.DOC')):
            with self.subTest(names=names), self.assertRaises(ValueError):
                MEDIA.floppy([(ZipInfo(name), b'') for name in names], b'DESKMATE_1 ')
