"""Synthetic regression tests for tools/prepare_history_figures.py.

No historical scan or copyrighted source is used here: the fake document
renders a coordinate-encoded placeholder page so page selection, rectangle
conversion, compositing, and provenance can be checked exactly.
"""
# SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import prepare_history_figures as figures  # noqa: E402

try:  # The PDF adapter is optional in the portable environment.
    import pymupdf
except ImportError:  # pragma: no cover - exercised where PyMuPDF is absent
    pymupdf = None

from PIL import Image  # noqa: E402

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


class FakePage:
    def __init__(self, size, text, shade):
        self.size = size
        self.text = text
        self.shade = shade


class FakeDocument:
    """Renders each page as a coordinate-encoded raster.

    Pixel(x, y) = (x % 256, y % 256, shade), so a correctly selected page and
    rectangle are provable by comparing against an equivalent direct crop.
    """

    def __init__(self, pages, sha256=DIGEST_A, size_bytes=1234):
        self._pages = pages
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.rendered = []

    @property
    def page_count(self):
        return len(self._pages)

    def page_size(self, index):
        return self._pages[index].size

    def page_text(self, index):
        return self._pages[index].text

    def render_page(self, index, dpi):
        self.rendered.append((index, dpi))
        page = self._pages[index]
        width = round(page.size[0] * dpi / 72)
        height = round(page.size[1] * dpi / 72)
        rows = []
        for y in range(height):
            row = bytearray()
            for x in range(width):
                row += bytes((x % 256, y % 256, page.shade))
            rows.append(bytes(row))
        return Image.frombytes("RGB", (width, height), b"".join(rows))


def synthetic_document():
    return FakeDocument([
        FakePage((144, 216), "Page one sample text", 40),
        FakePage((144, 216), "Page two has DeskMate and 25-1177", 120),
        FakePage((144, 216), "Page three sample text", 200),
    ])


def synthetic_record(**figure_overrides):
    figure = {
        "id": "history.synthetic-crop",
        "figure_number": "1",
        "status": "proposed-crop-private-review",
        "source": "scan",
        "source_url": "https://example.test/scan.pdf#page=2",
        "dpi": 144,
        "panels": [{
            "page_index": 1,
            "printed_page": "2",
            "rect": [10, 20, 60, 100],
            "label": "Synthetic panel",
            "required_text": ["DeskMate"],
        }],
        "expected_width": 100,
        "expected_height": 160,
        "dimension_tolerance_px": 2,
        "caption": "A synthetic caption for a synthetic crop.",
        "alt": "Synthetic placeholder alt text.",
        "attribution": "Synthetic test fixture, no third-party work.",
        "rights_status": "synthetic test fixture; not a historical source",
        "purpose": "Exercise the preparation path without historical media.",
        "excerpt_rationale": "One small rectangle is enough for the test.",
    }
    figure.update(figure_overrides)
    return {
        "schema_version": 1,
        "coordinate_system": {
            "units": "PDF points",
            "origin": "top-left corner of the unrotated page box",
            "rectangle": "[x0, y0, x1, y1]",
        },
        "limits": {
            "max_output_bytes": 6 * 1024 * 1024,
            "max_output_pixels": 4_000_000,
            "max_dimension": 4096,
            "panel_gap_px": 10,
        },
        "sources": {
            "scan": {
                "title": "Synthetic scan",
                "publisher": "Test fixture",
                "url": "https://example.test/scan.pdf",
                "sha256": DIGEST_A,
                "size_bytes": 1234,
                "page_count": 3,
                "printed_page_convention": "printed page = index + 1",
                "attribution": "Synthetic test fixture",
                "rights_status": "synthetic test fixture",
            },
        },
        "figures": [figure],
    }


class RecordValidationTests(unittest.TestCase):
    def test_valid_record_is_accepted(self):
        figures.validate_record(synthetic_record())

    def test_rejects_zero_area_and_negative_rectangles(self):
        for rect in ([10, 20, 10, 100], [10, 20, 60, 20], [-1, 4, 40, 50],
                     [10, 20, 60]):
            with self.subTest(rect=rect):
                record = synthetic_record()
                record["figures"][0]["panels"][0]["rect"] = rect
                with self.assertRaises(figures.RecordError):
                    figures.validate_record(record)

    def test_rejects_incomplete_figure_metadata(self):
        for field in ("caption", "alt", "attribution", "rights_status",
                      "purpose", "excerpt_rationale"):
            with self.subTest(field=field):
                record = synthetic_record()
                del record["figures"][0][field]
                with self.assertRaises(figures.RecordError):
                    figures.validate_record(record)

    def test_rejects_incomplete_source_record(self):
        for field in ("sha256", "size_bytes", "page_count", "rights_status",
                      "printed_page_convention"):
            with self.subTest(field=field):
                record = synthetic_record()
                del record["sources"]["scan"][field]
                with self.assertRaises(figures.RecordError):
                    figures.validate_record(record)

    def test_rejects_unknown_source_and_duplicate_identifiers(self):
        record = synthetic_record()
        record["figures"][0]["source"] = "missing"
        with self.assertRaises(figures.RecordError):
            figures.validate_record(record)

        record = synthetic_record()
        duplicate = copy.deepcopy(record["figures"][0])
        record["figures"].append(duplicate)
        with self.assertRaises(figures.RecordError):
            figures.validate_record(record)

    def test_rejects_unsupported_schema_and_status(self):
        record = synthetic_record()
        record["schema_version"] = 2
        with self.assertRaises(figures.RecordError):
            figures.validate_record(record)

        record = synthetic_record(status="published")
        with self.assertRaises(figures.RecordError):
            figures.validate_record(record)

    def test_linked_reference_needs_url_and_no_crops(self):
        record = synthetic_record(status="external-link-only")
        record["figures"][0]["external_url"] = "https://example.test/photo.jpg"
        del record["figures"][0]["panels"]
        del record["figures"][0]["source"]
        del record["figures"][0]["source_url"]
        figures.validate_record(record)

        record["figures"][0]["panels"] = [{"page_index": 0}]
        with self.assertRaises(figures.RecordError):
            figures.validate_record(record)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.output = Path(self.directory.name) / "figures"

    def tearDown(self):
        self.directory.cleanup()

    def prepare(self, record=None, document=None, **kwargs):
        record = record or synthetic_record()
        document = document or synthetic_document()
        return figures.prepare(record, {"scan": document}, self.output, **kwargs)

    def test_selects_the_intended_page_and_rectangle(self):
        document = synthetic_document()
        manifest = self.prepare(document=document)
        entry = manifest["generated"][0]
        self.assertEqual([call[0] for call in document.rendered], [1])
        produced = Image.open(self.output / entry["file"]).convert("RGB")
        expected = document.render_page(1, 144).crop((20, 40, 120, 200))
        self.assertEqual(produced.tobytes(), expected.tobytes())
        self.assertEqual(entry["panels"][0]["page_index"], 1)
        self.assertEqual(entry["panels"][0]["pixel_box"], [20, 40, 120, 200])

    def test_coordinate_conversion_and_dimensions(self):
        self.assertEqual(figures.pixel_box((10, 20, 60, 100), 144), (20, 40, 120, 200))
        self.assertEqual(figures.pixel_box((0, 0, 36, 36), 72), (0, 0, 36, 36))
        self.assertEqual(figures.pixel_box((0, 0, 72, 72), 200), (0, 0, 200, 200))
        manifest = self.prepare()
        entry = manifest["generated"][0]
        self.assertEqual((entry["width"], entry["height"]), (100, 160))
        self.assertEqual(entry["dpi"], 144)

    def test_composites_panels_in_reading_order(self):
        record = synthetic_record()
        record["figures"][0]["panels"] = [
            {"page_index": 0, "printed_page": "1", "rect": [0, 0, 40, 30],
             "label": "first", "required_text": ["Page one"]},
            {"page_index": 1, "printed_page": "2", "rect": [0, 0, 60, 20],
             "label": "second", "required_text": ["Page two"]},
        ]
        record["figures"][0]["expected_width"] = 120
        record["figures"][0]["expected_height"] = 60 + 40 + 10
        manifest = self.prepare(record=record)
        entry = manifest["generated"][0]
        self.assertEqual((entry["width"], entry["height"]), (120, 110))
        self.assertEqual([panel["pixel_offset"] for panel in entry["panels"]], [0, 70])
        produced = Image.open(self.output / entry["file"]).convert("RGB")
        document = synthetic_document()
        self.assertEqual(produced.crop((0, 0, 80, 60)).tobytes(),
                         document.render_page(0, 144).crop((0, 0, 80, 60)).tobytes())
        self.assertEqual(produced.crop((0, 70, 120, 110)).tobytes(),
                         document.render_page(1, 144).crop((0, 0, 120, 40)).tobytes())
        self.assertEqual(produced.crop((0, 60, 120, 70)).tobytes(),
                         Image.new("RGB", (120, 10), "white").tobytes())

    def test_rejects_unexpected_source_identity(self):
        wrong = FakeDocument(synthetic_document()._pages, sha256=DIGEST_B)
        with self.assertRaisesRegex(figures.RecordError, "digest mismatch"):
            self.prepare(document=wrong)
        short = FakeDocument(synthetic_document()._pages, size_bytes=99)
        with self.assertRaisesRegex(figures.RecordError, "size mismatch"):
            self.prepare(document=short)
        truncated = FakeDocument(synthetic_document()._pages[:2])
        with self.assertRaisesRegex(figures.RecordError, "page count mismatch"):
            self.prepare(document=truncated)

    def test_rejects_missing_page_and_unexpected_content(self):
        record = synthetic_record()
        record["figures"][0]["panels"][0]["page_index"] = 7
        with self.assertRaisesRegex(figures.RecordError, "outside the document"):
            self.prepare(record=record)

        record = synthetic_record()
        record["figures"][0]["panels"][0]["required_text"] = ["not printed here"]
        with self.assertRaisesRegex(figures.RecordError, "lacks required text"):
            self.prepare(record=record)

    def test_rejects_rectangle_outside_page(self):
        record = synthetic_record()
        record["figures"][0]["panels"][0]["rect"] = [100, 200, 400, 400]
        with self.assertRaisesRegex(figures.RecordError, "exceeds the page box"):
            self.prepare(record=record)

    def test_rejects_unreviewed_output_dimensions(self):
        record = synthetic_record(expected_width=400)
        with self.assertRaisesRegex(figures.RecordError, "differs from the reviewed"):
            self.prepare(record=record)

    def test_enforces_output_limits(self):
        record = synthetic_record()
        record["limits"]["max_output_bytes"] = 10
        with self.assertRaisesRegex(figures.RecordError, "byte limit"):
            self.prepare(record=record)

        record = synthetic_record()
        record["limits"]["max_output_pixels"] = 1000
        with self.assertRaisesRegex(figures.RecordError, "pixel limit"):
            self.prepare(record=record)

        record = synthetic_record()
        record["limits"]["max_dimension"] = 50
        with self.assertRaisesRegex(figures.RecordError, "dimension limit"):
            self.prepare(record=record)

    def test_output_must_stay_private(self):
        with self.assertRaisesRegex(figures.RecordError, "refusing"):
            figures.check_output_directory(figures.REPOSITORY_ROOT / "docs/history/figures")
        figures.check_output_directory(figures.REPOSITORY_ROOT / "local-results" / "x")
        figures.check_output_directory(self.output)

    def test_manifest_records_provenance_and_review_status(self):
        manifest = self.prepare()
        entry = manifest["generated"][0]
        self.assertIn("PRIVATE REVIEW", manifest["status"])
        self.assertNotIn("published", entry)
        self.assertEqual(entry["source_sha256"], DIGEST_A)
        self.assertEqual(entry["source_page_count"], 3)
        self.assertEqual(entry["panels"][0]["printed_page"], "2")
        self.assertEqual(entry["panels"][0]["rect"], [10, 20, 60, 100])
        self.assertEqual(entry["rights_status"],
                         synthetic_record()["figures"][0]["rights_status"])
        data = (self.output / entry["file"]).read_bytes()
        self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(entry["bytes"], len(data))
        self.assertTrue((self.output / figures.CONTACT_SHEET_NAME).is_file())
        stored = json.loads((self.output / figures.MANIFEST_NAME).read_text("utf-8"))
        self.assertEqual(stored["generated"][0]["sha256"], entry["sha256"])
        self.assertEqual(stored["record"]["limits"]["panel_gap_px"], 10)

    def test_linked_reference_is_reported_without_output(self):
        record = synthetic_record()
        figure = record["figures"][0]
        for key in ("panels", "source", "source_url", "dpi", "expected_width",
                    "expected_height", "dimension_tolerance_px"):
            figure.pop(key, None)
        figure.update({
            "status": "external-link-only",
            "external_url": "https://example.test/photo.jpg",
        })
        manifest = figures.prepare(record, {}, self.output)
        self.assertEqual(manifest["generated"], [])
        self.assertEqual(manifest["linked_references"][0]["external_url"],
                         "https://example.test/photo.jpg")
        self.assertFalse((self.output / figures.CONTACT_SHEET_NAME).exists())


class CommandLineTests(unittest.TestCase):
    def test_record_only_validates_the_committed_record(self):
        path = Path(__file__).resolve().parents[2] / figures.RECORD_PATH
        self.assertEqual(figures.main(["--record", str(path), "--record-only"]), 0)

    def test_missing_source_copy_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "record.json"
            record_path.write_text(json.dumps(synthetic_record()), encoding="utf-8")
            status = figures.main(["--record", str(record_path),
                                   "--output", str(Path(directory) / "out")])
            self.assertEqual(status, 2)


@unittest.skipUnless(pymupdf, "PyMuPDF is not installed in this environment")
class PdfAdapterTests(unittest.TestCase):
    def test_synthetic_pdf_pages_are_selectable_and_croppable(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "synthetic.pdf"
            document = pymupdf.open()
            for text in ("First synthetic page", "Second synthetic page DeskMate"):
                page = document.new_page(width=200, height=260)
                page.insert_text((20, 40), text, fontsize=12)
            document.save(pdf_path)
            document.close()

            scan = figures.PymupdfDocument(pdf_path)
            self.assertEqual(scan.page_count, 2)
            self.assertIn("DeskMate", scan.page_text(1))
            self.assertEqual(scan.size_bytes, pdf_path.stat().st_size)
            self.assertEqual(scan.sha256, hashlib.sha256(pdf_path.read_bytes()).hexdigest())

            record = synthetic_record()
            source = record["sources"]["scan"]
            source.update({
                "sha256": scan.sha256,
                "size_bytes": scan.size_bytes,
                "page_count": 2,
            })
            figure = record["figures"][0]
            figure["panels"] = [{
                "page_index": 1, "printed_page": "2", "rect": [10, 10, 190, 80],
                "label": "Second page crop", "required_text": ["DeskMate"],
            }]
            figure["expected_width"] = 360
            figure["expected_height"] = 140
            try:
                manifest = figures.prepare(record, {"scan": scan},
                                           Path(directory) / "figures")
            finally:
                scan.close()
            entry = manifest["generated"][0]
            self.assertEqual((entry["width"], entry["height"]), (360, 140))
            self.assertTrue((Path(directory) / "figures" / entry["file"]).is_file())


if __name__ == "__main__":
    unittest.main()
