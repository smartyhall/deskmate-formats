#!/usr/bin/env python3
"""Classify GitHub Actions changes; skip portable CI only for site-only diffs.

This is intentionally a small, conservative allowlist. Unknown, deleted, mixed,
or unresolvable changes run the full cross-platform matrix.
"""
# SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess

SITE_DIRS = ("website/", "docs/site/")
SITE_WORKFLOWS = frozenset({
    ".github/workflows/reference-preview.yml",
    ".github/workflows/reference-publish.yml",
})
SHA = re.compile(r"[0-9a-f]{40}")


def needs_portable(paths: set[str]) -> bool:
    """Return True unless every changed path belongs solely to the website."""
    return not paths or any(
        not (path.startswith(SITE_DIRS) or path in SITE_WORKFLOWS)
        for path in paths
    )


def changed_paths(event: str, previous: str, base: str, head: str) -> set[str]:
    """Compare PR merge result to its base, or a push commit to its predecessor."""
    start = base if event == "pull_request" else previous if event == "push" else ""
    if not all(SHA.fullmatch(value or "") for value in (start, head)):
        raise ValueError("missing or invalid Git revision; full CI required")
    if start == "0" * 40:
        raise ValueError("new branch or initial push; full CI required")
    result = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", "-z", start, head],
        check=True, capture_output=True,
    )
    return {item.decode("utf-8", "surrogateescape")
            for item in result.stdout.split(b"\0") if item}


def main() -> None:
    event = os.getenv("EVENT_NAME", "")
    try:
        paths = changed_paths(
            event, os.getenv("BEFORE_SHA", ""), os.getenv("PR_BASE_SHA", ""),
            os.getenv("GITHUB_SHA", ""),
        )
        portable = needs_portable(paths)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # A classification problem must never be interpreted as a site-only diff.
        print(f"Unable to classify changes safely: {error}; running full CI.")
        paths, portable = set(), True
    print(f"Changed paths: {len(paths)}; portable matrix required: {portable}")
    for path in sorted(paths):
        print(f"  {path}")
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"portable={'true' if portable else 'false'}\n")


if __name__ == "__main__":
    main()
