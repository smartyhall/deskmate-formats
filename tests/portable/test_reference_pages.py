"""Portable checks for generator-independent reference page navigation."""

import contextlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from check_reference_pages import validate_map  # noqa: E402

from reference_route_baseline import check_baseline  # noqa: E402


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
        location = REPO / "docs/site/page-map.json"
        self.assertEqual(
            validate_map(json.loads(location.read_text(encoding="utf-8")), REPO), []
        )


class NavigationMapV2Tests(unittest.TestCase):
    SECTIONS = ("deskmate", "formats", "recovery", "research", "project")

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs/hubs").mkdir(parents=True)
        (self.root / "docs/guide.md").write_text("# Guide", encoding="utf-8")
        for section in self.SECTIONS:
            (self.root / f"docs/hubs/{section}.md").write_text(
                f"# {section}", encoding="utf-8"
            )
        self.hubs = [self.hub(section) for section in self.SECTIONS]
        self.guide = self.page()

    def hub(self, section):
        return {
            "id": f"{section}.overview", "slug": section, "title": section.title(),
            "section": section, "role": "current-guide",
            "source": f"docs/hubs/{section}.md", "subsection": None, "order": 0,
            "summary": f"Start with the {section} overview.", "date": None,
            "is_hub": True,
        }

    def page(self, **overrides):
        entry = {
            "id": "deskmate.guide", "slug": "guide", "title": "Guide",
            "section": "deskmate", "role": "current-guide", "source": "docs/guide.md",
            "subsection": "History and orientation", "order": 10,
            "summary": "A short guide.", "date": None, "is_hub": False,
        }
        entry.update(overrides)
        return entry

    def check(self, *entries):
        return validate_map(
            {"schema_version": 2, "pages": list(entries)}, self.root
        )

    def test_complete_map_is_valid(self):
        self.assertEqual(self.check(*self.hubs, self.guide), [])

    def test_every_section_requires_exactly_one_hub(self):
        missing = self.check(*self.hubs[1:], self.guide)
        self.assertTrue(any("deskmate" in item and "hub" in item for item in missing))
        twice = self.check(*(self.hubs + [self.hub("deskmate")]), self.guide)
        self.assertTrue(any("exactly one hub" in item for item in twice))

    def test_hub_owns_its_section_route(self):
        bad = self.hub("deskmate") | {"slug": "start"}
        errors = self.check(*(self.hubs[1:] + [bad]), self.guide)
        self.assertTrue(any("hub slug must equal section" in item for item in errors))

    def test_hub_must_not_declare_a_subsection(self):
        bad = self.hub("deskmate") | {"subsection": "History"}
        errors = self.check(*(self.hubs[1:] + [bad]), self.guide)
        self.assertTrue(any("hub must not declare a subsection" in item for item in errors))

    def test_ordinary_pages_require_a_subsection(self):
        errors = self.check(*self.hubs, self.page(subsection=None))
        self.assertTrue(any("subsection" in item for item in errors))

    def test_rejects_missing_unknown_and_mistyped_fields(self):
        self.assertTrue(self.check(*self.hubs, self.page(summary=None)))
        self.assertTrue(self.check(*self.hubs, self.page(extra="nope")))
        self.assertTrue(self.check(*self.hubs, self.page(order=True)))
        self.assertTrue(self.check(*self.hubs, self.page(order=-1)))
        self.assertTrue(self.check(*self.hubs, self.page(is_hub="false")))
        self.assertTrue(self.check(*self.hubs, self.page(section="planning")))

    def test_summary_is_plain_trimmed_text(self):
        self.assertTrue(self.check(*self.hubs, self.page(summary=" padded ")))
        self.assertTrue(self.check(*self.hubs, self.page(summary="<b>bold</b>")))
        self.assertTrue(self.check(*self.hubs, self.page(summary="x" * 241)))

    def test_date_is_iso_or_null(self):
        self.assertEqual(self.check(*self.hubs, self.page(date="2026-11-20")), [])
        self.assertTrue(self.check(*self.hubs, self.page(date="20 November 2026")))
        self.assertTrue(self.check(*self.hubs, self.page(date="2026-02-30")))

    def test_hub_identity_is_unique_and_sourced(self):
        clash = self.page(id="deskmate.overview")
        self.assertTrue(any("duplicate id" in item for item in
                            self.check(*self.hubs, clash)))


class PublishedRouteBaselineTests(unittest.TestCase):
    revision = "a" * 40

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.baseline = {
            "schema_version": 1, "source_revision": self.revision,
            "anchor_status": "pending-rendered-baseline",
            "routes": [
                {"route": "/", "page_id": None, "anchors": None},
                {"route": "/example/", "page_id": "example.page", "anchors": None},
            ],
        }
        (self.root / "index.html").write_text('<article id="home">Home</article>', encoding="utf-8")
        self.page = self.root / "example/index.html"
        self.page.parent.mkdir()
        self.page.write_text(
            '<main id="chrome"><article><h1 id="old">Example</h1>'
            '<a name="legacy"></a></article></main>', encoding="utf-8"
        )

    def capture(self, **kwargs):
        options = {"source_revision": self.revision, "source_kind": "verified-local-build"}
        options.update(kwargs)
        return check_baseline(self.root, self.baseline, capture=True, **options)

    def test_capture_and_preserve_content_only(self):
        self.assertEqual(self.capture(), [])
        self.assertEqual(self.baseline["anchor_status"], "captured")
        self.assertEqual(self.baseline["routes"][0]["anchors"], [])
        self.assertEqual(self.baseline["routes"][1]["anchors"], ["legacy", "old"])
        self.assertEqual(check_baseline(self.root, self.baseline), [])
        self.page.write_text('<article><h1 id="new">Example</h1></article>', encoding="utf-8")
        self.assertIn("/example/: missing baseline anchor #old",
                      check_baseline(self.root, self.baseline))
        self.assertTrue(self.capture())

    def test_missing_route_even_before_anchor_capture(self):
        self.page.unlink()
        self.assertIn("/example/: missing baseline route",
                      check_baseline(self.root, self.baseline))
        self.assertTrue(self.capture())
        self.assertIsNone(self.baseline["routes"][0]["anchors"])

    def test_reject_malformed_or_duplicate_route(self):
        self.baseline["routes"][1]["route"] = "/../"
        self.assertTrue(check_baseline(self.root, self.baseline))
        self.baseline["routes"][1]["route"] = "/"
        self.assertTrue(check_baseline(self.root, self.baseline))

    def test_reject_invalid_schema_and_status(self):
        self.baseline["schema_version"] = 2
        self.assertTrue(check_baseline(self.root, self.baseline))
        self.baseline["schema_version"] = 1
        self.baseline["anchor_status"] = "unknown"
        self.assertTrue(check_baseline(self.root, self.baseline))

    def test_reject_wrong_revision_and_duplicate_anchor(self):
        self.assertTrue(self.capture(source_revision="b" * 40))
        self.page.write_text('<article><h1 id="x">X</h1><h2 id="x">Y</h2></article>',
                             encoding="utf-8")
        self.assertTrue(self.capture())

    def test_additive_extension(self):
        self.assertEqual(self.capture(), [])
        self.page.write_text('<article><h1 id="old">Example</h1><a name="legacy"></a>'
                             '<h2 id="new">New</h2></article>', encoding="utf-8")
        self.assertEqual(check_baseline(self.root, self.baseline), [])
        self.assertEqual(check_baseline(
            self.root, self.baseline, extend=True, source_revision="b" * 40,
            source_kind="verified-local-build",
        ), [])
        self.assertEqual(self.baseline["routes"][1]["anchors"], ["legacy", "new", "old"])
        self.page.write_text('<article><h1 id="old">Example</h1></article>', encoding="utf-8")
        self.assertTrue(check_baseline(
            self.root, self.baseline, extend=True, source_revision="c" * 40,
            source_kind="verified-local-build",
        ))
        self.assertEqual(self.baseline["routes"][1]["anchors"], ["legacy", "new", "old"])

    def test_capture_history_is_reviewable(self):
        self.assertEqual(self.capture(), [])
        record = self.baseline["capture_history"][0]
        self.assertTrue(record["captured_at"].endswith("Z"))
        self.assertEqual(record["source_kind"], "verified-local-build")
        self.assertIn("workflow_run_id", record)
        self.assertEqual(check_baseline(self.root, self.baseline), [])
        for broken in (
            {"source_revision": "short"},
            {"source_kind": "unverified"},
            {"captured_at": "26 November 2026"},
            {"unexpected": 1},
        ):
            with self.subTest(broken=broken):
                candidate = dict(self.baseline)
                candidate["capture_history"] = [record | broken]
                self.assertTrue(check_baseline(self.root, candidate))
        candidate = dict(self.baseline)
        candidate["capture_history"] = [record | {"source_kind": "verified-ci-artifact",
                                                  "artifact_id": None,
                                                  "artifact_sha256": None}]
        self.assertTrue(check_baseline(self.root, candidate))

    def test_extension_records_run_provenance(self):
        self.assertEqual(self.capture(), [])
        self.assertEqual(check_baseline(
            self.root, self.baseline, extend=True, source_revision="b" * 40,
            source_kind="verified-local-build", workflow_run_id=45312811457,
        ), [])
        self.assertEqual(
            self.baseline["capture_history"][-1]["workflow_run_id"], 45312811457
        )


class GeneratedSiteCliTests(unittest.TestCase):
    cli_path = REPO / "website/scripts/check_generated_site.py"

    def setUp(self):
        if not self.cli_path.is_file():
            self.skipTest("reference-site tooling is not distributed here")
        sys.path.insert(0, str(self.cli_path.parent))
        import check_generated_site
        self.cli = check_generated_site
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "index.html").write_text(
            '<article><h1 id="home">Home</h1></article>', encoding="utf-8"
        )
        (self.root / "unit").mkdir()
        (self.root / "unit/index.html").write_text(
            '<article><h1 id="a">A</h1></article>', encoding="utf-8"
        )
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps({
            "schema_version": 1,
            "source_revision": "a" * 40,
            "anchor_status": "captured",
            "routes": [
                {"route": "/", "page_id": None, "anchors": []},
                {"route": "/unit/", "page_id": "unit.page", "anchors": ["a"]},
            ],
        }), encoding="utf-8")

    def run_cli(self, *args):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            status = self.cli.run(list(args))
        return status, stderr.getvalue()

    def base_args(self):
        return (str(self.root), "/", "--baseline", str(self.baseline))

    def test_check_mode_passes_on_a_matching_site(self):
        self.assertEqual(self.run_cli(*self.base_args())[0], 0)

    def test_check_mode_reports_missing_fragment(self):
        (self.root / "unit/index.html").write_text(
            '<article><h1 id="b">B</h1></article><a href="#a">self</a>',
            encoding="utf-8",
        )
        status, stderr = self.run_cli(*self.base_args())
        self.assertEqual(status, 1)
        self.assertIn("missing baseline anchor #a", stderr)
        self.assertIn("missing fragment: #a", stderr)

    def test_base_path_error_explains_shell_rewriting(self):
        status, stderr = self.run_cli(str(self.root), "relative", "--baseline", str(self.baseline))
        self.assertEqual(status, 1)
        self.assertIn("MSYS_NO_PATHCONV", stderr)

    def test_extension_refuses_to_overwrite_the_tracked_baseline(self):
        before = self.baseline.read_text(encoding="utf-8")
        status, stderr = self.run_cli(
            *self.base_args(), "--extend-baseline",
            "--source-revision", "a" * 40, "--source-kind", "verified-local-build",
            "--output", str(self.baseline),
        )
        self.assertEqual(status, 1)
        self.assertIn("separate file", stderr)
        self.assertEqual(self.baseline.read_text(encoding="utf-8"), before)

    def test_extension_writes_a_reviewable_candidate(self):
        candidate = self.root / "candidate.json"
        status, stderr = self.run_cli(
            *self.base_args(), "--extend-baseline",
            "--source-revision", "b" * 40, "--source-kind", "verified-local-build",
            "--workflow-run-id", "45312811457", "--output", str(candidate),
        )
        self.assertEqual(status, 0, stderr)
        written = json.loads(candidate.read_text(encoding="utf-8"))
        self.assertEqual(written["routes"][1]["anchors"], ["a"])
        self.assertEqual(written["capture_history"][-1]["workflow_run_id"], 45312811457)
        self.assertEqual(
            json.loads(self.baseline.read_text(encoding="utf-8")).get("capture_history", []),
            [],
        )


if __name__ == "__main__":
    unittest.main()
