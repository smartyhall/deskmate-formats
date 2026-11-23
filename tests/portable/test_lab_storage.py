"""Synthetic controls for scope, allocation, image metadata, and hash receipts."""

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import lab_storage


class StorageInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_empty_tree_and_exclusion(self):
        (self.root / "empty").mkdir()
        excluded = self.root / "excluded"
        excluded.mkdir()
        (excluded / "hidden.img").write_bytes(b"hidden")
        report = lab_storage.scan(self.root, lab_storage.posix_allocation, [excluded])
        self.assertEqual(report["files"], [])
        self.assertEqual(report["directories"], 2)
        self.assertEqual([g["path"] for g in report["gaps"]], [str(excluded)])

    def test_symlink_loop_and_explicit_root_escape(self):
        nested = self.root / "nested"
        nested.mkdir()
        loop = nested / "loop"
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(loop), str(self.root)],
                           check=True, capture_output=True)
            self.addCleanup(loop.rmdir)
        else:
            loop.symlink_to(self.root, target_is_directory=True)
        report = lab_storage.scan(self.root, lab_storage.posix_allocation)
        self.assertEqual(report["directories"], 2)
        self.assertEqual([g["path"] for g in report["gaps"]], [str(loop)])
        with self.assertRaises(ValueError):
            lab_storage.scan(loop / "nested", lab_storage.posix_allocation)

    def test_failed_allocation_is_unknown_and_duplicates_are_candidates(self):
        for name, content in [("a.img", b"abc"), ("b.IMG", b"def"), ("a.txt", b"abc")]:
            (self.root / name).write_bytes(content)
        with patch.object(lab_storage, "posix_allocation", side_effect=PermissionError):
            report = lab_storage.scan(self.root, lab_storage.posix_allocation)
        self.assertEqual(len(report["files"]), 3)
        self.assertEqual(len(report["gaps"]), 3)
        self.assertTrue(all(row["allocated_bytes"] is None for row in report["files"]))
        groups = lab_storage.duplicate_candidates(report["files"])
        self.assertEqual([[Path(p).name for p in group] for group in groups], [["a.img", "b.IMG"]])

    def test_selected_hash_checkpoint_survives_budget_stop(self):
        catalog = self.root / "catalog"
        catalog.mkdir()
        first, second = self.root / "a.img", self.root / "b.img"
        first.write_bytes(b"aaa")
        second.write_bytes(b"bbb")
        args = ([first, second], catalog, [self.root], [catalog], 3)
        with self.assertRaises(ValueError):
            lab_storage.hash_selected(*args, resume=False)
        lab_storage.hash_selected(*args, resume=True)
        hashes = {json.loads(p.read_text())["sha256"] for p in catalog.glob("hash-*.json")}
        self.assertEqual(hashes, {hashlib.sha256(s).hexdigest() for s in (b"aaa", b"bbb")})
        second.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            lab_storage.hash_selected(*args, resume=True)

    def test_hash_rejects_changed_signature(self):
        path = self.root / "a.img"
        path.write_bytes(b"dummy")
        actual = lab_storage.signature(path.stat())
        with patch.object(lab_storage, "signature", side_effect=[actual, actual, (*actual, 1)]):
            with self.assertRaisesRegex(ValueError, "changed during"):
                lab_storage.bounded_hash(path, 5)

    def test_cli_resume_retains_completed_shard_and_refresh_sees_change(self):
        source = self.root / "source"
        source.mkdir()
        catalog = self.root / "catalog"
        catalog.mkdir()
        command = [
            sys.executable, lab_storage.__file__, str(source), "--catalog", str(catalog),
        ]
        subprocess.run(command + ["--resume"], check=True)
        report, = catalog.glob("*.json")
        original = report.read_bytes()
        (source / "added.img").write_bytes(b"x")
        subprocess.run(command + ["--resume"], check=True)
        self.assertEqual(report.read_bytes(), original)
        subprocess.run(command, check=True)
        records = json.loads(report.read_bytes())["files"]
        self.assertEqual(records[0]["logical_bytes"], 1)

    @unittest.skipUnless(os.name == "nt", "requires Win32")
    def test_win32_allocation_and_link_count(self):
        path = self.root / "disk.img"
        path.write_bytes(b"x" * 4097)
        other = path.with_name("same-file.img")
        os.link(path, other)
        report = lab_storage.scan(self.root, lab_storage.WindowsAllocation())
        first, second = report["files"]
        self.assertEqual(first["links"], 2)
        self.assertGreaterEqual(first["allocated_bytes"], 4097)
        self.assertIsNotNone(first["file_id"])
        self.assertEqual(first["file_id"], second["file_id"])

    def test_sparse_file_allocation_is_smaller_than_length(self):
        path = self.root / "sparse.img"
        path.touch()
        allocation = lab_storage.posix_allocation
        if os.name == "nt":
            subprocess.run(["fsutil", "sparse", "setflag", str(path)],
                           check=True, capture_output=True)
            allocation = lab_storage.WindowsAllocation()
        with path.open("r+b") as stream:
            stream.seek(16 * 2**20)
            stream.write(b"x")
        record, = lab_storage.scan(self.root, allocation)["files"]
        self.assertLess(record["allocated_bytes"], record["logical_bytes"])

    @unittest.skipUnless(os.name == "nt", "requires Windows long paths")
    def test_windows_catalog_and_hash_can_read_long_paths(self):
        directory = self.root
        for letter in "abc":
            directory /= letter * 100
            native = Path(lab_storage.native_path(directory))
            native.mkdir()
            self.addCleanup(native.rmdir)
        path = directory / "disk.img"
        native = Path(lab_storage.native_path(path))
        native.write_bytes(b"test")
        self.addCleanup(native.unlink)
        observed = lab_storage.scan(self.root, lab_storage.WindowsAllocation())
        self.assertEqual(observed["gaps"], [])
        self.assertEqual(observed["files"][0]["path"], str(path))
        result = lab_storage.bounded_hash(path, 4)
        self.assertEqual(result["sha256"], hashlib.sha256(b"test").hexdigest())

    def test_classic_vhd_parent_header_and_bounds(self):
        footer = bytearray(512)
        footer[:8] = b"conectix"
        footer[16:24] = (512).to_bytes(8, "big")
        footer[48:56] = (4096).to_bytes(8, "big")
        footer[60:64] = (4).to_bytes(4, "big")
        footer[68:84] = b"C" * 16
        header = bytearray(1024)
        header[:8] = b"cxsparse"
        header[40:56] = b"P" * 16
        name = "parent.vhd".encode("utf-16-be")
        header[64:64 + len(name)] = name
        child = footer + header + footer
        data = lab_storage.bounded_vhd_metadata(io.BytesIO(child), len(child))
        self.assertEqual(data["type"], "differencing")
        self.assertEqual(data["capacity_bytes"], 4096)
        self.assertEqual(data["parent_id"], (b"P" * 16).hex())
        self.assertEqual(data["parent_name"], "parent.vhd")
        with self.assertRaisesRegex(ValueError, "outside file"):
            lab_storage.bounded_vhd_metadata(io.BytesIO(footer), len(footer))


if __name__ == "__main__":
    unittest.main()
