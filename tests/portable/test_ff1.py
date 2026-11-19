"""Check lossless FF1 reconstruction and optional outline interchange."""
from dataclasses import replace
from importlib.util import find_spec
from io import BytesIO
from struct import pack_into, unpack_from
import unittest

from deskmate_formats import ff1, ff1_geometric, ff1_interchange
from deskmate_formats.font_resources import MAX_SIZE, Contour, FontResourceError, draw_outline_slot


class FontWriterTests(unittest.TestCase):
    def setUp(self):
        self.model = ff1_geometric.geometric_face()
        self.data = ff1.serialize_resource(self.model)

    def test_roundtrip_sections_and_offsets(self):
        header = bytearray(self.data[:66])
        pack_into('<I', header, 38, len(self.data))
        original = bytes(header) + self.data[66:] + b'opaque tail'
        parsed = ff1.parse_resource(original)
        self.assertEqual(ff1.serialize_resource(parsed), original)
        self.assertEqual(parsed.family, 'Lab Grid')
        glyph = parsed.glyphs[0]
        edited = replace(glyph, outline=replace(glyph.outline, auxiliary=b'\x02\0\0\0\0\0'))
        output = ff1.serialize_resource(replace(parsed, glyphs=(edited, *parsed.glyphs[1:])))
        self.assertEqual(unpack_from('<I', output, 38)[0], len(self.data) + 6)
        reparsed = ff1.parse_resource(output)
        self.assertEqual(reparsed.trailing, b'opaque tail')
        self.assertEqual(reparsed.glyphs[1:], parsed.glyphs[1:])
        self.assertEqual(ff1.serialize_resource(reparsed), output)

    def test_malformed_and_overflow(self):
        for bad in (self.data[:-1], b'\0' + self.data[1:], self.data + bytes(MAX_SIZE)):
            with self.assertRaises(FontResourceError):
                ff1.parse_resource(bad)
        glyph = self.model.glyphs[0]
        for changed in (
            replace(glyph, advance=-1),
            replace(glyph, advance=65536),
            replace(glyph, outline=replace(glyph.outline, contours=(Contour((0, 32768), ()),))),
            replace(glyph, outline=replace(glyph.outline, contours=(Contour((0, 0), (((1, 0),),)),))),
        ):
            with self.assertRaisesRegex(FontResourceError, 'invalid glyph 32'):
                ff1.serialize_resource(replace(self.model, glyphs=(changed, *self.model.glyphs[1:])))
        with self.assertRaisesRegex(FontResourceError, 'snapshot limit'):
            ff1.serialize_resource(replace(self.model, trailing=bytes(MAX_SIZE)))
        with self.assertRaisesRegex(FontResourceError, 'name'):
            ff1_geometric.geometric_face('Non-ASCII \N{LATIN CAPITAL LETTER E WITH ACUTE}')

    def test_draw_outline_slot_routing(self):
        self.assertEqual(draw_outline_slot(0x82), 197)
        self.assertEqual(draw_outline_slot(0x90), 220)
        self.assertEqual(draw_outline_slot(0xC1), 127)
        self.assertEqual(len({draw_outline_slot(i) for i in range(128, 224)}), 96)
        self.assertEqual({draw_outline_slot(i) for i in range(224, 256)}, {32})
        self.assertEqual(draw_outline_slot(ord('A')), ord('A'))

    @unittest.skipUnless(find_spec('fontTools'), 'optional FontTools extra')
    def test_interchange(self):
        data = ff1_interchange.export_cff(self.model)
        self.assertEqual(data, ff1_interchange.export_cff(ff1.parse_resource(self.data)))
        rebuilt, report = ff1_interchange.import_outline(data, 'Geometric Copy')
        self.assertEqual(report['max_coordinate_error_em1000'], 0)
        self.assertEqual(report['max_advance_error_em1000'], 0)
        self.assertEqual(len(report['represented_codepoints']), 223)
        self.assertEqual(rebuilt.glyphs[:95], self.model.glyphs[:95])
        self.assertEqual(rebuilt.glyphs[96:], self.model.glyphs[96:])

    @unittest.skipUnless(find_spec('fontTools'), 'optional FontTools extra')
    def test_native_text_mapping_roundtrip(self):
        direct = ff1_interchange.export_cff(self.model)
        model, report = ff1_interchange.import_outline(direct, 'Test', native_text_map=True)
        self.assertEqual(len(report['represented_codepoints']), 191)
        self.assertEqual(model.glyphs[220 - 32], self.model.glyphs[0x90 - 32])
        result = ff1_interchange.export_cff(model, native_text_map=True)
        rebuilt, _ = ff1_interchange.import_outline(result, 'Test', native_text_map=True)
        self.assertEqual(rebuilt.glyphs, model.glyphs)

    @unittest.skipUnless(find_spec('fontTools'), 'optional FontTools extra')
    def test_truetype_composite_and_quadratic(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen

        pen = TTGlyphPen(None)
        pen.moveTo((0, 0))
        pen.qCurveTo((300, 600), (600, 0))
        pen.closePath()
        glyphs = {'.notdef': TTGlyphPen(None).glyph(), 'arch': pen.glyph()}
        composite = TTGlyphPen(glyphs)
        composite.addComponent('arch', (1, 0, 0, 1, 100, -200))
        glyphs['component'] = composite.glyph()
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder(list(glyphs))
        builder.setupCharacterMap({ord('A'): 'component'})
        builder.setupGlyf(glyphs)
        builder.setupHorizontalMetrics({'.notdef': (0, 0), 'arch': (700, 0), 'component': (800, 100)})
        builder.setupHorizontalHeader(ascent=800, descent=-200)
        builder.setupNameTable({'familyName': 'Quadratic Trial', 'styleName': 'Regular'})
        builder.setupOS2()
        builder.setupPost()
        source = BytesIO()
        builder.save(source)
        model, report = ff1_interchange.import_outline(source.getvalue(), 'Trial')
        glyph = model.glyphs[ord('A') - 32]
        self.assertEqual(glyph.advance, 800)
        self.assertEqual(glyph.outline.contours,
                         (Contour((100, 200), (((300, -200), (500, -200), (700, 200)), ((100, 200),))),))
        self.assertEqual(report['max_coordinate_error_em1000'], 0)
