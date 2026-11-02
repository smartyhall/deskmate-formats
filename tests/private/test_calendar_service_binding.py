"""Original-byte constraints for issue 25; no guest execution or API inference."""
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


class CalendarServiceBinding(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ['DOSLAB_ROOT']) / 'EXPERIMENTS/FILER/F00_baseline/before/files/DESKMATE'
        self.desk = (base / 'DESK.EXE').read_bytes()
        self.calendar = (base / 'CALENDAR.PDM').read_bytes()

    def test_original_identities(self):
        self.assertEqual(hashlib.sha256(self.desk).hexdigest(),
                         '0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3')
        self.assertEqual(hashlib.sha256(self.calendar).hexdigest(),
                         '819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23')

    def test_calendar_signed_choice_and_sync_points(self):
        b = self.calendar
        self.assertEqual(b[0xd7f3:0xd803],
                         bytes.fromhex('58 0b c0 7f 05 b8 06 02 eb 03 b8 0c 02 cd e0 c3'))
        # JG after OR AX,AX selects 020C for a signed positive helper result.
        self.assertEqual(0xd7f8 + struct.unpack_from('<b', b, 0xd7f7)[0], 0xd7fd)
        self.assertEqual(b[0xd7e9:0xd7f3], bytes.fromhex('8c d8 8e c0 bb 62 2a ba 44 29'))

    def test_desk_old_vector_check_precedes_installation(self):
        b = self.desk
        self.assertEqual(b[0x37b0:0x37c7],
                         bytes.fromhex('b8 e0 35 cd 21 8e 1e 10 00 8c 06 48 00 89 1e 46 00 8c c0 0b c3 74 1b'))
        self.assertEqual(b[0x37cc:0x37ea],
                         bytes.fromhex('be 52 00 8d 7f 03 b9 09 00 fc f3 a6 75 08 5a 1f ba b1 05 f9 eb 58 ba 4f 00 b8 e0 25 cd 21'))
        self.assertEqual(b[0x42a2:0x42ab], b'DESKMATE$')
        # Equality avoids the set-vector instruction; it is not unconditional.
        self.assertEqual(0x37e2 + struct.unpack_from('<b', b, 0x37e1)[0], 0x383a)

    def test_bootstrap_far_slot_has_distinct_relocated_segment(self):
        b = self.desk
        reloc = {r['file_offset']: r['original_word'] for r in probe.inspect_mz(b)['relocations']}
        self.assertEqual(reloc[0x425e], 0x456)  # CS:000E in bootstrap image segment 0405.
        self.assertEqual(reloc[0x4770], 0x405)  # Initial DS:0010 for vector installation.
        self.assertEqual(reloc[0x4774], 0)      # Core-call slot segment; MZ load base added.
        self.assertEqual(b[0x42cf:0x42d5], bytes.fromhex('1e 2e 8e 1e 0e 00'))
        self.assertEqual(b[0x42ed:0x42f9], bytes.fromhex('fa c7 06 12 00 c2 03 fb ff 1e 12 00'))

    def test_conditional_ah02_dispatch_table_is_not_an_export_table(self):
        b = self.desk
        self.assertEqual(b[0x5c7:0x5cc], bytes.fromhex('80 fc 02 74 4c'))
        self.assertEqual(0x5cc + struct.unpack_from('<b', b, 0x5cb)[0], 0x618)
        self.assertEqual(b[0x618:0x61e], bytes.fromhex('50 b8 86 04 eb 41'))
        self.assertEqual(b[0x666:0x67a],
                         bytes.fromhex('8b 5e 02 2e 8a 3c 3a df 72 02 8a df 46 32 ff d1 e3 2e 8b 18'))
        self.assertEqual(b[0x680:0x686], bytes.fromhex('5d 58 ff 26 10 04'))
        self.assertEqual(b[0x686], 13)
        for selector in (6, 12):
            offset = struct.unpack_from('<H', b, 0x687 + 2 * selector)[0]
            self.assertEqual(offset, 0x505)
            self.assertEqual(0x200 + offset, 0x705)
        self.assertEqual(b[0x705], 0xe8)
        self.assertEqual(0x708 + struct.unpack_from('<h', b, 0x706)[0], 0x2d65)
        self.assertEqual(b[0x2d65:0x2d6c], bytes.fromhex('a2 05 03 8b c2 eb 62'))
        # AL is saved before AX is overwritten; sharing code does not prove
        # selectors 06 and 0C have the same semantics.

    def test_module_iteration_callback_is_a_continuation_not_an_export(self):
        b = self.desk
        self.assertEqual(b[0x2db7], 0xe8)
        self.assertEqual(0x2dba + struct.unpack_from('<h', b, 0x2db8)[0], 0x2c61)
        self.assertEqual(b[0x2c61:0x2c72],
                         bytes.fromhex('58 06 57 56 51 53 8b d8 bf 80 01 b9 20 00 c4 75 02'))
        self.assertEqual(b[0x2c78:0x2c81], bytes.fromhex('ff d3 72 08 83 c7 0b e2 ee'))
        self.assertEqual(b[0x2dba:0x2dc4], bytes.fromhex('57 51 8b fe 8b f2 b1 08 f3 a6'))
