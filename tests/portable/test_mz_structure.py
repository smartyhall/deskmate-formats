"""Synthetic MZ relocation checks independent of proprietary modules."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location(
    'inspect_structure', Path(__file__).resolve().parents[2] / 'tools/inspect_structure.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def synthetic():
    b = bytearray(160)
    struct.pack_into('<13H', b, 0, 0x5a4d, 160, 1, 1, 4, 0, 0, 0, 0, 0, 3, 1, 28)
    struct.pack_into('<HH', b, 28, 6, 0)
    struct.pack_into('<HH', b, 68, 7, 2)
    return bytes(b)


class MZStructureTests(unittest.TestCase):
    def test_file_entry_and_relocation_arithmetic(self):
        d = probe.inspect_mz(synthetic())
        self.assertEqual(d['header_bytes'], 64)
        self.assertEqual(d['entry_file_offset_candidate'], 83)
        self.assertEqual(d['relocations'][0]['file_offset'], 70)
        self.assertEqual(d['relocations'][0]['original_word'], 2)
        self.assertNotIn('data_segment', d)

    def test_relocated_far_pointer_and_unknown_segment(self):
        b = synthetic()
        r = probe.resolve_mz_far(b, 68)
        self.assertTrue(r['segment_has_mz_relocation'])
        self.assertEqual(r['target_file_offset_candidate'], 103)
        self.assertTrue(r['target_in_stored_image'])
        unknown = probe.resolve_mz_far(b, 74)
        self.assertIsNone(unknown['target_file_offset_candidate'])
        with self.assertRaises(ValueError):
            probe.resolve_mz_far(b, len(b) - 3)

    def test_bad_header_image_and_relocation_bounds(self):
        for where, value in [(0, 0), (2, 512), (4, 0), (8, 1), (6, 100), (28, 159)]:
            b = bytearray(synthetic())
            struct.pack_into('<H', b, where, value)
            with self.subTest(where=where), self.assertRaises(ValueError):
                probe.inspect_mz(b)

    def test_full_final_sector_and_overlay_are_distinct(self):
        b = bytearray(synthetic())
        b.extend(bytes(512 - len(b)))
        struct.pack_into('<H', b, 2, 0)
        r = probe.inspect_mz(bytes(b) + b'overlay')
        self.assertEqual(r['declared_file_bytes'], 512)
        self.assertEqual(r['trailing_bytes'], 7)

    def test_out_of_file_pointer_is_reported_without_dereference(self):
        b = bytearray(synthetic())
        struct.pack_into('<HH', b, 68, 0xffff, 0xffff)
        r = probe.resolve_mz_far(bytes(b), 68)
        self.assertFalse(r['target_in_stored_image'])
