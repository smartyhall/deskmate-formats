"""Extract the actual native Text corpus and reject unmeasured controls."""
from pathlib import Path
import unittest

from deskmate_formats import text

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/text'


class TextNativeTest(unittest.TestCase):
    def test_plain_and_formatted_corpus(self):
        expected = {
            '300-native-atlas.doc': 'ALPHA\nBETA',
            't00.doc': '',
            't01.doc': 'A',
            't02.doc': 'AB',
            't03.doc': 'ABC',
            't04.doc': 'ABC\nQ7',
            't05.doc': 'ABC\nQ7\n\nR9',
            't06.doc': 'ABC\nQ7\n\nR8',
            't07.doc': 'ABC\nQ7\n\nR8',
            't08.doc': 'ABC\nQ7\n\nR8 \n',
            't10.txt': 'ABC\nQ7\n\nR8 \n',
            't11.doc': 'ABC',
            't12.doc': 'KéZ W',
            't13.doc': ' '.join(c * 2 + '01234567' for c in 'abcdefghij'),
            't14.doc': 'X ',
            't15.doc': 'X  ',
            't16.doc': 'X',
        }
        for name, content in expected.items():
            with self.subTest(name=name):
                self.assertEqual(text.extract_file(FIXTURES / name), content)

    def test_large_file_matches_every_line(self):
        path = FIXTURES / 't09.doc'
        self.assertEqual(path.stat().st_size, 2527)
        expected = 'ABC \n' + ''.join(
            f'l{n:02}-0123456789abcdefghijklmnopqrstuvwxyz0123456789\n' for n in range(1, 49)
        )
        self.assertEqual(text.extract_file(path), expected)

    def test_personal_deskmate_2_native_save_envelope(self):
        early = (FIXTURES / 'pdm2-native-hist.doc').read_bytes()
        self.assertEqual(len(early), 35)
        self.assertEqual(early[:5], b'\x01DOC\x00')
        self.assertEqual(early[22:], (FIXTURES / '300-native-atlas.doc').read_bytes())

    def test_alternate_305_thesaurus_substitution(self):
        doc = text.parse_file(FIXTURES / '305-alternate-thesaurus.doc', include_controls=True)
        self.assertEqual(doc.text, 'center ')
        self.assertEqual(doc.pictures, ())
        self.assertEqual(doc.controls, (
            text.TextControl(22, 0, b'\x13'),
            text.TextControl(30, 7, b'\x12'),
        ))

    def test_margin_records_preserve_opaque_payload_and_offsets(self):
        first = bytes.fromhex('03 09 00 00 04')
        second = bytes.fromhex('03 04 1A 03 04')
        raw = text.FORMATTED_HEADER + first + b'Atlas\r\n' + second + b'Index\x1a'
        doc = text.parse_bytes(raw, include_controls=True)
        self.assertEqual(doc.text, 'Atlas\nIndex')
        self.assertEqual(doc.controls, (
            text.TextControl(22, 0, first),
            text.TextControl(34, 6, second),
        ))
        self.assertEqual(doc.control_count, 2)
        for malformed in (first[:-1], first[:-1] + b'\x06'):
            with self.subTest(malformed=malformed), self.assertRaises(text.TextFormatError):
                text.extract_bytes(text.FORMATTED_HEADER + malformed + b'\x1a')

    def test_rejects_truncation_and_unsupported_structure(self):
        raw = (FIXTURES / 't11.doc').read_bytes()
        for data in (
            raw[:-1], raw[:5] + b'\x90' + raw[6:],
            raw[:0x1A] + b'\x03\x1A', raw[:0x1A] + b'\x1A',
            b'A\x1aB\x1a', b'A\nB\x1a', b'A\x13B\x1a',
        ):
            with self.subTest(data=data), self.assertRaises(text.TextFormatError):
                text.extract_bytes(data)
