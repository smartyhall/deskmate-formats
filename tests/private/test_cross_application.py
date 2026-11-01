"""Opt-in fixed observations; these tests do not implement a Filer reader."""
import hashlib
import importlib.util
import os
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'inspect_structure', Path(__file__).resolve().parents[2] / 'tools/inspect_structure.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class CrossApplicationObservations(unittest.TestCase):
    def setUp(self):
        self.root = Path(os.environ['DOSLAB_ROOT'])
        self.base = self.root / 'EXPERIMENTS/FILER/F00_baseline/before/files/DESKMATE'

    def test_complete_self_schema_region(self):
        for name in ('PERSONAL.CLN', 'PERSONAL.ADR', 'CARMAINT.FIL', 'INVNTORY.FIL'):
            with self.subTest(file=name):
                b = (self.base / name).read_bytes()
                self.assertEqual(hashlib.sha256(b[0x800:0x898]).hexdigest(),
                                 '090cfee8845b005925fd79a7dfce21362976239a08d02dc7061b84928316c353')

    def test_all_known_table_indexes_and_zero_sentinels(self):
        # Explicit fixture-specific index pages/counts, not discovery rules.
        profiles = {'PERSONAL.CLN': ((3, 13), (5, 6)),
                    'PERSONAL.ADR': ((3, 27), (5, 0), (7, 15), (9, 1)),
                    'CARMAINT.FIL': ((3, 28), (5, 22), (7, 4), (9, 0)),
                    'INVNTORY.FIL': ((3, 26), (5, 20), (7, 3), (11, 3))}
        for name, tables in profiles.items():
            b = (self.base / name).read_bytes()
            for page, count in tables:
                with self.subTest(file=name, page=page):
                    self.assertEqual(b[page * 1024:page * 1024 + 40], probe.INDEX_HEADER)
                    entries = probe.inspect_triples(b, page * 1024 + 40, count + 1)['entries']
                    self.assertTrue(entries[-1]['zero_tuple'])
                    self.assertTrue(all(e['low_id_prefix_matches'] for e in entries[:-1]))
                    self.assertEqual(len(set(e['target'] for e in entries[:-1])), count)

    def test_inventory_retired_layout_candidates_and_counter_exception(self):
        b = (self.base / 'INVNTORY.FIL').read_bytes()
        entries = probe.inspect_triples(b, 0x1428, 20)['entries']
        targets = {e['target'] for e in entries}
        for start, end, rid in ((0x10f0, 0x111a, 0x16), (0x1196, 0x11c0, 0x1a)):
            self.assertEqual(b[start:start + 2], bytes((0x44, rid)))
            self.assertEqual(b[end - 2:end], bytes((1, 2)))
            self.assertNotIn(start, targets)
        self.assertEqual(b[0x43a:0x43d], b'002')
        # DBCOLS token cannot universally be max extant schema ID + 1.
        self.assertEqual(b[0x418:0x41d], b'00022')
        ids = probe.inspect_triples(b, 0xc28, 26)['entries']
        self.assertEqual(max(e['id_candidate'] for e in ids), 0x29)

    def test_native_addressbook_mutations_keep_self_schema(self):
        reference = (self.base / 'PERSONAL.ADR').read_bytes()[0x800:0x898]
        for case in ('A01_contact', 'A02_longer_name', 'PHASE2/A03_work_phone', 'PHASE2/A04_city'):
            b = (self.root / 'EXPERIMENTS/ADDRESSBOOK' / case /
                 'after/files/DESKMATE/PERSONAL.ADR').read_bytes()
            self.assertEqual(b[0x800:0x898], reference)
            entry = probe.inspect_triples(b, 0x1428, 1)['entries'][0]
            self.assertEqual((entry['target'], entry['id_candidate']), (0x1000, 0x10))

    def test_filer_populated_and_empty_data_candidates(self):
        empty = (self.base / 'CARMAINT.FIL').read_bytes()
        filled = (self.base / 'INVNTORY.FIL').read_bytes()
        self.assertEqual(empty[0x2000:0x2400], bytes((3,)) + bytes(1023))
        self.assertEqual(empty[0x2428:0x242e], bytes(6))
        entries = probe.inspect_triples(filled, 0x2c28, 3)['entries']
        self.assertEqual([e['target'] for e in entries], [0x2800, 0x291e, 0x29d2])
        self.assertEqual([e['id_candidate'] for e in entries], [0x10, 0x11, 0x12])
        for e in entries:
            end = filled.index(bytes((1, 2)), e['target'], 0x2c00)
            self.assertEqual(len(filled[e['target'] + 2:end].split(bytes((1,)))), 5)
