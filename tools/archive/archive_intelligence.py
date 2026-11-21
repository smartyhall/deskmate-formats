"""Build and query an offline, content-addressed archive research index."""

import argparse
from collections import Counter
from contextlib import closing
from dataclasses import asdict
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

if __package__:
    from .intelligence_extract import CONTAINER_KINDS, Limits, extract, identify
else:
    from intelligence_extract import CONTAINER_KINDS, Limits, extract, identify

SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS configuration (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source (
    id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, snapshot TEXT NOT NULL,
    rel TEXT NOT NULL, local TEXT, modified TEXT, receipt_status TEXT NOT NULL,
    expected_size INTEGER, expected_hash TEXT, state TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS source_snapshot ON source(snapshot);
CREATE TABLE IF NOT EXISTS analysis (
    id TEXT PRIMARY KEY, digest TEXT NOT NULL, kind TEXT NOT NULL,
    size INTEGER NOT NULL, status TEXT NOT NULL, detail TEXT
);
CREATE TABLE IF NOT EXISTS member (
    analysis_id TEXT NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL, name TEXT NOT NULL, size INTEGER, digest TEXT,
    status TEXT NOT NULL, PRIMARY KEY (analysis_id, ordinal)
);
CREATE TABLE IF NOT EXISTS occurrence (
    id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source(id) ON DELETE CASCADE,
    parent_id TEXT REFERENCES occurrence(id) ON DELETE CASCADE,
    ordinal INTEGER, name TEXT NOT NULL, chain TEXT NOT NULL, depth INTEGER NOT NULL,
    size INTEGER, digest TEXT, kind TEXT,
    analysis_id TEXT REFERENCES analysis(id), status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS occurrence_source ON occurrence(source_id);
CREATE INDEX IF NOT EXISTS occurrence_digest ON occurrence(digest);
CREATE INDEX IF NOT EXISTS occurrence_analysis ON occurrence(analysis_id);
CREATE VIRTUAL TABLE IF NOT EXISTS document USING fts5(
    analysis_id UNINDEXED, page UNINDEXED, title UNINDEXED, body,
    tokenize='unicode61 remove_diacritics 2'
);
"""


class Cancelled(Exception):
    pass


class IntegrityError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_id(*fields):
    return hashlib.sha256(canonical(fields).encode("ascii")).hexdigest()


def contained(root, local):
    parts = local.split("/")
    if any(part in {"", ".", ".."} or ":" in part or "\\" in part or
           part.endswith((" ", ".")) or "\x00" in part for part in parts):
        raise IntegrityError(f"Unsafe local mapping: {local!r}")
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root):
        raise IntegrityError(f"Local mapping leaves its input root: {local!r}")
    return candidate


def read_manifest(manifest):
    with manifest.open(encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            try:
                yield json.loads(line)
            except ValueError as exc:
                raise IntegrityError(f"Inventory line {line_no}: invalid JSON") from exc


def read_transfer_state(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as state:
        state.row_factory = sqlite3.Row
        # Take a short committed snapshot. Release the reader before hashing or extraction.
        rows = state.execute("SELECT * FROM entries WHERE kind='file' ORDER BY rel").fetchall()
    yield from map(dict, rows)


def read_receipts(rows):
    seen = set()
    for line_no, row in enumerate(rows, 1):
        try:
            if row["kind"] == "dir":
                continue
            if row["kind"] != "file":
                raise ValueError("unknown entry kind")
            url = urlsplit(row["url"])
            if (url.scheme not in {"http", "https", "ftp"} or not url.hostname
                    or url.username or url.password or url.query or url.fragment):
                raise ValueError("expected an original URL without credentials, query or fragment")
            if row["url"] in seen:
                raise ValueError("duplicate source URL")
            seen.add(row["url"])
            if not isinstance(row["rel"], str) or not row["rel"] or "\x00" in row["rel"]:
                raise ValueError("invalid source path")
            if row["status"] == "verified":
                if (not isinstance(row["local"], str) or
                        type(row["bytes"]) is not int or row["bytes"] < 0 or
                        not re.fullmatch("[a-f0-9]{64}", row["sha256"])):
                    raise ValueError("verified receipt requires local name, byte size and SHA-256")
            yield row
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise IntegrityError(f"Inventory row {line_no}: {exc}") from exc


def open_index(path, *, write=False):
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        database = sqlite3.connect(path)
    else:
        database = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    version = database.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION and (version or not write):
        database.close()
        raise IntegrityError(f"Unsupported archive index schema {version}")
    if write:
        try:
            database.execute("PRAGMA journal_mode = WAL")
            database.executescript(SCHEMA)
            database.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        except sqlite3.Error:
            database.close()
            raise
    return database


class Indexer:
    def __init__(self, database, store, stop, *, limits, depth, nodes, expanded,
                 seven_zip, pdftotext, lhasa, pdf_python, nomarch=None):
        self.db = database
        self.store = store
        self.stop = stop
        self.limits = limits
        self.depth = depth
        self.nodes = nodes
        self.expanded = expanded
        self.options = {"seven_zip": seven_zip, "pdftotext": pdftotext,
                        "lhasa": lhasa, "pdf_python": pdf_python, "nomarch": nomarch}

    def check_stop(self):
        if self.stop.exists():
            raise Cancelled

    def hash_path(self, path):
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                self.check_stop()
                size += len(block)
                digest.update(block)
        return size, digest.hexdigest()

    def blob_path(self, digest):
        return self.store / digest[:2] / digest

    def add_blob(self, data):
        digest = hashlib.sha256(data).hexdigest()
        path = self.blob_path(digest)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
                stage = Path(temporary.name)
                temporary.write(data)
            try:
                stage.replace(path)
            finally:
                stage.unlink(missing_ok=True)
        return digest

    def analyse(self, path, name, digest, size, kind):
        # Gzip's fallback member name is sourced from its containing filename.
        key = stable_id(digest, kind, name if kind in {"gz", "tgz"} else "")
        prior = self.db.execute("SELECT status FROM analysis WHERE id=?", (key,)).fetchone()
        if prior is None:
            result = extract(path, name, kind, self.limits, **self.options)
            self.check_stop()
            self.db.execute("INSERT INTO analysis VALUES (?,?,?,?,?,?)",
                            (key, digest, kind, size, result.status, result.detail))
            for member in result.members:
                self.check_stop()
                member_hash = self.add_blob(member.data) if member.data is not None else None
                self.db.execute("INSERT INTO member VALUES (?,?,?,?,?,?)",
                                (key, member.ordinal, member.name, member.size,
                                 member_hash, member.status))
            for document in result.documents:
                title = next((s.strip()[:240] for s in document.text.splitlines() if s.strip()), "")
                self.db.execute("INSERT INTO document VALUES (?,?,?,?)",
                                (key, document.page, title, document.text))
            return key, result.status
        return key, prior["status"]

    def walk(self, source, path, name, chain, identity, parent, ordinal, size, digest,
             depth, status, budget):
        self.check_stop()
        budget["nodes"] += 1
        key = kind = None
        if digest is not None:
            kind = identify(path, name)
            if depth >= self.depth and kind in CONTAINER_KINDS:
                status = "depth_limit"
            else:
                key, status = self.analyse(path, name, digest, size, kind)
        self.db.execute("INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (identity, source, parent, ordinal, name, canonical(chain), depth,
                         size, digest, kind, key, status))
        if key is None:
            return
        children = self.db.execute(
            "SELECT * FROM member WHERE analysis_id=? ORDER BY ordinal", (key,)
        ).fetchall()
        for child in children:
            child_digest = child["digest"]
            child_size = child["size"]
            if (budget["nodes"] >= self.nodes or
                    child_digest is not None and budget["bytes"] + child_size > self.expanded):
                self.db.execute("UPDATE occurrence SET status='tree_limit' WHERE id=?", (identity,))
                break
            if child_digest is not None:
                budget["bytes"] += child_size
            child_name = child["name"]
            locator = {"name": child_name, "ordinal": child["ordinal"]}
            self.walk(source, self.blob_path(child_digest) if child_digest else None,
                      child_name, [*chain, locator], stable_id(identity, locator),
                      identity, child["ordinal"], child_size, child_digest,
                      depth + 1, child["status"], budget)

    def index_source(self, root, row):
        try:
            path = contained(root, row["local"])
            size, digest = self.hash_path(path)
            if (size, digest) != (row["expected_size"], row["expected_hash"]):
                raise IntegrityError(f"Receipt mismatch. Observed {size} bytes and SHA-256 {digest}")
        except (OSError, IntegrityError) as exc:
            self.db.execute("UPDATE source SET state='input_error',detail=? WHERE id=?",
                            (str(exc), row["id"]))
            return "input_error"
        name = PurePosixPath(row["rel"]).name
        self.walk(row["id"], path, name, [], row["id"], None, None, size, digest, 0,
                  "verified", Counter())
        self.db.execute("UPDATE source SET state='indexed',detail=NULL WHERE id=?", (row["id"],))
        return "indexed"


def import_manifest(db, root, receipts, check_stop):
    snapshot = str(root)
    with db:
        db.execute("CREATE TEMP TABLE IF NOT EXISTS current_manifest (id TEXT PRIMARY KEY)")
        db.execute("DELETE FROM current_manifest")
        for row in read_receipts(receipts):
            check_stop()
            identity = stable_id(row["url"])
            db.execute("INSERT INTO current_manifest VALUES (?)", (identity,))
            previous = db.execute("SELECT * FROM source WHERE id=?", (identity,)).fetchone()
            verified = row["status"] == "verified"
            identity_fields = (snapshot, row["rel"], row.get("local"), row.get("bytes"),
                               row.get("sha256"), row["status"])
            if previous is not None:
                old_fields = tuple(previous[k] for k in ("snapshot", "rel", "local", "expected_size",
                                                           "expected_hash", "receipt_status"))
                if identity_fields == old_fields:
                    db.execute("UPDATE source SET modified=? WHERE id=?", (row.get("modified"), identity))
                    continue
                if previous["snapshot"] != snapshot and previous["receipt_status"] == "verified" and not verified:
                    continue  # A pending receipt does not erase another snapshot's verified copy.
                db.execute("DELETE FROM source WHERE id=?", (identity,))
            db.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
                       (identity, row["url"], snapshot, row["rel"], row.get("local"),
                        row.get("modified"), row["status"], row.get("bytes"), row.get("sha256"),
                        "queued" if verified else "unavailable"))
        db.execute("DELETE FROM source WHERE snapshot=? AND id NOT IN (SELECT id FROM current_manifest)",
                   (snapshot,))


def configure(db, profile, store, update_tools):
    settings = {"profile": canonical(profile), "store": str(store)}
    with db:
        for key, value in settings.items():
            current = db.execute("SELECT value FROM configuration WHERE key=?", (key,)).fetchone()
            if current is not None and current["value"] != value:
                if key != "profile" or not update_tools:
                    raise IntegrityError(f"Index {key} changed. Retain original settings or use --update-tools.")
                previous = json.loads(current["value"])
                kinds = set()
                tool_kinds = {
                    "seven_zip": {"zip", "arj", "cab", "lzh", "7z", "rar", "mz",
                                  "iso9660", "udf"},
                    "lhasa": {"lzh"}, "pdftotext": {"pdf"}, "pdf_python": {"pdf"}, "nomarch": {"arc"},
                }
                for setting in set(previous) | set(profile):
                    if previous.get(setting) != profile.get(setting):
                        if setting not in tool_kinds:
                            raise IntegrityError("Index extraction bounds changed. Use a new database.")
                        kinds.update(tool_kinds[setting])
                if kinds:
                    rows = requeue_rows(db)
                    cache_ids = {row["id"] for row in db.execute("SELECT id,kind FROM analysis")
                                 if row["kind"] in kinds}
                    invalidate(db, rows, [row for row in rows if row["kind"] in kinds], cache_ids)
            db.execute("INSERT OR REPLACE INTO configuration VALUES (?,?)", (key, value))


def emit(value, stream=None):
    print(json.dumps(value, ensure_ascii=True, sort_keys=True),
          file=sys.stdout if stream is None else stream, flush=True)


def ingest(args):
    root = args.root.resolve(strict=True)
    if args.live:
        receipts = read_transfer_state(root / "transfer-state" / "mirror.sqlite3")
    else:
        receipts = read_manifest(args.manifest or root / "manifests" / "inventory.jsonl")
    store = (args.store or args.database.with_suffix(".blobs")).resolve()
    stop = (args.stop or args.database.with_suffix(".STOP")).resolve()
    if any(p.resolve().is_relative_to(root) for p in (store, args.database, stop)):
        raise IntegrityError("Store, database and stop sentinel must be outside the input root")
    limit = Limits()
    options = {"limits": limit, "depth": args.depth, "nodes": args.nodes, "expanded": args.expanded,
               "seven_zip": args.seven_zip, "pdftotext": args.pdftotext,
               "lhasa": args.lhasa, "pdf_python": args.pdf_python}
    if args.nomarch is not None:
        options["nomarch"] = args.nomarch
    profile = {key: str(value.resolve()) if isinstance(value, Path) else value
               for key, value in options.items()}
    profile["limits"] = asdict(limit)
    with closing(open_index(args.database, write=True)) as db:
        worker = Indexer(db, store, stop, **options)
        counts = Counter()
        try:
            worker.check_stop()
            configure(db, profile, store, args.update_tools)
            import_manifest(db, root, receipts, worker.check_stop)
            rows = db.execute("SELECT * FROM source WHERE snapshot=? AND receipt_status='verified' "
                              "ORDER BY rel, url", (str(root),)).fetchall()
            for row in rows:
                worker.check_stop()
                if args.select and not fnmatchcase(row["rel"].casefold(), args.select.casefold()):
                    continue
                if row["state"] == "indexed" and not args.recheck:
                    continue
                if args.max_files is not None and sum(counts.values()) >= args.max_files:
                    break
                with db:
                    db.execute("DELETE FROM occurrence WHERE source_id=?", (row["id"],))
                    status = worker.index_source(root, row)
                counts[status] += 1
                if args.progress and sum(counts.values()) % args.progress == 0:
                    emit({"event": "progress", "this_run": dict(counts)})
        except Cancelled:
            emit({"event": "cancelled", "this_run": dict(counts)})
            return 130
        emit({"event": "finished", "this_run": dict(counts), "index": summary(db)})
    return 0


def requeue_rows(db):
    return db.execute(
        "SELECT o.source_id,o.kind,o.status,o.analysis_id,s.rel "
        "FROM occurrence o JOIN source s ON s.id=o.source_id"
    ).fetchall()


def invalidate(db, rows, selected, cache_ids=()):
    analyses = {r["analysis_id"] for r in selected if r["analysis_id"] is not None}
    analyses.update(cache_ids)
    affected = {r["source_id"] for r in selected}
    # A shared analysis may have been reached through a different source.
    affected.update(r["source_id"] for r in rows if r["analysis_id"] in analyses)
    db.executemany("DELETE FROM occurrence WHERE source_id=?", ((s,) for s in sorted(affected)))
    db.executemany("UPDATE source SET state='queued',detail=NULL WHERE id=?",
                   ((s,) for s in sorted(affected)))
    ids = [(a,) for a in sorted(analyses)]
    db.executemany("DELETE FROM document WHERE analysis_id=?", ids)
    db.executemany("DELETE FROM analysis WHERE id=?", ids)
    return {"requeued_sources": len(affected), "invalidated_analyses": len(analyses)}


def requeue(args):
    with closing(open_index(args.database, write=True)) as db, db:
        rows = requeue_rows(db)
        selected = [r for r in rows
                    if (args.kind is None or r["kind"] == args.kind)
                    and (args.status is None or r["status"] == args.status)
                    and (args.select is None or fnmatchcase(r["rel"].casefold(), args.select.casefold()))]
        emit(invalidate(db, rows, selected))
    return 0


def grouped(db, query):
    return dict(db.execute(query).fetchall())


def summary(db):
    return {
        "receipts": grouped(db, "SELECT receipt_status,count(*) FROM source GROUP BY receipt_status"),
        "sources": grouped(db, "SELECT state,count(*) FROM source GROUP BY state"),
        "occurrences": grouped(db, "SELECT kind,count(*) FROM occurrence WHERE kind IS NOT NULL GROUP BY kind"),
        "analysis_status": grouped(db, "SELECT a.status,count(*) FROM analysis a WHERE EXISTS "
                                      "(SELECT 1 FROM occurrence o WHERE o.analysis_id=a.id) GROUP BY a.status"),
        "occurrence_status": grouped(db, "SELECT status,count(*) FROM occurrence GROUP BY status"),
        "unique_by_kind": grouped(db, "SELECT kind,count(DISTINCT digest) FROM occurrence "
                                    "WHERE digest IS NOT NULL GROUP BY kind"),
        "bytes_and_duplicates": dict(db.execute(
            "SELECT count(digest) AS hashed_occurrences, count(DISTINCT digest) AS unique_digests, "
            "count(digest)-count(DISTINCT digest) AS duplicate_occurrences, "
            "coalesce(sum(CASE WHEN depth=0 THEN size END),0) AS verified_root_bytes FROM occurrence"
        ).fetchone()),
        "documents": dict(db.execute(
            "SELECT count(*) AS indexed_pages, count(DISTINCT analysis_id) AS text_analyses "
            "FROM document WHERE EXISTS (SELECT 1 FROM occurrence o WHERE o.analysis_id=document.analysis_id)"
        ).fetchone()),
    }


LOCATION = "o.id,s.url,s.rel,s.modified,o.chain,o.name,o.kind,o.size,o.digest AS sha256"
JOIN = " FROM occurrence o JOIN source s ON s.id=o.source_id "


def query(args):
    with closing(open_index(args.database)) as db:
        if args.command == "stats":
            emit(summary(db))
            return 0
        if args.command == "sources":
            for row in db.execute("SELECT id,url,rel,modified,receipt_status,expected_size,expected_hash,state,detail "
                                  "FROM source WHERE (? IS NULL OR state=?) ORDER BY rel,url LIMIT ?",
                                  (args.state, args.state, args.limit)):
                emit(dict(row))
            return 0
        if args.command == "search":
            sql = ("SELECT " + LOCATION + ", document.page,document.title,"
                   "snippet(document,3,'[',']',' … ',22) AS snippet " + JOIN +
                   "JOIN document ON document.analysis_id=o.analysis_id WHERE document MATCH ? "
                   "ORDER BY bm25(document),s.rel,s.url,o.chain,document.page LIMIT ?")
            params = (args.match, args.limit)
        elif args.command == "files":
            sql = ("SELECT " + LOCATION + ",o.status,a.detail " + JOIN +
                   "LEFT JOIN analysis a ON a.id=o.analysis_id WHERE "
                   "(? IS NULL OR o.kind=?) AND (? IS NULL OR o.status=?) AND "
                   "(? IS NULL OR instr(lower(o.name), lower(?))>0) "
                   "ORDER BY s.rel,s.url,o.chain LIMIT ?")
            params = (args.kind, args.kind, args.status, args.status, args.name, args.name, args.limit)
        elif args.command == "document":
            sql = ("SELECT " + LOCATION + ",d.page,d.title,d.body " + JOIN +
                   "JOIN document d ON d.analysis_id=o.analysis_id "
                   "WHERE o.id=? AND (? IS NULL OR d.page=?) ORDER BY d.page LIMIT ?")
            params = (args.id, args.page, args.page, args.limit)
        else:
            sql = ("SELECT " + LOCATION + ",o.status " + JOIN +
                   "WHERE o.digest IN (SELECT digest FROM occurrence WHERE digest IS NOT NULL "
                   "GROUP BY digest HAVING count(*)>1) ORDER BY o.digest,s.rel,s.url,o.chain LIMIT ?")
            params = (args.limit,)
        for row in db.execute(sql, params):
            record = dict(row)
            record["chain"] = json.loads(record["chain"])
            emit(record)
    return 0


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("ingest", help="index verified sources and record residual statuses")
    run.add_argument("root", type=Path)
    inputs = run.add_mutually_exclusive_group()
    inputs.add_argument("--manifest", type=Path)
    inputs.add_argument("--live", action="store_true", help="snapshot committed transfer state read-only")
    run.add_argument("--store", type=Path)
    run.add_argument("--stop", type=Path)
    run.add_argument("--seven-zip", type=Path)
    run.add_argument("--lhasa", type=Path)
    run.add_argument("--nomarch", type=Path, help="Optional ARC methods 8/9 decoder with binary stdout")
    pdf = run.add_mutually_exclusive_group()
    pdf.add_argument("--pdftotext", type=Path)
    pdf.add_argument("--pdf-python", type=Path, help="Python interpreter with optional pypdf installed")
    run.add_argument("--update-tools", action="store_true", help="requeue only analyses affected by tool changes")
    run.add_argument("--depth", type=positive, default=8)
    run.add_argument("--nodes", type=positive, default=20_000)
    run.add_argument("--expanded", type=positive, default=256 * 1024 * 1024)
    run.add_argument("--max-files", type=positive)
    run.add_argument("--progress", type=positive, default=50)
    run.add_argument("--select", help="case-insensitive glob for original source paths")
    run.add_argument("--recheck", action="store_true", help="verify bytes again and rebuild occurrence paths")
    refresh = commands.add_parser("requeue", help="invalidate cached analyses and queue affected sources")
    refresh.add_argument("--kind")
    refresh.add_argument("--status")
    refresh.add_argument("--select")
    commands.add_parser("stats")
    files = commands.add_parser("files")
    files.add_argument("--kind")
    files.add_argument("--status")
    files.add_argument("--name", help="case-insensitive substring of the member or root name")
    search = commands.add_parser("search")
    search.add_argument("match", help="SQLite FTS5 query")
    document = commands.add_parser("document", help="read indexed pages for an occurrence ID")
    document.add_argument("id")
    document.add_argument("--page", type=int)
    sources = commands.add_parser("sources")
    sources.add_argument("--state")
    duplicates = commands.add_parser("duplicates")
    for command in (files, search, duplicates, document, sources):
        command.add_argument("--limit", type=positive, default=100)
    args = parser.parse_args(argv)
    if args.command == "requeue" and args.kind is None and args.select is None and args.status is None:
        parser.error("requeue needs --kind, --status or --select")
    if args.command == "ingest" and args.depth > 64:
        parser.error("depth must be at most 64")
    try:
        action = {"ingest": ingest, "requeue": requeue}.get(args.command, query)
        return action(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        emit({"error": str(exc)}, sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
