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


class CrossEditionTests(unittest.TestCase):
    """Native files written by one edition over another edition's note."""

    def test_rsx_edited_a_305_note_and_appended_its_own_caret_position(self):
        note = corkboard.parse_file(FIXTURES / '305-edited-foreign-14line-20261128/DMCORKBD')
        lines = [f'LAB {i:02d} ALPHA BRAVO CHARLIE'.encode() for i in range(1, 15)]
        self.assertEqual(note.header_words, (379, 0))
        self.assertEqual(note.text, b'\r'.join(lines) + b'Z9')

    def test_305_edited_an_rsx_cp437_note_and_preserved_every_high_byte(self):
        note = corkboard.parse_file(FIXTURES / '305-edit-rsx-cp437-20261128/DMCORKBD')
        self.assertEqual(note.header_words, (19, 0))
        self.assertEqual(note.text, bytes.fromhex('829bb0b1b2c4c9cddbe1f10d454e4482e1') + b'Z9')
        self.assertEqual(note.decoded[-5:], '\u00e9\u00dfZ9')

    def test_305_turned_a_zero_filled_buffer_into_a_two_byte_note(self):
        note = corkboard.parse_file(FIXTURES / '305-create-from-blank-20261128/DMCORKBD')
        self.assertEqual(note.header_words, (2, 0))
        self.assertEqual(note.text, b'Z9')
        self.assertEqual(note.data[6:], bytes(2864 - 6))

    def test_a_wrapped_line_edit_left_bytes_after_the_terminator(self):
        # The visible text is unchanged; the mechanism behind the residual write
        # is not established, so only the observed bytes are asserted.
        note = corkboard.parse_file(FIXTURES / 'rsx-wrapped-line-residual-20261128/DMCORKBD')
        self.assertEqual(note.header_words, (42, 0))
        self.assertEqual(len(note.text), 2730)
        residual = note.data[4 + len(note.text) + 1:]
        self.assertEqual(sum(1 for byte in residual if byte), 63)
        self.assertIn(b'\n', residual)

    def test_a_control_range_save_dropped_only_the_line_feed(self):
        note = corkboard.parse_file(FIXTURES / 'rsx-control-range-save-20261128/DMCORKBD')
        self.assertEqual(note.header_words, (161, 0))
        self.assertEqual(len(note.text), 159)
        self.assertNotIn(b'\n', note.text)
        self.assertIn(b'\x01', note.text)
        self.assertIn(b'\x1f', note.text)
        self.assertIn(b'\x7f', note.text)
        self.assertTrue(note.text.startswith(b'<01>\x01<02>\x02'))


class CorkboardWriterTests(unittest.TestCase):
    """The writer is checked against native files it did not produce."""

    def fixture(self, name):
        return (FIXTURES / name / 'DMCORKBD').read_bytes()

    def test_create_reproduces_every_published_native_file(self):
        cases = [('rsx-two-lines', 41), ('305-alternate', 377),
                 ('rsx-cp437-20261128', 17), ('rsx-maximum-2794-20261128', 42),
                 ('rsx-caret-selection-20261128', 57)]
        for name, caret in cases:
            with self.subTest(name=name):
                native = self.fixture(name)
                text = native[4:].split(b'\0', 1)[0]
                built = corkboard.create_note(text, caret=caret)
                self.assertEqual(built, native)

    def test_clear_reproduces_the_published_cleared_file(self):
        edited = self.fixture('rsx-information-center-edit')
        self.assertEqual(corkboard.clear_note(edited), self.fixture('rsx-cleared'))

    def test_caret_defaults_to_the_end_and_can_be_set_inside(self):
        text = b'ABCDE\rFGH'
        self.assertEqual(corkboard.create_note(text)[0:2], b'\x09\x00')
        self.assertEqual(corkboard.create_note(text, caret=3)[0:2], b'\x03\x00')
        for bad in (-1, len(text) + 1, 1.0, '3', True):
            with self.subTest(bad=bad), self.assertRaises(corkboard.PolicyError):
                corkboard.create_note(text, caret=bad)

    def test_create_is_str_or_cp437_bytes_and_zero_fills_the_tail(self):
        built = corkboard.create_note('CAF\u00c9')
        # CP437 0x90 is uppercase E-acute; the measured native byte 0x82 is the
        # lowercase form, which the fixture test above covers.
        self.assertEqual(built[4:8], bytes.fromhex('43414690'))
        self.assertEqual(built[8:], bytes(2864 - 8))
        self.assertEqual(corkboard.parse_bytes(built).decoded, 'CAF\u00c9')

    def test_refuses_text_the_native_editor_was_never_observed_to_accept(self):
        for text, error in ((b'A\0B', 'NUL'), (b'A\x1bB', 'outside the measured'),
                            (b'A\x7fB', 'outside the measured'), ('\u4e2d', 'CP437')):
            with self.subTest(text=text), self.assertRaisesRegex(corkboard.PolicyError, error):
                corkboard.create_note(text)

    def test_capacity_policy_is_a_demonstrated_boundary_with_an_override(self):
        with self.assertRaisesRegex(corkboard.PolicyError, '2794'):
            corkboard.create_note(b'A' * 2795)
        self.assertEqual(len(corkboard.create_note(b'A' * 2795,
                                                   allow_above_demonstrated=True)), 2864)
        with self.assertRaisesRegex(corkboard.PolicyError, 'terminator'):
            corkboard.create_note(b'A' * 2860, allow_above_demonstrated=True)

    def test_update_preserves_residual_bytes_and_the_unknown_second_word(self):
        original = bytearray(self.fixture('rsx-cleared'))
        original[2:4] = b'\x34\x12'
        updated = corkboard.update_note(bytes(original), b'REPLACED')
        self.assertEqual(updated[0:2], b'\x08\x00')
        self.assertEqual(updated[2:4], b'\x34\x12')
        self.assertEqual(updated[4:12], b'REPLACED')
        self.assertEqual(updated[12], 0)
        # The prior content after the first NUL is untouched by default.
        self.assertEqual(updated[13:], bytes(original)[13:])
        self.assertEqual(corkboard.parse_bytes(updated).decoded, 'REPLACED')

    def test_update_can_zero_the_residual_and_override_the_second_word(self):
        original = self.fixture('rsx-cleared')
        updated = corkboard.update_note(original, b'NEW', preserve_residual=False,
                                        second_word=7)
        self.assertEqual(updated[2:4], b'\x07\x00')
        self.assertEqual(updated[7:], bytes(2864 - 7))

    def test_update_keeps_the_previous_second_word_when_only_the_text_changes(self):
        original = bytearray(self.fixture('rsx-two-lines'))
        original[2:4] = b'\x01\x02'
        updated = corkboard.update_note(bytes(original), b'SHORT')
        self.assertEqual(updated[2:4], b'\x01\x02')
        self.assertEqual(len(updated), 2864)

    def test_write_helpers_refuse_a_buffer_that_is_not_a_note(self):
        for bad in (b'', b'\0' * 2863, b'\0' * 2865, 'text', None):
            with self.subTest(bad=bad):
                with self.assertRaises(corkboard.PolicyError):
                    corkboard.update_note(bad, b'X')
                with self.assertRaises(corkboard.PolicyError):
                    corkboard.clear_note(bad)

    def test_clear_is_not_a_secure_erase_unless_sanitize_is_asked_for(self):
        native = self.fixture('rsx-information-center-edit')
        cleared = corkboard.clear_note(native)
        self.assertEqual(cleared[5:], native[5:])
        self.assertIn(b'TESX', cleared)
        sanitized = corkboard.clear_note(native, sanitize=True)
        self.assertEqual(sanitized[4:], bytes(2860))
        self.assertEqual(sanitized[0:4], native[0:4])
