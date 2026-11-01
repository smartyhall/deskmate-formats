"""Independent synthetic probes for bounds, alignment and candidate arithmetic."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'inspect_structure', Path(__file__).resolve().parents[2] / 'tools/inspect_structure.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class StructuralProbeTests(unittest.TestCase):
    def test_independent_regions_and_half_open_differences(self):
        r = probe.compare_regions(b'xxABC00D', b'ABC11Dtail', 2, 0, 6)
        self.assertEqual(r['equal_bytes'], 4)
        self.assertEqual(r['differences'], [dict(start_relative=3, end_relative=5,
                         left_offset=5, right_offset=3, left_hex='3030', right_hex='3131')])
        self.assertTrue(probe.compare_regions(b'a', b'xxa', 0, 2, 1)['equal'])

    def test_bounds_never_silently_truncate(self):
        for offset, size in [(-1, 1), (0, -1), (1, 1)]:
            with self.subTest(offset=offset, size=size), self.assertRaises(ValueError):
                probe.compare_regions(b'a', b'a', offset, 0, size)
        self.assertTrue(probe.compare_regions(b'', b'', 0, 0, 0)['equal'])
        with self.assertRaises(ValueError):
            probe.inspect_triples(b'12345', 0, 1)

    def test_triples_check_location_prefix_and_do_not_stop_at_zero(self):
        b = bytearray(192)
        struct.pack_into('<HHH', b, 0, 2, 7, 0x15)
        struct.pack_into('<HHH', b, 12, 1, 64, 0x16)
        struct.pack_into('<HHH', b, 18, 3, 0, 0x100)
        b[135:137] = bytes((0x80, 0x15))
        r = probe.inspect_triples(bytes(b), 0, 4, 64)['entries']
        self.assertEqual(r[0]['target'], 135)
        self.assertTrue(r[0]['low_id_prefix_matches'])
        self.assertTrue(r[1]['zero_tuple'])
        self.assertFalse(r[2]['target_in_bounds'])
        self.assertIsNone(r[3]['low_id_prefix_matches'])
        with self.assertRaises(ValueError):
            probe.inspect_triples(b, 0, 1, 0)

    def test_block_map_preserves_partial_tail_and_empty_input(self):
        self.assertEqual(probe.block_map(b''), [])
        r = probe.block_map(bytes((0, 1, 0, 2, 3)), 4)
        self.assertEqual([(x['offset'], x['length'], x['nonzero_bytes']) for x in r],
                         [(0, 4, 2), (4, 1, 1)])
        with self.assertRaises(ValueError):
            probe.block_map(b'', 0)

    def test_cli_json_and_input_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'synthetic.bin'
            p.write_bytes(b'012345')
            before = (p.read_bytes(), p.stat().st_mtime_ns)
            for args in [('blocks', str(p)),
                         ('compare', str(p), str(p), '--left-offset', '0',
                          '--right-offset', '0', '--length', '0x6'),
                         ('triples', str(p), '--offset', '0', '--count', '1')]:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    probe.main(args)
                self.assertEqual(json.loads(out.getvalue())['inputs'][0]['size'], 6)
            self.assertEqual(before, (p.read_bytes(), p.stat().st_mtime_ns))
