#!/usr/bin/env python3
"""Stage historical DeskMate catalog/ad figures from reviewed local PDF scans.

Does not fetch historical media or publish images automatically.
Requires: Python 3, PyMuPDF, Pillow.
Usage:
  python tools/prepare_history_figures.py --catalog /path/to/1988-tandy.pdf \
    --sl-ad /path/to/1988-compute-oct.pdf --sl-page N --output /tmp/deskmate-figures
Page numbers used by this tool are ZERO-based. --sl-page is deliberately
mandatory, because scanned advertisements may have no searchable text.
Review the rendered files and manifest before any website publication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path


CATALOG = "https://colorcomputerarchive.com/repo/Documents/Catalogs/Radio%20Shack/Tandy%20Computer%20Catalog%20and%20Software%20Reference%20Guide%20%281988%29%28Tandy%29.pdf"
SL_AD = "https://colorcomputerarchive.com/repo/Documents/Magazines/Compute%20%28Clean%29/Compute_Issue_101_1988_Oct.pdf"


def digest(filename: Path) -> str:
    result = hashlib.sha256()
    with filename.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def png_page(document, index: int, width: int) -> tuple[bytes, int, int]:
    import fitz
    from PIL import Image
    if not 0 <= index < document.page_count:
        raise ValueError("PDF page index outside document: " + str(index))
    page = document[index]
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if img.width * img.height > 4_000_000:
        ratio = (4_000_000 / (img.width * img.height)) ** 0.5
        img = img.resize((int(img.width * ratio), int(img.height * ratio)),
                         Image.Resampling.LANCZOS)
    while True:
        buf = BytesIO()
        img.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
        if len(data) <= 6 * 1024 * 1024:
            return data, img.width, img.height
        if img.width < 700:
            raise ValueError("Image exceeds 6 MiB site limit")
        img = img.resize((int(img.width * .85), int(img.height * .85)),
                         Image.Resampling.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--sl-ad", type=Path, required=True)
    parser.add_argument("--sl-page", type=int, required=True,
                        help="Manually reviewed zero-based PDF page of original SL ad")
    parser.add_argument("--output", type=Path, required=True,
                        help="Private staging destination; do not point inside website/src")
    parser.add_argument("--width", type=int, default=1440)
    args = parser.parse_args()
    if not (800 <= args.width <= 1800):
        parser.error("--width must be between 800 and 1800")
    for source in (args.catalog, args.sl_ad):
        if not source.is_file():
            parser.error("Missing local original scan: " + str(source))
    import fitz
    catalog = fitz.open(args.catalog)
    advert = fitz.open(args.sl_ad)
    if catalog.page_count < 103:
        parser.error("Expected the 124-page 1988 Tandy catalog; inspect source")
    if not 0 <= args.sl_page < advert.page_count:
        parser.error("--sl-page is outside magazine PDF")
    specs = (
        ("tandy-1000-hx-1988", catalog, args.catalog, 8,
         "1987 — Personal DeskMate 2 and the HX/TX generation",
         "The 1988 Tandy catalog advertised the 1000 HX with Personal DeskMate 2 included. MS-DOS, rather than an identified copy of DeskMate, was in ROM.",
         "A 1988 Tandy 1000 HX catalog page with computer photo, price, and separate claims for MS-DOS in ROM and Personal DeskMate 2 included.",
         CATALOG),
        ("deskmate-software-1988", catalog, args.catalog, 102,
         "1988 — DeskMate 3 and the wider software platform",
         "The 1988 Tandy software guide separately advertised Personal DeskMate, Personal DeskMate 2, and Professional DeskMate.",
         "Original 1988 Tandy software catalog entries for distinct Personal and Professional DeskMate editions, with prices and machine compatibility.",
         CATALOG),
        ("tandy-1000-sl-rom-1988", advert, args.sl_ad, args.sl_page,
         "1988 — DeskMate 3 and the wider software platform",
         "A 1988 Radio Shack advertisement promoted the Tandy 1000 SL with both MS-DOS and DeskMate in ROM.",
         "Radio Shack's 1988 Tandy 1000 SL advertisement, describing the computer and built-in MS-DOS and DeskMate.",
         SL_AD),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    staged = []
    for stem, document, source, page, heading, caption, alt, url in specs:
        data, width, height = png_page(document, page, args.width)
        output = args.output / (stem + ".png")
        output.write_bytes(data)
        staged.append({
            "id": "ui.history." + stem.replace("-", "."),
            "path": "history/" + stem + ".png",
            "sha256": digest(output),
            "source_sha256": digest(source),
            "source_id": stem.replace("-", "_"),
            "size": len(data), "width": width, "height": height,
            "origin": "publisher-distributed-illustration",
            "caption": caption, "alt": alt,
            "rights_note": "Original Tandy/Radio Shack work; original rights retained. Historical editorial excerpt, not project-licensed original artwork.",
            "page_id": "history.timeline", "section_heading": heading,
            "original_url": url, "source_pdf_page_zero_based": page,
            "status": "unreviewed-staging-only",
        })
    report = {
        "status": "STAGING ONLY — NOT AUTHORIZED FOR AUTOMATIC PUBLICATION",
        "sources": {"tandy_catalog": {"sha256": digest(args.catalog), "url": CATALOG},
                    "sl_ad": {"sha256": digest(args.sl_ad), "url": SL_AD}},
        "staged": staged,
        "review": [
            "Inspect actual source scans and every output PNG pixel",
            "Confirm magazine page index, issue date, and captions",
            "Confirm source attribution and publication basis for limited excerpts",
            "Check no private data or misleading crop is present",
            "Only then copy approved PNGs and audited image metadata to website",
            "Provide accurate .png.license sidecars and website figure tests",
        ],
    }
    (args.output / "staging-manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Staged", len(staged), "historical PNGs; no files published.")
    for entry in staged:
        print(entry["path"], entry["size"], entry["sha256"])


if __name__ == "__main__":
    main()
