"""Validate and extend reviewed reference-site route and content-anchor baselines."""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import re


SOURCE_KINDS = ("verified-ci-artifact", "verified-local-build")
HISTORY_KEYS = {
    "source_revision", "source_kind", "captured_at", "artifact_id",
    "artifact_sha256", "workflow_run_id",
}
REVISION = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|\+00:00)")


class AnchorDocument(HTMLParser):
    """Track all public targets, plus the document article's content targets."""

    def __init__(self):
        super().__init__()
        self.ids = set()
        self.content_ids = set()
        self.duplicates = set()
        self.article_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.article_depth += 1
        attributes = dict(attrs)
        targets = {attributes.get("id")}
        if tag == "a":
            targets.add(attributes.get("name"))
        for target in targets - {None, ""}:
            if target in self.ids:
                self.duplicates.add(target)
            self.ids.add(target)
            if self.article_depth:
                self.content_ids.add(target)

    def handle_endtag(self, tag):
        if tag == "article" and self.article_depth:
            self.article_depth -= 1


def _positive(value):
    return type(value) is int and value > 0


def _validate_history(history) -> list[str]:
    """History entries must stay reviewable across hand edits and tool updates."""
    if history is None:
        return []
    if not isinstance(history, list):
        return ["capture history must be a list"]
    issues = []
    for index, record in enumerate(history, 1):
        label = f"capture history {index}"
        if not isinstance(record, dict):
            issues.append(f"{label}: must be an object")
            continue
        unknown = set(record) - HISTORY_KEYS
        if unknown:
            issues.append(f"{label}: unknown keys {sorted(unknown)}")
        revision = record.get("source_revision")
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            issues.append(f"{label}: source_revision must be an exact revision")
        if record.get("source_kind") not in SOURCE_KINDS:
            issues.append(f"{label}: invalid source_kind")
        stamp = record.get("captured_at")
        if not isinstance(stamp, str) or not TIMESTAMP.fullmatch(stamp):
            issues.append(f"{label}: captured_at must be a UTC timestamp")
        artifact = record.get("artifact_id")
        digest = record.get("artifact_sha256")
        if record.get("source_kind") == "verified-ci-artifact":
            if not _positive(artifact) or not isinstance(digest, str) or not DIGEST.fullmatch(digest):
                issues.append(f"{label}: CI capture requires artifact ID and SHA-256")
        elif artifact is not None or digest is not None:
            issues.append(f"{label}: local capture must not claim an artifact")
        run_id = record.get("workflow_run_id")
        if run_id is not None and not _positive(run_id):
            issues.append(f"{label}: workflow_run_id must be null or a positive integer")
    return issues


def _now() -> str:
    return (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        .replace("+00:00", "Z")
    )


def check_baseline(root: Path, baseline: dict, *, capture=False, extend=False,
                   source_revision=None, source_kind=None, artifact_id=None,
                   artifact_sha256=None, workflow_run_id=None) -> list[str]:
    """Check or update in memory; capture/extension never removes old anchors.

    Source revision is a caller attestation, not a claim that HTML proves
    its own provenance. Verify CI artifact metadata/digest or build checkout
    separately before invoking this function.
    """
    if not isinstance(baseline, dict) or baseline.get("schema_version") != 1:
        return ["unsupported route baseline schema"]
    status = baseline.get("anchor_status")
    if status not in ("pending-rendered-baseline", "captured"):
        return ["invalid route baseline anchor status"]
    history_issues = _validate_history(baseline.get("capture_history"))
    if history_issues:
        return history_issues
    if capture and (extend or status != "pending-rendered-baseline"):
        return ["initial capture requires a pending baseline"]
    if extend and status != "captured":
        return ["extension requires a captured baseline"]
    updating = capture or extend
    if updating:
        if not isinstance(source_revision, str) or not REVISION.fullmatch(source_revision):
            return ["capture/extension requires an exact source revision"]
        if capture and source_revision != baseline.get("source_revision"):
            return ["capture revision does not match the pinned baseline"]
        if source_kind not in SOURCE_KINDS:
            return ["capture/extension requires a verified source kind"]
        if source_kind == "verified-ci-artifact" and (
            not _positive(artifact_id)
            or not isinstance(artifact_sha256, str)
            or not DIGEST.fullmatch(artifact_sha256)
        ):
            return ["CI capture requires artifact ID and SHA-256"]
        if workflow_run_id is not None and not _positive(workflow_run_id):
            return ["workflow run ID must be a positive integer"]
    routes = baseline.get("routes")
    if not isinstance(routes, list) or not routes:
        return ["route baseline must contain routes"]
    issues = []
    seen = set()
    seen_ids = set()
    updates = []
    for entry in routes:
        if not isinstance(entry, dict):
            issues.append("malformed baseline entry")
            continue
        route = entry.get("route")
        if not isinstance(route, str) or not re.fullmatch(r"/(?:[a-z0-9-]+/)*", route):
            issues.append(f"invalid baseline route: {route!r}")
            continue
        if route in seen:
            issues.append(f"duplicate baseline route: {route}")
            continue
        seen.add(route)
        page_id = entry.get("page_id")
        if page_id is None and route not in ("/", "/search/"):
            issues.append(f"{route}: missing document page ID")
            continue
        if page_id is not None:
            if not isinstance(page_id, str) or not page_id or page_id in seen_ids:
                issues.append(f"{route}: invalid or duplicate document page ID")
                continue
            seen_ids.add(page_id)
        expected = entry.get("anchors")
        if expected is None and status == "captured":
            issues.append(f"{route}: captured baseline has no anchor list")
            continue
        if expected is not None and (
            not isinstance(expected, list)
            or not all(isinstance(a, str) and a for a in expected)
            or len(set(expected)) != len(expected)
            or (page_id is None and expected)
        ):
            issues.append(f"{route}: invalid baseline anchors")
            continue
        target = root / route.strip("/") / "index.html"
        if not target.is_file():
            issues.append(f"{route}: missing baseline route")
            continue
        parser = AnchorDocument()
        parser.feed(target.read_text(encoding="utf-8"))
        for duplicate in sorted(parser.duplicates):
            issues.append(f"{route}: duplicate anchor #{duplicate}")
        for missing in sorted(set(expected or []) - parser.ids):
            issues.append(f"{route}: missing baseline anchor #{missing}")
        if updating:
            additions = parser.content_ids if page_id is not None else set()
            updates.append((entry, sorted(set(expected or []) | additions)))
    if updating and not issues:
        for entry, anchors in updates:
            entry["anchors"] = anchors
        baseline["anchor_status"] = "captured"
        baseline.setdefault("capture_history", []).append({
            "source_revision": source_revision,
            "source_kind": source_kind,
            "captured_at": _now(),
            "artifact_id": artifact_id,
            "artifact_sha256": artifact_sha256,
            "workflow_run_id": workflow_run_id,
        })
    return issues
