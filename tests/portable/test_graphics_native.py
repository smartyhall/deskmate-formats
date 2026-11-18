"""Cross-check Draw, Text and Filer graphics against application-written bytes."""
from pathlib import Path
from struct import pack, pack_into
import unittest
from xml.etree import ElementTree

from deskmate_formats import database, draw, filer, filer_graphics, graphics, text


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated'


def read_drawing(name):
    return draw.parse_file(FIXTURES / 'draw' / (name + '.fig'))


def read_text(name):
    return text.parse_file(FIXTURES / 'text' / (name + '.doc'))


def read_filer(name):
    return filer.parse_file(FIXTURES / 'filer' / (name + '.fil'))


def picture_form(picture):
    return graphics.parse_bytes(picture.payload, text_picture=True)


def leaf(form):
    element, = form.draw_order()
    return element


class DrawGraphicsTest(unittest.TestCase):
    def test_native_sizes_palette_and_primitive_geometry(self):
        line = read_drawing('d01')
        self.assertEqual(line.page_setup[:4], b'\x14FIG')
        self.assertEqual(line.palette_offset, 74)
        self.assertEqual(line.palette[1], (1, 192, 192, 0))
        self.assertEqual(line.trailer, b'\x00')
        self.assertEqual(len(line.form.list_data), 26)
        self.assertEqual(line.form.strokes, b'\x00\x00')
        self.assertEqual(leaf(line.form).bounds, (800, 985, 1200, 985))
        self.assertEqual(leaf(read_drawing('d02').form).bounds, (800, 985, 1625, 985))
        self.assertEqual(leaf(read_drawing('d05').form).bounds, (600, 985, 2425, 2360))
        self.assertEqual(leaf(read_drawing('d06').form).bounds, (1400, 2745, 2800, 4065))
        self.assertEqual(line.form.list_data, read_drawing('d12').form.list_data)
        self.assertNotEqual(line.form.header, read_drawing('d12').form.header)

    def test_pixel_shift_color_and_reconstruction_order(self):
        a, b = (leaf(read_drawing(name).form) for name in ('d16a', 'd16b'))
        self.assertEqual(tuple(y - x for x, y in zip(a.bounds, b.bounds)), (13, 0, 13, 0))
        rect = read_drawing('d04')
        green = read_drawing('d07c')
        self.assertEqual(rect.palette, green.palette)
        self.assertEqual(leaf(rect.form).bounds, leaf(green.form).bounds)
        self.assertEqual(leaf(green.form).raw[18], 10)
        combo = read_drawing('d17')
        self.assertEqual([e.kind for e in combo.form.draw_order()], ['L', 'R', 'E'])
        self.assertEqual([e.kind for e in read_drawing('d11').form.draw_order()], ['L', 'R'])
        preview = graphics.render_svg(combo.form, combo.palette)
        tags = [e.tag.partition('}')[2] for e in ElementTree.fromstring(preview)]
        self.assertEqual(tags, ['desc', 'rect', 'line', 'rect', 'ellipse'])
        opaque = read_drawing('d10').form
        self.assertIn(b'GRAPH7Q9', next(e.raw for e in opaque.elements if e.kind == 'Uf'))
        self.assertIn('5566', graphics.render_svg(opaque))

    def test_rejects_inconsistent_sizes_and_invalid_element_references(self):
        raw = (FIXTURES / 'draw/d01.fig').read_bytes()
        for offset, value in ((0, 0x10), (24, 7), (40, 8), (74, 9), (46, 0)):
            bad = bytearray(raw)
            bad[offset] = value
            with self.subTest(offset=offset), self.assertRaises(graphics.GraphicsFormatError):
                draw.parse_bytes(bad)
        with self.assertRaises(graphics.GraphicsFormatError):
            draw.parse_bytes(raw[:-1])

    def test_rejects_cyclic_group(self):
        picture, = read_text('tp06').pictures
        raw = bytearray(picture.payload)
        group_offset = graphics.PREFIX_SIZE + 6
        pack_into('<H', raw, group_offset + 20, 3)
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'cyclic group'):
            graphics.parse_bytes(raw, text_picture=True)

    def test_native_group_break_and_polygon_pattern(self):
        original = read_drawing('d17').form
        grouped = read_drawing('d19').form
        self.assertEqual(len(grouped.entries), 1)
        self.assertEqual(len(next(e for e in grouped.elements if e.kind == 'OO').children), 3)
        flat = read_drawing('d21').form
        self.assertEqual(len(flat.entries), 3)
        for variant in (grouped, flat):
            self.assertEqual([e.raw for e in variant.draw_order()], [e.raw for e in original.draw_order()])
        unfilled = read_drawing('d20').form
        polygon = leaf(unfilled)
        filled = leaf(read_drawing('d22').form)
        self.assertEqual(polygon.points, ((0, 0), (375, 1100), (1750, 753), (1000, 0), (0, 0)))
        self.assertEqual((polygon.raw[24], filled.raw[24]), (0xFE, 9))
        self.assertEqual(polygon.points, filled.points)
        preview = ElementTree.fromstring(graphics.render_svg(unfilled))
        self.assertEqual(preview[1].attrib['fill'], 'none')


class TextPictureTest(unittest.TestCase):
    def test_native_picture_placement_and_conversion(self):
        document = read_text('tp01')
        picture, = document.pictures
        self.assertEqual(document.text, 'BEFORE LINE\nAFTER LINE')
        self.assertEqual((picture.offset, picture.payload_offset, picture.end_offset), (35, 40, 114))
        self.assertEqual((picture.column, picture.text_offset, len(picture.payload)), (0, 12, 71))
        shifted, = read_text('tp02').pictures
        self.assertEqual((shifted.column, shifted.payload), (3, picture.payload))
        self.assertEqual(read_text('tp03').pictures[0].offset, len(text.FORMATTED_HEADER))
        first, second = read_text('tp04').pictures
        self.assertEqual(first.end_offset, second.offset)
        self.assertEqual([leaf(picture_form(p)).kind for p in (first, second)], ['R', 'L'])
        self.assertEqual((read_text('tp05').text, read_text('tp05').pictures), ('THREE SHAPES\n', ()))
        self.assertEqual((read_text('tpascii').header, read_text('tpascii').text), (b'', document.text))
        with self.assertRaisesRegex(text.TextFormatError, 'structured Text reader'):
            text.extract_file(FIXTURES / 'text/tp01.doc')

    def test_whole_drawing_and_one_selected_object(self):
        for name, kinds in (('tp06', ['L', 'R', 'E']), ('tp07', ['E'])):
            picture, = read_text(name).pictures
            self.assertEqual([e.kind for e in picture_form(picture).draw_order()], kinds)

    def test_length_bounds_before_any_embedded_control(self):
        payload = b'\x01\x02\x1a\x03\x0d\x0a\xff'
        envelope = b'\x01' + pack('<HH', len(payload), 3) + payload + pack('<H', len(payload)) + b'\x02'
        prefix = text.FORMATTED_HEADER + b'A\r\n'
        parsed = text.parse_bytes(prefix + envelope + b'B \x1a')
        self.assertEqual((parsed.text, parsed.pictures[0].payload), ('A\nB', payload))
        for bad in (
            prefix + envelope[:-2],                         # truncated trailer
            prefix + envelope[:-3] + b'\x06\x00\x02',      # wrong mirror length
            prefix + envelope[:-1] + b'\x03',               # wrong terminator
            prefix + b'\x01\xff\xff' + envelope[3:],      # truncated advertised content
            text.FORMATTED_HEADER + b'A' + envelope,         # mid-paragraph start
            b'A\r\n' + envelope,                           # plain stream
            prefix + b'\x01\x00\x00\x00\x00\x00\x00\x02',  # zero payload
        ):
            with self.subTest(bad=bad), self.assertRaises(text.TextFormatError):
                text.parse_bytes(bad + b'\x1a')


class FilerGraphicsTest(unittest.TestCase):
    def test_native_line_between_all_three_wrappers(self):
        a = leaf(read_drawing('d01').form)
        b = leaf(picture_form(read_text('tp01').pictures[0]))
        section, = filer_graphics.decode(read_filer('g01'))
        c = leaf(section.form)
        self.assertEqual(section.row_offsets, (0x2000,))
        self.assertEqual(section.marker, 'F')
        self.assertEqual(len(section.encoded_chunks[0]), 126)
        for element in (a, b, c):
            self.assertEqual(element.raw[:2] + element.raw[18:], b'L\x00\x01\x00')
            x0, y0, x1, y1 = element.bounds
            self.assertEqual((x1 - x0, y1 - y0), (400, 0))
        self.assertEqual((a.bounds[:2], b.bounds[:2], c.bounds[:2]), ((800, 985), (100, 110), (1000, 1100)))
        shifted, = filer_graphics.decode(read_filer('g03'))
        self.assertEqual(leaf(shifted.form).bounds[:2], (1300, 1540))

    def test_moved_resized_deleted_and_recolored_pictures(self):
        baseline = read_filer('qrecord-empty')
        self.assertEqual(filer_graphics.decode(baseline), ())
        expected = {
            'g04': ['R'], 'g05': ['R', 'L'], 'gdel': ['L'],
            'gmove': ['R'], 'gsize': ['R'], 'gcol': ['R'],
        }
        for name, kinds in expected.items():
            snapshot = read_filer(name)
            self.assertEqual(snapshot.table('LAYOUTS').rows, baseline.table('LAYOUTS').rows)
            section, = filer_graphics.decode(snapshot)
            self.assertEqual([element.kind for element in section.form.draw_order()], kinds)
        for name, color in (('g04', 1), ('gcol', 10)):
            section, = filer_graphics.decode(read_filer(name))
            self.assertEqual(leaf(section.form).raw[18], color)

    def test_native_continuation_and_bad_escape(self):
        snapshot = read_filer('g18')
        section, = filer_graphics.decode(snapshot)
        self.assertEqual(len(read_drawing('d18').form.entries), 36)
        self.assertEqual([len(c) for c in section.encoded_chunks], [1015, 392])
        self.assertEqual(len(section.payload), 842)
        self.assertEqual([e.kind for e in section.form.draw_order()], ['L'] * 36)
        boundary, = filer_graphics.decode(read_filer('g20'))
        self.assertEqual([len(c) for c in boundary.encoded_chunks], [1016, 373])
        self.assertTrue(boundary.encoded_chunks[0].endswith(b'\x07\x40'))
        self.assertEqual(len(boundary.payload), 842)
        self.assertEqual([e.kind for e in boundary.form.draw_order()], ['L'] * 36)
        for chunk in (b'\x07', b'\x07H', b'\x05'):
            with self.assertRaises(graphics.GraphicsFormatError):
                filer_graphics._unescape(chunk)

    def test_legacy_filer_omits_only_non_self_schema_unique_field(self):
        source = read_filer('qrecord-empty')
        table = source.table('DBCOLS')
        raw = bytearray(source.data)
        row = next(row for row in table.rows if row.fields[1] == b'DATA')
        self.assertEqual(raw[row.end-4:row.end], b'\x010\x01\x02')
        page_end = (row.offset // 1024 + 1) * 1024
        raw[row.end-4:page_end] = raw[row.end-2:page_end] + b'\x00\x00'
        for later in table.rows:
            if later.offset > row.offset:
                pack_into('<H', raw, later.index_offset + 2, (later.offset % 1024) - 2)
        with self.assertRaises(database.DatabaseError):
            database.parse_bytes(raw)
        legacy = filer.parse_bytes(raw)
        modified = next(r for r in legacy.table('DBCOLS').rows if r.offset == row.offset)
        self.assertEqual(modified.fields, row.fields[:5])
