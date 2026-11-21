"""Validate stable reference-page IDs and source ownership before site generation."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys


ID = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9-]*)+$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$")
SECTIONS = {
    "introduction", "planning", "system", "formats", "applications", "research",
    "evidence", "recovery",
}
ROLES = {
    "site-plan", "current-guide", "manufacturer-reference",
    "dated-research", "dated-snapshot",
}
REQUIRED = {"id", "slug", "title", "section", "role", "source"}


def validate_map(data, root):
    """Return actionable errors; never perform site rendering or file writes."""
    errors = []
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return ["page map must be an object with schema_version 1"]
    if set(data) != {"schema_version", "pages"}:
        errors.append("page map keys must be schema_version and pages")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        return errors + ["pages must be a nonempty array"]

    root = Path(root).resolve()
    used_ids, used_slugs, used_sources = set(), set(), set()
    for index, entry in enumerate(pages, 1):
        label = f"page {index}"
        if not isinstance(entry, dict) or set(entry) != REQUIRED:
            errors.append(f"{label}: requires exactly {sorted(REQUIRED)}")
            continue
        if not all(isinstance(entry[key], str) and entry[key].strip()
                   and entry[key] == entry[key].strip() for key in REQUIRED):
            errors.append(f"{label}: metadata values must be nonempty strings")
            continue
        page_id, slug, source = entry["id"], entry["slug"], entry["source"]
        if not ID.fullmatch(page_id):
            errors.append(f"{label}: invalid page id {page_id!r}")
        if not SLUG.fullmatch(slug):
            errors.append(f"{label}: invalid route slug {slug!r}")
        if entry["section"] not in SECTIONS:
            errors.append(f"{label}: unknown section {entry['section']!r}")
        if entry["role"] not in ROLES:
            errors.append(f"{label}: unknown source role {entry['role']!r}")
        for kind, value, seen in (
            ("id", page_id, used_ids), ("slug", slug, used_slugs),
            ("source", source, used_sources),
        ):
            if value in seen:
                errors.append(f"{label}: duplicate {kind} {value!r}")
            seen.add(value)

        candidate = PurePosixPath(source)
        if (source.startswith("/") or "\\" in source or
                ".." in candidate.parts or "." in candidate.parts or
                len(candidate.parts) < 2 or candidate.parts[0] != "docs" or
                candidate.suffix != ".md"):
            errors.append(f"{label}: unsafe or non-document source {source!r}")
            continue
        target = (root / source).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            errors.append(f"{label}: source missing or outside repo {source!r}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--map", dest="map_path", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    location = args.map_path or root / "docs/site/page-map.json"
    try:
        data = json.loads(location.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"Unable to read reference page map: {error}", file=sys.stderr)
        return 1
    errors = validate_map(data, root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Reference page map: {len(data['pages'])} valid staged pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
