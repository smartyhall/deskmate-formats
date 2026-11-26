"""Portable checks for generator-independent reference page navigation."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from check_reference_pages import validate_map  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "website/scripts"))
from check_generated_site import check_baseline  # noqa: E402


class ReferencePageMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "docs/site/README.md"
        source.parent.mkdir(parents=True)
        source.write_text("# Test", encoding="utf-8")
        self.page = {
            "id": "site.overview",
            "slug": "planning/overview",
            "title": "Test",
            "section": "planning",
            "role": "site-plan",
            "source": "docs/site/README.md",
        }

    def check(self, *entries):
        return validate_map({"schema_version": 1, "pages": list(entries)}, self.root)

    def test_valid_map(self):
        self.assertEqual(self.check(self.page), [])

    def test_duplicate_route_and_id(self):
        errors = self.check(self.page, self.page.copy())
        self.assertTrue(any("duplicate id" in item for item in errors))
        self.assertTrue(any("duplicate slug" in item for item in errors))

    def test_distinct_ids_cannot_share_authoritative_source(self):
        alternate = self.page | {"id": "site.other", "slug": "planning/other"}
        errors = self.check(self.page, alternate)
        self.assertTrue(any("duplicate source" in item for item in errors))

    def test_missing_and_traversal_sources(self):
        for source in ("docs/site/missing.md", "../secret.md", "/docs/site/README.md",
                       "docs/../private.md", "docs\\site\\README.md"):
            with self.subTest(source=source):
                errors = self.check(self.page | {"source": source})
                self.assertTrue(errors)

    def test_unknown_role_and_malformed_entries(self):
        self.assertTrue(self.check(self.page | {"role": "all-confirmed"}))
        self.assertTrue(self.check(self.page | {"slug": "Bad Route"}))
        self.assertTrue(validate_map({"schema_version": 2, "pages": []}, self.root))
        self.assertTrue(self.check({"id": "only.id"}))

    def test_repository_staging_map(self):
        repo = Path(__file__).resolve().parents[2]
        location = repo / "docs/site/page-map.json"
        self.assertEqual(
            validate_map(json.loads(location.read_text(encoding="utf-8")), repo), []
        )


class PublishedRouteBaselineTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.baseline = {
            "schema_version": 1,
            "anchor_status": "pending-rendered-baseline",
            "routes": [{"route": "/example/", "page_id": "example.page", "anchors": None}],
        }
        self.page = self.root / "example/index.html"
        self.page.parent.mkdir()
        self.page.write_text('<h1 id="old">Example</h1><a name="legacy"></a>', encoding="utf-8")

    def test_capture_and_preserve_anchors(self):
        self.assertEqual(check_baseline(self.root, self.baseline, capture=True), [])
        self.assertEqual(self.baseline["anchor_status"], "captured")
        self.assertEqual(self.baseline["routes"][0]["anchors"], ["legacy", "old"])
        self.assertEqual(check_baseline(self.root, self.baseline), [])
        self.page.write_text('<h1 id="new">Example</h1>', encoding="utf-8")
        self.assertIn("/example/: missing baseline anchor #old",
                      check_baseline(self.root, self.baseline))
        self.assertTrue(check_baseline(self.root, self.baseline, capture=True))

    def test_missing_route_even_before_anchor_capture(self):
        self.page.unlink()
        self.assertIn("/example/: missing baseline route",
                      check_baseline(self.root, self.baseline))

    def test_reject_malformed_or_traversal_route(self):
        self.baseline["routes"][0]["route"] = "/../"
        self.assertTrue(check_baseline(self.root, self.baseline))

    def test_new_anchor_does_not_break_baseline(self):
        self.assertEqual(check_baseline(self.root, self.baseline, capture=True), [])
        with self.page.open("a", encoding="utf-8") as output:
            output.write('<h2 id="new">New</h2>')
        self.assertEqual(check_baseline(self.root, self.baseline), [])


if __name__ == "__main__":
    unittest.main()
