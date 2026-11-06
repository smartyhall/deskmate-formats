"""Synthetic checks for the offline DMCSR comparison helper."""

import importlib.util
from pathlib import Path
from struct import pack
import sys
import unittest


_TOOL = Path(__file__).resolve().parents[2] / 'tools' / 'experimental' / 'calendar_window_context.py'
_SPEC = importlib.util.spec_from_file_location('calendar_window_context', _TOOL)
context = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = context
_SPEC.loader.exec_module(context)


class WindowContextTests(unittest.TestCase):
    def test_window_growth_and_restoration(self):
        day = pack('<3H', 0x07D8, 0x0F9C, 1)
        editor = pack('<3H', 0x088C, 0x0F7C, 7)
        result = context.compare_triplet(day, editor, day)
        self.assertEqual(result['a_to_b_window_records'], 3)
        self.assertEqual(result['a_to_b_small_records'], 2)
        self.assertTrue(result['a_to_b_selected_id_changed'])
        self.assertTrue(result['a_equals_c'])

    def test_handle_only_change_and_missing_restoration(self):
        day = pack('<3H', 0x079C, 0x0F9C, 0xFFFF)
        transient = pack('<3H', 0x079C, 0x0F9C, 2)
        result = context.compare_triplet(day, transient, transient)
        self.assertEqual(result['a_to_b_window_records'], 0)
        self.assertEqual(result['a_to_b_small_records'], 0)
        self.assertTrue(result['a_to_b_selected_id_changed'])
        self.assertFalse(result['a_equals_c'])

    def test_rejects_bad_bounds_alignment_and_size(self):
        valid = pack('<3H', 0x079C, 0x0F9C, 1)
        for sample in (valid[:5], valid+b'\0', pack('<3H', 0x07D9, 0x0F9C, 1),
                       pack('<3H', 0x079C, 0x0F9B, 1), pack('<3H', 0x088C, 0x079C, 1),
                       pack('<3H', 0x079C, 0x0F9C, 0x0800)):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                context.decode_sample(sample)


if __name__ == '__main__':
    unittest.main()
