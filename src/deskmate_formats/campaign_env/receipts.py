"""Durable receipts, and the redacted projection that may be published.

A receipt is written once, atomically, and digested, so a later reader can tell
whether what it is reading is what was written.  The full receipt contains
absolute paths, because that is what makes it useful locally; the *public*
projection removes them, because this laboratory's paths name the account, the
checkout layout and other campaigns.

The projection is an allowlist walk rather than a blocklist: a key this module
has never heard of is dropped instead of published by default, so adding a
field to a receipt cannot leak it.  This is not a general secret filter —
receipts here contain no credentials or prompts to begin with — and a receipt
still needs reading before it is published.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

MAX_RECEIPT_BYTES = 8 * 1024 * 1024

REDACTED_PATH = "<path>"
REDACTED_HOME = "<home>"

_WINDOWS_PATH = r"[A-Za-z]:[\\/][^\s\"'<>|,;]*"
_UNC_PATH = r"\\\\[^\s\"'<>|,;]+"
_HOME_PATH = r"/(?:home|Users)/[^\s\"'<>|,;]+"

#: Keys whose value is a private path.  The value is replaced by a redacted
#: string, so the receipt keeps its shape without keeping the location.
PATH_KEYS = frozenset({
    "checkout",
    "root",
    "directory",
    "venv",
    "site_packages",
    "interpreter",
    "executable",
    "cwd",
    "top_level",
    "origin",
    "expected_origin",
    "record",
    "record_path",
    "probe_origin",
    "path",
    "private_root",
    "env_root",
    "experiment_root",
    "recorded_checkout",
})

#: Keys dropped outright: a search path is a list of private directories.
DROPPED_KEYS = frozenset({"sys_path", "environment", "env"})

#: Keys reduced to their file name, like the performance harness does for the
#: interpreter: the directory names the account, the name does not.
BASENAME_KEYS = frozenset({"basename"})


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(record: object) -> bytes:
    return (json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write(path: "str | os.PathLike[str]", record: object) -> dict[str, object]:
    """Write one receipt atomically and return its digest and size."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical(record)
    if len(payload) > MAX_RECEIPT_BYTES:
        raise ValueError("receipt exceeds the reviewed size limit")
    handle, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return {"path": str(target), "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def read(path: "str | os.PathLike[str]") -> dict[str, object]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    if target.stat().st_size > MAX_RECEIPT_BYTES:
        raise ValueError("receipt exceeds the reviewed size limit")
    return json.loads(target.read_text(encoding="utf-8"))


def file_digest(path: "str | os.PathLike[str]") -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def redact(text: object, *, roots: "tuple[str, ...]" = ()) -> str:
    """Replace known private roots and path-like content with placeholders."""
    if text is None:
        return ""
    result = str(text)
    if not result:
        return ""
    for root in sorted((item for item in roots if item and len(item) > 3), key=len, reverse=True):
        for variant in {root, root.replace("\\", "/"), root.replace("/", "\\")}:
            result = re.sub(re.escape(variant) + r"[^\s\"'<>|,;]*", REDACTED_PATH, result, flags=re.IGNORECASE)
    result = re.sub(_WINDOWS_PATH, REDACTED_PATH, result)
    result = re.sub(_UNC_PATH, REDACTED_PATH, result)
    result = re.sub(_HOME_PATH, REDACTED_HOME, result)
    return result


def _project(value: object, roots: "tuple[str, ...]", *, key: str | None = None) -> object:
    if key is not None and key in DROPPED_KEYS:
        return None
    if isinstance(value, dict):
        # A null value is a recorded observation ("revision unknown"), not an
        # absent key: dropping it would turn "could not establish" into "did not
        # ask", so only DROPPED_KEYS are removed.
        return {name: _project(item, roots, key=name) for name, item in value.items()
                if name not in DROPPED_KEYS}
    if isinstance(value, list):
        return [_project(item, roots) for item in value]
    if isinstance(value, str):
        if key in PATH_KEYS:
            return redact(Path(value).name if key in BASENAME_KEYS else value, roots=roots)
        return redact(value, roots=roots)
    return value


def public(record: dict[str, object], *, roots: "tuple[str, ...]" = ()) -> dict[str, object]:
    """The publishable form of a receipt: same measurements, no private paths."""
    private_roots = tuple({*(str(root) for root in roots if root), os.getcwd()})
    projected = _project(record, private_roots)
    assert isinstance(projected, dict)
    projected["public_projection_version"] = 1
    projected["projected_utc"] = utc_now()
    return projected
