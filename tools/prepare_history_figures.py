#!/usr/bin/env python3
"""Prepare historical DeskMate period figures from reviewed local scans.

The reviewed record (``docs/history/history-figure-sources.json``) is the single
source of truth for what may be produced: expected source digest and size, PDF
page count, page selection, crop rectangles, rendering resolution, expected
output dimensions, output size limits, reviewed caption and alternative text,
attribution, and rights-review status. This tool refuses anything that does not
match the record; it never guesses a page, a crop, or a caption.

Crop rectangles are PDF points (1/72 inch) measured from the top-left corner of
the unrotated page box, in ``[x0, y0, x1, y1]`` order. A page is rendered once at
the recorded resolution and cropped with ``round(point * dpi / 72)`` arithmetic,
so the pixel result is reproducible and testable.

Requires PyMuPDF and Pillow. Standard-library validation also works through
``--record-only``. Output must stay outside the repository: source scans,
provisional images, and contact sheets are private review artifacts and are
never published by this tool.

Usage:
  python tools/prepare_history_figures.py --output /tmp/deskmate-history-figures \
    --source tandy-1988-catalog=/path/to/1988-tandy-catalog.pdf \
    --source compute-1988-10=/path/to/compute-1988-10.pdf
  python tools/prepare_history_figures.py --record-only
"""
# SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import sys
import textwrap

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = Path("docs/history/history-figure-sources.json")
SCHEMA_VERSION = 1
DIGEST = re.compile(r"[0-9a-f]{64}")
FIGURE_ID = re.compile(r"history\.[a-z0-9]+(?:[.-][a-z0-9]+)*")
CROP_STATUS = "proposed-crop-private-review"
LINK_STATUS = "external-link-only"
STATUSES = {CROP_STATUS, LINK_STATUS}
LIMIT_KEYS = ("max_output_bytes", "max_output_pixels", "max_dimension", "panel_gap_px")
SOURCE_KEYS = ("title", "publisher", "url", "sha256", "size_bytes", "page_count",
               "attribution", "rights_status", "printed_page_convention")
FIGURE_TEXT_KEYS = ("caption", "alt", "attribution", "rights_status", "purpose",
                    "excerpt_rationale")
CAPTION_LIMIT = 500
MANIFEST_NAME = "figure-manifest.json"
CONTACT_SHEET_NAME = "contact-sheet.png"
MANIFEST_STATUS = "PRIVATE REVIEW ONLY - NOT AUTHORIZED FOR PUBLICATION"


class RecordError(ValueError):
    """The reviewed record or a prepared output did not match expectations."""


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _text(value, where: str, *, limit: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{where}: expected non-empty text")
    if limit is not None and len(value) > limit:
        raise RecordError(f"{where}: text exceeds {limit} characters")
    if value != value.strip():
        raise RecordError(f"{where}: text has leading or trailing whitespace")
    return value


def _integer(value, where: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        rule = f">= {minimum}" if maximum is None else f"in {minimum}..{maximum}"
        raise RecordError(f"{where}: expected an integer {rule}")
    return value


def _number(value, where: str) -> float:
    if type(value) not in (int, float) or value != value:
        raise RecordError(f"{where}: expected a finite number")
    return float(value)


def _http_url(value, where: str) -> str:
    url = _text(value, where)
    if not url.startswith(("https://", "http://")):
        raise RecordError(f"{where}: expected an http(s) URL")
    return url


def _rect(value, where: str) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise RecordError(f"{where}: expected [x0, y0, x1, y1]")
    x0, y0, x1, y1 = (_number(item, f"{where}[{index}]") for index, item in enumerate(value))
    if x1 <= x0 or y1 <= y0:
        raise RecordError(f"{where}: rectangle has no positive area")
    if x0 < 0 or y0 < 0:
        raise RecordError(f"{where}: rectangle starts outside the page box")
    return x0, y0, x1, y1


def validate_record(record) -> dict:
    """Validate the reviewed record structurally; no source scan is needed."""
    if not isinstance(record, dict):
        raise RecordError("record: expected a JSON object")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise RecordError(f"record: schema_version must be {SCHEMA_VERSION}")
    coordinates = record.get("coordinate_system")
    if not isinstance(coordinates, dict):
        raise RecordError("record: missing coordinate_system")
    for key in ("units", "origin", "rectangle"):
        _text(coordinates.get(key), f"record.coordinate_system.{key}")
    limits = record.get("limits")
    if not isinstance(limits, dict):
        raise RecordError("record: missing limits")
    for key in LIMIT_KEYS:
        _integer(limits.get(key), f"record.limits.{key}", minimum=1)

    sources = record.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise RecordError("record: missing sources")
    for key, source in sources.items():
        where = f"record.sources.{key}"
        if not isinstance(source, dict):
            raise RecordError(f"{where}: expected an object")
        for field in SOURCE_KEYS:
            where_field = f"{where}.{field}"
            if field == "sha256":
                value = source.get(field)
                if not isinstance(value, str) or not DIGEST.fullmatch(value):
                    raise RecordError(f"{where_field}: expected a lowercase SHA-256 digest")
            elif field == "size_bytes":
                _integer(source.get(field), where_field, minimum=1)
            elif field == "page_count":
                _integer(source.get(field), where_field, minimum=1)
            elif field == "url":
                _http_url(source.get(field), where_field)
            else:
                _text(source.get(field), where_field)
        if source.get("printed_page_convention") is not None:
            _text(source["printed_page_convention"], where + ".printed_page_convention")

    figures = record.get("figures")
    if not isinstance(figures, list) or not figures:
        raise RecordError("record: missing figures")
    seen = set()
    for index, figure in enumerate(figures):
        where = f"record.figures[{index}]"
        if not isinstance(figure, dict):
            raise RecordError(f"{where}: expected an object")
        identifier = _text(figure.get("id"), where + ".id")
        if not FIGURE_ID.fullmatch(identifier):
            raise RecordError(f"{where}.id: unexpected figure identifier: {identifier}")
        if identifier in seen:
            raise RecordError(f"{where}.id: duplicate figure identifier: {identifier}")
        seen.add(identifier)
        _text(figure.get("figure_number"), where + ".figure_number")
        status = figure.get("status")
        if status not in STATUSES:
            raise RecordError(f"{where}.status: expected one of {sorted(STATUSES)}")
        for field in FIGURE_TEXT_KEYS:
            limit = CAPTION_LIMIT if field in ("caption", "alt") else None
            _text(figure.get(field), f"{where}.{field}", limit=limit)
        if status == LINK_STATUS:
            _http_url(figure.get("external_url"), where + ".external_url")
            if "panels" in figure or "source" in figure:
                raise RecordError(f"{where}: a linked reference must not define crops")
            continue
        source_key = _text(figure.get("source"), where + ".source")
        if source_key not in sources:
            raise RecordError(f"{where}.source: unknown source key: {source_key}")
        _http_url(figure.get("source_url"), where + ".source_url")
        _integer(figure.get("dpi"), where + ".dpi", minimum=100, maximum=400)
        _integer(figure.get("expected_width"), where + ".expected_width", minimum=1)
        _integer(figure.get("expected_height"), where + ".expected_height", minimum=1)
        _integer(figure.get("dimension_tolerance_px"), where + ".dimension_tolerance_px",
                 minimum=0, maximum=8)
        panels = figure.get("panels")
        if not isinstance(panels, list) or not panels:
            raise RecordError(f"{where}.panels: expected at least one crop panel")
        for panel_index, panel in enumerate(panels):
            panel_where = f"{where}.panels[{panel_index}]"
            if not isinstance(panel, dict):
                raise RecordError(f"{panel_where}: expected an object")
            _integer(panel.get("page_index"), panel_where + ".page_index")
            _text(panel.get("printed_page"), panel_where + ".printed_page")
            _text(panel.get("label"), panel_where + ".label")
            _rect(panel.get("rect"), panel_where + ".rect")
            required = panel.get("required_text")
            if not isinstance(required, list) or not required:
                raise RecordError(f"{panel_where}.required_text: expected at least one phrase")
            for item in required:
                _text(item, panel_where + ".required_text[]")
    return record


def load_record(path: Path) -> dict:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RecordError(f"record: cannot read {path}: {error}") from error
    return validate_record(record)


def pixel_box(rect, dpi: int) -> tuple[int, int, int, int]:
    """Convert a PDF-point rectangle to integer pixels at a given resolution."""
    scale = dpi / 72
    x0, y0, x1, y1 = rect
    return (round(x0 * scale), round(y0 * scale), round(x1 * scale), round(y1 * scale))


def _normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def _check_page_text(document, figure_id: str, panel: dict) -> None:
    text = _normalise(document.page_text(panel["page_index"]))
    for phrase in panel["required_text"]:
        if _normalise(phrase) not in text:
            raise RecordError(
                f"{figure_id}: page {panel['page_index']} lacks required text {phrase!r}")


def _check_rect(rect, page_size, where: str) -> None:
    width, height = page_size
    x0, y0, x1, y1 = rect
    if x1 > width + 0.5 or y1 > height + 0.5:
        raise RecordError(
            f"{where}: rectangle {list(rect)} exceeds the page box "
            f"({width:.2f} x {height:.2f} points)")


def _render(document, page_index: int, dpi: int, cache: dict):
    from PIL import Image

    key = (id(document), page_index, dpi)
    if key not in cache:
        image = document.render_page(page_index, dpi)
        if not isinstance(image, Image.Image):
            raise RecordError("renderer did not return a Pillow image")
        cache[key] = image.convert("RGB")
    return cache[key]


def _check_source_identity(figure_id: str, source_key: str, source: dict, document) -> None:
    if document.sha256 != source["sha256"]:
        raise RecordError(
            f"{figure_id}: source {source_key} digest mismatch: expected "
            f"{source['sha256']}, got {document.sha256}")
    if document.size_bytes != source["size_bytes"]:
        raise RecordError(
            f"{figure_id}: source {source_key} size mismatch: expected "
            f"{source['size_bytes']} bytes, got {document.size_bytes}")
    if document.page_count != source["page_count"]:
        raise RecordError(
            f"{figure_id}: source {source_key} page count mismatch: expected "
            f"{source['page_count']}, got {document.page_count}")


def _figure_image(figure: dict, source: dict, source_key: str, document,
                  limits: dict, cache: dict):
    from PIL import Image

    _check_source_identity(figure["id"], source_key, source, document)
    dpi = figure["dpi"]
    crops = []
    provenance = []
    for index, panel in enumerate(figure["panels"]):
        where = f"{figure['id']}.panels[{index}]"
        page_index = panel["page_index"]
        if page_index >= document.page_count:
            raise RecordError(f"{where}: page index {page_index} is outside the document")
        rect = _rect(panel["rect"], where + ".rect")
        _check_rect(rect, document.page_size(page_index), where)
        _check_page_text(document, figure["id"], panel)
        image = _render(document, page_index, dpi, cache)
        box = pixel_box(rect, dpi)
        if box[2] <= box[0] or box[3] <= box[1]:
            raise RecordError(f"{where}: crop rectangle collapses to zero pixels")
        if box[2] > image.width or box[3] > image.height:
            raise RecordError(
                f"{where}: crop {list(box)} exceeds the rendered page "
                f"({image.width} x {image.height} pixels)")
        crops.append(image.crop(box))
        provenance.append({
            "page_index": page_index,
            "printed_page": panel["printed_page"],
            "rect": [round(value, 2) for value in rect],
            "pixel_box": list(box),
            "label": panel["label"],
            "required_text": list(panel["required_text"]),
            "pixel_offset": None,
        })

    gap = limits["panel_gap_px"]
    width = max(crop.width for crop in crops)
    height = sum(crop.height for crop in crops) + gap * (len(crops) - 1)
    composed = Image.new("RGB", (width, height), "white")
    offset = 0
    for crop, entry in zip(crops, provenance):
        composed.paste(crop, (0, offset))
        entry["pixel_offset"] = offset
        offset += crop.height + gap
    return composed, provenance


def _encode_png(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def _enforce_limits(figure_id: str, image, data: bytes, limits: dict) -> None:
    width, height = image.size
    if width > limits["max_dimension"] or height > limits["max_dimension"]:
        raise RecordError(
            f"{figure_id}: output {width}x{height} exceeds the "
            f"{limits['max_dimension']} pixel dimension limit")
    if width * height > limits["max_output_pixels"]:
        raise RecordError(
            f"{figure_id}: output {width}x{height} exceeds the "
            f"{limits['max_output_pixels']} pixel limit")
    if len(data) > limits["max_output_bytes"]:
        raise RecordError(
            f"{figure_id}: output is {len(data)} bytes, over the "
            f"{limits['max_output_bytes']} byte limit")


def _check_dimensions(figure: dict, image) -> None:
    tolerance = figure["dimension_tolerance_px"]
    for actual, expected, axis in ((image.width, figure["expected_width"], "width"),
                                   (image.height, figure["expected_height"], "height")):
        if abs(actual - expected) > tolerance:
            raise RecordError(
                f"{figure['id']}: output {axis} {actual}px differs from the reviewed "
                f"{expected}px by more than {tolerance}px")


def _is_inside_repository(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPOSITORY_ROOT)
    except ValueError:
        return False
    return True


def check_output_directory(output: Path) -> Path:
    """Keep private review artifacts out of tracked project content.

    Output may live outside the repository, or in the repository's ignored
    private working directories, but never in tracked site or documentation
    paths.
    """
    resolved = output.resolve()
    if _is_inside_repository(resolved):
        relative = resolved.relative_to(REPOSITORY_ROOT)
        private = ("local-results", "private-fixtures")
        if not relative.parts or relative.parts[0].lower() not in private:
            raise RecordError(
                "output: refusing to write tracked repository content; use a private "
                "directory outside the repository or local-results/")
    return resolved


SHEET_SUBSTITUTIONS = {
    "\u2014": " - ", "\u2013": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
}


def _sheet_text(value: str) -> str:
    """The bundled bitmap font lacks typographic glyphs; keep the sheet readable."""
    for source, replacement in SHEET_SUBSTITUTIONS.items():
        value = value.replace(source, replacement)
    return value


def _font(size: int = 16):
    from PIL import ImageFont

    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def build_contact_sheet(entries: list) -> "object":
    """Compose a private review sheet: each crop beside its intended caption."""
    from PIL import Image, ImageDraw

    width, margin, thumb_width = 1100, 26, 720
    title_font, body_font = _font(20), _font(15)
    wrapped = {}
    for figure, image in entries:
        caption = _sheet_text("Caption: " + figure["caption"])
        wrapped[figure["id"]] = textwrap.wrap(caption, width=118) or [""]
    height = margin
    for figure, image in entries:
        scale = min(1.0, thumb_width / image.width, 900 / image.height)
        height += int(image.height * scale) + 118 + len(wrapped[figure["id"]]) * 20
    sheet = Image.new("RGB", (width, height + margin), "white")
    draw = ImageDraw.Draw(sheet)
    cursor = margin
    for figure, image in entries:
        title = f"Figure {figure['figure_number']} - {figure['id']}"
        draw.text((margin, cursor), _sheet_text(title), fill="black", font=title_font)
        cursor += 30
        source = figure.get("source") or "external linked reference"
        pages = ", ".join(sorted({p["printed_page"] for p in figure.get("panels", [])}))
        detail = f"Source: {source}" + (f"; printed pages: {pages}" if pages else "")
        draw.text((margin, cursor), _sheet_text(detail), fill="black", font=body_font)
        cursor += 22
        rights = "Rights: " + _sheet_text(figure["rights_status"])[:130]
        draw.text((margin, cursor), rights, fill="black", font=body_font)
        cursor += 24
        scale = min(1.0, thumb_width / image.width, 900 / image.height)
        thumbnail = image.resize((int(image.width * scale), int(image.height * scale)),
                                 Image.Resampling.LANCZOS)
        sheet.paste(thumbnail, (margin, cursor))
        cursor += thumbnail.height + 10
        for line in wrapped[figure["id"]]:
            draw.text((margin, cursor), line, fill="black", font=body_font)
            cursor += 20
        cursor += 26
    return sheet


def prepare(record: dict, documents: dict, output: Path, *, contact_sheet: bool = True) -> dict:
    """Validate sources and write private crops plus a provenance manifest."""
    validate_record(record)
    output = check_output_directory(output)
    limits = record["limits"]
    sources = record["sources"]

    prepared = []
    cache = {}
    for figure in record["figures"]:
        if figure["status"] == LINK_STATUS:
            continue
        source_key = figure["source"]
        if source_key not in documents:
            raise RecordError(f"{figure['id']}: no local copy supplied for {source_key}")
        image, provenance = _figure_image(
            figure, sources[source_key], source_key, documents[source_key], limits, cache)
        _check_dimensions(figure, image)
        data = _encode_png(image)
        _enforce_limits(figure["id"], image, data, limits)
        prepared.append((figure, image, data, provenance))

    sheet = None
    if contact_sheet and prepared:
        sheet = _encode_png(build_contact_sheet([(f, i) for f, i, _, _ in prepared]))

    output.mkdir(parents=True, exist_ok=True)
    generated = []
    for figure, image, data, provenance in prepared:
        name = figure["id"] + ".png"
        (output / name).write_bytes(data)
        generated.append({
            "id": figure["id"],
            "figure_number": figure["figure_number"],
            "file": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "width": image.width,
            "height": image.height,
            "dpi": figure["dpi"],
            "caption": figure["caption"],
            "alt": figure["alt"],
            "attribution": figure["attribution"],
            "source_url": figure["source_url"],
            "source_key": figure["source"],
            "source_sha256": sources[figure["source"]]["sha256"],
            "source_page_count": sources[figure["source"]]["page_count"],
            "rights_status": figure["rights_status"],
            "purpose": figure["purpose"],
            "excerpt_rationale": figure["excerpt_rationale"],
            "panels": provenance,
            "status": figure["status"],
        })
    if sheet is not None:
        (output / CONTACT_SHEET_NAME).write_bytes(sheet)

    manifest = {
        "status": MANIFEST_STATUS,
        "record": {
            "schema_version": record["schema_version"],
            "coordinate_system": record["coordinate_system"],
            "limits": limits,
        },
        "generated": generated,
        "linked_references": [
            {
                "id": figure["id"],
                "figure_number": figure["figure_number"],
                "external_url": figure["external_url"],
                "caption": figure["caption"],
                "alt": figure["alt"],
                "attribution": figure["attribution"],
                "rights_status": figure["rights_status"],
                "status": figure["status"],
            }
            for figure in record["figures"] if figure["status"] == LINK_STATUS
        ],
        "review": [
            "Inspect every output pixel against the original leaf before any reuse.",
            "Confirm page indices, printed pages, and captions with a second reader.",
            "Record the operator's publication-rights decision per figure.",
            "Copy approved PNGs to the site only with a manifest entry and REUSE sidecar.",
        ],
    }
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


class PymupdfDocument:
    """Minimal PyMuPDF adapter used by the command-line interface."""

    def __init__(self, path: Path):
        try:
            import pymupdf
        except ImportError as error:  # pragma: no cover - dependency guard
            raise RecordError(
                "PyMuPDF is required to render scans; install it in a private "
                "environment before preparing figures") from error
        if not path.is_file():
            raise RecordError(f"missing local source scan: {path}")
        self._document = pymupdf.open(path)
        self.size_bytes = path.stat().st_size
        self.sha256 = sha256_file(path)

    @property
    def page_count(self) -> int:
        return self._document.page_count

    def page_size(self, index: int) -> tuple[float, float]:
        rect = self._document[index].rect
        return rect.width, rect.height

    def page_text(self, index: int) -> str:
        return self._document[index].get_text()

    def render_page(self, index: int, dpi: int):
        import pymupdf
        from PIL import Image

        page = self._document[index]
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    def close(self) -> None:
        """Release the source file handle (Windows keeps an open scan locked)."""
        self._document.close()


def parse_sources(values: list) -> dict:
    mapping = {}
    for value in values:
        key, separator, path = value.partition("=")
        if not separator or not key or not path:
            raise RecordError(f"--source expects KEY=PATH, got {value!r}")
        if key in mapping:
            raise RecordError(f"--source given twice for {key}")
        mapping[key] = Path(path)
    return mapping


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", type=Path, default=RECORD_PATH)
    parser.add_argument("--source", action="append", default=[], metavar="KEY=PATH",
                        help="local copy of a reviewed source, keyed as in the record")
    parser.add_argument("--output", type=Path,
                        help="private output directory outside the repository")
    parser.add_argument("--record-only", action="store_true",
                        help="validate the reviewed record without source scans")
    parser.add_argument("--no-contact-sheet", action="store_true",
                        help="skip the private caption contact sheet")
    args = parser.parse_args(argv)

    try:
        record = load_record(args.record)
        if args.record_only:
            print(f"Record valid: {len(record['figures'])} figures, "
                  f"{len(record['sources'])} sources.")
            return 0
        if args.output is None:
            parser.error("--output is required unless --record-only is used")
        documents = {key: PymupdfDocument(path)
                     for key, path in parse_sources(args.source).items()}
        try:
            manifest = prepare(record, documents, args.output,
                               contact_sheet=not args.no_contact_sheet)
        finally:
            for document in documents.values():
                close = getattr(document, "close", None)
                if close is not None:
                    close()
    except RecordError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Prepared {len(manifest['generated'])} private figures in {args.output}")
    for entry in manifest["generated"]:
        print(f"  {entry['file']} {entry['width']}x{entry['height']} "
              f"{entry['bytes']} bytes {entry['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
