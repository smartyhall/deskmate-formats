"""Redaction and the sanitized publication projection for performance reports.

A report quotes test messages, skip reasons, interpreter paths and the command
that produced it. On a shared laboratory VM those contain account names,
checkout locations, temporary directories and exception strings that must not be
published. Two mechanisms keep them out of anything shareable:

``redact_text``
    scrubs path-like content from free text as it is recorded, so a stored
    report does not accumulate private paths in the first place;

``public_projection``
    reduces a whole report to an allowlist of fields, so a field added later
    cannot be published by accident.

Neither function is a general secret filter. Neither removes tokens, keys or
prompt text, so a report still needs reading before it is published; what they
guarantee is that routine paths and messages do not travel with it.
"""

from __future__ import annotations

import os
from typing import Any


REDACTED_PATH = "<path>"
REDACTED_HOME = "<home>"

# A drive-qualified path, a UNC share, and a home directory prefix.  POSIX
# system paths (``/usr/bin/python3``) are left alone: they are not private and
# removing them makes a report harder to read than it needs to be.
_WINDOWS_PATH = r"[A-Za-z]:[\\/][^\s\"'<>|,;]*"
_UNC_PATH = r"\\\\[^\s\"'<>|,;]+"
_HOME_PATH = r"/(?:home|Users)/[^\s\"'<>|,;]+"

#: ``meta`` keys that may be published.  Anything else a future version adds is
#: dropped from the public projection instead of being published by default.
PUBLIC_META_KEYS: tuple[str, ...] = (
    "label",
    "profile",
    "started_utc",
    "finished_utc",
    "wall_seconds",
    "tests",
    "outcomes",
    "successful",
    "iteration",
    "iterations",
    "iteration_wall_seconds",
    "iteration_outcomes",
    "discovered_tests",
    "executed_tests",
    "trace_processes",
    "trace_git_commands",
    "sample_interval",
    "sample_tests",
    "host_sampling",
    "invocation",
    "source",
    "source_before",
    "source_after",
    "source_changed",
    "package",
    "timing",
)

#: ``environment`` keys that may be published.  The executable is reduced to
#: its file name: the directory names the account and the install layout.
PUBLIC_ENVIRONMENT_KEYS: tuple[str, ...] = (
    "python_version",
    "python_implementation",
    "platform",
    "system",
    "release",
    "machine",
    "processor",
    "cpu_count",
    "preferred_encoding",
    "python_utf8_mode",
    "python_dont_write_bytecode",
)

_SOURCE_KEYS = (
    "revision", "branch", "dirty", "complete", "worktree_digest",
    "untracked_digest", "untracked_files", "untracked_bytes",
    "untracked_truncated", "untracked_reason", "state", "observed_utc",
)


def redact_text(text: object, *, roots: tuple[str, ...] = ()) -> str:
    """Replace path-like content in ``text`` with placeholders.

    ``roots`` are exact directories the caller knows are private (the working
    directory, the checkout, the temporary root).  They are replaced first, then
    anything that still looks like a drive-qualified, UNC or home-directory path.
    """
    if text is None:
        return ""
    result = str(text)
    if not result:
        return ""
    for root in sorted((item for item in roots if item and len(item) > 3), key=len, reverse=True):
        for variant in {root, root.replace("\\", "/"), root.replace("/", "\\")}:
            # A known private root is replaced together with whatever follows
            # it, so a file name under that directory cannot survive the prefix.
            result = _sub_literal(result, variant, REDACTED_PATH)
    result = _sub_pattern(result, _WINDOWS_PATH, REDACTED_PATH)
    result = _sub_pattern(result, _UNC_PATH, REDACTED_PATH)
    result = _sub_pattern(result, _HOME_PATH, REDACTED_HOME)
    return result


def _sub_literal(text: str, needle: str, replacement: str) -> str:
    import re

    # Consume the rest of the path-like token, not just the prefix: replacing
    # ``C:\work`` in ``C:\work\secret.json`` would leave ``\secret.json``.
    pattern = re.escape(needle) + r"[^\s\"'<>|,;]*"
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)


def _sub_pattern(text: str, pattern: str, replacement: str) -> str:
    import re

    return re.sub(pattern, replacement, text)


def _source_projection(source: object) -> object:
    if not isinstance(source, dict):
        return source
    projected = {key: source.get(key) for key in _SOURCE_KEYS}
    failures = source.get("failed_commands") or []
    # Each entry is harness-generated argument names plus a failure class.  The
    # failure class is a type name, never an exception string: Git's stderr can
    # quote the paths that were just redacted.
    projected["failed_commands"] = [
        {
            "arguments": [str(item) for item in (entry.get("arguments") or [])],
            "returncode": entry.get("returncode"),
            "failure": entry.get("failure"),
        }
        for entry in failures
        if isinstance(entry, dict)
    ]
    return projected


def _package_projection(package: object) -> object:
    if not isinstance(package, dict):
        return package
    modules = package.get("modules") or {}
    return {
        "name": package.get("name"),
        "version": package.get("version"),
        "distribution_version": package.get("distribution_version"),
        # The origin itself is a checkout path; whether it was established, and
        # whether it matched the named source, are the parts worth publishing.
        "origin_recorded": bool(package.get("origin")),
        "expected_origin_recorded": bool(package.get("expected_origin")),
        "matches_source": package.get("matches_source"),
        "source_on_path": package.get("source_on_path"),
        "source_first": package.get("source_first"),
        "modules_recorded": sorted(
            name for name, path in modules.items() if path is not None
        ),
    }


def public_projection(report: dict[str, Any], *,
                     roots: tuple[str, ...] = ()) -> dict[str, Any]:
    """Return the publishable form of a run report.

    The projection keeps every measurement and every identity verdict, and drops
    the parts that describe *where* the measurement was taken: absolute paths,
    the raw working directory and unredacted free text.

    The current working directory is always treated as private, so a report
    loaded from an older version is scrubbed as thoroughly as a fresh one.
    """
    private_roots = (*roots, os.getcwd())
    meta = report.get("meta") or {}
    environment = report.get("environment") or {}
    host = report.get("host") or {}

    projected_meta: dict[str, Any] = {
        key: meta.get(key) for key in PUBLIC_META_KEYS if key in meta
    }
    for key in ("source", "source_before", "source_after"):
        if key in projected_meta:
            projected_meta[key] = _source_projection(projected_meta[key])
    if "package" in projected_meta:
        projected_meta["package"] = _package_projection(projected_meta["package"])

    projected_environment = {
        key: environment.get(key) for key in PUBLIC_ENVIRONMENT_KEYS
    }
    executable = environment.get("python_executable")
    projected_environment["python_executable_name"] = (
        os.path.basename(str(executable)) if executable else None
    )

    invocation = projected_meta.get("invocation")
    if isinstance(invocation, dict) and invocation.get("arguments"):
        projected_meta["invocation"] = dict(
            invocation,
            arguments=redact_text(invocation["arguments"], roots=private_roots),
        )

    projected_tests = []
    for test in report.get("tests") or ():
        entry = dict(test)
        entry["message"] = redact_text(test.get("message"), roots=private_roots)
        projected_tests.append(entry)

    projected_errors = []
    for issue in report.get("suite_errors") or ():
        entry = dict(issue)
        entry["message"] = redact_text(issue.get("message"), roots=private_roots)
        projected_errors.append(entry)

    return {
        "schema_version": report.get("schema_version"),
        "meta": projected_meta,
        "environment": projected_environment,
        "host": {
            "summary": host.get("summary"),
            "sampling": host.get("sampling"),
            "samples": host.get("samples"),
        },
        "tests": projected_tests,
        "suite_errors": projected_errors,
    }
