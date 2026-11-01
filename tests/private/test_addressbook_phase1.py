"""Address Book raw fixture observations, not a format parser."""
from pathlib import Path
import hashlib, os, unittest

class AddressBookEvidenceTests(unittest.TestCase):
    def fixture(self,name,side='after'):
        return (Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/ADDRESSBOOK'/name/side/'files/DESKMATE/PERSONAL.ADR').read_bytes()

    def test_no_edit_negative_control(self):
        before=self.fixture('A00_recon','before');after=self.fixture('A00_recon')
        self.assertEqual(before,after)
        self.assertEqual(hashlib.sha256(after).hexdigest(),'cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c')
        self.assertEqual(after[:4],bytes([3,0,0,0]))

    def test_exact_single_contact_changes(self):
        for name,first,length,digest in [('A01_contact',b'TEST',61,'19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8'),('A02_longer_name',b'TESTLONG',65,'ae216968bce070f7a5d9619b844e20295428dac628984a05d22f203e032d76a6')]:
            with self.subTest(case=name):
                before=self.fixture(name,'before');after=self.fixture(name)
                self.assertEqual(before,self.fixture('A00_recon'))
                self.assertEqual(len(after),10240)
                self.assertEqual(hashlib.sha256(after).hexdigest(),digest)
                self.assertEqual([i for i,(a,b) in enumerate(zip(before,after)) if a!=b],[0x435,0x43f,*range(0x1000,0x1000+length+1),0x1428,0x142c])
                self.assertEqual(after[0x1000:0x1003],bytes([0x80,0x10,1]))
                self.assertEqual(after[0x1003:0x1003+len(first)],first)
                self.assertEqual(after[0x1428:0x142e],bytes([4,0,0,0,0x10,0]))
                self.assertEqual(after[0x1000+length-2:0x1000+length+1],bytes([1,2,3]))
                root=Path(os.environ['DOSLAB_ROOT'])/'EXPERIMENTS/ADDRESSBOOK'/name
                self.assertEqual(after,(root/'evidence/immediate_saved.ADR').read_bytes())
                self.assertEqual((root/'before/files/DESKMATE/PERSONAL.CLN').read_bytes(),(root/'after/files/DESKMATE/PERSONAL.CLN').read_bytes())

    def test_four_extra_characters_only(self):
        short=self.fixture('A01_contact');long=self.fixture('A02_longer_name')
        self.assertEqual(long[:0x1007],short[:0x1007])
        self.assertEqual(long[0x1007:0x100b],b'LONG')
        self.assertEqual(long[0x100b:0x1042],short[0x1007:0x103e])
        self.assertEqual(long[0x1042:],short[0x1042:])
