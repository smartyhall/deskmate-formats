"""Exercise native Worksheet files and malformed variants of measured structures."""
from pathlib import Path
from struct import pack_into
import unittest

from deskmate_formats import worksheet


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/worksheet'


def read(name):
    return worksheet.parse_file(FIXTURES / (name + '.wks'))


def raw(name):
    return (FIXTURES / (name + '.wks')).read_bytes()


def populated(name):
    return {(c.row, c.column): c for c in read(name).cells if not c.dummy}


class NativeWorksheetTest(unittest.TestCase):
    def test_empty_file_and_counted_dummies(self):
        pad = read('w00')
        self.assertEqual((pad.size, pad.pad_size, pad.string_pool_offset), (232, 210, 232))
        self.assertEqual(pad.page_setup[:4], b'\x0eWKS')
        self.assertEqual(pad.column_widths, (10,) * 100)
        self.assertEqual((pad.extreme_row, pad.extreme_column), (0, 0))
        self.assertEqual([t.count for t in pad.toplists], [1] * 5)
        self.assertEqual([t.cell_size for t in pad.toplists], [6, 14, 14, 14, 8])
        self.assertEqual([t.cells_start for t in pad.toplists], [176, 182, 196, 210, 224])
        self.assertTrue(all(c.dummy and c.row == c.column == 100 for c in pad.cells))
        self.assertEqual(raw('wempty'), raw('w00'))

    def test_label_pool_order_compaction_and_width(self):
        base = read('w01')
        cell = populated('w01')[1, 1]
        self.assertEqual((cell.text, cell.offset, cell.string_offset), ('ALPHA7', 176, 112))
        self.assertEqual(126 + cell.string_offset, base.string_pool_offset)
        copies = populated('w10')
        self.assertEqual(set(copies), {(1, 1), (5, 2), (3, 4)})
        self.assertEqual(len({c.string_offset for c in copies.values()}), 3)
        self.assertEqual(raw('w14'), raw('w01'))
        self.assertEqual(populated('w12')[1, 1].text, 'BETA77')
        self.assertEqual(populated('w13')[1, 1].text, 'ALPHA7LONG')
        self.assertEqual(read('w11').column_widths[:3], (10, 16, 10))

    def test_pointer_words_are_opaque_and_native_resave_rebases(self):
        base = read('w01')
        data = bytearray(raw('w01'))
        for entry in base.toplists:
            pack_into('<2H', data, entry.offset, 0x80, 0x90)
        variant = worksheet.parse_bytes(data)
        self.assertEqual(variant.toplists[0].start_pointer, 0x80)
        self.assertEqual(variant.cells, base.cells)
        for name in ('w15', 'wctx', 'wfix'):
            self.assertEqual(raw(name), raw('w01'))

    def test_binary64_and_nonsemantic_dummy_contents(self):
        for name, stored, display in (('w02', 123.0, '123.00'), ('w03', 12.5, '12.50'), ('w04', -7.0, '-7.00')):
            cell = populated(name)[1, 1]
            self.assertEqual((cell.numeric_value, cell.text), (stored, display))
        self.assertEqual([c.numeric_value for c in populated('wnum').values()], [0.0, 1.0, 123456789.0])
        dummy = next(c for c in read('w07').cells if c.dummy and c.category == 'number')
        self.assertEqual(dummy.status, 0x4022)
        self.assertIsNone(dummy.numeric_value)
        for name, status in (('w03', 2), ('wint', 0x40), ('wleft', 0x4A)):
            cell = populated(name)[1, 1]
            self.assertEqual((cell.status, cell.numeric_value, cell.text), (status, 12.5, '12.50'))

    def test_formula_calculation_error_and_stale_result(self):
        observed = {
            'w05': (0.0, False, False), 'w05c': (5.0, True, False),
            'w06': (5.0, True, False), 'w06c': (11.0, True, False),
            'werr': (0.0, True, True),
        }
        for name, expected in observed.items():
            cell = populated(name)[1, 3]
            self.assertEqual((cell.numeric_value, cell.result_flag, cell.error_flag), expected)
            self.assertEqual(cell.text, 'R1C1/0' if name == 'werr' else 'R1C1+R1C2')
        self.assertEqual(raw('w06c'), raw('wrecalc'))
        self.assertEqual(populated('w06')[1, 2].numeric_value, 9.0)

    def test_reference_error_preserves_expression_and_old_cache(self):
        for name, status in (('wref', 0xB2), ('wrefc', 0xA2)):
            cell = populated(name)[1, 2]
            self.assertEqual((cell.text, cell.numeric_value, cell.status), ('R1C1+R1C2', 11.0, status))
            self.assertTrue(cell.error_flag)

    def test_decimal_precision_and_alignment_status_controls(self):
        for name, status in (('wdp2', 0x42), ('wdp4', 0x44), ('wdl4', 0x4C)):
            cell = populated(name)[1, 1]
            self.assertEqual((cell.text, cell.numeric_value, cell.status), ('12.50', 12.5, status))
        self.assertEqual(raw('wcu'), raw('wdp2'))

    def test_formula_copy_rewrites_relative_references_only(self):
        p = populated('wabsc')
        relative, absolute = p[2, 3], p[2, 4]
        self.assertEqual((relative.text, relative.numeric_value), ('R2C1+R2C2', 10.0))
        self.assertEqual((absolute.text, absolute.numeric_value), ('#R1C1+#R1C2', 11.0))
        self.assertEqual(populated('wrow')[2, 3].text, relative.text)
        self.assertEqual(populated('wcol')[1, 4].text, 'R1C2+R1C3')
        self.assertEqual(populated('wback')[1, 3].text, 'R1C1+R1C2')
        self.assertEqual(populated('wsparse')[99, 99].text, 'FAR99')

    def test_multiline_padding_and_input_recalculation(self):
        block = populated('w08m')[1, 1]
        self.assertEqual((block.row_span, block.column_span, block.text), (2, 2, 'FIRST\nSECOND'))
        self.assertEqual(block.raw_string, b'FIRST\rSECOND' + b'\x01' * 33 + b'\x02')
        before, after = populated('wmix'), populated('wmix2')
        self.assertEqual({c.category for c in before.values()}, set(dict(worksheet.CELL_SIZES)))
        self.assertEqual((before[2, 1].text, before[2, 1].numeric_value), ('RATE7', 4.5))
        self.assertEqual((after[2, 1].text, after[2, 1].numeric_value), ('RATE7', 7.5))
        self.assertEqual((before[2, 2].numeric_value, after[2, 2].numeric_value), (40.5, 67.5))
        self.assertEqual(after[2, 2].text, before[2, 2].text)

    def test_native_soft_wrap_and_three_cluster_growth(self):
        wrapped = populated('wsoft')[1, 1]
        self.assertEqual(wrapped.text, 'ONE TWO \nTHREE FOUR')
        self.assertEqual(wrapped.raw_string, b'ONE TWO \nTHREE FOUR' + b'\x01' * 18 + b'\x02')
        grown = read('wgrw')
        block, = (c for c in grown.cells if not c.dummy)
        self.assertEqual(grown.size, 5094)
        self.assertEqual((block.row_span, block.column_span, block.text), (63, 7, 'GROWTH\nCONTROL'))
        self.assertEqual(len(block.raw_string), 4853)

    def test_rejects_descriptors_dummies_and_invalid_pool_references(self):
        original = raw('w01')
        for offset, word in ((124, 0), (130, 14), (134, 0), (134, 65535), (180, 0), (180, 113), (180, 65535)):
            malformed = bytearray(original)
            pack_into('<H', malformed, offset, word)
            with self.subTest(offset=offset, word=word), self.assertRaises(worksheet.WorksheetFormatError):
                worksheet.parse_bytes(malformed)
        for offset in (0, 22, 122, 176, 182, len(original) - 1):
            malformed = bytearray(original)
            malformed[offset] = 0xFF
            with self.subTest(offset=offset), self.assertRaises(worksheet.WorksheetFormatError):
                worksheet.parse_bytes(malformed)
        for limit in (21, 126, 231, len(original) - 1):
            with self.subTest(limit=limit), self.assertRaises(worksheet.WorksheetFormatError):
                worksheet.parse_bytes(original[:limit])

    def test_rejects_text_block_dimensions_and_terminator(self):
        block = populated('w08m')[1, 1]
        for offset, value in ((block.offset + 6, 99), (read('w08m').size - 2, 3)):
            tampered = bytearray(raw('w08m'))
            tampered[offset] = value
            with self.assertRaises(worksheet.WorksheetFormatError):
                worksheet.parse_bytes(tampered)
