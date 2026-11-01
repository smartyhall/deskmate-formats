"""Fixed native-code observations; no inferred API names or runtime execution."""
import importlib.util
import os
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location(
    'inspect_structure', Path(__file__).resolve().parents[2] / 'tools/inspect_structure.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

PROFILES = (
    ('FILER.PDM', 0x8770, 0xe88, 0xfa6, 0x6c67, 0x740d),
    ('ADDRESS.PDM', 0xbdd0, 0x28a6, 0x29c4, 0xa1e5, 0xa9b9),
    ('CALENDAR.PDM', 0xea70, 0x2944, 0x2a62, 0xd7e5, 0xde9f),
)


class DatabaseBindingObservations(unittest.TestCase):
    def data(self, name):
        return (Path(os.environ['DOSLAB_ROOT']) /
                'EXPERIMENTS/FILER/F00_baseline/before/files/DESKMATE' / name).read_bytes()

    def test_named_binding_arguments_and_interrupt(self):
        for name, base, label, slot, start, _ in PROFILES:
            with self.subTest(file=name):
                b = self.data(name)
                self.assertEqual(b[base + label:base + label + 5], b'DMDB\0')
                self.assertEqual(b[start + 4:start + 8], bytes((0x8c, 0xd8, 0x8e, 0xc0)))
                self.assertEqual(b[start + 8:start + 11], bytes((0xbb,)) + struct.pack('<H', slot))
                self.assertEqual(b[start + 11:start + 14], bytes((0xba,)) + struct.pack('<H', label))
                self.assertEqual(b[start + 19:start + 22], bytes((0xb8, 6, 2)))
                self.assertEqual(b[start + 24:start + 27], bytes((0xb8, 12, 2)))
                self.assertEqual(b[start + 27:start + 30], bytes((0xcd, 0xe0, 0xc3)))

    def test_same_slot_in_stack_marshalling_call_thunks(self):
        for name, _, _, slot, _, start in PROFILES:
            with self.subTest(file=name):
                b = self.data(name)
                # SS -> BX -> ES, BP+4 -> BX, then a far-indirect call.
                self.assertEqual(b[start + 5:start + 14],
                                 bytes((0x8c, 0xd3, 0x8e, 0xc3, 0x8b, 0xdd, 0x83, 0xc3, 4)))
                self.assertEqual(b[start + 14:start + 18], bytes((0xff, 0x1e)) + struct.pack('<H', slot))
                self.assertEqual(b[start + 18:start + 22], bytes((0x5b, 7, 0x5d, 0xc3)))

    def test_stub_reader_name_and_pointer_slot(self):
        b = self.data('DMDB.R89')
        self.assertEqual(b[0x200:0x205], bytes((0xb8, 0x1f, 0, 0x8e, 0xd8)))
        self.assertEqual(b[0x425:0x42c], b'DMDBRD\0')
        self.assertEqual(b[0x305:0x310], bytes((0xba, 0x35, 0, 0xbb, 0x48, 0, 0xb8, 6, 2, 0xcd, 0xe0)))
        for site in (0x2e9, 0x3b8):
            self.assertEqual(b[site:site + 4], bytes((0xff, 0x1e, 0x48, 0)))

    def test_reader_descriptor_callbacks_are_relocated(self):
        b = self.data('DMDBRD.RES')
        self.assertEqual(b[0x52e2:0x52ea], b'DMDBRD\0\0')
        for pointer, expected in ((0x52ea, 0x4edb), (0x52ee, 0x4e92)):
            r = probe.resolve_mz_far(b, pointer)
            self.assertTrue(r['segment_has_mz_relocation'])
            self.assertEqual(r['target_file_offset_candidate'], expected)

    def test_reader_named_follow_on_components_and_slots(self):
        b = self.data('DMDBRD.RES')
        self.assertEqual(b[0x51b4:0x51c4], b'DMDBUPD\0DMDBBLD\0')
        for start, slot, label in ((0x1ad8, 0x128, 0x134), (0x1b29, 0x130, 0x13c)):
            self.assertEqual(b[start + 9:start + 12], bytes((0xbb,)) + struct.pack('<H', slot))
            self.assertEqual(b[start + 12:start + 15], bytes((0xba,)) + struct.pack('<H', label))
        self.assertEqual(b[0x1b64:0x1b69], bytes((0xb8, 6, 2, 0xcd, 0xe0)))
