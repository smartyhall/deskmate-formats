"""Collect private file-allocation inventories without opening guest filesystems."""

import argparse
import ctypes
import hashlib
import json
import os
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPARSE = 0x400
SPARSE_OR_COMPRESSED = 0x200 | 0x800
SCHEMA = 1


def native_path(path):
    """Allow local absolute Windows paths beyond legacy MAX_PATH."""
    name = str(path)
    if os.name == "nt":
        return "\\\\?\\" + name
    return name


class WindowsAllocation:
    """Query NTFS allocations using read-attributes handles shared with writers."""

    class StandardInfo(ctypes.Structure):
        _fields_ = [
            ("allocation", ctypes.c_int64),
            ("length", ctypes.c_int64),
            ("links", ctypes.c_uint32),
            ("delete_pending", ctypes.c_ubyte),
            ("directory", ctypes.c_ubyte),
        ]

    def __init__(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.open = kernel.CreateFileW
        self.open.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        self.open.restype = ctypes.c_void_p
        self.info = kernel.GetFileInformationByHandleEx
        self.info.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
        ]
        self.close = kernel.CloseHandle
        self.close.argtypes = [ctypes.c_void_p]
        self.compressed_size = kernel.GetCompressedFileSizeW
        self.compressed_size.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
        self.compressed_size.restype = ctypes.c_uint32

    def __call__(self, path, metadata):
        name = native_path(path)
        # FILE_READ_ATTRIBUTES, share read/write/delete, OPEN_EXISTING, OPEN_REPARSE_POINT
        handle = self.open(name, 0x80, 7, None, 3, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = self.StandardInfo()
            if not self.info(handle, 1, ctypes.byref(info), ctypes.sizeof(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if info.directory or info.delete_pending or info.length != metadata.st_size:
                raise OSError("File changed during allocation query")
            if metadata.st_file_attributes & SPARSE_OR_COMPRESSED:
                high = ctypes.c_uint32()
                ctypes.set_last_error(0)
                low = self.compressed_size(name, ctypes.byref(high))
                if low == 0xffffffff and ctypes.get_last_error():
                    raise ctypes.WinError(ctypes.get_last_error())
                return (high.value << 32) | low, info.links, "GetCompressedFileSizeW"
            return info.allocation, info.links, "FileStandardInfo"
        finally:
            self.close(handle)


def posix_allocation(path, metadata):
    blocks = getattr(metadata, "st_blocks", None)
    return None if blocks is None else blocks * 512, metadata.st_nlink, "st_blocks"


def is_boundary(metadata):
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & REPARSE
    )


def validate_path(path):
    """Reject symlinks, junctions and reparse points in every existing component."""
    for component in [*reversed(path.parents), path]:
        if is_boundary(os.lstat(native_path(component))):
            raise ValueError(f"Reparse point or symlink in path: {component}")


def scan(root, allocation, excluded=()):
    validate_path(root)
    root_metadata = os.lstat(native_path(root))
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError(f"Expected directory: {root}")
    files, gaps = [], []
    pending = [root]
    root_device = root_metadata.st_dev
    directories = 0
    while pending:
        directory = pending.pop()
        try:
            if is_boundary(os.lstat(native_path(directory))):
                raise ValueError("Directory became a reparse point or symlink")
            with os.scandir(native_path(directory)) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
            directories += 1
        except (OSError, ValueError) as exc:
            gaps.append({"path": str(directory), "reason": str(exc)})
            continue
        for entry in children:
            path = directory / entry.name
            try:
                metadata = entry.stat(follow_symlinks=False)
                other_device = metadata.st_dev and metadata.st_dev != root_device
                if path in excluded or is_boundary(metadata) or other_device:
                    gaps.append({"path": str(path), "reason": "scope or filesystem boundary"})
                elif stat.S_ISDIR(metadata.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(metadata.st_mode):
                    row = {
                        "path": str(path),
                        "logical_bytes": metadata.st_size,
                        "mtime_ns": metadata.st_mtime_ns,
                        "allocated_bytes": None,
                        "links": None,
                        "file_id": None,
                    }
                    files.append(row)
                    allocated, links, method = allocation(path, metadata)
                    row.update(allocated_bytes=allocated, links=links, allocation_method=method)
                    if links > 1 and not metadata.st_ino:
                        metadata = os.lstat(native_path(path))
                    if metadata.st_ino:
                        row["file_id"] = [metadata.st_dev, metadata.st_ino]
                else:
                    gaps.append({"path": str(path), "reason": "not a regular file"})
            except OSError as exc:
                gaps.append({"path": str(path), "reason": str(exc)})
    return {"files": files, "gaps": gaps, "directories": directories}


def signature(metadata):
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns


def bounded_vhd_metadata(stream, length):
    """Read only the classic VHD footer and, for a child, its parent identifier."""
    if length < 512:
        return None
    stream.seek(length - 512)
    footer = stream.read(512)
    if len(footer) != 512 or footer[:8] != b"conectix":
        return None
    kind = int.from_bytes(footer[60:64], "big")
    if kind not in (2, 3, 4):
        raise ValueError("Unknown classic VHD disk type")
    result = {
        "type": {2: "fixed", 3: "dynamic", 4: "differencing"}[kind],
        "capacity_bytes": int.from_bytes(footer[48:56], "big"),
        "id": footer[68:84].hex(),
    }
    if kind == 4:
        offset = int.from_bytes(footer[16:24], "big")
        if offset > length - 1536:
            raise ValueError("Classic VHD parent header outside file")
        stream.seek(offset)
        header = stream.read(1024)
        if len(header) != 1024 or header[:8] != b"cxsparse":
            raise ValueError("Missing classic VHD parent header")
        result["parent_id"] = header[40:56].hex()
        result["parent_name"] = header[64:576].decode("utf-16-be").split("\0", 1)[0]
    return result


def bounded_hash(path, budget):
    """Return a whole-file SHA-256 only if it fits the budget and appears stable."""
    validate_path(path)
    before = os.lstat(native_path(path))
    if not stat.S_ISREG(before.st_mode) or before.st_size > budget:
        raise ValueError(f"Expected regular file within byte budget: {path}")
    expected = signature(before)
    digest = hashlib.sha256()
    remaining = before.st_size
    with open(native_path(path), "rb") as stream:
        if signature(os.fstat(stream.fileno())) != expected:
            raise ValueError(f"File changed before hashing: {path}")
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError(f"File truncated during hashing: {path}")
            digest.update(chunk)
            remaining -= len(chunk)
    if signature(os.lstat(native_path(path))) != expected:
        raise ValueError(f"File changed during hashing: {path}")
    return {"path": str(path), "signature": list(expected), "sha256": digest.hexdigest()}


def duplicate_candidates(files):
    """Group same-length files by suffix as a triage signal."""
    groups = {}
    for row in files:
        if row["logical_bytes"]:
            key = (Path(row["path"]).suffix.lower(), row["logical_bytes"])
            groups.setdefault(key, []).append(row["path"])
    return [paths for paths in groups.values() if len(paths) > 1]


def write_report(destination, report):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, delete=False
    ) as stream:
        staging = Path(stream.name)
        try:
            json.dump(report, stream, separators=(",", ":"))
            stream.write("\n")
            stream.close()
            staging.replace(destination)
        finally:
            staging.unlink(missing_ok=True)


def absolute(value):
    path = Path(os.path.abspath(value))
    if os.name == "nt" and (not path.drive or path.drive.startswith("\\")):
        raise argparse.ArgumentTypeError("Use a local drive path")
    return path


def report_key(path):
    return hashlib.sha256(os.fsencode(os.path.normcase(path))).hexdigest()[:24]


def hash_selected(paths, catalog, roots, exclusions, budget, resume):
    for path in dict.fromkeys(paths):
        if not any(root in path.parents for root in roots) or any(
            part in exclusions for part in [path, *path.parents]
        ):
            raise ValueError(f"Hash target outside scan scope: {path}")
        validate_path(path)
        destination = catalog / f"hash-{report_key(path)}.json"
        if destination.exists() or destination.is_symlink():
            validate_path(destination)
            if resume:
                saved = json.loads(destination.read_text(encoding="utf-8"))
                if saved.get("path") == str(path) and saved.get("signature") == list(
                    signature(os.lstat(native_path(path)))
                ):
                    continue
        receipt = bounded_hash(path, budget)
        budget -= receipt["signature"][2]
        write_report(destination, {**receipt, "measured_at": datetime.now(UTC).isoformat()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=absolute)
    parser.add_argument("--catalog", required=True, type=absolute, help="existing private directory")
    parser.add_argument("--exclude", action="append", default=[], type=absolute)
    parser.add_argument("--resume", action="store_true", help="reuse completed root shards")
    parser.add_argument("--hash-file", action="append", default=[], type=absolute)
    parser.add_argument("--hash-budget", type=int, default=0, help="logical bytes for selected hashes")
    args = parser.parse_args()
    if args.hash_budget < 0 or (args.hash_file and not args.hash_budget):
        parser.error("selected hashes require a positive byte budget")
    validate_path(args.catalog)
    if not args.catalog.is_dir():
        parser.error("catalog must be an existing directory")
    allocation = WindowsAllocation() if os.name == "nt" else posix_allocation
    exclusions = sorted(set([args.catalog, *args.exclude]))
    for root in dict.fromkeys(args.roots):
        if root in exclusions or any(parent in exclusions for parent in root.parents):
            parser.error(f"root is inside an exclusion: {root}")
        scope = {"schema": SCHEMA, "root": str(root), "excluded": list(map(str, exclusions))}
        destination = args.catalog / f"{report_key(root)}.json"
        if destination.exists() or destination.is_symlink():
            validate_path(destination)
            if args.resume:
                saved = json.loads(destination.read_text(encoding="utf-8"))
                if all(saved.get(field) == value for field, value in scope.items()):
                    continue
        started = datetime.now(UTC).isoformat()
        inventory = scan(root, allocation, exclusions)
        write_report(destination, {
            **scope, **inventory, "started": started, "finished": datetime.now(UTC).isoformat(),
            "same_suffix_and_length": duplicate_candidates(inventory["files"]),
        })
    hash_selected(args.hash_file, args.catalog, args.roots, exclusions, args.hash_budget, args.resume)


if __name__ == "__main__":
    main()
