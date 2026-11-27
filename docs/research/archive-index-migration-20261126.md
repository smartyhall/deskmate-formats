# Archive index migration proposal — identity axes and selective reprocessing

Campaign `freebuff/archive-qualification-2`. This is a proposal with a
rehearsal, not an applied migration. The live index, the downloader and the
index writer are untouched.

## The problem

`tools/archive/archive_intelligence.py` stores one `kind` per `analysis` row and
one per `occurrence` row. The 2026-11-26 corpus measurement showed why that is
not enough: of 106 executables in the mirror, **90 also carry an embedded ZIP**.
A single column can record either identity, and whichever the indexer writes
second silently erases the first. The same column also cannot express doubt: a
`PK` signature inside an executable is certain, an extension is only a hint, and
a damaged header can leave the structural kind unknown while the bytes are
still identifiable by extension.

## Proposed schema version 2

The change is purely additive. No version-1 column is removed, renamed or
retyped, so every existing query keeps working.

```sql
CREATE TABLE identity (
    analysis_id TEXT NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
    axis        TEXT NOT NULL,   -- structural | carrier | embedded | extension
    value       TEXT NOT NULL,   -- a kind token, e.g. zip, mz, arj
    confidence  TEXT NOT NULL,   -- certain | probable | ambiguous | none
    evidence    TEXT NOT NULL,   -- short token, e.g. mz-plus-embedded-zip
    PRIMARY KEY (analysis_id, axis, value)
);
CREATE TABLE analysis_evidence (
    analysis_id TEXT NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,   -- completeness | integrity | unsupported-method
    value       TEXT NOT NULL,
    PRIMARY KEY (analysis_id, key)
);
ALTER TABLE occurrence ADD COLUMN derived INTEGER NOT NULL DEFAULT 0;
ALTER TABLE occurrence ADD COLUMN origin_id TEXT REFERENCES occurrence(id);
CREATE INDEX analysis_digest ON analysis(digest);
CREATE INDEX identity_value ON identity(axis, value);
```

`occurrence.derived` and `origin_id` answer a different question from the
identity axes: a normalised logical image produced from a sector container is a
derivative of a specific original, and a recovery tool must not present it as
the artifact that was acquired. Version 1 cannot express that relationship at
all.

## Migration rules

1. Version 1 is required to migrate. Any other `user_version` is refused.
2. `identity` is backfilled from `analysis.kind` with `axis='structural'`,
   `confidence='certain'` and `evidence='backfilled-from-schema-v1'`. Only a
   value that is already stored is turned into a row, so the backfill cannot
   invent a measurement.
3. New occurrence columns default to `derived=0, origin_id=NULL`, which is the
   only defensible reading of a version-1 row.
4. `user_version` becomes 2 only after every statement succeeds; the whole
   migration runs in one transaction.
5. Rollback is `DROP TABLE identity`, `DROP TABLE analysis_evidence`, dropping
   the two indexes and the two added columns, then `user_version = 1`. This is
   documented rather than automated because SQLite cannot drop a column before
   3.35 and the rehearsal does not need it.

## Selective reprocessing

`analysis.digest` is the SHA-256 of the artifact, so a newly available handler
does not need a rescan. The question "which artifacts lack this axis?" is one
query:

```sql
SELECT DISTINCT a.digest FROM analysis a
WHERE NOT EXISTS (SELECT 1 FROM identity i
                  WHERE i.analysis_id = a.id AND i.axis = ?)
```

`index_migration.missing_axis()` runs exactly that, and `analysis_digest` makes
it a lookup rather than a scan. Reprocessing then reads the stored blob for a
digest and appends identity and evidence rows. The rehearsal confirms that a
value added for one artifact removes only that digest from the result, so a
partial reprocess is resumable and idempotent.

## Rehearsal evidence

`tools/archive/index_migration.py` implements the plan, the migration and the
two reports. `tests/portable/test_archive_index_migration.py` builds throwaway
version-1 databases from the indexer's own `SCHEMA` and checks six properties:
the plan is additive and ends by setting version 2; every version-1 row survives
byte for byte; the backfilled identity rows carry the recorded evidence token;
a second migration is refused without changing anything; the selective query
returns exactly the digests missing an axis; and an unknown version is left
untouched. An `origin_id` row is also shown to distinguish a derivative from its
original.

The module refuses to be pointed at a live database by accident only in the
sense that it requires `--database` and prints the plan unless `--write` is
given. It cannot detect whether a path is the live index: **operators must pass
a copy.**

## Why it is not applied

`archive_intelligence.open_index` rejects any `user_version` other than
`SCHEMA_VERSION` (1). A migrated database would therefore be unreadable by the
current indexer. Adoption needs the indexer to accept version 2 in a reviewed
change, together with a decision about when new analyses write identity rows.
That is exactly the coordination the campaign rules require before touching the
archive index, so this checkpoint stops at a rehearsed proposal.

## Remaining work

1. Teach the indexer to write and read version 2, behind a flag at first.
2. Backfill identity rows for the existing corpus from stored analyses only.
3. Extend `missing_axis()` into a resumable reprocessing queue with a receipt.
4. Decide whether `analysis.kind` remains as a denormalised convenience column
   or is dropped in version 3.
