"""Propose and rehearse the archive-index schema migration, never apply it live.

The index stores one `kind` per analysis and per occurrence. That cannot
represent an executable carrying an embedded archive, and it cannot say which
extraction capabilities were exercised. This module defines version 2 as
purely additive changes and rehearses them against a database path you supply:

* a new `identity` table holds one row per axis (structural, carrier, embedded,
  extension) with a value, a confidence and a short evidence token;
* a new `analysis_evidence` table holds the other observations (unpacked size,
  completeness, integrity result, unsupported methods);
* `occurrence` gains `derived` and `origin_id` so a normalised image or a
  stacked derivative can be told apart from the original artifact;
* `analysis.digest` is indexed so a new handler can reprocess only the artifacts
  that lack its axis instead of rescanning every source.

No version-1 column is removed, renamed or retyped, and every backfilled value
comes from data that is already stored, so the rehearsal can be undone by
dropping the added objects and resetting `user_version` to 1.

Adoption is deliberately out of scope: `archive_intelligence.open_index`
rejects any version other than 1, so a migrated database is not readable by the
current indexer. The indexer must accept version 2 in a reviewed change first,
and the live database is not touched here.
"""

import argparse
import sqlite3
from pathlib import Path
import sys


TARGET_VERSION = 2

STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS identity (
        analysis_id TEXT NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
        axis TEXT NOT NULL,
        value TEXT NOT NULL,
        confidence TEXT NOT NULL,
        evidence TEXT NOT NULL,
        PRIMARY KEY (analysis_id, axis, value)
    )""",
    """CREATE TABLE IF NOT EXISTS analysis_evidence (
        analysis_id TEXT NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (analysis_id, key)
    )""",
    "CREATE INDEX IF NOT EXISTS analysis_digest ON analysis(digest)",
    "CREATE INDEX IF NOT EXISTS identity_value ON identity(axis, value)",
)

ADDED_COLUMNS = (
    ("occurrence", "derived", "INTEGER NOT NULL DEFAULT 0"),
    ("occurrence", "origin_id", "TEXT"),
)

# Version-1 evidence tokens that remain true after the migration.
BACKFILL = """INSERT OR IGNORE INTO identity(analysis_id, axis, value, confidence, evidence)
              SELECT id, 'structural', kind, 'certain', 'backfilled-from-schema-v1'
              FROM analysis WHERE kind IS NOT NULL AND kind <> ''"""


def _columns(database, table):
    return {row[1] for row in database.execute(f"PRAGMA table_info({table})")}


def plan(path):
    """Return the statements that a migration of `path` would run."""
    database = _open(path, write=False)
    try:
        version = database.execute("PRAGMA user_version").fetchone()[0]
        if version != 1:
            raise ValueError(f"expected schema version 1, found {version}")
        for table in ("analysis", "occurrence", "source", "member"):
            if not _columns(database, table):
                raise ValueError(f"schema version 1 without a {table} table")
        steps = list(STATEMENTS)
        for table, column, declaration in ADDED_COLUMNS:
            if column not in _columns(database, table):
                steps.append(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        steps += [BACKFILL, f"PRAGMA user_version = {TARGET_VERSION}"]
        return steps
    finally:
        database.close()


def _open(path, *, write):
    path = Path(path)
    if write:
        database = sqlite3.connect(path)
    else:
        database = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    return database


def migrate(path):
    """Apply the version-2 changes to `path`, which must be a disposable copy."""
    path = Path(path)
    steps = plan(path)
    database = _open(path, write=True)
    try:
        with database:
            for statement in steps:
                database.execute(statement)
        return steps
    finally:
        database.close()


def inspect(path):
    """Report the stored identity axes and the artifacts still missing one."""
    database = _open(path, write=False)
    try:
        version = database.execute("PRAGMA user_version").fetchone()[0]
        report = {"version": version, "axes": {}, "duplicate_kinds": 0}
        if version < TARGET_VERSION:
            return report
        for row in database.execute("SELECT axis, value, COUNT(*) FROM identity "
                                    "GROUP BY axis, value ORDER BY axis, value"):
            report["axes"].setdefault(row[0], {})[row[1]] = row[2]
        report["duplicate_kinds"] = database.execute(
            "SELECT COUNT(*) FROM (SELECT analysis_id FROM identity "
            "WHERE axis='structural' GROUP BY analysis_id HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        return report
    finally:
        database.close()


def missing_axis(path, axis):
    """Digests whose analysis has no value for `axis`, for selective reprocessing.

    A new handler can reprocess exactly these artifacts. The query reads only
    stored metadata, so it never touches the downloader or the source tree.
    """
    database = _open(path, write=False)
    try:
        rows = database.execute(
            "SELECT DISTINCT a.digest FROM analysis a WHERE NOT EXISTS "
            "(SELECT 1 FROM identity i WHERE i.analysis_id = a.id AND i.axis = ?)",
            (axis,)).fetchall()
        return [row[0] for row in rows]
    finally:
        database.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", required=True,
                        help="path to a disposable copy of the archive index")
    parser.add_argument("--write", action="store_true",
                        help="apply the migration; without it only the plan is printed")
    parser.add_argument("--axis", help="report the digests missing this identity axis")
    options = parser.parse_args(argv)
    if not options.write:
        for statement in plan(options.database):
            print(statement)
        return 0
    migrate(options.database)
    report = inspect(options.database)
    print(f"schema version {report['version']}; axes {report['axes']}")
    if options.axis:
        digests = missing_axis(options.database, options.axis)
        print(f"{len(digests)} artifacts have no {options.axis} identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
