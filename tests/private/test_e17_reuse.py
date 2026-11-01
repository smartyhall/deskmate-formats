"""E17 original-fixture assertions; no fixture is written or distributed."""
from pathlib import Path
import hashlib,os,struct,unittest
from deskmate_formats.calendar.personal import CalendarParseError,parse_bytes
from deskmate_formats.calendar.writer import append_appointment


class E17EvidenceTests(unittest.TestCase):
    def fixtures(self):
        root=Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/PHASE2'
        before=(root/'E17_deleted_reuse/before/files/DESKMATE/PERSONAL.CLN').read_bytes()
        after=(root/'E17_deleted_reuse/after/files/DESKMATE/PERSONAL.CLN').read_bytes()
        preflight=(root/'E15_data_page_boundary/pre_after/files/DESKMATE/PERSONAL.CLN').read_bytes()
        return before,after,preflight

    def test_complete_observed_delta(self):
        before,after,_=self.fixtures()
        self.assertEqual((len(before),len(after)),(7168,7168))
        self.assertEqual(hashlib.sha256(before).hexdigest(),'818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea')
        self.assertEqual(hashlib.sha256(after).hexdigest(),'a220b4657e85e0d9986975ca6ab741296f986ed617326a26b2cf73e1bde0bae1')
        expected=[0x439,0x443,0x1482,0x1484,0x1486,0x148a,0x148c,0x148e,0x1490,0x1492,*range(0x1818,0x1831)]
        self.assertEqual([i for i,(a,b) in enumerate(zip(before,after)) if a!=b],expected)
        self.assertEqual(after[0x435:0x43a],b'00018')
        self.assertEqual(after[0x43b:0x43e],b'001')
        self.assertEqual(after[0x43f:0x444],b'00035')

    def test_append_and_originals_preserved(self):
        before,after,preflight=self.fixtures()
        self.assertEqual(after[0x1800:0x1818],before[0x1800:0x1818])
        self.assertEqual(after[0x1800],0x44)
        self.assertEqual(struct.unpack_from('<HHH',after,0x1482),(6,24,0x22))
        self.assertEqual(after[0x1818:0x181a],bytes([0x80,0x22]))
        self.assertEqual(after[0x1827:0x182e],b'REUSE17')
        self.assertEqual(after[0x182e:0x1831],bytes([1,2,3]))
        self.assertEqual(after[0x1831:],bytes(975))
        triples=[struct.unpack_from('<HHH',after,0x1428+6*i) for i in range(18)]
        self.assertNotIn(0x21,[entry[2] for entry in triples])
        originals=parse_bytes(preflight)
        self.assertEqual([e for e in triples if e[2]!=0x22],[(4,r.offset-4096,r.record_id) for r in originals.records])
        for r in originals.records:
            self.assertEqual(after[r.offset:r.offset+r.length],bytes.fromhex(r.raw_hex))
        self.assertEqual(after[:1024],before[:1024])
        self.assertEqual(after[2048:5120],before[2048:5120])

    def test_production_scope_remains_conservative(self):
        before,after,_=self.fixtures()
        for data in (before,after):
            for operation in (parse_bytes,append_appointment):
                with self.subTest(operation=operation.__name__),self.assertRaises(CalendarParseError) as caught:
                    operation(data)
                self.assertEqual(caught.exception.code,'unsupported_layout')
