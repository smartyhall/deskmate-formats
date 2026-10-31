"""E16 private fixture assertions; no original file is written or normalized."""
from pathlib import Path
import hashlib,os,struct,unittest
from deskmate_formats.calendar.personal import CalendarParseError,parse_bytes
from deskmate_formats.calendar.writer import append_appointment


class E16EvidenceTests(unittest.TestCase):
    def fixtures(self):
        root=Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/PHASE2'
        return ((root/'E15_data_page_boundary/after/files/DESKMATE/PERSONAL.CLN').read_bytes(),
                (root/'E15_data_page_boundary/pre_after/files/DESKMATE/PERSONAL.CLN').read_bytes(),
                (root/'E16_page_reclamation/after/files/DESKMATE/PERSONAL.CLN').read_bytes())

    def test_complete_e15_to_e16_delta(self):
        before,_,after=self.fixtures()
        expected=bytearray(before)
        expected[0x439]=ord('7')
        expected[0x43d]=ord('1')
        expected[0x1482:0x148e]=before[0x1488:0x1494]
        expected[0x148e:0x1494]=bytes(6)
        expected[0x1800]=0x44
        self.assertEqual(after,expected)
        self.assertEqual((len(before),len(after)),(7168,7168))
        self.assertEqual(sum(a!=b for a,b in zip(before,after)),11)
        self.assertEqual(hashlib.sha256(after).hexdigest(),'818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea')

    def test_live_records_stable_and_retired_payload_not_erased(self):
        before,preflight,after=self.fixtures()
        self.assertEqual(after[0x1801:],before[0x1801:])
        self.assertEqual(after[0x1818],3)
        self.assertEqual(after[0x1819:],bytes(999))
        self.assertIn(b'BOUND12',after[0x1800:])
        self.assertEqual(after[:1024],before[:1024])
        self.assertEqual(after[2048:5120],before[2048:5120])
        self.assertEqual(after[5120:6144],preflight[5120:6144])
        db=parse_bytes(preflight)
        entries=[struct.unpack_from('<HHH',after,r.index_offset) for r in db.records]
        self.assertEqual(entries,[(4,r.offset-4096,r.record_id) for r in db.records])
        self.assertNotIn(0x21,[entry[2] for entry in entries])
        for r in db.records:
            raw=bytes.fromhex(r.raw_hex)
            self.assertEqual(after[r.offset:r.offset+r.length],raw)
            self.assertEqual(after.count(raw),1)

    def test_no_binary_restoration_and_runtime_remains_conservative(self):
        _,preflight,after=self.fixtures()
        self.assertNotEqual(after,preflight)
        differences=[i for i,(a,b) in enumerate(zip(preflight,after)) if a!=b]
        self.assertEqual(differences,[0x26,0x27,0x2a,0x2b,0x43d,0x443])
        self.assertEqual(after[0x435:0x43a],b'00017')
        self.assertEqual(after[0x43b:0x43e],b'001')
        self.assertEqual(after[0x43f:0x444],b'00034')
        for operation in (parse_bytes,append_appointment):
            with self.subTest(operation=operation.__name__),self.assertRaises(CalendarParseError) as caught:
                operation(after)
            self.assertEqual(caught.exception.code,'unsupported_layout')
