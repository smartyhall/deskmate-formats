"""Fixed evidence for one Calendar request; no runtime API semantics asserted."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location(
    'inspect_structure', Path(__file__).resolve().parents[2] / 'tools/inspect_structure.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class LookupTraceObservations(unittest.TestCase):
    def setUp(self):
        self.lab = Path(os.environ['DOSLAB_ROOT'])
        self.b = (self.lab / 'EXPERIMENTS/FILER/F00_baseline/before/files/DESKMATE/CALENDAR.PDM').read_bytes()

    def test_image_and_selected_stack_arguments(self):
        self.assertEqual(hashlib.sha256(self.b).hexdigest(),
                         '819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23')
        self.assertEqual(self.b[0xa021:0xa02c],
                         bytes((0x2b, 0xc0, 0x50, 0x8d, 0x46, 0xec, 0x50, 0xb8, 0x0b, 0, 0x50)))

    def test_predicate_operands_match_existing_native_control_row(self):
        b = self.b
        self.assertEqual(b[0x10926:0x10932], b'Description\0')
        self.assertEqual(b[0x10996:0x1099f], b'Date>   \0')
        self.assertEqual(b[0x10a90:0x10a94], bytes((0x20, 0x20, 0xff, 0)))
        self.assertEqual(b[0x9ff9:0x9ffe], bytes((0xc6, 6, 0x2a, 0x1f, 0x3d)))
        native = (self.lab / 'EXPERIMENTS/PHASE2/E00_default/files/DESKMATE/PERSONAL.CLN').read_bytes()
        self.assertEqual(hashlib.sha256(native).hexdigest(),
                         'c556b7f57102fc5432ce926317c8c0aa95cf8992d7fb64a72e2f270e4c517890')
        self.assertEqual(native[0x1002:0x1005], b[0x10a90:0x10a93])
        self.assertEqual(native[0x1428:0x142e], bytes((4, 0, 0, 0, 0x10, 0)))

    def test_exact_relative_edges_and_zero_flag_branch(self):
        for at, expected in ((0xa006, 0xe296), (0xa02c, 0xcdf8),
                             (0xce0e, 0xd6ce), (0xd6f4, 0xde9f)):
            self.assertEqual(self.b[at], 0xe8)
            self.assertEqual(at + 3 + struct.unpack_from('<h', self.b, at + 1)[0], expected)
        self.assertEqual(self.b[0xcdfe:0xce04], bytes((0x83, 0x7e, 8, 1, 0x75, 4)))
        self.assertEqual(self.b[0xce08:0xce0e], bytes((0xff, 0x76, 6, 0xff, 0x76, 4)))

    def test_transport_and_return_word_observations(self):
        self.assertEqual(self.b[0xd6df:0xd6eb],
                         bytes((0x8b, 0x46, 4, 0xa3, 0x52, 0x2a, 0x8b, 0x46, 6, 0xa3, 0x54, 0x2a)))
        self.assertEqual(self.b[0xd6eb:0xd6f4], bytes((0x2b, 0xc0, 0x50, 0x50, 0xb8, 0x5a, 0x2a, 0x1e, 0x50)))
        self.assertEqual(self.b[0xa032:0xa03b], bytes((0x89, 0x46, 0xfe, 0x8b, 0x46, 0xf8, 0xa3, 0xd0, 0x66)))

    def test_first_unresolved_slot_and_advertised_callbacks(self):
        self.assertEqual(self.b[0xdead:0xdeb1], bytes((0xff, 0x1e, 0x62, 0x2a)))
        self.assertEqual(self.b[0x114d2:0x114d6], bytes((0xcd, 0xab, 0xba, 0xdc)))
        unresolved = probe.resolve_mz_far(self.b, 0x114d2)
        self.assertFalse(unresolved['segment_has_mz_relocation'])
        self.assertIsNone(unresolved['target_file_offset_candidate'])
        for pointer, target in ((0x114ca, 0xea4c), (0x114ce, 0xea5d)):
            result = probe.resolve_mz_far(self.b, pointer)
            self.assertTrue(result['segment_has_mz_relocation'])
            self.assertEqual(result['target_file_offset_candidate'], target)
