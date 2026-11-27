"""Portable checks for the segment-register instruction specimen.

The specimen is self-authored, so these tests are a statement about the
encodings we claim to use, not about any commercial binary. When Capstone is
installed the same bytes are decoded with an independent decoder, which is what
makes a later Ghidra listing comparable.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'segment_forms', ROOT / 'tests/fixtures/synthetic/segment_forms.py')
forms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forms)

try:
    import capstone
except ImportError:  # pragma: no cover - decoder is optional
    capstone = None


def decode(payload, mode, offset):
    md = capstone.Cs(capstone.CS_ARCH_X86, mode)
    return next(md.disasm(payload[offset:offset + 8], offset), None)


class SpecimenStructureTests(unittest.TestCase):
    def test_payload_holds_every_form_at_its_stated_offset(self):
        payload = forms.build_payload()
        self.assertEqual(len(payload), 64)
        for row in forms.truth_table():
            start = row['offset']
            self.assertEqual(payload[start:start + len(row['bytes']) // 2].hex(),
                             row['bytes'], row['name'])

    def test_forms_do_not_overlap(self):
        spans = sorted(
            (row['offset'], row['offset'] + len(row['bytes']) // 2)
            for row in forms.truth_table()
        )
        for (_start, end), (next_start, _next_end) in zip(spans, spans[1:]):
            self.assertLessEqual(end, next_start)

    def test_direction_names_the_written_register(self):
        prefixes = {0x66, 0x67, 0xF2, 0xF3}
        for row in forms.truth_table():
            encoded = bytes.fromhex(row['bytes'])
            opcode = next(b for b in encoded if b not in prefixes)
            if opcode == 0x8E:
                self.assertEqual(row['writes'], row['segment_register'], row['name'])
                self.assertEqual(row['reads'], row['general_register'], row['name'])
            else:
                self.assertEqual(opcode, 0x8C, row['name'])
                self.assertEqual(row['writes'], row['general_register'], row['name'])
                self.assertEqual(row['reads'], row['segment_register'], row['name'])

    def test_the_two_encodings_share_operands_in_opposite_roles(self):
        # 8E D8 and 8C D8 name the same pair with opposite meanings. Any
        # listing that prints the same text for both is ambiguous, which is
        # what makes the byte-level check necessary.
        to_segment = next(r for r in forms.truth_table() if r['bytes'] == '8ed8')
        from_segment = next(r for r in forms.truth_table() if r['bytes'] == '8cd8')
        self.assertEqual(
            {to_segment['general_register'], to_segment['segment_register']},
            {from_segment['general_register'], from_segment['segment_register']},
        )
        self.assertNotEqual(to_segment['writes'], from_segment['writes'])

    def test_long_mode_specimen(self):
        payload = forms.build_long_mode_payload()
        for row in forms.long_truth_table():
            start = row['offset']
            self.assertEqual(payload[start:start + len(row['bytes']) // 2].hex(),
                             row['bytes'], row['name'])


def operands_of(instruction) -> list[str]:
    return [part.strip().upper() for part in instruction.op_str.split(',')]


def register_operands(instruction, row) -> list[str]:
    """Register operands in printed order, ignoring a memory operand."""
    known = {row['general_register'], row['segment_register']} - {None}
    return [part for part in operands_of(instruction) if part in known]


@unittest.skipIf(capstone is None, 'capstone is not installed')
class IndependentDecodeTests(unittest.TestCase):
    """Capstone is the reference reading: destination first, per the manual."""

    def test_sixteen_bit_forms_decode_in_intel_order(self):
        payload = forms.build_payload()
        for row in forms.truth_table():
            with self.subTest(name=row['name']):
                instruction = decode(payload, capstone.CS_MODE_16, row['offset'])
                self.assertIsNotNone(instruction)
                self.assertEqual(instruction.mnemonic, 'mov')
                expected = [name for name in (row['writes'], row['reads']) if name]
                self.assertEqual(
                    register_operands(instruction, row),
                    expected,
                    f"{row['bytes']} decoded as {instruction.op_str}",
                )

    def test_long_mode_forms_decode_in_intel_order(self):
        payload = forms.build_long_mode_payload()
        for row in forms.long_truth_table():
            with self.subTest(name=row['name']):
                instruction = decode(payload, capstone.CS_MODE_64, row['offset'])
                self.assertIsNotNone(instruction)
                self.assertEqual(instruction.mnemonic, 'mov')
                expected = [name for name in (row['writes'], row['reads']) if name]
                self.assertEqual(
                    register_operands(instruction, row),
                    expected,
                    f"{row['bytes']} decoded as {instruction.op_str}",
                )


if __name__ == '__main__':
    unittest.main()
