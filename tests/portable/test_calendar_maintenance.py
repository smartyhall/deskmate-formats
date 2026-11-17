"""Bounded native-supported maintenance; byte oracles and hostile sources."""
from hashlib import sha256
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from deskmate_formats import database
from deskmate_formats.calendar.maintenance import normalize_index, replace_description, write_description
from test_calendar_index_controls import expected_split

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/application-generated/calendar'


class MaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (FIXTURES / 'sdk-30-days-allocator-tool-generated.cln').read_bytes()

    def test_normalize_two_native_profiles_and_idempotence(self):
        for source, native in (
            ('sdk-30-days-allocator-tool-generated.cln', 'native-30-day-open-close-20261117.cln'),
            ('sdk-29-days-forward-tool-generated.cln', 'native-29-day-open-close-20261117.cln'),
        ):
            with self.subTest(source=source):
                data = (FIXTURES / source).read_bytes()
                actual = normalize_index(data, experimental=True)
                self.assertEqual(actual, expected_split(data))
                self.assertEqual(actual, (FIXTURES / native).read_bytes())
                self.assertEqual(normalize_index(actual, experimental=True), actual)

    def test_description_and_normalize_reproduce_existing_native_save_whole_file(self):
        # Expected result comes from a prior native trial, not this feature.
        saved = (FIXTURES / 'native-30-day-edit-save-20261117.cln').read_bytes()
        actual = replace_description(self.source, 77, 'Plan 01 / allocator saved',
                                     normalize=True, experimental=True)
        self.assertEqual(actual, saved)
        self.assertEqual(sha256(actual).hexdigest(),
                         '4b59c4f30ba21260df8159ac8758077858f1f516efbfc95365c7a5096ccab970')
        self.assertEqual(normalize_index(saved, experimental=True), saved)

    def test_description_only_changes_unique_raw_ascii_target(self):
        actual = replace_description(self.source, 77, 'Plan 01 / allocator saved', experimental=True)
        expected = self.source.replace(b'Plan 01 / allocator trial', b'Plan 01 / allocator saved')
        self.assertEqual(self.source.count(b'Plan 01 / allocator trial'), 1)
        self.assertEqual(actual, expected)
        self.assertEqual(actual[5120:6144], self.source[5120:6144])
        # Stable routed input remains routed while the same event is edited.
        routed = normalize_index(self.source, experimental=True)
        self.assertEqual(replace_description(routed, 77, 'Plan 01 / allocator saved', experimental=True),
                         expected_split(expected))

    def test_every_appointment_can_be_edited_without_moving_any_other_bytes(self):
        # Includes finite-route endpoint, group edges and last logical row.
        for name in ('sdk-30-days-allocator-tool-generated.cln',
                     'native-30-day-open-close-20261117.cln',
                     'sdk-29-days-forward-tool-generated.cln',
                     'native-29-day-open-close-20261117.cln'):
            source = (FIXTURES / name).read_bytes()
            for row in database.parse_bytes(source).table('PERSONAL').rows:
                if row.record_id == 16:
                    continue
                text = '~' * len(row.fields[6])
                actual = replace_description(source, row.record_id, text, experimental=True)
                at = row.offset + len(row.raw) - 2 - len(row.fields[6])
                expected = source[:at] + text.encode() + source[at + len(text):]
                self.assertEqual(actual, expected, (name, row.record_id))

    def test_opt_in_types_values_and_record_ownership(self):
        for value in (False, None, 1, 'yes'):
            with self.assertRaises(ValueError):
                normalize_index(self.source, experimental=value)
        for source in (None, '', 8192, self.source[:-1], self.source + b'\0'):
            with self.assertRaises(ValueError):
                normalize_index(source, experimental=True)
        for ident in (16, 15, 999, True, '77', None):
            with self.assertRaises(ValueError):
                replace_description(self.source, ident, 'Plan 01 / allocator saved', experimental=True)
        for text in ('', 'short', 'X' * 121, '\x01' * 24, '\x7f' * 24, '\u00e9' * 24, None):
            with self.assertRaises(ValueError):
                replace_description(self.source, 77, text, experimental=True)
        with self.assertRaises(ValueError):
            replace_description(self.source, 77, 'Plan 01 / allocator saved', normalize=1, experimental=True)

    def test_malformed_routes_targets_holes_count_and_wrong_ownership_fail_closed(self):
        changes = []
        for at, value in ((5120, b'A'), (0x1428, b'\x02\x00'),
                          (0x142A, b'\x01\x00'), (0x142C, b'\x7f\x00'),
                          (0x1428, bytes(6)), (0x435, b'00061'),
                          (0x444, b'6'), (0x43A, b'999')):
            changed = bytearray(self.source)
            changed[at:at + len(value)] = value
            changes.append(bytes(changed))
        routed = bytearray(normalize_index(self.source, experimental=True))
        routed[5120] ^= 1
        changes.append(bytes(routed))
        # Valid endpoint route in group two is supported by the reader but
        # outside the two measured maintenance layouts.
        routed = bytearray(normalize_index(self.source, experimental=True))
        db = database.parse_bytes(routed)
        table = db.table('PERSONAL')
        endpoint = next(r for r in table.rows if r.offset == table.index_groups[1].entries[-1].address)
        routed[5130:5140] = database.index_prefix(endpoint.fields, (1, 2, 4, 5, 7))
        database.parse_bytes(routed)
        changes.append(bytes(routed))
        for changed in changes:
            with self.subTest(sha=sha256(changed).hexdigest()):
                with self.assertRaises(ValueError):
                    normalize_index(changed, experimental=True)
                with self.assertRaises(ValueError):
                    replace_description(changed, 77, 'Plan 01 / allocator saved', experimental=True)

    def test_valid_but_unmeasured_group_boundaries_rejected(self):
        db = database.parse_bytes(self.source)
        entries = db.table('PERSONAL').entries
        # Full second group, all entries in two partial groups, populated last
        # group and group-zero below/above measured slot 20. No route guessing.
        for counts in ((21, 41, 0, 0), (7, 7, 7, 41), (31, 31, 0, 0), (20, 20, 21, 1),
                       (19, 22, 21, 0), (21, 20, 21, 0)):
            changed = bytearray(self.source)
            changed[5160:6144] = bytes(984)
            cursor = 0
            for group, count in enumerate(counts):
                for n in range(count):
                    entry = entries[cursor]; cursor += 1
                    struct.pack_into('<HHH', changed, 5160 + group * 246 + n * 6,
                                     entry.page, entry.in_page_offset, entry.record_id)
            database.parse_bytes(changed)
            with self.assertRaises(ValueError):
                normalize_index(changed, experimental=True)

    def test_tied_starts_and_schema_owner_rejected(self):
        table = database.parse_bytes(self.source).table('PERSONAL')
        original = next(r for r in table.rows if r.record_id == 17)
        target = next(r for r in table.rows if r.record_id == 77)
        at = target.offset + 2 + sum(len(f) + 1 for f in target.fields[:3])
        tied = bytearray(self.source)
        tied[at] = original.fields[3][0]
        database.parse_bytes(tied)
        with self.assertRaisesRegex(ValueError, 'tied date/start'):
            normalize_index(tied, experimental=True)
        changed = self.source.replace(b'Date\x01PERSONAL\x01', b'Date\x01OTHER___\x01')
        self.assertNotEqual(changed, self.source)
        with self.assertRaises(ValueError):
            normalize_index(changed, experimental=True)

    def test_other_published_native_profiles_remain_unsupported(self):
        for name in ('e01-86box-historical-match.cln', 'e02-86box-historical-match.cln',
                     'native-second-empty-calendar-operator.cln',
                     'native-second-first-event-operator.cln'):
            with self.assertRaises(ValueError):
                normalize_index((FIXTURES / name).read_bytes(), experimental=True)

    def test_new_file_publication_refuses_overwrite_and_cli_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.cln', Path(folder) / 'result.cln'
            source.write_bytes(self.source)
            script = ROOT / 'tools/experimental/edit_calendar_description.py'
            result = subprocess.run([sys.executable, str(script), str(source), str(output),
                                     '77', 'Plan 01 / allocator saved', '--normalize-index',
                                     '--experimental'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), (FIXTURES / 'native-30-day-edit-save-20261117.cln').read_bytes())
            with self.assertRaises(FileExistsError):
                write_description(output, self.source, 77, 'Plan 01 / allocator saved', experimental=True)
            self.assertEqual(source.read_bytes(), self.source)
