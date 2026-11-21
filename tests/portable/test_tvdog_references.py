"""Validate the public archive references without a private mirror."""
import importlib.util
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit


REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs/ecosystem'


def read_json(name):
    return json.loads((DOCS / name).read_text(encoding='utf-8'))


class TVDogReferenceTests(unittest.TestCase):
    def setUp(self):
        self.library = read_json('tvdog-reference.json')
        self.ecosystem = read_json('catalog.json')

    @unittest.skipUnless(importlib.util.find_spec('jsonschema'), 'optional jsonschema')
    def test_public_reference_schema(self):
        from jsonschema import Draft202012Validator, FormatChecker

        schema = read_json('tvdog-reference.schema.json')
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(self.library)

    def test_links_and_source_identities(self):
        entries = self.ecosystem['entries']
        products = {entry['id'] for entry in entries}
        self.assertEqual(len(products), len(entries))
        for entry in entries:
            self.assertFalse(set(entry['source_ids']) - set(self.ecosystem['sources']), entry['id'])

        records = self.library['records']
        references = {record['id'] for record in records}
        self.assertEqual(len(references), len(records))
        self.assertEqual(len({lead['id'] for lead in self.library['leads']}), len(self.library['leads']))
        hashes = {}
        members = {}
        for record in records:
            with self.subTest(reference=record['id']):
                self.assertFalse(set(record.get('products', [])) - products)
                self.assertFalse(set(record.get('related_refs', [])) - references)
                self.assertNotIn(record['id'], record.get('related_refs', []))
                for link in record.get('project_refs', []):
                    document = (DOCS / link).resolve()
                    self.assertTrue(document.is_relative_to(REPO))
                    self.assertTrue(document.is_file(), link)
                for source in record['sources']:
                    url = source['url']
                    self.assertTrue(urlsplit(url).netloc)
                    if 'sha256' in source:
                        identity = (source['sha256'], source['bytes'])
                        self.assertEqual(hashes.setdefault(url, identity), identity)
                    for member in source.get('members', []):
                        key = (url, tuple(member['path']))
                        identity = (member['sha256'], member['bytes'])
                        self.assertEqual(members.setdefault(key, identity), identity)
        for lead in self.library['leads']:
            self.assertFalse(set(lead['reference_ids']) - references, lead['id'])
