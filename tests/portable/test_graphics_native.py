"""Cross-check Draw, Text and Filer graphics against application-written bytes."""
from hashlib import sha256
from pathlib import Path
from struct import pack, pack_into
import unittest
from xml.etree import ElementTree

from deskmate_formats import database, draw, filer, filer_graphics, graphics, graphics_raster, text


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated'


def read_drawing(name):
    return draw.parse_file(FIXTURES / 'draw' / (name + '.fig'))


class ObliquePenTest(unittest.TestCase):
    def test_normal_zoom_native_line_neighborhoods(self):
        # Drawing-area RGB crops from the isolated line trials. Each crop
        # includes four background pixels beyond the stored endpoints.
        cases = (
            ((8, 51), (56, 72), 0, 0, '23a2d80800e47e6011d6250257e81583be20711a9f4d10adad3b4474deb97875'),
            ((164, 141), (212, 162), 2, 1, 'aa3bb1cc8b153d1b6c6789bc4ee7b72e6b7c39bcf187b9830fd8b8b1124588ff'),
            ((575, 373), (554, 321), 7, 3, 'da274081dc5a608410052ef3d510de68ce564ecc166136b09efadbf6df531815'),
            ((450, 193), (398, 141), 5, 1, 'bfb1348e9ac4ab5c6ec7866f0653e966f8f5c02825ffd4f8c936992d77cc159e'),
        )
        width, height = graphics_raster.WIDTH, graphics_raster.HEIGHT
        for start, end, style, weight, expected in cases:
            with self.subTest(start=start, end=end, style=style, weight=weight):
                image = bytearray(b'\0\0\x81' * (width * height))
                graphics_raster._square_pen_stroke(image, start, end, b'\xc2\xc2\0', style, weight)
                left, right = sorted((start[0], end[0]))
                top, bottom = sorted((start[1], end[1]))
                crop = b''.join(image[3 * (y * width + left - 4):3 * (y * width + right + 5)]
                                for y in range(top - 4, bottom + 5))
                self.assertEqual(sha256(crop).hexdigest(), expected)


class ArcRecoveryTest(unittest.TestCase):
    def test_native_arc_size_disagreement_is_opt_in(self):
        root = FIXTURES / 'draw'
        good = (root / 'arc-extent-control.fig').read_bytes()
        bad = (root / 'arc-extent-native-resaved.fig').read_bytes()
        self.assertEqual(good[:72] + b'\x17' + good[73:], bad)
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'extended element exceeds'):
            draw.parse_bytes(bad)
        recovered = draw.parse_bytes(bad, recover_arc_length=True)
        self.assertEqual(recovered.recovered_arcs, (10,))
        self.assertEqual(recovered.form.list_data[28:30], b'\x17\0')
        self.assertEqual([e.kind for e in recovered.form.elements], ['UA', 'L'])
        self.assertEqual(graphics.render_svg(recovered.form, recovered.palette),
                         graphics.render_svg(draw.parse_bytes(good).form, recovered.palette))
        for offset, value in ((72, 24), (98, ord('R')), (55, ord('V'))):
            candidate = bytearray(bad)
            candidate[offset] = value
            with self.subTest(offset=offset), self.assertRaises(graphics.GraphicsFormatError):
                draw.parse_bytes(candidate, recover_arc_length=True)

    def test_quadratic_geometry_and_reflection_boundary(self):
        drawing = read_drawing('arc-grid-native')
        arcs = tuple(drawing.form.draw_order())
        self.assertEqual(graphics.arc_quadratic(arcs[0]), ((400, 800), (1100, 200), (1800, 800)))
        self.assertEqual(graphics.arc_quadratic(arcs[1]), ((3450, 800), (2750, 200), (2050, 800)))
        self.assertEqual(graphics.arc_quadratic(arcs[4]), ((400, 2450), (455, 650), (1850, 2450)))
        self.assertEqual(graphics.arc_quadratic(arcs[8]), ((400, 4450), (1300, 1550), (2200, 4450)))
        self.assertIsNone(graphics.arc_quadratic(arcs[9]))
        preview = graphics.preview_svg(drawing.form, drawing.palette)
        self.assertEqual(preview.rendered_elements, 10)
        self.assertEqual([omission.reason for omission in preview.omissions], ['unsupported_arc_extent'])
        self.assertIn('d="M 400 800 Q 1100 200 1800 800"', preview.svg)


class ExternalFontTest(unittest.TestCase):
    def test_descriptor_and_optional_safe_substitution(self):
        original = bytearray((FIXTURES / 'draw/d23.fig').read_bytes())
        drawing = draw.parse_bytes(original)
        element, = drawing.form.draw_order()
        start = 44 + element.offset
        original[start + 26:start + 31] = b'Dixon'
        original[start + 100:start + 109] = b'LAB <& 42'
        renamed = draw.parse_bytes(original)
        run = graphics.external_font_run(next(renamed.form.draw_order()))
        self.assertEqual(run.name, 'Dixon')
        self.assertEqual(run.text_bytes, b'LAB <& 42')
        self.assertEqual(run.padding, b'\0')
        self.assertEqual(len(run.descriptor), 40)
        self.assertEqual((run.point_size_word, run.width_percent_word), (24, 100))
        self.assertNotIn('<text ', graphics.render_svg(renamed.form, renamed.palette))
        substitute = graphics.render_svg(renamed.form, renamed.palette, substitute_external_fonts=True)
        self.assertIn('Generic monospace substitutes for 1 external font runs', substitute)
        self.assertIn('LAB &lt;&amp; 42', substitute)

    def test_native_dixon_and_marin(self):
        drawing = read_drawing('outline-fonts-native')
        refs = [graphics.external_font_run(item) for item in drawing.form.draw_order()]
        self.assertEqual([(ref.name, ref.text_bytes, ref.point_size_word, ref.width_percent_word) for ref in refs],
                         [('Dixon', b'DIXON 24', 24, 100), ('Marin', b'MARIN 24', 24, 100)])


class ArcTransferTest(unittest.TestCase):
    def test_arc_and_rectangle_across_native_wrappers(self):
        drawing = read_drawing('arc-transfer-native').form
        document = text.parse_file(FIXTURES / 'text/arc-transfer-native.doc')
        picture, = document.pictures
        data = filer.parse_file(FIXTURES / 'filer/arc-transfer-native.fil')
        card, report = filer_graphics.decode(data)
        self.assertEqual((picture.column, picture.payload[-1]), (0, 25))
        self.assertEqual((card.marker, report.marker), ('F', 'R'))
        self.assertEqual((len(card.payload), len(report.payload)), (122, 122))
        self.assertEqual([len(chunk) for item in (card, report) for chunk in item.encoded_chunks], [205, 205])
        wrapped = (
            (graphics.parse_bytes(picture.payload, text_picture=True), (-850, -410)),
            (card.form, (850, 140)),
            (report.form, (1050, 580)),
        )
        for form, (dx, dy) in wrapped:
            with self.subTest(dx=dx, dy=dy):
                self.assertEqual(len(form.entries), 1)
                for source, copy in zip(drawing.draw_order(), form.draw_order(), strict=True):
                    self.assertEqual(source.kind, copy.kind)
                    self.assertEqual(source.raw[18:], copy.raw[18:])
                    a, b, c, d = source.bounds
                    self.assertEqual(copy.bounds, (a + dx, b + dy, c + dx, d + dy))
                preview = graphics.preview_svg(form)
                self.assertEqual(preview.rendered_elements, 2)
                self.assertIn('<path d="M ', preview.svg)

    def test_independent_text_replacement_and_native_resave(self):
        folder = FIXTURES / 'text'
        records = [text.parse_file(folder / name) for name in (
            'arc-replacement-tool-generated.doc', 'arc-replacement-native.doc')]
        forms = []
        for document in records:
            self.assertEqual(document.text, 'ARC SAMPLE\n')
            picture, = document.pictures
            self.assertEqual((picture.offset, picture.column, len(picture.payload), picture.payload[-1]),
                             (34, 3, 123, 25))
            forms.append(graphics.parse_bytes(picture.payload, text_picture=True))
        self.assertEqual(forms[0].list_data, forms[1].list_data)
        self.assertEqual([e.kind for e in forms[1].draw_order()], ['UA', 'R'])

    def test_brush_tools_saved_as_extended_paths(self):
        open_path, closed_path = read_drawing('brushes-native').form.draw_order()
        self.assertEqual([part.kind for part in (open_path, closed_path)], ['UP', 'UP'])
        self.assertEqual((len(open_path.points), len(closed_path.points)), (8, 6))
        self.assertEqual(open_path.raw[32:34], b'\0\0')
        self.assertEqual(closed_path.raw[32:34], b'\xff\xff')
        self.assertEqual(open_path.raw[22:25], closed_path.raw[22:25])


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

    def test_native_scalable_text_survives_transfer_without_stroke_bank(self):
        drawing = read_drawing('d23').form
        picture, = read_text('tp09').pictures
        section, = filer_graphics.decode(read_filer('g23'))
        for form in (drawing, picture_form(picture), section.form):
            element = leaf(form)
            self.assertEqual((element.kind, element.font_name, element.text_bytes),
                             ('Uf', 'Cobb', b'VECTOR 42'))
            self.assertEqual(graphics.parse_strokes(form.strokes), ())
            self.assertIn('5566', graphics.render_svg(form))

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


class EmbeddedStrokeTest(unittest.TestCase):
    def test_inline_text_and_embedded_glyph_geometry(self):
        paths = bytes((8, 120, 64, 8, 120, 120, 0, 32, 83, 96, 83))
        bank = pack('<HBB', len(paths) + 4, 3, ord('A')) + paths + b'\x00\x00'
        glyph, = graphics.parse_strokes(bank)
        self.assertEqual(glyph.paths, (((8, 120), (64, 8), (120, 120)), ((32, 83), (96, 83))))
        label = pack('<BBhHhHhHhHBBBB', ord('T'), 3, 100, 0, 200, 0, 228, 0, 328, 0, 0, 1, 1, 0)
        listing = pack('<HHH', 1, 3, 1) + label + b'A\x00'
        header = pack('<2B10H', 1, 0, len(listing) // 2, len(bank), 2, 3, 2, 0, 0, 0,
                      len(listing), len(bank))
        form = graphics.parse_bytes(header + listing + bank)
        self.assertEqual(leaf(form).text_bytes, b'A')
        preview = ElementTree.fromstring(graphics.render_svg(form))
        self.assertEqual(preview[1].attrib['aria-label'], 'A')
        self.assertEqual(preview[1][0].attrib['points'], '108,320 164,208 220,320')

    def test_stroke_bank_rejects_malformed_lengths_and_points(self):
        for bank in (b'\x04\x00\x03A', b'\x01\x00\x03A\x00\x00',
                     b'\x08\x00\x03A\x01\x01\x81\x02\x00\x00',
                     b'\x09\x00\x03A\x01\x01\x02\x02\x03\x00\x00'):
            with self.subTest(bank=bank), self.assertRaises(graphics.GraphicsFormatError):
                graphics.parse_strokes(bank)
