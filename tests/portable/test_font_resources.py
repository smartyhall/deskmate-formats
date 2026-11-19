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
