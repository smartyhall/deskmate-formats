"""External-fixture assertions for the single observed E19 transition."""
import hashlib
import os
from pathlib import Path
import struct
import unittest

from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes
from deskmate_formats.calendar.writer import append_appointment


class E19PressureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get("DOSLAB_ROOT")
        if not root:
            raise unittest.SkipTest("Set DOSLAB_ROOT for private E19 evidence")
        directory = Path(root) / "EXPERIMENTS/PHASE2/E19_space_pressure"
        cls.base = (directory / "segment01/before/files/DESKMATE/PERSONAL.CLN").read_bytes()
        cls.pre = (directory / "segment12/after/files/DESKMATE/PERSONAL.CLN").read_bytes()
        cls.final = (directory / "segment13/after/files/DESKMATE/PERSONAL.CLN").read_bytes()

    def test_complete_crossing_delta(self):
        for data, size, digest in (
            (self.base, 7168, "818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea"),
            (self.pre, 7168, "f70406212f170065a5dec83f11d8a55e1ec05f58dda1d57b6c9973d5d6b9d0ed"),
            (self.final, 8192, "ad6683ae34d3367026e47aeddd91ca93502551c557f02f7762039ff2d82011a1"),
        ):
            self.assertEqual(len(data), size)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
        expected = {
            0x29: (255, 0), 0x2A: (143, 127), 0x2B: (255, 248),
            0x2C: (0, 255), 0x2D: (0, 240), 0x438: (50, 51),
            0x439: (57, 48), 0x443: (54, 55), 0x14CA: (4, 7),
            0x14CC: (39, 0), 0x14CE: (17, 46), 0x14D2: (63, 39),
            0x14D4: (18, 17), 0x14D6: (0, 4), 0x14D8: (0, 63),
            0x14DA: (0, 18),
        }
        self.assertEqual({i: (a, b) for i, (a, b) in enumerate(zip(self.pre, self.final))
                          if a != b}, expected)
        suffix = "A0123456789B0123456789C0123456789D0123456789E0123456789"
        row = bytes.fromhex("802e8f6c6f01680101ac01b0013101") + ("P1913" + suffix).encode() + b"\x01\x02"
        self.assertEqual(len(row), 77)
        self.assertEqual(self.final[0x1C00:], row + b"\x03" + bytes(946))

    def test_retained_rows_index_and_counters(self):
        self.assertEqual(self.base[0x1000:0x1400], self.final[0x1000:0x1400])
        self.assertEqual(self.pre[0x1800:0x1C00], self.final[0x1800:0x1C00])
        self.assertEqual(self.base[0x1800:0x1818], self.final[0x1800:0x1818])
        self.assertEqual(self.pre[0x1BB4:], b"\x03" + bytes(75))
        before = [struct.unpack_from("<HHH", self.pre, 0x1428 + 6*i) for i in range(29)]
        after = [struct.unpack_from("<HHH", self.final, 0x1428 + 6*i) for i in range(30)]
        self.assertEqual(after, before[:27] + [(7, 0, 0x2E)] + before[27:])
        self.assertNotIn(0x21, [entry[2] for entry in after])
        self.assertEqual(self.final[0x14DC:0x1800], bytes(804))
        for page, offset, ident in before:
            start = page*1024 + offset
            end = self.pre.index(b"\x01\x02", start) + 2
            self.assertEqual(self.pre[start:end], self.final[start:end], hex(ident))
        self.assertEqual(self.final[0x435:0x43A], b"00030")
        self.assertEqual(self.final[0x43B:0x43E], b"001")
        self.assertEqual(self.final[0x43F:0x444], b"00047")

    def test_production_tools_still_reject_unsupported_layouts(self):
        for data in (self.pre, self.final):
            for operation in (parse_bytes, append_appointment):
                with self.subTest(size=len(data), operation=operation.__name__):
                    with self.assertRaises(CalendarParseError) as error:
                        operation(data)
                    self.assertEqual(error.exception.code, "unsupported_layout")
