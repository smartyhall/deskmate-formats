"""Rehearse the archive-index migration on disposable copies only.

The live index is never opened here: every database is created in a temporary
directory from the version-1 schema that the indexer writes.
"""

from contextlib import closing
import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    import archive_intelligence as index
    import index_migration as migration


def v1_database(path, rows=(('a1', 'd1', 'zip'), ('a2', 'd2', 'mz'), ('a3', 'd3', 'text'))):
    database = sqlite3.connect(path)
    database.executescript(index.SCHEMA)
    database.execute(f'PRAGMA user_version = {index.SCHEMA_VERSION}')
    database.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     ('s1', 'https://example.invalid/x', 'snap', 'x.zip', 'x.zip',
                      None, 'verified', 10, 'd1', 'ingested', None))
    for analysis_id, digest, kind in rows:
        database.execute("INSERT INTO analysis VALUES (?,?,?,?,?,?)",
                         (analysis_id, digest, kind, 10, 'ok', None))
        database.execute("INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (f'o-{analysis_id}', 's1', None, 0, f'{analysis_id}.bin',
                          f'{analysis_id}.bin', 0, 10, digest, kind, analysis_id, 'ok'))
    database.commit()
    database.close()


class MigrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.database = self.root / 'index.sqlite3'
        v1_database(self.database)

    def test_plan_is_additive_and_ends_with_the_new_version(self):
        steps = migration.plan(self.database)
        self.assertIn('CREATE TABLE IF NOT EXISTS identity', steps[0])
        self.assertTrue(any(step.startswith('ALTER TABLE occurrence ADD COLUMN derived')
                            for step in steps))
        self.assertEqual(steps[-1], 'PRAGMA user_version = 2')
        self.assertFalse(any('DROP ' in step or step.startswith('DELETE') or step.startswith('UPDATE')
                             for step in steps))

    def test_migration_preserves_version_one_rows_and_backfills_without_confidence(
            self):
        before = self._rows()
        migration.migrate(self.database)
        self.assertEqual(self._rows(), before)
        report = migration.inspect(self.database)
        self.assertEqual(report['version'], 2)
        self.assertEqual(report['axes']['structural'], {'mz': 1, 'text': 1, 'zip': 1})
        self.assertEqual(report['duplicate_kinds'], 0)
        with closing(sqlite3.connect(self.database)) as database:
            # Version 1 stored a kind but not the axis that decided it, so the
            # backfill must not claim certainty it does not have.
            self.assertEqual(
                database.execute("SELECT confidence, evidence FROM identity "
                                 "WHERE analysis_id='a1'").fetchone(),
                ('unknown', 'backfilled-from-schema-v1-kind-only'))
            self.assertEqual(
                database.execute("SELECT derived, origin_id FROM occurrence "
                                 "WHERE id='o-a1'").fetchone(), (0, None))
        self.assertEqual(report['confidence']['structural'], {'unknown': 3})

    def test_a_completed_migration_can_be_restarted_as_a_no_op(self):
        migration.migrate(self.database)
        self.assertEqual(migration.migrate(self.database), [])
        self.assertEqual(migration.plan(self.database), [])
        self.assertEqual(migration.inspect(self.database)['axes']['structural'],
                         {'mz': 1, 'text': 1, 'zip': 1})

    def test_an_interrupted_migration_leaves_version_one_intact(self):
        steps = [migration.STATEMENTS[0], 'THIS IS NOT SQL']
        with patch.object(migration, 'plan', return_value=steps):
            with self.assertRaises(sqlite3.Error):
                migration.migrate(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            self.assertEqual(database.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertFalse(database.execute(
                "SELECT name FROM sqlite_master WHERE name='identity'").fetchall())
        # The untouched database migrates cleanly afterwards.
        migration.migrate(self.database)
        self.assertEqual(migration.inspect(self.database)['version'], 2)

    def test_selective_reprocessing_lists_only_the_missing_axis(self):
        migration.migrate(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            database.execute("INSERT INTO identity VALUES ('a1','embedded','zip','certain','mz-plus-zip')")
            database.commit()
        self.assertEqual(migration.missing_axis(self.database, 'embedded'), ['d2', 'd3'])
        self.assertEqual(migration.missing_axis(self.database, 'carrier'), ['d1', 'd2', 'd3'])

    def test_an_unknown_version_is_not_touched(self):
        with closing(sqlite3.connect(self.database)) as database:
            database.execute('PRAGMA user_version = 99')
        with self.assertRaises(ValueError):
            migration.plan(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            self.assertEqual(database.execute('PRAGMA user_version').fetchone()[0], 99)

    def test_classification_axes_are_stored_separately(self):
        from types import SimpleNamespace
        migration.migrate(self.database)
        found = SimpleNamespace(kind='zip', extension_kind='mz', carrier='pe',
                                embedded=('zip',), confidence='certain')
        with closing(sqlite3.connect(self.database)) as database:
            rows = migration.record_classification(database, 'a1', found, 'pe-plus-zip')
            database.commit()
        self.assertEqual([row[1:] for row in rows],
                         [('structural', 'zip', 'certain', 'pe-plus-zip'),
                          ('extension', 'mz', 'probable', 'pe-plus-zip'),
                          ('carrier', 'pe', 'certain', 'pe-plus-zip'),
                          ('embedded', 'zip', 'certain', 'pe-plus-zip')])
        report = migration.inspect(self.database)
        self.assertEqual(report['axes']['carrier'], {'pe': 1})
        self.assertEqual(report['axes']['embedded'], {'zip': 1})
        # The payload keeps its own row instead of overwriting the kind.
        self.assertEqual(report['axes']['structural']['zip'], 1)
        self.assertEqual(report['duplicate_kinds'], 0)

    def test_malformed_identity_rows_are_refused(self):
        from types import SimpleNamespace
        migration.migrate(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            for found in (SimpleNamespace(kind='', extension_kind=None, carrier=None,
                                          embedded=(), confidence='certain'),
                          SimpleNamespace(kind='zip', extension_kind=None, carrier=None,
                                          embedded=(), confidence='absolute')):
                with self.assertRaises(ValueError):
                    migration.record_classification(database, 'a1', found, 'probe')
            with self.assertRaises(ValueError):
                migration.record_classification(
                    database, 'a1', SimpleNamespace(kind='zip', extension_kind=None,
                                                    carrier=None, embedded=(),
                                                    confidence='certain'), '')
            with self.assertRaises(ValueError):
                migration.record_evidence(database, 'a1', 'guessed', 'yes')

    def test_recording_the_same_identity_refines_it_instead_of_duplicating(self):
        from types import SimpleNamespace
        migration.migrate(self.database)
        found = SimpleNamespace(kind='zip', extension_kind=None, carrier=None,
                                embedded=(), confidence='certain')
        with closing(sqlite3.connect(self.database)) as database:
            migration.record_classification(database, 'a1', found, 'classified')
            database.commit()
            row = database.execute("SELECT confidence, evidence, COUNT(*) FROM identity "
                                   "WHERE analysis_id='a1' AND axis='structural'").fetchone()
        self.assertEqual(tuple(row), ('certain', 'classified', 1))

    def test_two_different_structural_kinds_are_flagged(self):
        migration.migrate(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            database.execute("INSERT INTO identity VALUES ('a1','structural','mz','certain','probe')")
            database.commit()
        self.assertEqual(migration.inspect(self.database)['duplicate_kinds'], 1)

    def test_evidence_is_recorded_apart_from_identity(self):
        migration.migrate(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            migration.record_evidence(database, 'a1', 'completeness', 'complete')
            migration.record_evidence(database, 'a1', 'integrity', 'verified-crc')
            database.commit()
        report = migration.inspect(self.database)
        self.assertEqual(report['evidence'], {'completeness': 1, 'integrity': 1})
        self.assertEqual(report['axes']['structural']['zip'], 1)

    def test_identity_rows_require_a_migrated_database(self):
        from types import SimpleNamespace
        found = SimpleNamespace(kind='zip', extension_kind=None, carrier=None,
                                embedded=(), confidence='certain')
        with closing(sqlite3.connect(self.database)) as database:
            with self.assertRaises(ValueError):
                migration.record_classification(database, 'a1', found, 'probe')

    def test_originals_and_derivatives_can_be_distinguished(self):
        migration.migrate(self.database)
        with closing(sqlite3.connect(self.database)) as database:
            database.execute("INSERT INTO occurrence VALUES "
                             "('o-derived','s1','o-a1',1,'disk.img','x.zip/disk.img',1,10,"
                             "'d4','disk-image','a1','ok',1,'o-a1')")
            database.commit()
        with closing(sqlite3.connect(self.database)) as database:
            derived = database.execute(
                "SELECT origin_id FROM occurrence WHERE derived = 1").fetchall()
        self.assertEqual(derived, [('o-a1',)])

    def _rows(self):
        # Only the version-1 columns: the added ones are intentionally new.
        with closing(sqlite3.connect(self.database)) as database:
            analysis = database.execute(
                "SELECT id, digest, kind, size, status, detail FROM analysis ORDER BY id").fetchall()
            occurrence = database.execute(
                "SELECT id, source_id, parent_id, ordinal, name, chain, depth, size, digest, "
                "kind, analysis_id, status FROM occurrence ORDER BY id").fetchall()
        return analysis, occurrence


if __name__ == '__main__':
    unittest.main()
