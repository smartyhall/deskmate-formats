"""Independent byte-exact regression for a native SECOND first-event append.

Uses immutable committed fixtures only, no production parser or emulator.
The separate multicalendar tests cover successful production parsing; this
regression deliberately remains an independent original-byte comparison.
"""
import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1] / "fixtures/application-generated/calendar"
SOURCE = ROOT / "native-second-empty-calendar-operator.cln"
TARGET = ROOT / "native-second-first-event-operator.cln"


class NativeSecondFirstEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        cls.target = TARGET.read_bytes()

    def test_exact_native_identity(self):
        self.assertEqual(len(self.source), 10240)
        self.assertEqual(len(self.target), 10240)
        self.assertEqual(
            hashlib.sha256(self.source).hexdigest(),
            "338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5",
        )
        self.assertEqual(
            hashlib.sha256(self.target).hexdigest(),
            "b9c9a4cae3cffac1bc337f7b378ea25df74efd3b6771e117c6e0fc3f81b77084",
        )

    def test_only_expected_byte_positions_change(self):
        changed = {
            offset for offset, (before, after) in
            enumerate(zip(self.source, self.target)) if before != after
        }
        expected = {
            0x0464, 0x046E, *range(0x2027, 0x2048),
            0x242E, 0x2430, 0x2432,
        }
        self.assertEqual(changed, expected)
        self.assertEqual(len(changed), 38)
        for page in (0, 2, 3, 4, 5, 6, 7):
            self.assertEqual(
                self.source[1024 * page:1024 * (page + 1)],
                self.target[1024 * page:1024 * (page + 1)],
            )

    def test_new_record_and_index_are_table_local(self):
        self.assertEqual(self.source[0x0464], ord("1"))
        self.assertEqual(self.target[0x0464], ord("2"))
        self.assertEqual(self.source[0x046E], ord("7"))
        self.assertEqual(self.target[0x046E], ord("8"))
        self.assertEqual(
            self.target[0x2027:0x2048],
            bytes.fromhex(
                "80118f6b7901680101ac01b00131015345434f4e44204f4e4c5920303031010203"
            ),
        )
        self.assertEqual(
            self.target[0x242E:0x2434], bytes.fromhex("080027001100")
        )
        self.assertEqual(
            self.source[0x242E:0x2434], bytes(6)
        )


if __name__ == "__main__":
    unittest.main()
