"""Propose and rehearse the archive-index schema migration, never apply it live.

The version-1 index stores one `kind` per analysis and per occurrence. That
cannot represent an executable carrying an embedded archive, it cannot say which
axis decided the kind, and it cannot say which extraction capabilities were
exercised. Version 2 is purely additive:

* an `identity` table holds one row per axis and value, with a confidence and a
  short evidence token. The axes are kept apart on purpose -- ``structural``,
  ``extension``, ``carrier`` and ``embedded`` -- so a self-extracting archive is
  three identities rather than one label, and an extension discrepancy stays
  visible next to a genuine second identity;
* an `analysis_evidence` table holds the observations that are not identities:
  unpacked size, completeness, integrity result, unsupported methods and the
  recovery outcome;
* `occurrence` gains `derived` and `origin_id` so a normalised image or a stacked
  derivative can be told apart from the original artifact;
* `analysis.digest` is indexed so a new handler can reprocess only the artifacts
  that lack its axis instead of rescanning every source.

No version-1 column is removed, renamed or retyped, and every backfilled value
comes from data that is already stored. The backfill deliberately records
``confidence = 'unknown'``: version 1 kept only the kind, so it cannot say
whether a structural signature, a name or textual content produced it, and
inventing ``certain`` would be exactly the collapse this schema exists to
prevent. A later pass can refine those rows through
:func:`record_classification` and :func:`missing_axis`.

Adoption is deliberately out of scope: `archive_intelligence.open_index`
rejects any version other than 1, so a migrated database is not readable by the
current indexer. The indexer must accept version 2 in a reviewed change first,
and the live database is not touched here.

A migration is transactional, so an interrupted run leaves the database at
version 1, and re-running a completed one is a no-op rather than an error.
"""

import argparse
import sqlite3
from pathlib import Path
import sys


TARGET_VERSION = 2

# One identifier per axis. ``extension`` is the identifier a suffix implies,
# ``carrier`` is the executable wrapper and ``embedded`` is a payload found
# inside that wrapper; none of them replaces ``structural``.
AXES = ('structural', 'extension', 'carrier', 'embedded')
CONFIDENCES = ('certain', 'probable', 'unknown')
EVIDENCE_KEYS = ('completeness', 'integrity', 'unpacked-size', 'unsupported-methods',
                 'recovery', 'classification')

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
    """CREATE INDEX IF NOT EXISTS analysis_digest ON analysis(digest)""",
    """CREATE INDEX IF NOT EXISTS identity_value ON identity(axis, value)""",
)

ADDED_COLUMNS = (
    ("occurrence", "derived", "INTEGER NOT NULL DEFAULT 0"),
    ("occurrence", "origin_id", "TEXT"),
)

# Version-1 evidence tokens that remain true after the migration. The axis is
# known (the indexer recorded a kind) but the deciding evidence is not, so the
# confidence stays unknown until a classified pass replaces it.
BACKFILL = """INSERT OR IGNORE INTO identity(analysis_id, axis, value, confidence, evidence)
              SELECT id, 'structural', kind, 'unknown', 'backfilled-from-schema-v1-kind-only'
              FROM analysis WHERE kind IS NOT NULL AND kind <> ''"""


def _columns(database, table):
    return {row[1] for row in database.execute(f"PRAGMA table_info({table})")}


def plan(path):
    """Return the statements that a migration of `path` would run.

    A database already at the target version needs nothing, so an interrupted
    rehearsal can be restarted by running the same command again.
    """
    database = _open(path, write=False)
    try:
        version = database.execute("PRAGMA user_version").fetchone()[0]
        if version == TARGET_VERSION:
            return []
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
        # DDL is only transactional under an explicit transaction; the legacy
        # implicit-commit behaviour would leave a half-migrated schema behind.
        database = sqlite3.connect(path, isolation_level=None)
    else:
        database = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    return database


def migrate(path):
    """Apply the version-2 changes to `path`, which must be a disposable copy."""
    path = Path(path)
    steps = plan(path)
    if not steps:
        return []
    database = _open(path, write=True)
    try:
        database.execute('BEGIN IMMEDIATE')
        try:
            for statement in steps:
                database.execute(statement)
            database.execute('COMMIT')
        except sqlite3.Error:
            database.execute('ROLLBACK')
            raise
        return steps
    finally:
        database.close()


def _require_migrated(database):
    version = database.execute("PRAGMA user_version").fetchone()[0]
    if version != TARGET_VERSION:
        raise ValueError(f"identity rows require schema version {TARGET_VERSION}, "
                         f"found {version}")


def _insert_identities(database, rows):
    """Validate and insert identity rows, refusing silent duplicates.

    A duplicate ``(analysis_id, axis, value)`` means the same identity was
    recorded twice, so the primary key raises instead of quietly keeping one.
    """
    for analysis_id, axis, value, confidence, evidence in rows:
        if axis not in AXES:
            raise ValueError(f"unknown identity axis {axis!r}")
        if not value:
            raise ValueError("an identity value must not be empty")
        if confidence not in CONFIDENCES:
            raise ValueError(f"unknown confidence {confidence!r}")
        if not evidence:
            raise ValueError("an identity row needs an evidence token")
    # Recording the same identity again refines its confidence and evidence, so
    # a classified pass can replace a backfilled 'unknown' row in place. A
    # *different* value for the same axis is a second identity, not a duplicate,
    # and ``inspect`` reports it through ``duplicate_kinds``.
    database.executemany(
        "INSERT INTO identity(analysis_id, axis, value, confidence, evidence) "
        "VALUES (?,?,?,?,?) ON CONFLICT(analysis_id, axis, value) DO UPDATE SET "
        "confidence=excluded.confidence, evidence=excluded.evidence", rows)


def record_classification(database, analysis_id, classification, evidence):
    """Record every identity axis of one classification as its own row.

    ``classification`` is an ``intelligence_extract.Classification`` (or any
    object with the same attributes). The structural kind is written first and
    is never overwritten by a carrier or an embedded payload, so no format label
    is collapsed into another.
    """
    _require_migrated(database)
    rows = [(analysis_id, 'structural', classification.kind, classification.confidence,
             evidence)]
    if classification.extension_kind:
        rows.append((analysis_id, 'extension', classification.extension_kind,
                     'probable', evidence))
    if classification.carrier:
        rows.append((analysis_id, 'carrier', classification.carrier, 'certain', evidence))
    for value in dict.fromkeys(classification.embedded):
        rows.append((analysis_id, 'embedded', value, classification.confidence, evidence))
    with database:
        _insert_identities(database, rows)
    return rows


def record_evidence(database, analysis_id, key, value):
    """Record one non-identity observation, such as completeness or integrity."""
    _require_migrated(database)
    if key not in EVIDENCE_KEYS:
        raise ValueError(f"unknown evidence key {key!r}")
    if not value:
        raise ValueError("an evidence value must not be empty")
    with database:
        database.execute("INSERT INTO analysis_evidence(analysis_id, key, value) "
                         "VALUES (?,?,?)", (analysis_id, key, value))


def inspect(path):
    """Report the stored identity axes, confidences and the artifacts missing one."""
    database = _open(path, write=False)
    try:
        version = database.execute("PRAGMA user_version").fetchone()[0]
        report = {"version": version, "axes": {}, "confidence": {}, "evidence": {},
                  "duplicate_kinds": 0}
        if version < TARGET_VERSION:
            return report
        for row in database.execute("SELECT axis, value, COUNT(*) FROM identity "
                                    "GROUP BY axis, value ORDER BY axis, value"):
            report["axes"].setdefault(row[0], {})[row[1]] = row[2]
        for row in database.execute("SELECT axis, confidence, COUNT(*) FROM identity "
                                    "GROUP BY axis, confidence ORDER BY axis, confidence"):
            report["confidence"].setdefault(row[0], {})[row[1]] = row[2]
        for row in database.execute("SELECT key, COUNT(*) FROM analysis_evidence "
                                    "GROUP BY key ORDER BY key"):
            report["evidence"][row[0]] = row[1]
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
    if axis not in AXES:
        raise ValueError(f"unknown identity axis {axis!r}")
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
        steps = plan(options.database)
        if not steps:
            print(f"schema version {TARGET_VERSION} is already current; nothing to do")
            return 0
        for statement in steps:
            print(statement)
        return 0
    migrate(options.database)
    report = inspect(options.database)
    print(f"schema version {report['version']}; axes {report['axes']}; "
          f"confidence {report['confidence']}")
    if options.axis:
        digests = missing_axis(options.database, options.axis)
        print(f"{len(digests)} artifacts have no {options.axis} identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
