"""Exercise the FF1 directory inspection profile with synthetic bytes."""
from struct import pack_into
import unittest

from deskmate_formats import font_resources as ff1


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
