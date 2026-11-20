"""Verify a settled archive_mirror snapshot without changing it or contacting its source."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import sys
from urllib.parse import urlsplit

from archive_mirror import Listing, digest, listing_child

SHA256 = re.compile(r"[a-f0-9]{64}")
WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$", re.I)


def identity(relative):
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()


def real_path(root, relative):
    """Reject traversal, Windows alternate streams, and all reparse points."""
    parts = relative.split("/")
    if any(part in ("", ".", "..") or re.search(r'[<>:"\\|?*\x00-\x1f]', part)
           or part.endswith((".", " "))
           or WINDOWS_RESERVED.fullmatch(part.partition(".")[0].rstrip())
           for part in parts):
        raise ValueError("unsafe local path")
    path = root
    for part in parts:
        path /= part
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or
                getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("link or reparse point")
    return path


def read_state(root):
    path = real_path(root, "transfer-state/mirror.sqlite3")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        if [row[0] for row in db.execute("PRAGMA quick_check")] != ["ok"]:
            raise ValueError("SQLite quick_check failed")
        meta = dict(db.execute("SELECT key, value FROM meta"))
        entries = {row["rel"]: dict(row) for row in db.execute("SELECT * FROM entries ORDER BY rel")}
    return meta, entries


def check_exports(root, entries, calculated, issues):
    summary = json.loads(real_path(root, "manifests/summary.json").read_text(encoding="utf-8-sig"))
    exported = set()
    inventory = real_path(root, "manifests/inventory.jsonl")
    with inventory.open(encoding="utf-8-sig") as handle:
        for line in handle:
            row = json.loads(line)
            relative = row["rel"]
            if relative in exported:
                issues.append({"issue": "duplicate_inventory_row", "rel": relative})
            exported.add(relative)
            original = entries.get(relative, {})
            fields = sorted(key for key in row.keys() | original.keys()
                            if key not in row or key not in original or row[key] != original[key])
            if fields:
                issues.append({"issue": "inventory_row_mismatch", "rel": relative, "fields": fields})
    issues.extend({"issue": "inventory_row_missing", "rel": relative}
                  for relative in sorted(entries.keys() - exported))
    for key, value in calculated.items():
        if summary.get(key) != value:
            issues.append({"issue": "summary_field_mismatch", "field": key,
                           "state": value, "export": summary.get(key)})
    return summary.get("observed_utc"), len(exported)


def checked_bytes(path, row, *, read=False):
    if not path.is_file():
        raise FileNotFoundError("expected a regular file")
    if read and path.stat().st_size > 16 * 1024**2:
        raise ValueError("listing exceeds the mirror's 16 MiB limit")
    before = path.stat()
    raw = path.read_bytes() if read else None
    actual_hash = hashlib.sha256(raw).hexdigest() if read else digest(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("file changed during validation")
    if (actual_hash, after.st_size) != (row["sha256"], row["bytes"]):
        raise ValueError(f"bytes or digest mismatch (actual {after.st_size}, {actual_hash})")
    return raw


def checked_listing(root, row, origin):
    if not SHA256.fullmatch(row["sha256"] or ""):
        raise ValueError("directory has no usable listing digest")
    prefix = identity(row["rel"])
    listing = f"listings/{prefix}-{row['sha256']}.html"
    raw = checked_bytes(real_path(root, listing), row, read=True)
    parser = Listing()
    parser.feed(raw.decode("utf-8-sig"))
    parser.close()
    if not " ".join(parser.title).strip().lower().startswith(("index of ", "directory listing")):
        raise ValueError("saved page has no recognizable directory index title")
    children = {child for href in parser.links
                if (child := listing_child(origin, row["url"], href))}
    return listing, children


def inventory_disk(root, start, issues):
    """List regular files only, reporting but never descending into links."""
    pending = [start]
    while pending:
        relative = pending.pop()
        try:
            path = real_path(root, relative)
            if path.is_dir():
                pending.extend(sorted((p.relative_to(root).as_posix() for p in path.iterdir()), reverse=True))
            elif path.is_file():
                yield relative, path
            else:
                issues.append({"issue": "unexpected_filesystem_type", "local": relative})
        except (OSError, ValueError) as error:
            issues.append({"issue": "unreadable_local_path", "local": relative, "detail": str(error)})


def verify(root):
    root = root.resolve(strict=True)
    meta, entries = read_state(root)
    origin = urlsplit(meta["root"])
    issues = []
    counts = Counter(row["status"] for row in entries.values())
    verified_files = [row for row in entries.values() if row["kind"] == "file" and row["status"] == "verified"]
    expected_summary = {"source": meta["root"], "status_counts": dict(counts),
                        "verified_files": len(verified_files),
                        "verified_file_bytes": sum(row["bytes"] or 0 for row in verified_files),
                        "complete_for_discovered_tree": bool(entries) and counts["verified"] == len(entries),
                        "host_not_before_epoch": float(meta.get("not_before", 0))}
    snapshot, export_count = check_exports(root, entries, expected_summary, issues)
    expected_children = defaultdict(set)
    rows_by_part = {}
    for row in entries.values():
        rel, kind = row["rel"], row["kind"]
        if rel:
            parent = rel.rstrip("/").rpartition("/")[0]
            expected_children[parent + "/" if parent else ""].add((rel, kind, row["url"]))
        if kind == "file":
            rows_by_part[f"transfer-state/{identity(rel)}.part"] = row

    matched_listings, verified_rows = set(), set()
    contents, states = defaultdict(list), defaultdict(Counter)
    allocated = set()
    for rel, row in entries.items():
        kind, local = row["kind"], row["local"]
        states[kind][row["status"]] += 1
        try:
            if kind not in ("dir", "file"):
                raise ValueError("unexpected transfer entry kind")
            if not rel:
                if (kind, local, row["url"]) != ("dir", "originals", meta["root"]):
                    raise ValueError("unexpected source root entry")
            else:
                parent, _, name = rel.rstrip("/").rpartition("/")
                parent_row = entries.get(parent + "/" if parent else "")
                if parent_row is None or parent_row["kind"] != "dir":
                    raise ValueError("missing directory entry for parent")
                if local not in (f"mapped/{identity(rel)}", f"{parent_row['local']}/{name}"):
                    raise ValueError("local pathname does not match the source entry or its mapped identity")
            path = real_path(root, local)
            allocated.add(local)
            if row["status"] != "verified":
                if kind == "file" and path.exists():
                    issues.append({"issue": "unverified_final_path_exists", "rel": rel, "local": local})
                continue
            if kind == "dir":
                listing, found = checked_listing(root, row, origin)
                matched_listings.add(listing)
                if not path.is_dir():
                    raise ValueError("local directory missing")
                recorded = expected_children[rel]
                for key, children in (("listing_only_child", found - recorded), ("state_only_child", recorded - found)):
                    for child_rel, child_kind, child_url in sorted(children):
                        issues.append({"issue": key, "parent": rel, "rel": child_rel,
                                       "kind": child_kind, "url": child_url})
            else:
                checked_bytes(path, row)
                if row["expected"] is not None and row["expected"] != row["bytes"]:
                    raise ValueError("downloaded size differs from transfer expectation")
                contents[row["sha256"]].append(row)
            verified_rows.add(rel)
        except (OSError, ValueError) as error:
            issues.append({"issue": "entry_validation_failed", "rel": rel, "local": local, "detail": str(error)})

    physical = dict((relative, path.stat().st_size) for start in ("originals", "mapped")
                    for relative, path in inventory_disk(root, start, issues))
    for relative in sorted(physical.keys() - allocated):
        issues.append({"issue": "orphan_original", "local": relative, "bytes": physical[relative]})
    partials = {}
    for relative, path in inventory_disk(root, "transfer-state", issues):
        if not relative.endswith(".part"):
            continue
        owner = rows_by_part.get(relative)
        partials[relative] = {"bytes": path.stat().st_size, "rel": owner["rel"] if owner else None}
        if owner is None or owner["status"] == "verified":
            issues.append({"issue": "orphan_partial" if owner is None else "verified_row_has_partial",
                           "local": relative, **partials[relative]})
    for relative in sorted(rows_by_part.keys() - partials.keys()):
        owner = rows_by_part[relative]
        if owner["status"] == "partial":
            issues.append({"issue": "partial_row_missing_bytes", "local": relative, "rel": owner["rel"]})
    listing_paths = {relative for relative, _ in inventory_disk(root, "listings", issues)}
    historical_listings = sorted(listing_paths - matched_listings - {"listings/robots.txt"})
    residual = [row for row in entries.values() if row["rel"] not in verified_rows]
    duplicates = [{"sha256": sha, "bytes": group[0]["bytes"], "paths": [row["rel"] for row in group]}
                  for sha, group in sorted(contents.items()) if len(group) > 1]
    dates = sorted(row["observed"] for row in entries.values() if row["observed"])
    extensions = Counter(PurePosixPath(rel).suffix.lower() or "(none)"
                         for rel in verified_rows if entries[rel]["kind"] == "file")
    return {"schema_version": 1, "source": meta["root"], "snapshot_utc": snapshot,
            "first_observation_utc": dates[0] if dates else None,
            "last_observation_utc": dates[-1] if dates else None,
            "inventory_rows": export_count, "transfer_summary": expected_summary,
            "states_by_kind": {kind: dict(counts) for kind, counts in states.items()},
            "validated_listings": len(matched_listings), "unreferenced_listing_paths": historical_listings,
            "verified_originals": sum(map(len, contents.values())), "physical_original_files": len(physical),
            "physical_original_bytes": sum(physical.values()), "unique_verified_contents": len(contents),
            "unique_verified_bytes": sum(group[0]["bytes"] for group in contents.values()),
            "verified_extension_counts": dict(extensions), "duplicate_groups": duplicates,
            "partials": partials, "residual": residual, "issues": issues}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mirror", type=Path, help="settled mirror root")
    parser.add_argument("--output", type=Path, required=True, help="new private JSON report outside the mirror")
    args = parser.parse_args(argv)
    try:
        mirror = args.mirror.resolve(strict=True)
        if args.output.resolve().is_relative_to(mirror):
            raise ValueError("report must be outside the mirror")
        result = verify(mirror)
        with args.output.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(result, output, sort_keys=True, indent=2)
            output.write("\n")
    except (KeyError, OSError, ValueError, sqlite3.Error) as error:
        print(f"Mirror verification failed: {error}", file=sys.stderr)
        return 2
    print(f"{result['verified_originals']} originals, {result['validated_listings']} listings, "
          f"{len(result['residual'])} residual entries, {len(result['issues'])} issues")
    if result["issues"]:
        return 4
    return 3 if result["residual"] else 0


if __name__ == "__main__":
    sys.exit(main())
