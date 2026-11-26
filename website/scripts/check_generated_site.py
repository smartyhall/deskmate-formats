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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from reference_route_baseline import check_baseline  # noqa: E402


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


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("site_output", type=Path)
    cli.add_argument("base_path")
    cli.add_argument(
        "--baseline", type=Path,
        default=Path(__file__).resolve().parents[2] / "docs/site/published-route-baseline.json",
    )
    modes = cli.add_mutually_exclusive_group()
    modes.add_argument("--capture-anchors", action="store_true")
    modes.add_argument("--extend-baseline", action="store_true")
    cli.add_argument("--source-revision")
    cli.add_argument("--source-kind", choices=("verified-ci-artifact", "verified-local-build"))
    cli.add_argument("--artifact-id", type=int)
    cli.add_argument("--artifact-sha256")
    cli.add_argument("--output", type=Path, help="write reviewed candidate JSON as UTF-8")
    args = cli.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        updating = args.capture_anchors or args.extend_baseline
        failures = check_baseline(
            args.site_output, baseline, capture=args.capture_anchors,
            extend=args.extend_baseline, source_revision=args.source_revision,
            source_kind=args.source_kind, artifact_id=args.artifact_id,
            artifact_sha256=args.artifact_sha256,
        )
        if updating and not failures:
            payload = json.dumps(baseline, indent=2, ensure_ascii=True) + "\n"
            if args.output:
                if args.output.resolve() == args.baseline.resolve():
                    raise ValueError("write candidate to a separate file for review")
                args.output.write_text(payload, encoding="utf-8")
            else:
                print(payload, end="")
        elif not updating:
            if isinstance(baseline, dict) and baseline.get("anchor_status") == "pending-rendered-baseline":
                print("Route baseline active; rendered anchor capture pending", file=sys.stderr)
            failures.extend(check(args.site_output, args.base_path))
    except (OSError, UnicodeError, ValueError) as error:
        failures = [f"Unable to read or process route baseline: {error}"]
    for problem in failures:
        print(problem, file=sys.stderr)
    raise SystemExit(bool(failures))
