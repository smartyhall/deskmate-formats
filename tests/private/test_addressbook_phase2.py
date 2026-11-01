"""Fixed observations against external application-produced Address Book fixtures."""
import hashlib
import json
import os
from pathlib import Path
import unittest

BASELINE = 'cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c'


class AddressBookPhase2Tests(unittest.TestCase):
    def root(self, case):
        return Path(os.environ['DOSLAB_ROOT']) / 'EXPERIMENTS/ADDRESSBOOK' / case

    def adr(self, case, side='after'):
        return (self.root(case) / side / 'files/DESKMATE/PERSONAL.ADR').read_bytes()

    def test_a03_complete_preserved_installations(self):
        root = self.root('PHASE2/A03_work_phone')
        manifests = {}
        for side in ('before', 'saved', 'after'):
            directory = root / side / 'files'
            items = json.loads((root / side / 'manifest.json').read_text())['files']
            expected = {e['path'].replace('\\', '/'): (e['size'], e['sha256']) for e in items}
            actual = {f.relative_to(directory).as_posix(): (f.stat().st_size, hashlib.sha256(f.read_bytes()).hexdigest()) for f in directory.rglob('*') if f.is_file()}
            self.assertEqual(len(actual), 126)
            self.assertEqual(actual, expected)
            manifests[side] = actual
        self.assertEqual(manifests['saved'], manifests['after'])
        self.assertEqual([p for p in manifests['before'] if manifests['before'][p] != manifests['after'][p]], ['DESKMATE/PERSONAL.ADR'])
        final = self.adr('PHASE2/A03_work_phone')
        self.assertEqual(final, (root / 'evidence/immediate_saved.ADR').read_bytes())
        self.assertEqual(self.adr('PHASE2/A03_work_phone', 'before'), self.adr('A01_contact', 'before'))
        self.assertEqual(hashlib.sha256(self.adr('PHASE2/A03_work_phone', 'before')).hexdigest(), BASELINE)

    def test_a03_exact_bytes_and_framing(self):
        before = self.adr('PHASE2/A03_work_phone', 'before')
        final = self.adr('PHASE2/A03_work_phone')
        self.assertEqual(len(final), 10240)
        self.assertEqual(hashlib.sha256(final).hexdigest(), '81b48761fce08c57cbe43a3bb0a23fc4f7d2faee0cdb800375c9175220787d5d')
        self.assertEqual([i for i, (x, y) in enumerate(zip(before, final)) if x != y], [0x435, 0x43f, *range(0x1000, 0x103a), 0x1428, 0x142c])
        self.assertEqual(final[0x1000:0x1002], bytes([0x80, 0x10]))
        self.assertEqual(final[0x1037:0x103a], bytes([1, 2, 3]))
        self.assertEqual(final[0x1428:0x142e], bytes([4, 0, 0, 0, 0x10, 0]))
        self.assertEqual(final[0x431:0x436], b'00001')
        self.assertEqual(final[0x43b:0x440], b'00017')
        self.assertEqual(final[0x437:0x43a], b'000')
        fields = final[0x1002:0x1037].split(bytes([1]))
        self.assertEqual(fields, [b'', b'TEST', b'USER A', b'', b'', b'', b'', b'', b'555-0142', b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n'])
        self.assertEqual(final[0x1000:0x1039].count(bytes([1])), 16)

    def test_a03_only_four_phone_bytes_removed_from_a01(self):
        original = self.adr('A01_contact')
        short = self.adr('PHASE2/A03_work_phone')
        self.assertEqual(original[0x1014:0x1018], b'202-')
        self.assertEqual(short[:0x1014], original[:0x1014])
        self.assertEqual(short[0x1014:0x103a], original[0x1018:0x103e])
        self.assertEqual(short[0x103a:0x103e], bytes(4))
        self.assertEqual(short[0x103e:], original[0x103e:])
