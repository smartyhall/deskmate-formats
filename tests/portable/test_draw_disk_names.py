"""Portable checks for the FAT16 filename filter used by the stopped-disk reader."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('draw_disk', ROOT / 'tools/experimental/draw_disk.py')
draw_disk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(draw_disk)


class EntryNameTest(unittest.TestCase):
    def test_document_name_pads_base_and_extension(self):
        self.assertEqual(draw_disk.entry_name('Q1.FIG'), b'Q1      FIG')

    def test_extensionless_buffer_name(self):
        # The measured Corkboard file has no extension in the FAT directory.
        self.assertEqual(draw_disk.entry_name('DMCORKBD'), b'DMCORKBD   ')

    def test_full_eight_character_base_and_extension(self):
        self.assertEqual(draw_disk.entry_name('PERSONAL.CLN'), b'PERSONALCLN')

    def test_short_extension_is_padded(self):
        self.assertEqual(draw_disk.entry_name('A.D'), b'A       D  ')

    def test_lowercase_and_directory_paths_are_rejected(self):
        for name in ('dmcorkbd', 'DMCORKBD ', '../DMCORKBD',
                     'DESKMATE/DMCORKBD', 'DESKMATE\\DMCORKBD', ''):
            with self.assertRaises(ValueError):
                draw_disk.entry_name(name)

    def test_overlong_name_or_extension_is_rejected(self):
        for name in ('TOOLONGNAME.TXT', 'NOTE.LONG', 'NOTEFILE9'):
            with self.assertRaises(ValueError):
                draw_disk.entry_name(name)

    def test_non_string_is_rejected(self):
        with self.assertRaises(ValueError):
            draw_disk.entry_name(None)


if __name__ == '__main__':
    unittest.main()
