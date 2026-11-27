"""Extend the published route baseline from a verified site artifact.

The baseline is additive: this tool may add routes and anchors, but it never
removes or rewrites an existing route's anchors. ``check_baseline`` already
fails when a captured anchor is missing from the rendered document, so a
disappearing public target stops the extension instead of being refreshed away.

Adding a route and capturing its anchors are deliberately separate: a new route
is inserted with an empty anchor list and only then filled from the artifact, so
the review diff shows which routes are new.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reference_route_baseline import check_baseline  # noqa: E402


def page_routes(page_map: dict) -> list[tuple[str, str]]:
    """Return (route, page id) in the page map's own reading order."""
    routes = []
    for entry in page_map.get("pages", []):
        slug = entry["slug"]
        routes.append((f"/{slug}/", entry["id"]))
    return routes


def merge_routes(baseline: dict, page_map: dict) -> list[str]:
    """Insert missing page routes at their page-map position; keep the rest."""
    existing = {entry["route"]: entry for entry in baseline["routes"]}
    ordered = [existing[route] for route in ("/", "/search/") if route in existing]
    for route, page_id in page_routes(page_map):
        if route in existing:
            ordered.append(existing[route])
        else:
            ordered.append({"route": route, "page_id": page_id, "anchors": []})
    # Any baseline route that the page map no longer describes is retained for
    # review rather than dropped silently.
    described = {route for route, _ in page_routes(page_map)} | {"/", "/search/"}
    for entry in baseline["routes"]:
        if entry["route"] not in described:
            ordered.append(entry)
    return ordered


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--page-map", type=Path, required=True)
    parser.add_argument("--site", type=Path, required=True,
                        help="Extracted verified artifact (or local build) root")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--source-kind", choices=("verified-ci-artifact", "verified-local-build"),
                        required=True)
    parser.add_argument("--artifact-id", type=int)
    parser.add_argument("--artifact-sha256")
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    page_map = json.loads(args.page_map.read_text(encoding="utf-8"))

    before = {entry["route"]: set(entry.get("anchors") or []) for entry in baseline["routes"]}
    baseline["routes"] = merge_routes(baseline, page_map)

    missing = [entry["route"] for entry in baseline["routes"]
               if not (args.site / entry["route"].strip("/") / "index.html").is_file()]
    if missing:
        for route in missing:
            print(f"missing from artifact: {route}")
        return 1

    issues = check_baseline(
        args.site,
        baseline,
        extend=True,
        source_revision=args.source_revision,
        source_kind=args.source_kind,
        artifact_id=args.artifact_id,
        artifact_sha256=args.artifact_sha256,
        workflow_run_id=args.workflow_run_id,
    )
    if issues:
        for issue in issues:
            print(issue)
        return 1

    added_routes, added_anchors, lost = [], 0, []
    for entry in baseline["routes"]:
        route = entry["route"]
        after = set(entry["anchors"])
        previous = before.get(route, set())
        if route not in before:
            added_routes.append((route, len(after)))
        else:
            if previous - after:
                lost.append((route, sorted(previous - after)))
            added_anchors += len(after - previous)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

    print(f"routes: {len(before)} -> {len(baseline['routes'])}")
    for route, count in added_routes:
        print(f"  new route {route} with {count} anchors")
    print(f"anchors added to existing routes: {added_anchors}")
    print(f"anchors removed: {len(lost)}")
    for route, anchors in lost:
        print(f"  {route}: {anchors}")
    print(f"wrote {args.output}")
    return 0 if not lost else 1


if __name__ == "__main__":
    raise SystemExit(main())
