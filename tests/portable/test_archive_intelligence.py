"""Offline index tests with independently authored synthetic bytes."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "archive"))
import archive_intelligence as index  # noqa: E402


def zipped(*members):
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for name, data in members:
            archive.writestr(name, data)
    return output.getvalue()


class ArchiveIntelligenceTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.root = self.home / "mirror"
        self.root.mkdir()
        self.database = self.home / "library.sqlite"
        self.manifest = self.root / "inventory.jsonl"
        self.rows = []

    def receipt(self, name, data, *, local=None):
        local = local or name
        path = self.root / local
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        row = {"kind": "file", "url": f"https://example.invalid/archive/{name}",
               "rel": name, "local": local, "status": "verified",
               "bytes": len(data), "sha256": sha256(data).hexdigest()}
        self.rows.append(row)
        return row

    def command(self, *arguments, status=0):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = index.main(["--database", str(self.database), *arguments])
        self.assertEqual(code, status, errors.getvalue())
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def ingest(self, *arguments, status=0):
        self.manifest.write_text("\n".join(map(json.dumps, self.rows)), encoding="utf-8")
        return self.command("ingest", str(self.root), "--manifest", str(self.manifest),
                            *arguments, status=status)

    def test_resume_duplicates_nested_requeue_and_search(self):
        text = b"Fixture Title\r\nRockwell outlined \x82 specimen\r\n"
        inner = zipped(("NOTE.TXT", text))
        outer = zipped(("renamed.bundle", inner), ("../../outside.txt", b"hidden"))
        self.receipt("a.zip", outer, local="mapped/private-name")
        self.receipt("b.zip", outer)
        self.receipt("c.txt", text)
        first, = self.ingest("--max-files", "1")
        self.assertEqual(first["index"]["sources"], {"indexed": 1, "queued": 2})
        self.assertEqual(first["index"]["occurrence_status"]["unsafe-path"], 1)
        self.assertFalse((self.home / "outside.txt").exists())

        stop = self.database.with_suffix(".STOP")
        stop.touch()
        cancelled, = self.ingest(status=130)
        self.assertEqual(cancelled["event"], "cancelled")
        stop.unlink()
        finished, = self.ingest()
        self.assertEqual(finished["this_run"], {"indexed": 2})
        self.assertEqual(finished["index"]["documents"]["text_analyses"], 1)
        hits = self.command("search", '"rockwell outlined"')
        self.assertEqual([r["rel"] for r in hits], ["a.zip", "b.zip", "c.txt"])
        self.assertEqual([l["name"] for l in hits[0]["chain"]], ["renamed.bundle", "NOTE.TXT"])
        body, = self.command("document", hits[0]["id"])
        self.assertIn("é specimen", body["body"])
        dupes = self.command("duplicates")
        self.assertEqual(len(dupes), 7)

        requeued, = self.command("requeue", "--kind", "text", "--select", "a.zip")
        self.assertEqual(requeued, {"invalidated_analyses": 1, "requeued_sources": 3})
        self.assertEqual(self.command("search", "rockwell"), [])
        self.ingest()
        self.assertEqual(hits, self.command("search", '"rockwell outlined"'))
        unchanged, = self.ingest()
        self.assertEqual(unchanged["this_run"], {})

    def test_input_mismatch_and_snapshot_increment(self):
        row = self.receipt("notes.txt", b"Old title")
        self.ingest()
        (self.root / "notes.txt").write_bytes(b"Updated title")
        result, = self.ingest("--recheck")
        self.assertEqual(result["index"]["sources"], {"input_error": 1})
        self.assertEqual(self.command("search", "old"), [])
        self.rows.clear()
        self.receipt("notes.txt", b"Updated title")
        self.ingest()
        hit, = self.command("search", "updated")
        self.assertEqual(hit["id"], index.stable_id(row["url"]))
        self.assertEqual(self.command("search", "old"), [])

    def test_failed_extraction_unsafe_mapping_and_bad_receipt(self):
        self.receipt("corrupt.zip", b"PK\x03\x04invalid")
        row = self.receipt("escape.txt", b"input")
        row["local"] = "../escape.txt"
        self.ingest()
        failure, = self.command("files", "--status", "failed")
        self.assertEqual(failure["rel"], "corrupt.zip")
        unsafe, = self.command("sources", "--state", "input_error")
        self.assertIn("Unsafe local mapping", unsafe["detail"])
        self.rows.append(dict(row))
        self.ingest(status=2)
        self.assertEqual(len(self.command("sources")), 2)

    def test_live_only_imports_committed_arrivals_without_reextracting(self):
        first = self.receipt("first.txt", b"Common sample")
        second = self.receipt("second.txt", b"Common sample")
        state = self.root / "transfer-state" / "mirror.sqlite3"
        state.parent.mkdir()
        with sqlite3.connect(state) as transfer:
            self.addCleanup(transfer.close)
            transfer.execute("CREATE TABLE entries "
                             "(kind,url,rel,local,status,bytes,sha256)")
            for row, status in ((first, "verified"), (second, "partial")):
                transfer.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,?)",
                                 tuple(row[k] for k in ("kind", "url", "rel", "local"))
                                 + (status, row["bytes"], row["sha256"]))
            transfer.commit()
            first_run, = self.command("ingest", str(self.root), "--live")
            self.assertEqual(first_run["this_run"], {"indexed": 1})
            self.assertEqual(first_run["index"]["receipts"], {"partial": 1, "verified": 1})
            transfer.execute("UPDATE entries SET status='verified'")
            transfer.commit()
        with patch.object(index, "extract", side_effect=AssertionError("repeated extraction")):
            next_run, = self.command("ingest", str(self.root), "--live")
        self.assertEqual(next_run["this_run"], {"indexed": 1})
        matches = self.command("search", "sample")
        self.assertEqual([m["rel"] for m in matches], ["first.txt", "second.txt"])

    def test_seven_zip_upgrade_requeues_iso_and_udf(self):
        from types import SimpleNamespace

        self.receipt("one.iso", b"synthetic ISO recognition control")
        self.receipt("two.udf", b"synthetic UDF recognition control")
        self.receipt("unrelated.txt", b"Unrelated text document")
        original_identify = index.identify
        def identify(path, name):
            return {"one.iso": "iso9660", "two.udf": "udf"}.get(
                name, original_identify(path, name))

        def unavailable(path, name, kind, *args, **kwargs):
            self.assertIn(kind, {"iso9660", "udf"})
            return SimpleNamespace(status="unsupported", detail="7zip-unavailable",
                                   members=[], documents=[])

        with patch.object(index, "identify", side_effect=identify), (
                patch.object(index, "extract", side_effect=unavailable) as initial):
            self.ingest()
            self.assertEqual(initial.call_count, 2)

        def upgraded(path, name, kind, *args, **kwargs):
            self.assertIn(kind, {"iso9660", "udf"})
            return SimpleNamespace(status="ok", detail=None, members=[], documents=[])

        with patch.object(index, "identify", side_effect=identify), (
                patch.object(index, "extract", side_effect=upgraded) as new):
            result, = self.ingest("--update-tools", "--seven-zip",
                                  str(self.home / "seven-zip.exe"))
        self.assertEqual(new.call_count, 2)
        self.assertEqual(result["this_run"], {"indexed": 2})
        self.assertEqual(len(self.command("search", "unrelated")), 1)

    def test_capability_upgrade_reindexes_only_affected_sources(self):
        self.receipt("note.txt", b"Qualified title")
        self.receipt("manual.pdf", b"%PDF-fake")
        self.ingest()
        pdf_python = self.home / "python"
        available = index.extract

        def extract_one(path, name, kind, *args, **kwargs):
            self.assertEqual(kind, "pdf")
            return available(path, name, kind, *args, **kwargs)

        with patch.object(index, "extract", side_effect=extract_one) as adapter:
            run, = self.ingest("--update-tools", "--pdf-python", str(pdf_python))
        self.assertEqual(adapter.call_count, 1)
        self.assertEqual(run["this_run"], {"indexed": 1})
        self.assertEqual(len(self.command("search", "qualified")), 1)


if __name__ == "__main__":
    unittest.main()
