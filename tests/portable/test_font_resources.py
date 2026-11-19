"""Exercise the FF1 directory inspection profile with synthetic bytes."""
from struct import pack, pack_into
import unittest

from deskmate_formats import font_resources as ff1
from deskmate_formats import graphics, graphics_raster


def resource():
    data = bytearray(66 + 2 * 46)
    data[:5] = b'\xbd\x7a\0\x01\x01'
    pack_into('<H', data, 10, 2)
    pack_into('<HH', data, 14, 32, 224)
    pack_into('<H', data, 32, 46)
    data[66:69] = b'Lab'
    data[112:120] = b'Lab Wide'
    return data


class DirectoryTest(unittest.TestCase):
    def test_directory(self):
        info = ff1.parse_bytes(bytes(resource()))
        self.assertEqual((info.first_code_word, info.code_count_word), (32, 224))
        self.assertEqual([(face.name, face.offset) for face in info.variants],
                         [('Lab', 66), ('Lab Wide', 112)])

    def test_bad_directory(self):
        for bad in (bytes(resource()[:-1]), bytes([1]) + bytes(resource()[1:])):
            with self.assertRaises(ff1.FontResourceError):
                ff1.parse_bytes(bad)

    def test_verified_inner_glyph_index(self):
        data = resource()
        outer_end = len(data)
        pack_into('<H', data, 16, 2)
        data.extend(b'\0' * 68)
        inner = outer_end + 4
        pack_into('<H', data, outer_end + 2, 48)
        data[inner:inner + 4] = b'\x1e\xf3\x01\x01'
        pack_into('<I', data, inner + 4, 64)
        pack_into('<HHH', data, inner + 12, 1000, 32, 2)
        pack_into('<HHH', data, inner + 46, 52, 411, 577)
        pack_into('<II', data, inner + 52, 60, 62)
        glyphs = ff1.parse_glyph_index(bytes(data))
        self.assertEqual(glyphs.units_per_em_word, 1000)
        self.assertEqual(glyphs.entries, (
            ff1.GlyphEntry(32, 411, inner + 60, 2),
            ff1.GlyphEntry(33, 577, inner + 62, 2),
        ))
        pack_into('<I', data, inner + 56, 60)
        with self.assertRaisesRegex(ff1.FontResourceError, 'overlapping or unordered'):
            ff1.parse_glyph_index(bytes(data))

    def test_outline_commands_and_auxiliary_extent(self):
        contour = (pack('<Bhh', 0, -30, -100) + pack('<Bhh', 1, 80, -100)
                   + pack('<B6h', 2, 100, 20, -30, 20, -30, -100))
        raw = pack('<H4h2H', 1, -30, -100, 100, 20, len(contour), 6) + contour + b'\x02\0\0\0\0\0'
        entry = ff1.GlyphEntry(65, 120, 3, len(raw))
        outline = ff1.parse_glyph_outline(b'pad' + raw, entry)
        self.assertEqual(outline.bounds, (-30, -100, 100, 20))
        self.assertEqual(outline.contours, (ff1.Contour((-30, -100), (((80, -100),),
                                                                     ((100, 20), (-30, 20), (-30, -100)))),))
        self.assertEqual(outline.auxiliary, b'\x02\0\0\0\0\0')
        with self.assertRaisesRegex(ff1.FontResourceError, 'opcode 0x03.*code 65.*byte 14'):
            ff1.parse_glyph_outline(b'pad' + raw[:14] + b'\x03' + raw[15:], entry)
        with self.assertRaisesRegex(ff1.FontResourceError, 'invalid FF1 glyph extent'):
            ff1.parse_glyph_outline(b'pad' + raw[:-1], entry)
        with self.assertRaisesRegex(ff1.FontResourceError, 'open FF1 contour'):
            ff1.parse_glyph_outline(b'pad' + raw[:36] + b'\x00' + raw[37:], entry)

    def test_local_face_projects_solid_ink_with_a_counter(self):
        contours = bytes()
        for points in (((0, -600), (600, -600), (600, 0), (0, 0), (0, -600)),
                       ((200, -400), (200, -200), (400, -200), (400, -400), (200, -400))):
            contours += b''.join(pack('<Bhh', int(i > 0), *point) for i, point in enumerate(points))
        resource_bytes = pack('<H4h2H', 1, 0, -600, 600, 0, len(contours), 0) + contours
        glyph = ff1.GlyphEntry(65, 750, 0, len(resource_bytes))
        face = ff1.OutlineFace('Lab', '', ff1.GlyphIndex(1000, (glyph,)), resource_bytes)
        raw = bytearray(102)
        raw[:2], raw[20], raw[26:29], raw[100] = b'Uf', 4, b'Lab', 65
        pack_into('<H', raw, 18, 51)
        pack_into('<HH', raw, 56, 72, 100)
        pack_into('<HH', raw, 64, 12, 255)
        pack_into('<HHHH', raw, 90, 1, 100, 800, 1)
        element = graphics.Element(6, 'Uf', 102, (100, 0, 200, 0, 700, 0, 800, 0), bytes(raw))
        form = graphics.Form(b'', b'', b'', (graphics.Entry(6, 1),), (element,), b'')
        palette = [(0, 0, 0, 128), (4, 192, 192, 0)]
        svg = graphics.preview_svg(form, palette, outline_faces={'lab': face})
        self.assertIn('M 100 200 L 700 200', svg.svg)
        self.assertIn('fill="#c0c000"', svg.svg)
        self.assertEqual(svg.omissions, ())
        self.assertEqual(graphics.preview_svg(form, palette).omissions[0].reason, 'external_font_reference')
        raster = graphics_raster.preview_rsx(form, palette, outline_faces={'lab': face})
        self.assertEqual(raster.omissions, ())
        self.assertEqual(raster.rgb[3 * (22 * 640 + 20):][:3], b'\xc2\xc2\0')
        self.assertEqual(raster.rgb[3 * (43 * 640 + 30):][:3], b'\0\0\x81')
