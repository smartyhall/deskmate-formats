"""Private E15 evidence regressions; original databases remain external/read-only."""
from datetime import date
from pathlib import Path
import hashlib,json,os,struct,unittest
from deskmate_formats.calendar.personal import parse_bytes,CalendarParseError
from deskmate_formats.calendar.writer import Appointment,append_appointment


class E15EvidenceTests(unittest.TestCase):
    def root(self):
        return Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/PHASE2/E15_data_page_boundary'

    def test_generation_and_unchanged_closed_preflight(self):
        root=self.root()
        data=(root.parents[1]/'PHASE3A/multi_record/generated_PERSONAL.CLN').read_bytes()
        keys=[(date(2026,10,23),s,e) for s,e in [(555,615),(600,660),(615,660),(660,720)]]
        keys += [(date(2026,10,24),s,e) for s,e in [(540,600),(600,660),(615,660),(660,720)]]
        keys += [(date(2026,11,1),s,e) for s,e in [(540,600),(555,615),(615,660)]]
        for n,(day,start,end) in enumerate(keys,1):
            data=append_appointment(data,Appointment(day,start,end,f'FILL{n:03d}'+'X'*53))
        self.assertEqual(data,(root/'generated_PERSONAL.CLN').read_bytes())
        for stage in ('pre_before','pre_after'):
            self.assertEqual(data,(root/stage/'files/DESKMATE/PERSONAL.CLN').read_bytes())
        self.assertEqual(hashlib.sha256(data).hexdigest(),'ed43356dac2b6351429f785e4b868b4458f6bc1a68f05f447477da30021862a4')
        self.assertEqual(len(parse_bytes(data).appointments),16)
        self.assertEqual(json.loads((root/'pre_after_comparison.json').read_text())['changed_files'],[])

    def test_exact_allocation_delta_and_existing_rows(self):
        root=self.root()
        before=(root/'pre_after/files/DESKMATE/PERSONAL.CLN').read_bytes()
        after=(root/'after/files/DESKMATE/PERSONAL.CLN').read_bytes()
        self.assertEqual((len(before),len(after)),(6144,7168))
        # Independent byte oracle for this measured fixture, not an allocator.
        expected=bytearray(before+bytes(1024))
        expected[0x26:0x28]=bytes.fromhex('00 6f')
        expected[0x2a:0x2c]=bytes.fromhex('8f ff')
        expected[0x439]=ord('8');expected[0x443]=ord('4')
        expected[0x1488:0x1494]=before[0x1482:0x148e]
        struct.pack_into('<HHH',expected,0x1482,6,0,0x21)
        fields=[bytes((0x8f,0x6c,0x62)),b'b',b'',bytes((0xac,)),bytes((0xb0,)),b'1',b'BOUND12']
        row=bytes((0x80,0x21))+b'\x01'.join(fields)+b'\x01\x02'
        self.assertEqual(len(row),24)
        expected[0x1800:0x1818]=row;expected[0x1818]=3
        self.assertEqual(after,expected)
        self.assertEqual(hashlib.sha256(after).hexdigest(),'42517ab1f90f9e7b6c5cf184219bc301254db33adf3f875a36347237743f1380')
        self.assertEqual(after[4096:5120],before[4096:5120])
        for old in parse_bytes(before).records:
            raw=bytes.fromhex(old.raw_hex)
            self.assertEqual(after[old.offset:old.offset+old.length],raw)
            self.assertEqual(after.count(raw),1)

    def test_seven_page_file_remains_unsupported(self):
        after=(self.root()/'after/files/DESKMATE/PERSONAL.CLN').read_bytes()
        for operation in (parse_bytes,append_appointment):
            with self.subTest(operation=operation.__name__),self.assertRaises(CalendarParseError) as error:
                operation(after)
            self.assertEqual(error.exception.code,'unsupported_layout')
