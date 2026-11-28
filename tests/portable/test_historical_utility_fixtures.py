"""Verify the historical Filer utility fixtures independently of the guests."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import unittest

from deskmate_formats.database import DatabaseError
from deskmate_formats.filer import parse_bytes
from tools.experimental.inspect_fil2dbf import inspect_dbf

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/application-generated"
TRIAL = ROOT / "docs/evidence/historical-utility-qualification-001.json"


class UtilityFixtureTest(unittest.TestCase):
    def fixture(self, name):
        path = FIXTURES / name
        data = path.read_bytes()
        entries = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))["fixtures"]
        entry, = (item for item in entries if item["path"] == name)
        self.assertEqual((len(data), sha256(data).hexdigest()), (entry["size"], entry["sha256"]))
        return data

    def test_repair_relocates_tables_and_preserves_record_fields(self):
        original = self.fixture("filer/qrecord-one.fil")
        defect = self.fixture("filer/qrecord-index-defect-20261127.fil")
        repaired = self.fixture("filer/qrecord-dbrepair-20261127.fil")
        self.assertEqual([i for i, (a, b) in enumerate(zip(original, defect)) if a != b], [0x1C2A])
        self.assertEqual((original[0x1C2A:0x1C2C], defect[0x1C2A:0x1C2C]), (b"\0\0", b"\1\0"))
        with self.assertRaisesRegex(DatabaseError, "unindexed row"):
            parse_bytes(defect)
        initial, result = parse_bytes(original), parse_bytes(repaired)
        for table in initial.tables:
            output = result.table(table.name)
            self.assertEqual(table.columns, output.columns)
            self.assertEqual(Counter(row.fields for row in table.rows),
                             Counter(row.fields for row in output.rows))
        data_in = initial.table("DATA")
        data_out = result.table("DATA")
        self.assertEqual([(row.record_id, row.fields) for row in data_out.rows], [(16, (b"F7Q9",))])
        self.assertEqual((data_in.data_page, data_in.index_page), (6, 7))
        self.assertEqual((data_out.data_page, data_out.index_page), (4, 5))
        self.assertNotEqual({(row.record_id, row.fields) for row in initial.table("DBCOLS").rows},
                            {(row.record_id, row.fields) for row in result.table("DBCOLS").rows})

    def test_dbf_matches_pre_run_prediction(self):
        data = self.fixture("fil2dbf/qrecord-data-20261127.dbf")
        evidence = json.loads(TRIAL.read_text(encoding="utf-8"))
        expected = evidence["fil2dbf"]["expectations"]["prediction"]
        actual = inspect_dbf(data)
        for key in ("version", "record_count", "header_length", "record_length", "header_terminator"):
            self.assertEqual(actual[key], expected[key])
        self.assertEqual(actual["eof_hex"], f'{expected["conventional_eof"]:02x}')
        field, = actual["fields"]
        self.assertEqual((field["name"], field["type"], field["width"], field["decimals"]),
                         (expected["name_to_enter"], expected["type"], expected["width"], expected["decimals"]))
        self.assertEqual(actual["records"], [{"deleted": False, "values": ["F7Q9"],
                                              "raw_hex": expected["record_bytes_hex"]}])
        with self.assertRaisesRegex(ValueError, "record count"):
            inspect_dbf(data[:-2])
