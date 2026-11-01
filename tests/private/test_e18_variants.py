"""Private E18 observations; fixtures are never modified or distributed."""
from pathlib import Path
import hashlib, os, struct, unittest
from deskmate_formats.calendar.personal import CalendarParseError, parse_bytes
from deskmate_formats.calendar.writer import append_appointment

CASES = [
    ('E18_short3', b'S18', 20, 'cda46df771e8214b0a3484123da57359ff3143d7c947423e93f1e5f853725a2d'),
    ('E18_long20', b'LONG18' + b'X'*14, 37, '736a9441eb8b691c58b7fa0deb1b181e408646c893d9f3cd9df11059e3d8662f'),
]

class E18EvidenceTests(unittest.TestCase):
    def fixtures(self):
        root = Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/PHASE2'
        for name, description, length, digest in CASES:
            d = root/name
            yield name, description, length, digest, (d/'before/files/DESKMATE/PERSONAL.CLN').read_bytes(), (d/'after/files/DESKMATE/PERSONAL.CLN').read_bytes()

    def test_all_changed_positions_and_hashes(self):
        for name, desc, length, digest, before, after in self.fixtures():
            with self.subTest(case=name):
                self.assertEqual(hashlib.sha256(before).hexdigest(), '818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea')
                self.assertEqual(hashlib.sha256(after).hexdigest(), digest)
                self.assertEqual((len(before), len(after)), (7168,7168))
                expected = [0x439,0x443,0x1482,0x1484,0x1486,0x148a,0x148c,0x148e,0x1490,0x1492,*range(0x1818,0x1818+length+1)]
                self.assertEqual([i for i,(a,b) in enumerate(zip(before,after)) if a!=b], expected)
                self.assertEqual(after[0x1827:0x1827+len(desc)], desc)
                self.assertEqual(after[0x435:0x43a], b'00018')
                self.assertEqual(after[0x43b:0x43e], b'001')
                self.assertEqual(after[0x43f:0x444], b'00035')

    def test_retired_and_original_records_not_reused(self):
        root=Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/PHASE2'
        originals=parse_bytes((root/'E15_data_page_boundary/pre_after/files/DESKMATE/PERSONAL.CLN').read_bytes())
        for name, _, length, _, before, after in self.fixtures():
            with self.subTest(case=name):
                self.assertEqual(after[0x1800:0x1818], before[0x1800:0x1818])
                self.assertEqual(after[0x1800], 0x44)
                self.assertEqual(struct.unpack_from('<HHH',after,0x1482),(6,24,0x22))
                self.assertEqual(after[0x1818:0x181a], bytes([0x80,0x22]))
                end=0x1818+length
                self.assertEqual(after[end-2:end+1], bytes([1,2,3]))
                self.assertEqual(after[end+1:], bytes(len(after)-end-1))
                triples=[struct.unpack_from('<HHH',after,0x1428+i*6) for i in range(18)]
                self.assertNotIn(0x21,[t[2] for t in triples])
                self.assertEqual([t for t in triples if t[2]!=0x22],[(4,r.offset-4096,r.record_id) for r in originals.records])
                for r in originals.records:
                    self.assertEqual(after[r.offset:r.offset+r.length], bytes.fromhex(r.raw_hex))

    def test_production_still_rejects_seven_pages(self):
        for name, _, _, _, before, after in self.fixtures():
            for data in (before,after):
                for operation in (parse_bytes,append_appointment):
                    with self.subTest(case=name,operation=operation.__name__), self.assertRaises(CalendarParseError) as caught:
                        operation(data)
                    self.assertEqual(caught.exception.code,'unsupported_layout')
