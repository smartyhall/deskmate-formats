# SPDX-FileCopyrightText: 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.archive.faxback_ocr import candidates, metadata_evidence


class FaxbackOcrTests(unittest.TestCase):
    def test_keep_catalog_and_document_zero_variants_distinct(self):
        result = metadata_evidence(['Fax Back No. 1234', '26 - 0123 and 026-4567'],
                                   '01234', ('026-0123', '026-4567'))
        self.assertTrue(result['number_zero_variant'])
        self.assertFalse(result['number_exact'])
        self.assertEqual(result['catalog_exact'], ['026-4567'])
        self.assertEqual(result['catalog_zero_variant'], ['26-0123'])
        self.assertTrue(metadata_evidence(['Document #88888'], '01234', ())['number_conflict'])
        revision = metadata_evidence(['Catalog 25-1082A and 025-1082A and 25-1082'],
                                     '01234', ('025-1082A',))
        self.assertEqual(revision['catalog_exact'], ['025-1082A'])
        self.assertEqual(revision['catalog_zero_variant'], ['25-1082A'])
        self.assertNotIn('25-1082', revision['catalog_zero_variant'])


    def test_select_only_scans_in_general_triage(self):
        with TemporaryDirectory() as temp:
            index = Path(temp) / 'faxback.sqlite'
            library = Path(temp) / 'library.sqlite'
            db = sqlite3.connect(index)
            db.executescript("""
                CREATE TABLE record(url, path, sha256, number, format);
                CREATE TABLE catalog_ref(url, catalog);
                INSERT INTO record VALUES ('u1', '01001.pdf', 'a', 1001, 'pdf');
                INSERT INTO record VALUES ('u2', '01002.pdf', 'b', 1002, 'pdf');
                INSERT INTO record VALUES ('u3', '01003.pdf', 'c', 1003, 'pdf');
                INSERT INTO catalog_ref VALUES ('u2', '026-0123');
            """)
            db.close()
            db = sqlite3.connect(library)
            db.executescript("""
                CREATE TABLE analysis(kind, digest, status, detail);
                INSERT INTO analysis VALUES ('pdf', 'a', 'ok', 'has text');
                INSERT INTO analysis VALUES ('pdf', 'b', 'unsupported', '1 page; ocr-triage');
                INSERT INTO analysis VALUES ('pdf', 'c', 'unsupported', 'no-pdf-text-ocr-required');
            """)
            db.close()
            self.assertEqual(list(candidates(index, library, 1001)),
                             [('u2', '01002.pdf', 'b', 1002, ('026-0123',)),
                              ('u3', '01003.pdf', 'c', 1003, ())])
            self.assertEqual(list(candidates(index, library, 1003)),
                             [('u3', '01003.pdf', 'c', 1003, ())])
            self.assertEqual(list(candidates(index, library, 1004)), [])
