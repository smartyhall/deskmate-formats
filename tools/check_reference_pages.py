"""Validate stable reference-page IDs and source ownership before site generation."""

import argparse
import datetime
import json
from pathlib import Path, PurePosixPath
import re
import sys


ID = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9-]*)+$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$")
# Version 1 kept the eight repository-organisation groups.
SECTIONS = {
    "introduction", "planning", "system", "formats", "applications", "research",
    "evidence", "recovery",
}
# Version 2 classifies navigation by reader question instead.
SECTION_IDS = ("deskmate", "formats", "recovery", "research", "project")
ROLES = {
    "site-plan", "current-guide", "manufacturer-reference",
    "dated-research", "dated-snapshot",
}
REQUIRED = {"id", "slug", "title", "section", "role", "source"}
REQUIRED_V2 = REQUIRED | {"subsection", "order", "summary", "date", "is_hub"}
SUMMARY_MAX = 240
SUBSECTION_MAX = 80
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _trimmed(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _check_identity(entry, errors, label, used):
    """Validate the identity fields shared by both schema versions."""
    page_id, slug, source = entry["id"], entry["slug"], entry["source"]
    if not ID.fullmatch(page_id):
        errors.append(f"{label}: invalid page id {page_id!r}")
    if not SLUG.fullmatch(slug):
        errors.append(f"{label}: invalid route slug {slug!r}")
    for kind, value in (("id", page_id), ("slug", slug), ("source", source)):
        if value in used[kind]:
            errors.append(f"{label}: duplicate {kind} {value!r}")
        used[kind].add(value)


def _check_source(source, root, errors, label):
    candidate = PurePosixPath(source)
    if (source.startswith("/") or "\\" in source or
            ".." in candidate.parts or "." in candidate.parts or
            len(candidate.parts) < 2 or candidate.parts[0] != "docs" or
            candidate.suffix != ".md"):
        errors.append(f"{label}: unsafe or non-document source {source!r}")
        return
    target = (root / source).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        errors.append(f"{label}: source missing or outside repo {source!r}")


def _validate_v1(data, root):
    errors = []
    if set(data) != {"schema_version", "pages"}:
        errors.append("page map keys must be schema_version and pages")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        return errors + ["pages must be a nonempty array"]

    root = Path(root).resolve()
    used = {"id": set(), "slug": set(), "source": set()}
    for index, entry in enumerate(pages, 1):
        label = f"page {index}"
        if not isinstance(entry, dict) or set(entry) != REQUIRED:
            errors.append(f"{label}: requires exactly {sorted(REQUIRED)}")
            continue
        if not all(_trimmed(entry[key]) for key in REQUIRED):
            errors.append(f"{label}: metadata values must be nonempty strings")
            continue
        if entry["section"] not in SECTIONS:
            errors.append(f"{label}: unknown section {entry['section']!r}")
        if entry["role"] not in ROLES:
            errors.append(f"{label}: unknown source role {entry['role']!r}")
        _check_identity(entry, errors, label, used)
        _check_source(entry["source"], root, errors, label)
    return errors


def _validate_hub(entry, errors, label):
    """A hub owns its section route and carries no subsection."""
    if entry["is_hub"] is not True:
        return
    if entry["slug"] != entry["section"]:
        errors.append(f"{label}: hub slug must equal section {entry['section']!r}")
    if entry["subsection"] is not None:
        errors.append(f"{label}: hub must not declare a subsection")


def _validate_entry_v2(entry, errors, label, root, used, hubs):
    if not isinstance(entry, dict) or set(entry) != REQUIRED_V2:
        errors.append(f"{label}: requires exactly {sorted(REQUIRED_V2)}")
        return False
    for key in ("id", "slug", "title", "section", "role", "source", "summary"):
        if not _trimmed(entry[key]):
            errors.append(f"{label}: {key} must be a nonempty trimmed string")
            return False
    if entry["section"] not in SECTION_IDS:
        errors.append(f"{label}: unknown navigation section {entry['section']!r}")
    if entry["role"] not in ROLES:
        errors.append(f"{label}: unknown source role {entry['role']!r}")
    if not isinstance(entry["is_hub"], bool):
        errors.append(f"{label}: is_hub must be a boolean")
        return False
    subsection = entry["subsection"]
    if subsection is not None and not (
        _trimmed(subsection) and len(subsection) <= SUBSECTION_MAX
    ):
        errors.append(f"{label}: subsection must be null or a trimmed 1-{SUBSECTION_MAX} character label")
    if isinstance(entry["order"], bool) or not isinstance(entry["order"], int) or entry["order"] < 0:
        errors.append(f"{label}: order must be a nonnegative integer")
    summary = entry["summary"]
    if _trimmed(summary):
        if len(summary) > SUMMARY_MAX:
            errors.append(f"{label}: summary exceeds {SUMMARY_MAX} characters")
        if "<" in summary or ">" in summary:
            errors.append(f"{label}: summary must be plain text, not markup")
    moment = entry["date"]
    if moment is not None:
        if not isinstance(moment, str) or not DATE.fullmatch(moment):
            errors.append(f"{label}: date must be null or an ISO calendar date")
        else:
            try:
                datetime.date.fromisoformat(moment)
            except ValueError:
                errors.append(f"{label}: date is not a real calendar date")
    _validate_hub(entry, errors, label)
    _check_identity(entry, errors, label, used)
    _check_source(entry["source"], root, errors, label)
    if entry["is_hub"] is True:
        hubs.setdefault(entry["section"], []).append(entry["id"])
    return True


def _validate_v2(data, root):
    errors = []
    if set(data) != {"schema_version", "pages"}:
        errors.append("page map keys must be schema_version and pages")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        return errors + ["pages must be a nonempty array"]

    root = Path(root).resolve()
    used = {"id": set(), "slug": set(), "source": set()}
    hubs = {}
    usable = []
    for index, entry in enumerate(pages, 1):
        if _validate_entry_v2(entry, errors, f"page {index}", root, used, hubs):
            usable.append(entry)
    if usable:
        for section in SECTION_IDS:
            found = hubs.get(section, [])
            if len(found) != 1:
                errors.append(
                    f"section {section!r}: requires exactly one hub, found {len(found)}"
                )
        subsections = {}
        for entry in usable:
            if entry["is_hub"] is not True:
                subsections.setdefault(entry["section"], set()).add(entry["subsection"])
        for section, labels in subsections.items():
            if None in labels:
                errors.append(f"section {section!r}: ordinary pages require a subsection")
    return errors


def validate_map(data, root):
    """Return actionable errors; never perform site rendering or file writes."""
    if not isinstance(data, dict):
        return ["page map must be an object"]
    version = data.get("schema_version")
    if version == 1:
        return _validate_v1(data, root)
    if version == 2:
        return _validate_v2(data, root)
    return ["page map must use schema_version 1 or 2"]


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
