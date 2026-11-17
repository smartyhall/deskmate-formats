"""Hash-pinned static index/creation anchors; no DeskMate execution or ROMs.

Opt in with DESKMATE_REFERENCE_EXTRACTED. Short instruction operands and numeric
tables identify original paths, not a bundled disassembly or runtime trace.
"""
import hashlib
import os
from pathlib import Path
import struct
import unittest


class MulticalendarSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('DESKMATE_REFERENCE_EXTRACTED')
        if not root:
            raise unittest.SkipTest('Set DESKMATE_REFERENCE_EXTRACTED')
        inputs = {
            'CALENDAR.PDM': ('deskmate/dm305dk4/CALENDAR.PDM', '819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23'),
            'DMDBRD.RES': ('deskmate/dm305dk4/DMDBRD.RES', 'c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee'),
            'DMDBUPD.RES': ('deskmate/dm305dk4/DMDBUPD.RES', '9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f'),
            'DMDBBLD.RES': ('deskmate/dm305dk5/DMDBBLD.RES', '91ada27c026de823aef6a9aae541bafcb6a312552cc5bd612ec8b0e90e53aeed'),
        }
        cls.inputs = {}
        for name, (relative, sha) in inputs.items():
            data = (Path(root) / relative).read_bytes()
            if hashlib.sha256(data).hexdigest() != sha:
                raise AssertionError('source identity mismatch: ' + name)
            cls.inputs[name] = data

    def anchor(self, name, at, raw):
        raw = bytes.fromhex(raw)
        self.assertEqual(self.inputs[name][at:at + len(raw)], raw, hex(at))

    def call(self, name, at, target):
        data = self.inputs[name]
        self.assertEqual(data[at], 0xE8)
        self.assertEqual((at + 3 + struct.unpack_from('<h', data, at + 1)[0]) & 0xFFFF, target)

    def test_four_subdivision_offsets_and_native_full_slot(self):
        self.assertEqual(struct.unpack_from('<4H', self.inputs['DMDBRD.RES'], 0x5120),
                         (40, 286, 532, 778))
        self.anchor('DMDBUPD.RES', 0x2A5C, '814604f000')  # last slot +240
        self.anchor('DMDBUPD.RES', 0x3081, '81c6f000')
        self.anchor('DMDBUPD.RES', 0x3085, 'bf2800')  # scan back 40 slots
        self.anchor('DMDBUPD.RES', 0x308A, '83ee06')

    def test_route_rebuilt_from_terminal_row_with_ten_byte_prefix(self):
        self.call('DMDBUPD.RES', 0x285F, 0x3076)  # last locator, not first
        self.call('DMDBUPD.RES', 0x288D, 0x23C6)  # get terminal row
        self.call('DMDBUPD.RES', 0x28A0, 0x11C8)  # build routing prefix
        self.anchor('DMDBUPD.RES', 0x121A, '3d0a00')
        self.anchor('DMDBUPD.RES', 0x121F, 'b80900')
        self.anchor('DMDBUPD.RES', 0x1246, 'c60701')
        self.anchor('DMDBUPD.RES', 0x1266, 'c60700')
        self.call('DMDBUPD.RES', 0x20F4, 0x16C5)
        self.call('DMDBUPD.RES', 0x213C, 0x1BFC)  # full-row fallback after prefix tie

    def test_split_half_copy_operands_are_not_a_general_balancing_proof(self):
        self.anchor('DMDBUPD.RES', 0x1C8C, '837e0c7e')  # 126-byte half copy
        self.anchor('DMDBUPD.RES', 0x1C92, '83c678')  # source +120 = slot 20
        self.anchor('DMDBUPD.RES', 0x1C98, 'b8f600')  # clear 246-byte destination
        self.anchor('DMDBUPD.RES', 0x2CD9, 'b87e00')
        self.call('DMDBUPD.RES', 0x2CEB, 0x1C46)

    def test_create_selector_and_character_comparison(self):
        self.anchor('DMDBBLD.RES', 0x218, '83f904')
        self.call('DMDBBLD.RES', 0x239, 0x286)
        # C byte comparison folds only a..z, then subtracts unsigned bytes.
        for at, raw in ((0x434D, '807e0461'), (0x4353, '807e047a'),
                        (0x4359, '8066045f'), (0x4370, '2ae4'), (0x4377, '2bc1')):
            self.anchor('DMDBRD.RES', at, raw)

    def test_close_configuration_update_is_separate_from_user_event_update(self):
        # Reverified existing SDK crosswalk: close invokes the three-field
        # config updater, selector 19, before selector 9 table close. Not a
        # trace of loaded runtime targets or proof of disk flush timing.
        self.call('CALENDAR.PDM', 0xA101, 0x9F6D)
        self.anchor('CALENDAR.PDM', 0x9F79, 'c746e80300')
        self.anchor('CALENDAR.PDM', 0x9F93, 'c746ec0000')
        self.anchor('CALENDAR.PDM', 0x9FB3, 'c646f200')
        self.anchor('CALENDAR.PDM', 0x9FBF, 'b81300')
        self.call('CALENDAR.PDM', 0x9FC3, 0xCDF8)
        self.anchor('CALENDAR.PDM', 0xA12C, 'b80900')

    def test_full_slot_guard_precedes_split_and_route_rebuild(self):
        self.anchor('DMDBUPD.RES', 0x2A5C, '814604f000')
        self.anchor('DMDBUPD.RES', 0x2A64, '833f00')
        self.call('DMDBUPD.RES', 0x2197, 0x2A59)
        self.anchor('DMDBUPD.RES', 0x219F, '7403')
        self.call('DMDBUPD.RES', 0x21B3, 0x2A72)
        self.call('DMDBUPD.RES', 0x21D2, 0x284A)
        self.call('DMDBUPD.RES', 0x2CC8, 0x1C46)
        self.call('DMDBUPD.RES', 0x2CEB, 0x1C46)
