"""Versioned task data. This module has no execution semantics."""

from datetime import UTC, datetime
import re

from deskmate_formats.observer.events import EventError, decode_json, encode_json


MAX_MANIFEST_BYTES = 8192
MAX_REVISION = 2**31 - 1
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_SEGMENT = re.compile(r"[a-z0-9][a-z0-9._-]{0,79}")
_DEVICE = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_EXPIRY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_REQUIRED = set("schema_version id revision idempotency_key title description category profile "
                "resources dependencies".split())
_OPTIONAL = {"expires_at", "instructions"}
_EDIT_FIELDS = {"development"}
_DETERMINISTIC_FIELDS = {"deterministic"}
_RESOURCES = {"source-read", "synthetic-fixtures", "portable-tests"}


class TaskError(ValueError):
    """Intake refused. Diagnostics omit submitted values."""


def task_id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise TaskError("invalid task identity or idempotency key")
    return value


def revision(value):
    if type(value) is not int or not 1 <= value <= MAX_REVISION:
        raise TaskError("invalid task revision")
    return value


def safe_path(value):
    if type(value) is not str or len(value) > 240:
        raise TaskError("invalid repository path")
    for segment in value.split("/"):
        if (not _SEGMENT.fullmatch(segment) or segment.endswith(".")
                or _DEVICE.fullmatch(segment.partition(".")[0])):
            raise TaskError("invalid repository path")
    return value


def manifest_path(value):
    safe_path(value)
    parts = value.split("/")
    if len(parts) != 3 or parts[:2] != ["ops", "tasks"] or not parts[2].endswith(".json"):
        raise TaskError("expected a manifest under ops/tasks")
    task_id(parts[2][:-5])
    return value


def plain_text(value, limit, label, *, multiline=False):
    if (type(value) is not str or not 0 < len(value) <= limit or not value.strip()
            or not (value.replace("\n", " ") if multiline else value).isprintable()):
        raise TaskError(f"invalid {label}")
    return value


def _array(value, limit, label):
    if type(value) is not list or len(value) > limit:
        raise TaskError(f"invalid {label}")
    return value


def _members(value, fields, label):
    if type(value) is not dict or value.keys() != fields:
        raise TaskError(f"invalid {label} fields")


def _dependency(value, own_id):
    _members(value, {"id", "revision"}, "dependency")
    identifier = task_id(value["id"])
    if identifier == own_id:
        raise TaskError("task depends on itself")
    return identifier, revision(value["revision"])


def _instruction(value):
    _members(value, {"path", "sha256"}, "instruction reference")
    path = safe_path(value["path"])
    if not path.startswith("docs/") or not path.endswith(".md"):
        raise TaskError("expected a Markdown instruction reference under docs")
    digest = value["sha256"]
    if type(digest) is not str or not _DIGEST.fullmatch(digest):
        raise TaskError("invalid instruction digest")
    return path


def _distinct(values, label):
    if len(set(values)) != len(values):
        raise TaskError(f"duplicate {label}")


def utc_now():
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_manifest(data):
    """Decode strict UTF-8 JSON and return its normalized, detached data."""
    try:
        value = decode_json(data, MAX_MANIFEST_BYTES)
    except EventError as error:
        raise TaskError(str(error)) from None
    extras = {2: _EDIT_FIELDS, 3: _DETERMINISTIC_FIELDS}.get(
        value.get("schema_version") if type(value) is dict else None, set())
    if type(value) is not dict or not _REQUIRED <= value.keys() <= _REQUIRED | _OPTIONAL | extras:
        raise TaskError("missing or unexpected manifest fields")
    if type(value["schema_version"]) is not int or value["schema_version"] not in (1, 2, 3):
        raise TaskError("unsupported manifest schema version")
    identifier = task_id(value["id"])
    revision(value["revision"])
    task_id(value["idempotency_key"])
    plain_text(value["title"], 120, "title")
    plain_text(value["description"], 2048, "description", multiline=True)
    if value["category"] not in ("research", "verification") or value["profile"] != "offline":
        raise TaskError("unsupported category or execution profile")
    allowed = (_RESOURCES if value["schema_version"] in (1, 3)
               else {"source-read", "source-edit", "portable-tests"})
    resources = _array(value["resources"], len(allowed), "resources")
    if not resources or any(type(item) is not str or item not in allowed for item in resources):
        raise TaskError("unsupported resource requirement")
    _distinct(resources, "resource")
    if value["schema_version"] == 2:
        validate_development(value)
    elif value["schema_version"] == 3:
        validate_deterministic(value)
    dependencies = _array(value["dependencies"], 16, "dependencies")
    _distinct([_dependency(item, identifier)[0] for item in dependencies], "dependency")
    instructions = _array(value.get("instructions", []), 4, "instruction references")
    _distinct([_instruction(item) for item in instructions], "instruction reference")
    if "expires_at" in value:
        expiry = value["expires_at"]
        if type(expiry) is not str or not _EXPIRY.fullmatch(expiry):
            raise TaskError("expected UTC expiry with second precision")
        try:
            datetime.fromisoformat(expiry)
        except ValueError:
            raise TaskError("invalid expiry date or time") from None
    return value


def validate_deterministic(manifest):
    """Validate a no-model task against the reviewed procedure registry."""
    block = manifest.get("deterministic")
    _members(block, {"procedure", "arguments"}, "deterministic")
    from . import procedures
    try:
        spec = procedures.get(block["procedure"])
        arguments = spec.normalize(block["arguments"])
    except procedures.ProcedureError as error:
        raise TaskError(str(error)) from None
    if arguments != block["arguments"]:
        raise TaskError("deterministic arguments must already be normalized")
    if list(manifest["resources"]) != list(spec.resources):
        raise TaskError("deterministic resources must equal the reviewed procedure requirements")
    return spec


def canonical_manifest(data):
    """Deterministic encoding of validated data, separate from the Git bytes."""
    return encode_json(validate_manifest(data))


def development_path(path):
    safe_path(path)
    if not ((path.startswith("src/") or path.startswith("tests/portable/")) and path.endswith(".py")
            or path.startswith("docs/") and path.endswith(".md")):
        raise TaskError("development supports Python source, portable tests and Markdown documentation only")
    return path


def validate_development(manifest):
    dev = manifest.get("development")
    _members(dev, {"source_revision", "modify", "create", "acceptance", "test_profiles", "deliverables"}, "development")
    if not isinstance(dev["source_revision"], str) or not re.fullmatch(r"[a-f0-9]{40}", dev["source_revision"]):
        raise TaskError("development requires an exact reviewed source commit")
    paths = []
    for key in ("modify", "create"):
        paths.extend(development_path(p) for p in _array(dev[key], 16, key))
    if not paths:
        raise TaskError("development requires explicit file scopes")
    _distinct([p.casefold() for p in paths], "development file")
    criteria = _array(dev["acceptance"], 8, "acceptance criteria")
    if not criteria:
        raise TaskError("development requires acceptance criteria")
    for criterion in criteria:
        plain_text(criterion, 512, "acceptance criterion")
    profiles = _array(dev["test_profiles"], 2, "test profiles")
    if any(p not in ("portable-full", "synthetic-unit") for p in profiles):
        raise TaskError("unsupported portable validation profile")
    _distinct(profiles, "test profile")
    if set(manifest["resources"]) != {"source-read", "source-edit"} | ({"portable-tests"} if profiles else set()):
        raise TaskError("development resources differ from requested capabilities")
    if dev["deliverables"] != ["final-response", "local-checkpoint"]:
        raise TaskError("unsupported development deliverables")
