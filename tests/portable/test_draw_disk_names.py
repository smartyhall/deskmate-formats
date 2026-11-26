"""Directory-name handling for the independent RSX document reader.

These are pure-name tests: no disk image, no emulator. They exist because the
reader previously accepted only a fixed list of extensions, which excluded
ordinary extensionless 8.3 files such as the Corkboard document.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('draw_disk', ROOT / 'tools/experimental/draw_disk.py')
draw_disk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(draw_disk)


class EntryNameTests(unittest.TestCase):
    def test_extensionless_eight_character_name(self):
        self.assertEqual(draw_disk.entry_name('DMCORKBD'), b'DMCORKBD   ')

    def test_short_stem_and_extension_are_space_padded(self):
        self.assertEqual(draw_disk.entry_name('A.B'), b'A       B  ')
        self.assertEqual(draw_disk.entry_name('DRAW.FIG'), b'DRAW    FIG')

    def test_lowercase_and_path_characters_are_refused(self):
        for name in ('dmcorkbd', 'DMCORKBRD.DOC', 'DESKMATE/DMCORKBD', 'A B.TXT',
                     'TOOLONGNM.DOC', 'A.TOOLONG', ''):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    draw_disk.entry_name(name)


if __name__ == '__main__':
    unittest.main()
