"""Check the public purchase records without using the private archive."""

from datetime import date
import json
from pathlib import Path, PurePosixPath
import unittest
from urllib.parse import urlsplit

ECOSYSTEM = Path(__file__).resolve().parents[2] / "docs" / "ecosystem"
PRICE_BASIS = {"advertised", "bundle", "conditional-promotion", "launch", "option", "suggested-retail"}


class DemonstratorPurchaseFactsTests(unittest.TestCase):
    def setUp(self):
        document = ECOSYSTEM / "demonstrator-purchase-facts.json"
        self.facts = json.loads(document.read_text(encoding="utf-8"))
        self.sources = {source["id"]: source for source in self.facts["sources"]}

    def assert_sources(self, evidence):
        self.assertTrue(evidence)
        for ref in evidence:
            self.assertIn(ref["source_id"], self.sources)
            self.assertNotEqual("page" in ref, "lines" in ref)
            if "page" in ref:
                self.assertTrue(1 <= ref["page"] <= self.sources[ref["source_id"]]["pages"])
                self.assertTrue(ref["section"])
            else:
                first, last = ref["lines"]
                self.assertTrue(1 <= first <= last)

    def test_source_identities_and_member_locators(self):
        self.assertEqual(self.facts["schema_version"], 1)
        self.assertEqual(self.facts["market"], "US")
        self.assertEqual(len(self.sources), len(self.facts["sources"]))
        by_url = {}
        occurrences = set()
        for source_id, source in self.sources.items():
            with self.subTest(source_id=source_id):
                self.assertRegex(source_id, r"^[a-z0-9-]+$")
                url = urlsplit(source["url"])
                self.assertEqual(url.hostname, "ftp.oldskool.org")
                self.assertTrue(url.path.startswith("/pub/tvdog/"))
                self.assertFalse(url.query or url.fragment or url.username)
                self.assertGreater(source["source_bytes"], 0)
                self.assertRegex(source["source_sha256"], r"^[0-9a-f]{64}$")
                identity = (source["source_bytes"], source["source_sha256"])
                self.assertEqual(by_url.setdefault(source["url"], identity), identity)
                ordinal = None
                if member := source.get("member"):
                    name = PurePosixPath(member["name"])
                    self.assertFalse(name.is_absolute() or ".." in name.parts)
                    self.assertGreater(member["bytes"], 0)
                    self.assertRegex(member["sha256"], r"^[0-9a-f]{64}$")
                    ordinal = member["ordinal"]
                    self.assertGreaterEqual(ordinal, 0)
                location = (source["url"], ordinal)
                self.assertNotIn(location, occurrences)
                occurrences.add(location)
                if period := source["document_date"]:
                    precision_suffix = {4: "-01-01", 7: "-01", 10: ""}
                    date.fromisoformat(period + precision_suffix[len(period)])

    def test_prices_conditions_catalog_links_and_leads(self):
        catalog = json.loads((ECOSYSTEM / "catalog.json").read_text(encoding="utf-8"))
        catalog_ids = {entry["id"] for entry in catalog["entries"]}
        self.assertEqual(catalog["sources"]["express-order-guide-1988"]["url"],
                         self.sources["express-order-guide-1988"]["url"])
        for entry in catalog["entries"]:
            self.assertTrue(set(entry["source_ids"]) <= catalog["sources"].keys())
        facts = self.facts["offers"] + self.facts["observations"]
        self.assertEqual(len({item["id"] for item in facts}), len(facts))
        for offer in self.facts["offers"]:
            with self.subTest(offer=offer["id"]):
                self.assertIs(type(offer["price_usd_cents"]), int)
                self.assertGreaterEqual(offer["price_usd_cents"], 0)
                self.assertIn(offer["basis"], PRICE_BASIS)
                if offer["basis"] == "conditional-promotion":
                    self.assertTrue(offer["requires"])
                if sku := offer["catalog_number"]:
                    self.assertRegex(sku, r"^[0-9]+-[0-9]+[A-Z]?$")
                if catalog_id := offer.get("catalog_id"):
                    self.assertIn(catalog_id, catalog_ids)
                self.assert_sources(offer["evidence"])
        for observation in self.facts["observations"]:
            self.assert_sources(observation["evidence"])
        urls = set()
        for lead in self.facts["acquisition_leads"]:
            self.assertEqual(lead["snapshot_status"], "pending")
            self.assertNotIn(lead["url"], urls)
            self.assert_sources([lead["evidence"]])
            if resolution := lead.get("resolved_by_source_id"):
                source = self.sources[resolution]
                self.assertEqual(source["url"], lead["url"])
                self.assertGreater(source["acquired_utc"], self.facts["mirror_snapshot_utc"])
            urls.add(lead["url"])


if __name__ == "__main__":
    unittest.main()
