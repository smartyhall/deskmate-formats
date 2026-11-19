"""Check lossless FF1 reconstruction and optional outline interchange."""
from dataclasses import replace
from importlib.util import find_spec
from struct import pack_into, unpack_from
import unittest

from deskmate_formats import ff1, ff1_geometric, ff1_interchange
from deskmate_formats.font_resources import MAX_SIZE, Contour, FontResourceError


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
