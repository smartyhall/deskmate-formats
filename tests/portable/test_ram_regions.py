import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[2] / "tools/read_ram_text.py"
spec = importlib.util.spec_from_file_location("ram_regions", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RamRegionTests(unittest.TestCase):
    def test_physical_and_relative_are_equivalent(self):
        raw = b"\x01ABCDEF\x00"
        a = module.extract(raw, 1, 6, base_address=0x200)
        b = module.extract(raw, 0x201, 6, base_address=0x200, physical=True)
        self.assertEqual(a, b)
        self.assertEqual(a["capture_offset"], 1)
        self.assertEqual(a["physical_address"], 0x201)
        self.assertEqual(a["capture"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(bytes.fromhex(a["raw_hex"]), raw[1:7])

    def test_different_capture_origins(self):
        a = b"\x00" * 16 + b"OLD TEXT\x01"
        b = b"NEW TEXT\x01"
        result = module.compare_regions(a, b, 0x210, 9, before_base=0x200, after_base=0x210)
        self.assertEqual(result["before_capture_offset"], 16)
        self.assertEqual(result["after_capture_offset"], 0)
        self.assertEqual(bytes.fromhex(result["before_hex"]), a[16:])
        self.assertEqual(bytes.fromhex(result["after_hex"]), b)
        self.assertEqual([d["physical_address"] for d in result["differences"]], [0x210, 0x211, 0x212])
        self.assertEqual(result["candidate_ascii"]["after"][0]["text"], "NEW TEXT")
        self.assertFalse(result["live_screen_verified"])
        self.assertIsNone(result["focus"])

    def test_raw_context_preserves_non_text(self):
        a = bytearray(b"\xffSAME\x00OLD!\x01")
        b = bytearray(b"\xfeSAME\x00NEW!\x02")
        original_a, original_b = a[:], b[:]
        result = module.compare_regions(a, b, 0, len(a))
        self.assertEqual(bytes.fromhex(result["before_hex"]), original_a)
        self.assertEqual(bytes.fromhex(result["after_hex"]), original_b)
        self.assertEqual((a, b), (original_a, original_b))
        self.assertEqual(result["differences"][0]["before"], 255)
        self.assertEqual(result["differences"][-1]["after"], 2)
        self.assertEqual(result["candidate_ascii"]["before"][0]["text"], "SAME")

    def test_identical_bytes_do_not_prove_visibility(self):
        result = module.compare_regions(b"CACHED", b"CACHED", 0, 6)
        self.assertEqual(result["differences"], [])
        self.assertFalse(result["live_screen_verified"])
        self.assertIsNone(result["screen_coordinates"])

    def test_capture_and_conventional_bounds(self):
        for data, base in [(b"", 0), (b"A", -1), (b"AB", 0x9FFFF), (b"A", True), ("A", 0), (b"A" * 655361, 0)]:
            with self.subTest(base=base), self.assertRaises(ValueError):
                module.extract(data, 0, 1, base_address=base)
        self.assertEqual(module.extract(b"A", 0x9FFFF, 1, base_address=0x9FFFF, physical=True)["text"], "A")

    def test_bad_physical_spans_and_window_limit(self):
        for address, size in [(0x1FF, 1), (0x204, 1), (0x200, 0), (0x200, 257), (True, 1)]:
            with self.subTest(address=address, size=size), self.assertRaises(ValueError):
                module.compare_regions(b"ABCD", b"ABCD", address, size, before_base=0x200, after_base=0x200)

    def test_comparison_requires_both_captures_cover_region(self):
        with self.assertRaises(ValueError):
            module.compare_regions(b"ABCD", b"AB", 0, 4)
        with self.assertRaises(ValueError):
            module.extract(b"\xff", 0, 1, base_address=0x200)

    def test_cli_physical_json(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "capture.bin"
            p.write_bytes(b"\x00TEXT\x01")
            result = subprocess.run([sys.executable, str(TOOL), str(p), "0x201", "4", "--physical", "--base-address", "0x200"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual((value["text"], value["capture_offset"], value["physical_address"]), ("TEXT", 1, 0x201))

    def test_cli_errors_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "capture.bin"
            p.write_bytes(b"\xff")
            result = subprocess.run([sys.executable, str(TOOL), str(p), "0", "1"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("printable ASCII", result.stderr)
            result = subprocess.run([sys.executable, str(TOOL), str(p), "0", "1", "--compare-base-address", "5"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires --compare", result.stderr)

    def test_cli_compare_with_shifted_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a.bin", Path(directory) / "b.bin"
            a.write_bytes(b"\x00ABCD")
            b.write_bytes(b"ABXD")
            result = subprocess.run([sys.executable, str(TOOL), str(a), "0x201", "4", "--physical", "--base-address", "0x200", "--compare", str(b), "--compare-base-address", "0x201"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(value["differences"], [{"physical_address": 0x203, "before_capture_offset": 3, "after_capture_offset": 2, "before": 67, "after": 88}])
