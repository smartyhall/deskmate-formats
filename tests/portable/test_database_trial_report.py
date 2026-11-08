"""Independent trial diagnostics; invented controls never become native evidence."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from database_synthetic import addressbook
from synthetic import build, event

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    'database_trial_report', ROOT / 'tools/experimental/database_trial_report.py')
trial = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trial)
FIRST = [b'', b'TEST', b'USER A', b'', b'', b'', b'', b'', b'202-555-0142',
         b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n']
SECOND = [b'', b'ZULU', b'ALPHA', b'', b'', b'', b'', b'', b'555-0100',
          b'', b'', b'Birthday', b'', b'Anniversary', b'', b'n']


def second_book(reverse=False):
    data = bytearray(addressbook(contact_rows=[FIRST, SECOND]))
    if reverse:
        data[5160:5172] = data[5166:5172] + data[5160:5166]
    return bytes(data)


def growth_control(case):
    """Invented small rows, markers, header patch and targets; wrong native hashes."""
    before = bytearray(build('one'))
    if case == 'e19':
        retired = bytes((68, 33)) + event(33, 'Retired')[2:]
        live = event(34, 'Still live')
        before.extend(retired + live + b'\x03' + bytes(1024 - len(retired) - len(live) - 1))
        struct.pack_into('<HHH', before, 5172, 6, len(retired), 34)
        before[0x435:0x43A] = b'00003'
        before[0x43F:0x444] = b'00035'
    # Literal published deltas/targets, independent of the diagnostic's oracle.
    patches = ([(0x26, 'ff8f', '006f'), (0x2A, 'f000', '8fff')] if case == 'e15'
               else [(0x29, 'ff8fff0000', '007ff8fff0')])
    for pos, old, _ in patches:
        before[pos:pos + len(bytes.fromhex(old))] = bytes.fromhex(old)
    after = bytearray(before)
    target = [6, 0, 33] if case == 'e15' else [7, 0, 46]
    row = event(target[2], 'Synthetic crossing')
    after.extend(row + b'\x03' + bytes(1024 - len(row) - 1))
    count = 2 if case == 'e15' else 3
    struct.pack_into('<HHH', after, 5160 + 6 * count, *target)
    after[0x435:0x43A] = f'{count + 1:05d}'.encode()
    after[0x43F:0x444] = f'{target[2] + 1:05d}'.encode()
    for pos, _, new in patches:
        after[pos:pos + len(bytes.fromhex(new))] = bytes.fromhex(new)
    return bytes(before), bytes(after)


class TrialReportTests(unittest.TestCase):
    def test_addressbook_distinguishes_order_without_asserting_native_policy(self):
        before = addressbook(FIRST)
        for reverse, observation in ((False, 'first-name or insertion'), (True, 'last-name')):
            after = second_book(reverse)
            report = trial.addressbook_trial(before, after)
            checks = report['trial_checks']
            self.assertFalse(checks.pop('before_is_published_A01'))
            self.assertEqual(checks.pop('unrelated_changed_offsets'), [])
            self.assertTrue(all(checks.values()), checks)
            self.assertIn(observation, report['index_order_observation'])
            self.assertEqual(report['after']['rows'][17]['offset'], 0x103D)
            self.assertEqual(report['after']['rows'][17]['end'], 0x1075)
            self.assertEqual(before, addressbook(FIRST))
            self.assertIn('offline independent', report['evidence_class'])

    def test_wrong_fields_counter_and_unrelated_bytes_are_reported(self):
        after = bytearray(second_book(True))
        after[64] ^= 1
        after[0x43B:0x440] = b'00019'
        at = after.index(b'ZULU')
        after[at] = ord('Y')
        report = trial.addressbook_trial(addressbook(FIRST), after)
        self.assertEqual(report['trial_checks']['unrelated_changed_offsets'], [64])
        self.assertFalse(report['trial_checks']['counts_1_to_2_next_17_to_18'])
        self.assertFalse(report['trial_checks']['new_fields_match'])

    def test_malformed_framing_aliases_and_duplicate_targets_fail(self):
        source = second_book()
        cases = [source[:-1], source + b'X', b'BAD!' + source[4:]]
        for pos, value in ((5166, source[5160:5166]), (5166, struct.pack('<H', 3)),
                           (5168, struct.pack('<H', 1024)), (5172, b'X'),
                           (4096, b'\x44'), (4156, b'X'), (0x431, b'99999')):
            data = bytearray(source)
            data[pos:pos + len(value)] = value
            cases.append(data)
        for n, data in enumerate(cases):
            with self.subTest(case=n), self.assertRaises(ValueError):
                trial.snapshot(data, 'DATA')

    def test_published_growth_patches_do_not_authenticate_synthetic_inputs(self):
        for case, count in (('e15', 4), ('e19', 5)):
            before, after = growth_control(case)
            report = trial.growth_trial(before, after, case)
            checks = report['published_observation_checks']
            self.assertFalse(checks.pop('before_hash_matches'))
            self.assertFalse(checks.pop('after_hash_matches'))
            self.assertTrue(all(checks.values()), checks)
            self.assertEqual(len(report['header_changes']), count)
            self.assertEqual(sum(c['before'] is None for c in report['changes']), 1024)
            if case == 'e19':
                self.assertEqual(report['before']['retired_rows'], report['after']['retired_rows'])
                # E19 has a fifth changed header byte; a four-byte allowlist fails.
                changed = bytearray(after)
                changed[0x2D] = before[0x2D]
                self.assertFalse(trial.growth_trial(before, changed, case)
                                 ['published_observation_checks']['exact_header_delta_matches'])

    def test_missing_old_row_and_modified_retired_bytes_are_detected(self):
        before, after = growth_control('e19')
        changed = bytearray(after)
        at = changed.index(b'Retired')
        changed[at] = ord('X')
        report = trial.growth_trial(before, changed, 'e19')
        self.assertFalse(report['published_observation_checks']['retired_rows_preserved'])
        changed = bytearray(after)
        at = changed.index(b'LPHa124')
        changed[at] = ord('X')
        self.assertFalse(trial.growth_trial(before, changed, 'e19')
                         ['published_observation_checks']['old_rows_preserved'])

    def test_cli_reads_only_and_bounds_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after = root / 'before.adr', root / 'after.adr'
            before.write_bytes(addressbook(FIRST))
            after.write_bytes(second_book(True))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(trial.main(['addressbook', str(before), str(after)]), 0)
            self.assertEqual(json.loads(out.getvalue())['after']['count'], 2)
            self.assertEqual(before.read_bytes(), addressbook(FIRST))
            self.assertEqual(after.read_bytes(), second_book(True))
            self.assertEqual(len(list(root.iterdir())), 2)
            after.write_bytes(bytes(65537))
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                trial.main(['addressbook', str(before), str(after)])
            self.assertEqual(caught.exception.code, 2)

    def test_committed_calendar_semantics_match_json_independently(self):
        fixture = ROOT / 'tests/fixtures/application-generated/calendar/sdk-14-days-tool-generated.cln'
        data = fixture.read_bytes()
        snapshot = trial.snapshot(data, 'PERSONAL')
        expected = json.loads((ROOT / 'examples/calendar-14-days.v1.json').read_text(encoding='utf-8'))
        items = []
        for _, _, rid in snapshot['triples']:
            if rid == 16:
                continue
            fields = [bytes.fromhex(v) for v in snapshot['rows'][rid]['fields_hex']]
            day = date(fields[0][0] - 97 + 1980, fields[0][1] - 97, fields[0][2] - 97)
            self.assertEqual(fields[1], bytes((98 + (day.weekday() + 1) % 7,)))
            minutes = [((v[0] >> 2) & 31) * 60 + (v[0] & 3) * 15 for v in fields[3:5]]
            self.assertEqual(fields[2], b'')
            self.assertIn(fields[5], (b'1', b'q'))
            items.append({'date': day.isoformat(), 'start_minutes': minutes[0], 'end_minutes': minutes[1],
                          'description': fields[6].decode('ascii'), 'alarm_enabled': fields[5] == b'q',
                          'storage_record_id': rid})
        self.assertEqual(items, expected['items'])
        self.assertEqual(snapshot['sha256'], expected['source_sha256'])


if __name__ == '__main__':
    unittest.main()
