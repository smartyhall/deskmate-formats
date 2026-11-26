#!/usr/bin/env python3
"""Verify that generated static-site links and fragment references resolve."""
# SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import json
import posixpath
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.duplicates: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            identifier = attributes["id"]
            if identifier in self.ids:
                self.duplicates.append(identifier)
            self.ids.add(identifier)
        if tag == "a" and attributes.get("name"):
            self.ids.add(attributes["name"])
        key = "href" if tag in ("a", "link") else "src" if tag in ("script", "img") else ""
        if key and attributes.get(key):
            self.links.append(attributes[key])


def check(root: Path, base: str) -> list[str]:
    if not base.startswith("/") or not base.endswith("/"):
        raise ValueError("Base path must start and end with /")
    files = {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}
    docs = {name: Document() for name in files if name.endswith(".html")}
    for name, parser in docs.items():
        parser.feed(files[name].read_text(encoding="utf-8"))
    issues: list[str] = []
    scanned = 0
    for source, parser in docs.items():
        for duplicate in parser.duplicates:
            issues.append(f"{source}: duplicate ID #{duplicate}")
        for href in parser.links:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or href.startswith("//"):
                continue
            raw_path = unquote(parsed.path)
            if raw_path.startswith("/"):
                if not raw_path.startswith(base):
                    issues.append(f"{source}: reference outside site base: {href}")
                    continue
                target = raw_path[len(base):]
            else:
                target = posixpath.normpath(posixpath.join(
                    posixpath.dirname(source), raw_path
                )) if raw_path else source
                if target == ".":
                    target = ""
            if not target or target.endswith("/"):
                target += "index.html"
            if target not in files and not Path(target).suffix:
                target = target.rstrip("/") + "/index.html"
            scanned += 1
            if target not in files:
                issues.append(f"{source}: missing target: {href}")
            elif parsed.fragment and target in docs and unquote(parsed.fragment) not in docs[target].ids:
                issues.append(f"{source}: missing fragment: {href}")
    print(f"Static site: {len(docs)} HTML pages, {scanned} internal references, {len(issues)} issues")
    return issues


def check_baseline(root: Path, baseline: dict, *, capture: bool = False) -> list[str]:
    """Check source-revision routes and recorded HTML anchors independently of links.

    Capture is deliberately explicit and should be run against the pinned
    pre-change build, never a changed build to silence a regression.
    """
    issues: list[str] = []
    if baseline.get("schema_version") != 1:
        return ["unsupported route baseline schema"]
    status = baseline.get("anchor_status")
    if status not in ("pending-rendered-baseline", "captured"):
        return ["invalid route baseline anchor status"]
    if capture and status != "pending-rendered-baseline":
        return ["refusing to overwrite a captured anchor baseline"]
    routes = baseline.get("routes")
    if not isinstance(routes, list) or not routes:
        return ["route baseline must contain routes"]
    seen: set[str] = set()
    for entry in routes:
        if not isinstance(entry, dict):
            issues.append("malformed baseline entry")
            continue
        route = entry.get("route")
        if (not isinstance(route, str) or not route.startswith("/")
                or not route.endswith("/") or "//" in route
                or any(part in (".", "..") for part in route.split("/"))
                or any(char in route for char in "\\?#%")):
            issues.append(f"invalid baseline route: {route!r}")
            continue
        if route in seen:
            issues.append(f"duplicate baseline route: {route}")
            continue
        seen.add(route)
        expected = entry.get("anchors")
        if expected is None and status == "captured":
            issues.append(f"{route}: captured baseline has no anchor list")
        if expected is not None and (
            not isinstance(expected, list)
            or not all(isinstance(a, str) and a for a in expected)
            or len(set(expected)) != len(expected)
        ):
            issues.append(f"{route}: invalid baseline anchors")
            continue
        target = root / route.strip("/") / "index.html"
        if not target.is_file():
            issues.append(f"{route}: missing baseline route")
            continue
        parser = Document()
        parser.feed(target.read_text(encoding="utf-8"))
        if capture:
            entry["anchors"] = sorted(parser.ids)
        elif expected is not None:
            for missing in sorted(set(expected) - parser.ids):
                issues.append(f"{route}: missing baseline anchor #{missing}")
    if capture and not issues:
        baseline["anchor_status"] = "captured"
    return issues


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("site_output", type=Path)
    cli.add_argument("base_path")
    cli.add_argument(
        "--baseline", type=Path,
        default=Path(__file__).resolve().parents[2] / "docs/site/published-route-baseline.json",
    )
    cli.add_argument("--capture-anchors", action="store_true",
                     help="emit baseline JSON from the pinned pre-change build to stdout")
    args = cli.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    failures = check_baseline(args.site_output, baseline, capture=args.capture_anchors)
    if args.capture_anchors:
        if not failures:
            print(json.dumps(baseline, indent=2, ensure_ascii=False))
    else:
        if baseline["anchor_status"] == "pending-rendered-baseline":
            print("Route baseline active; rendered anchor capture pending", file=sys.stderr)
        failures.extend(check(args.site_output, args.base_path))
    for problem in failures:
        print(problem, file=sys.stderr)
    raise SystemExit(bool(failures))
