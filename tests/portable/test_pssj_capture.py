from importlib.util import module_from_spec, spec_from_file_location
import math
from pathlib import Path
import struct
import unittest


SPEC = spec_from_file_location(
    "pssj_capture", Path(__file__).resolve().parents[2] / "tools/experimental/pssj_capture.py"
)
capture = module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


class CaptureTests(unittest.TestCase):
    def test_timed_tones_and_silence(self):
        silence = bytes(capture.RATE // 10 * 2)

        def tone(frequency):
            return b"".join(struct.pack("<h", round(800 * math.sin(2 * math.pi * frequency * i / capture.RATE)))
                            for i in range(capture.RATE // 5))

        samples = capture.decode(silence + tone(448) + silence + tone(896))
        first, second = capture.measure(samples, 0, len(samples) / capture.RATE)
        self.assertEqual((first["start"], first["duration"]), (0.1, 0.2))
        self.assertEqual((second["start"], second["duration"]), (0.4, 0.2))
        self.assertTrue(first["frequencies"])
        self.assertTrue(second["frequencies"])
        self.assertTrue(all(abs(value - 448) < 1 for _, value in first["frequencies"]))
        self.assertTrue(all(abs(value - 896) < 1 for _, value in second["frequencies"]))
        self.assertEqual(capture.measure(samples, 0, 0.1), [])

    def test_invalid_frame_and_selector(self):
        with self.assertRaises(ValueError):
            capture.decode(b"\0")
        with self.assertRaises(ValueError):
            capture.measure(capture.decode(b"\0\0"), -1, 0)
