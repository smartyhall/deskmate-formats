"""Offline reconciliation tests for the archive mirror layout."""

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[2] / "tools" / "archive"), *sys.path]):
    from archive_mirror import Mirror
    from verify_mirror import identity, main, real_path, verify


class VerifyMirrorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)
        self.root = self.temp / "mirror"
        self.mirror = Mirror("https://example.test/tree/", self.root)
        self.addCleanup(self.mirror.db.close)
        self.make_listing("", ["A.zip", "CON.zip", "nested/"])
        self.make_listing("nested/", ["partial.zip"])
        self.data_a = self.make_file("A.zip", b"equivalent archived bytes")
        self.data_b = self.make_file("CON.zip", b"equivalent archived bytes")
        self.partial = self.root / "transfer-state" / (identity("nested/partial.zip") + ".part")
        self.partial.write_bytes(b"part")
        self.mirror.update("nested/partial.zip", status="partial", expected=100)
        self.export()

    def make_listing(self, rel, hrefs):
        for href in hrefs:
            path, kind, url = self.mirror.child(self.mirror.root + rel, href)
            self.mirror.add(path, kind, url)
        raw = ("<title>Index of /tree/" + rel + "</title>" + "".join(
            f'<a href="{href}">file</a>' for href in hrefs)).encode()
        local = self.mirror.db.execute("SELECT local FROM entries WHERE rel=?", (rel,)).fetchone()[0]
        (self.root / local).mkdir(exist_ok=True)
        sha = hashlib.sha256(raw).hexdigest()
        (self.root / "listings" / f"{identity(rel)}-{sha}.html").write_bytes(raw)
        self.mirror.update(rel, status="verified", bytes=len(raw), sha256=sha)

    def make_file(self, rel, data):
        local = self.mirror.db.execute("SELECT local FROM entries WHERE rel=?", (rel,)).fetchone()[0]
        result = self.root / local
        result.write_bytes(data)
        self.mirror.update(rel, status="verified", bytes=len(data), expected=len(data),
                           sha256=hashlib.sha256(data).hexdigest())
        return result

    def export(self):
        with redirect_stdout(StringIO()):
            self.mirror.export()

    def test_validates_listings_residual_mapping_and_duplicates(self):
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        report = verify(self.root)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["validated_listings"], 2)
        self.assertEqual(report["verified_originals"], 2)
        self.assertEqual(report["unique_verified_contents"], 1)
        self.assertEqual(report["duplicate_groups"][0]["paths"], ["A.zip", "CON.zip"])
        self.assertEqual(self.data_b.parent.name, "mapped")
        self.assertEqual([r["rel"] for r in report["residual"]], ["nested/partial.zip"])
        self.assertEqual(next(iter(report["partials"].values()))["bytes"], 4)
        self.assertEqual(report, verify(self.root))
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_detects_changed_missing_orphans_and_stale_export(self):
        self.data_a.write_bytes(self.data_a.read_bytes()[::-1])
        self.data_b.unlink()
        (self.root / "originals" / "orphan.zip").write_bytes(b"orphan")
        self.mirror.update("nested/partial.zip", attempts=2)
        self.mirror.add("nested/uncatalogued.zip", "file", self.mirror.root + "nested/uncatalogued.zip")
        self.mirror.db.commit()
        report = verify(self.root)
        types = [issue["issue"] for issue in report["issues"]]
        self.assertEqual(types.count("entry_validation_failed"), 2)
        self.assertIn("orphan_original", types)
        self.assertIn("summary_field_mismatch", types)
        self.assertIn("inventory_row_mismatch", types)
        self.assertIn("inventory_row_missing", types)
        self.assertIn("state_only_child", types)

    def test_rejects_unsafe_local_mapping(self):
        for local in ("/outside", "originals/..", "originals/CON.exe", "originals/file:ads", "originals/C:\\outside"):
            with self.subTest(local=local), self.assertRaises(ValueError):
                real_path(self.root, local)
        self.mirror.update("A.zip", local="../outside")
        self.export()
        self.assertTrue(any(item["issue"] == "entry_validation_failed" and item["rel"] == "A.zip"
                            for item in verify(self.root)["issues"]))

    def test_cli_writes_private_report_and_preserves_existing_files(self):
        output = self.temp / "report.json"
        args = [str(self.root), "--output", str(output)]
        with patch("sys.stderr", StringIO()), redirect_stdout(StringIO()):
            self.assertEqual(main([str(self.root), "--output", str(self.root / "report.json")]), 2)
            self.assertEqual(main(args), 3)
            self.assertEqual(main(args), 2)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["verified_originals"], 2)


if __name__ == "__main__":
    unittest.main()
