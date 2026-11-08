"""Hash-pinned static insertion anchors; these do not execute DeskMate.

Set DESKMATE_REFERENCE_EXTRACTED to the preserved oldskool/extracted root.
No commercial bytes, Capstone dependency, emulator or native file is bundled.
"""
import hashlib
import os
from pathlib import Path
import struct
import unittest


IDENTITIES = {
    'ADDRESS.PDM': 'ef685b20e259f0932378668d9b120882468dc0da157a015e2df95d4ce61a60fb',
    'DMDBRD.RES': 'c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee',
    'DMDBUPD.RES': '9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f',
}


class AddressBookInsertionSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('DESKMATE_REFERENCE_EXTRACTED')
        if not root:
            raise unittest.SkipTest('Set DESKMATE_REFERENCE_EXTRACTED')
        cls.inputs = {}
        for name, digest in IDENTITIES.items():
            data = (Path(root) / 'deskmate' / 'dm305dk4' / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise AssertionError('source identity mismatch: ' + name)
            cls.inputs[name] = data

    def call(self, name, at, target):
        data = self.inputs[name]
        self.assertEqual(data[at], 0xE8, hex(at))
        self.assertEqual((at + 3 + struct.unpack_from('<h', data, at + 1)[0]) & 0xFFFF,
                         target, hex(at))

    def anchor(self, name, at, raw):
        raw = bytes.fromhex(raw)
        self.assertEqual(self.inputs[name][at:at + len(raw)], raw, hex(at))

    def test_add_menu_and_selector_transport(self):
        data = self.inputs['ADDRESS.PDM']
        # Menu item's event word and DS-relative label pointer; CS jump table.
        self.assertEqual(struct.unpack_from('<HHH', data, 0xC1DD), (0xF582, 0, 0xE90))
        self.assertEqual(data[0xBDD0 + 0xE90:0xBDD0 + 0xE90 + 3], b'Add')
        self.assertEqual(struct.unpack_from('<H', data, 0xCCC)[0] + 0x200, 0xAA0)
        for at, target in ((0xAA0, 0x3B5F), (0x7A5, 0x3A44), (0x3B2A, 0x43F5),
                           (0x45C6, 0x8C05), (0x8C13, 0xF38),
                           (0xF47, 0x9A3E), (0x9A99, 0xA9B9)):
            self.call('ADDRESS.PDM', at, target)
        self.anchor('ADDRESS.PDM', 0x8C0F, 'b80700')  # ADD_ROW, not UPDATE_ROW
        self.anchor('ADDRESS.PDM', 0xA9C7, 'ff1ec429')

    def test_descriptor_ordinals_and_full_field_comparison(self):
        self.call('DMDBRD.RES', 0x2268, 0x43B6)
        self.anchor('DMDBRD.RES', 0x2261, 'b80900')  # descriptor field nine
        self.anchor('DMDBRD.RES', 0x2275, '8d440c')  # table sort-ordinal array
        self.call('DMDBUPD.RES', 0x2044, 0x11C8)
        self.call('DMDBUPD.RES', 0x213C, 0x1BFC)
        for at in (0x1C12, 0x1C28):
            self.call('DMDBUPD.RES', at, 0x29E5)  # both rows' complete fields
        self.call('DMDBUPD.RES', 0x1C3F, 0x2942)
        self.anchor('DMDBUPD.RES', 0x29B9, '807efa43')  # C has separate comparison
        self.call('DMDBUPD.RES', 0x299E, 0x33CB)  # K/default -> reader callback 2C
        self.assertEqual(struct.unpack_from('<H', self.inputs['DMDBRD.RES'],
                                           0x482B + 2 * 0x2C)[0] + 0x200, 0x4502)
        self.anchor('DMDBRD.RES', 0x450E, '36c51e4401')  # collation table

    def test_prefix_limit_and_equal_key_branch(self):
        # Distinguishes a routing prefix from truncating the actual row comparison.
        self.anchor('DMDBUPD.RES', 0x121A, '3d0a00')
        self.anchor('DMDBUPD.RES', 0x121F, 'b80900')
        self.anchor('DMDBUPD.RES', 0x1246, 'c60701')
        self.call('DMDBUPD.RES', 0x276B, 0x2942)
        self.anchor('DMDBUPD.RES', 0x2773, '7e0b')  # <= searches earlier; no ID tie-break here
        self.anchor('DMDBUPD.RES', 0x27F8, '8946fe')
        self.anchor('DMDBUPD.RES', 0x27FB, '836efc06')  # shift triples by six

    def test_row_id_and_descriptor_update(self):
        for at, target in ((0x25E, 0x2B0), (0x340, 0x1277), (0x394, 0x30A8),
                           (0x13B9, 0x1F8E), (0x13F2, 0x3001)):
            self.call('DMDBUPD.RES', at, target)
        self.anchor('DMDBUPD.RES', 0x36D, 'b80100')  # ordinary ID increment
        self.anchor('DMDBUPD.RES', 0x38B, 'b80700')  # descriptor update operation
        self.anchor('DMDBUPD.RES', 0x3111, 'b80700')  # descriptor next-ID ordinal
        self.call('DMDBUPD.RES', 0x3105, 0x2E3F)  # ASCII count increment
