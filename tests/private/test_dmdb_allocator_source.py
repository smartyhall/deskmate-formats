"""Pinned, offline instruction/data anchors; no emulator or commercial Git inputs.

Set DESKMATE_REFERENCE_EXTRACTED to the preserved oldskool/extracted directory.
These assertions identify static paths, not executed native branches.
"""
import hashlib
import os
from pathlib import Path
import struct
import unittest


class AllocatorSourceAnchors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('DESKMATE_REFERENCE_EXTRACTED')
        if not root:
            raise unittest.SkipTest('Set DESKMATE_REFERENCE_EXTRACTED')
        root = Path(root)
        identities = {
            'sdk-3.03/Development-Disk-1/DMDB.H': '47c2ff4638d8ab1bcc12aeab3e2dd5b51ccfeef9bbddb1a014912c831df4d5aa',
            'sdk-3.03/Development-Disk-1/DMDB.INC': '2ea33422d68ab2402ca2b83a1c1f5d7fee80db9c36000a8609d42712ce299a29',
            'deskmate/dm305dk4/DMDB.R89': '799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f',
            'deskmate/dm305dk4/DMDBRD.RES': 'c4bc9f5699bfaf1ac5adb57a011b04dcec00a2ae75edb2baf603c8001fa99cee',
            'deskmate/dm305dk4/DMDBUPD.RES': '9e77a2081ebb3a9549903f5d337580c65d6e0a3f603185064d4c82e16327cf4f',
        }
        cls.inputs = {}
        for rel, digest in identities.items():
            data = (root / rel).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise AssertionError('source identity mismatch: ' + rel)
            cls.inputs[Path(rel).name] = data

    def test_reader_callback_table(self):
        data = self.inputs['DMDBRD.RES']
        # CS offsets, with the independently verified MZ header added.
        for selector, target in ((0x16, 0x4058), (0x17, 0x40AA),
                                 (0x19, 0x45AB), (0x32, 0x43E3), (0x35, 0x4575)):
            self.assertEqual(struct.unpack_from('<H', data, 0x482B + 2 * selector)[0] + 0x200, target)
        self.assertEqual(data[0x48B1:0x48B5], bytes.fromhex('81c32b46'))

    def test_page_allocation_and_packing_operands(self):
        data = self.inputs['DMDBUPD.RES']
        for at, raw in ((0x1906, 'b8f80f'), (0x190D, 'e86800'),
                        (0x1933, 'e84200'), (0x1995, 'f6460401'),
                        (0x19A6, '80e1f0'), (0x19D7, '80e10f'),
                        (0x1AA6, 'b8ff0f'), (0x1ADE, 'e86618'),
                        (0x1AF2, '3dff0f'), (0x1AF7, 'b80004'),
                        (0x2F96, 'c746fc2000'), (0x2FA0, 'c746f8e003')):
            self.assertEqual(data[at:at + len(bytes.fromhex(raw))], bytes.fromhex(raw), hex(at))

    def test_add_row_path_and_space_guard(self):
        data = self.inputs['DMDBUPD.RES']
        for at, raw in ((0x235, '83f907'), (0x25E, 'e84f00'),
                        (0x340, 'e8340f'), (0x12E4, '050400'),
                        (0x12ED, 'e81c01'), (0x12F6, '7d45'),
                        (0x12FE, 'e8e405'), (0x137C, 'c60703'),
                        (0x141F, '2dff03'), (0x3039, 'b80004')):
            self.assertEqual(data[at:at + len(bytes.fromhex(raw))], bytes.fromhex(raw), hex(at))

    def test_new_page_initialization_and_decimal_counter(self):
        reader = self.inputs['DMDBRD.RES']
        for at, raw in ((0x3C32, '3d4e00'), (0x3C3F, 'b80004'),
                        (0x3C4F, 'c60703'), (0x43F3, '2b4604')):
            self.assertEqual(reader[at:at + len(bytes.fromhex(raw))], bytes.fromhex(raw), hex(at))
        update = self.inputs['DMDBUPD.RES']
        for at, raw in ((0x30E9, 'bb0500'), (0x3111, 'b80700'),
                        (0x2F35, 'b90a00'), (0x2F3A, '80c230')):
            self.assertEqual(update[at:at + len(bytes.fromhex(raw))], bytes.fromhex(raw), hex(at))
