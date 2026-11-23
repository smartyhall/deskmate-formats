from pathlib import Path
import unittest

from deskmate_formats import corkboard


FIXTURES = Path(__file__).parents[1] / 'fixtures/application-generated/corkboard'


class CorkboardTests(unittest.TestCase):
    def test_native_accessory_and_information_center_edit(self):
        before = corkboard.parse_file(FIXTURES / 'rsx-two-lines/DMCORKBD')
        edited = corkboard.parse_file(FIXTURES / 'rsx-information-center-edit/DMCORKBD')
        self.assertEqual(before.header_words, (41, 0))
        self.assertEqual(before.text, b'CORKBOARD ATLAS TEST 20261123\rSECOND LINE')
        self.assertEqual(edited.header_words, (20, 0))
        self.assertEqual(edited.text, before.text.replace(b'TEST', b'TESX'))
        self.assertEqual([i for i, pair in enumerate(zip(before.data, edited.data))
                          if pair[0] != pair[1]], [0, 0x17])

        cleared = corkboard.parse_file(FIXTURES / 'rsx-cleared/DMCORKBD')
        self.assertEqual(cleared.header_words, edited.header_words)
        self.assertEqual(cleared.text, b'')
        self.assertEqual(cleared.data, edited.data[:4] + b'\0' + edited.data[5:])

    def test_native_305_uses_two_bytes_in_first_header_word(self):
        note = corkboard.parse_file(FIXTURES / '305-alternate/DMCORKBD')
        expected = b'\r'.join(f'LAB {i:02d} ALPHA BRAVO CHARLIE'.encode() for i in range(1, 15))
        self.assertEqual(note.header_words, (377, 0))
        self.assertEqual(note.text, expected)

    def test_rejects_size_terminator_and_text_outside_measured_profile(self):
        for data, error in ((b'\0' * 2863, '2864-byte'), (b'\0' * 2865, '2864-byte'),
                            (b'A' * 2864, 'unterminated'),
                            (b'\0' * 4 + b'\x1b' + b'\0' * 2859, 'text byte')):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                corkboard.parse_bytes(data)
