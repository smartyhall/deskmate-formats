import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "experimental"))
from typography_ibm_print import CARD_PROLOGUE, DRAW_PROLOGUE, decode


class IbmGraphicTests(unittest.TestCase):
    def test_binary_payload_and_dot_positions(self):
        job = CARD_PROLOGUE + b"\x1bJ\x18\r \x1bL\x02\x00\x81\x0c\x0c"
        self.assertEqual(decode(job), ({(12, 8), (12, 15), (13, 12), (13, 13)}, [(12, 8, 2)]))

    def test_retains_draw_profile_and_line_feed(self):
        job = DRAW_PROLOGUE + b"\n\x1bL\x01\x00\x80\x0c"
        self.assertEqual(decode(job), ({(0, 12)}, [(0, 12, 1)]))

    def test_rejects_unverified_jobs(self):
        block = b"\x1bL\x01\x00\x80"
        for data in (block + b"\x0c", CARD_PROLOGUE + block, CARD_PROLOGUE + block + b"\x0c\x00",
                     CARD_PROLOGUE + b"\x1bL\x03\x00\x80\x0c", CARD_PROLOGUE + b"\x1bZ\x0c",
                     CARD_PROLOGUE + b" " * 85 + block + b"\x0c"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode(data)

    def test_native_card(self):
        fixture = ROOT / "tests/fixtures/application-generated/print-companion/card-ibm-graphic.prn"
        if not fixture.exists() and not (ROOT / ".git").exists():
            self.skipTest("Binary research fixture is excluded from distributions")
        data = fixture.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "236df7b76d8ed4dcc0562b74959c4770eb97feff50fd3765fa907b38adad6b6c")
        pixels, bands = decode(data)
        self.assertEqual(bands, [(228, 368, 243), (228, 376, 241), (228, 384, 243),
                                 (480, 416, 202), (480, 424, 200)])
        self.assertEqual(len(pixels), 1090)
