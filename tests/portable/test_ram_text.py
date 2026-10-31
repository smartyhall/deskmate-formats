import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("ram_text", Path(__file__).resolve().parents[2] / "tools/read_ram_text.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RamTextTests(unittest.TestCase):
    def test_exact_spaces_and_no_inference(self):
        result = module.extract(b"\x00SAMPLE  ROW \x01", 1, 12)
        self.assertEqual(result["text"], "SAMPLE  ROW ")
        self.assertIsNone(result["focus"])
        self.assertIsNone(result["screen_coordinates"])
        self.assertFalse(result["live_screen_verified"])

    def test_bounds(self):
        for offset, length in [(-1, 1), (0, 0), (0, 257), (2, 2)]:
            with self.subTest(offset=offset, length=length), self.assertRaises(ValueError):
                module.extract(b"ABC", offset, length)

    def test_non_ascii(self):
        for raw in (b"\x00", b"\x01", b"\x80", b"\n"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                module.extract(raw, 0, 1)

    def test_changed_capture(self):
        self.assertNotEqual(module.extract(b"FIRST", 0, 5)["text"], module.extract(b"OTHER", 0, 5)["text"])
