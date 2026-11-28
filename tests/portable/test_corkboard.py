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

    def test_first_word_is_an_insertion_offset_not_a_length(self):
        # Saved with the caret inside the note: word 57, text 64 bytes.
        note = corkboard.parse_file(FIXTURES / 'rsx-caret-selection-20261128/DMCORKBD')
        self.assertEqual(len(note.text), 64)
        self.assertEqual(note.header_words, (57, 0))
        self.assertEqual(note.text[:27], b'CURSOR PROBE 20261128 ALPHA')
        self.assertEqual(note.rows[-1], 'XABDELTA LAST')

    def test_cp437_high_bytes_are_text_not_rejected(self):
        note = corkboard.parse_file(FIXTURES / 'rsx-cp437-20261128/DMCORKBD')
        self.assertEqual(note.header_words, (17, 0))
        self.assertEqual(note.text, bytes.fromhex('829bb0b1b2c4c9cddbe1f10d454e4482e1'))
        self.assertEqual(note.decoded, '\u00e9\u00a2\u2591\u2592\u2593\u2500\u2554\u2550'
                                       '\u2588\u00df\u00b1\rEND\u00e9\u00df')
        self.assertEqual(note.rows, ['\u00e9\u00a2\u2591\u2592\u2593\u2500\u2554\u2550'
                                     '\u2588\u00df\u00b1', 'END\u00e9\u00df'])

    def test_measured_maximum_note_is_65_rows_of_42_characters(self):
        note = corkboard.parse_file(FIXTURES / 'rsx-maximum-2794-20261128/DMCORKBD')
        self.assertEqual(len(note.text), 2794)
        self.assertEqual(note.header_words, (42, 0))
        self.assertEqual(len(note.rows), 65)
        self.assertEqual({len(row) for row in note.rows}, {42})
        self.assertFalse(any(note.data[4 + len(note.text):]))
        self.assertTrue(note.text.startswith(b'000 ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'))

    def test_rejects_size_terminator_and_text_outside_measured_profile(self):
        for data, error in ((b'\0' * 2863, '2864-byte'), (b'\0' * 2865, '2864-byte'),
                            (b'A' * 2864, 'unterminated'),
                            (b'\0' * 4 + b'\x1b' + b'\0' * 2859, 'text byte'),
                            (b'\0' * 4 + b'\x7f' + b'\0' * 2859, 'text byte'),
                            (b'\0' * 4 + b'\x1f' + b'\0' * 2859, 'text byte')):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                corkboard.parse_bytes(data)
