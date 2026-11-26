"""Named, locally reviewed deterministic procedures.

This module is data and validation only. It never spawns a process and never
accepts a caller-supplied executable, argument vector or shell fragment. A
procedure is selected by name; the argument vector is assembled here from the
pinned interpreter and validated arguments.

A procedure id is a reviewed constant. Adding or changing one is a code review
event, not a task-authoring right, so arbitrary Git prose cannot turn into
execution authority.
"""

from dataclasses import dataclass
import re
import sys
from pathlib import Path

MAX_ARGUMENTS = 8
MAX_PATHS = 64
MAX_FILE_BYTES = 64 * 1024 * 1024

_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_DEVICE = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]", re.IGNORECASE)
_RESOURCES = frozenset(("source-read", "synthetic-fixtures", "portable-tests"))

HASH_SCRIPT = """
import hashlib, json, pathlib, sys
files = []
for name in sys.argv[1:]:
    path = pathlib.Path(name)
    if path.is_symlink() or not path.is_file():
        raise SystemExit("not a regular file: " + name)
    data = path.read_bytes()
    files.append({"path": name, "size": len(data),
                  "sha256": hashlib.sha256(data).hexdigest()})
print(json.dumps({"files": files}, sort_keys=True))
"""

COMPARE_SCRIPT = """
import hashlib, json, pathlib, sys
left, right = sys.argv[1], sys.argv[2]
a = pathlib.Path(left).read_bytes()
b = pathlib.Path(right).read_bytes()
print(json.dumps({
    "same": a == b,
    "expected": {"path": left, "size": len(a),
                 "sha256": hashlib.sha256(a).hexdigest()},
    "actual": {"path": right, "size": len(b),
               "sha256": hashlib.sha256(b).hexdigest()},
}, sort_keys=True))
"""

AUDIT_SCRIPT = (
    "from pathlib import Path; "
    "from deskmate_formats.supervisor import repository_audit as a; "
    "a.ROOT = Path.cwd(); print(a.audit())"
)


class ProcedureError(ValueError):
    """A procedure was unknown or its arguments were refused."""


@dataclass(frozen=True, slots=True)
class Procedure:
    """One reviewed procedure. ``arguments`` documents accepted keys."""

    name: str
    summary: str
    resources: tuple[str, ...]
    timeout_seconds: int
    arguments: tuple[str, ...]
    validate: object
    build: object

    def normalize(self, arguments):
        if type(arguments) is not dict:
            raise ProcedureError("procedure arguments must be an object")
        if not arguments.keys() <= set(self.arguments):
            raise ProcedureError("unexpected procedure argument")
        return self.validate(arguments)

    def argv(self, arguments, *, interpreter, artifacts, working_directory):
        """Return the exact argument vector for normalized arguments."""
        return [str(interpreter), *self.build(self.normalize(arguments), artifacts,
                                              str(working_directory))]


def _interpreter():
    path = Path(sys.executable).resolve()
    if not path.is_file():
        raise ProcedureError("the running Python interpreter is unavailable")
    return path


def _safe_path(value, label="path"):
    """Reject absolute, traversal, device and Windows-hostile relative paths."""
    if type(value) is not str or not 0 < len(value) <= 240:
        raise ProcedureError(f"invalid {label}")
    for segment in value.split("/"):
        if (not _SEGMENT.fullmatch(segment) or segment.endswith(".")
                or _DEVICE.fullmatch(segment.partition(".")[0])):
            raise ProcedureError(f"invalid {label}")
    return value


def _paths(arguments, limit=MAX_PATHS):
    paths = arguments.get("paths")
    if type(paths) is not list or not 0 < len(paths) <= limit:
        raise ProcedureError("expected a bounded list of repository paths")
    normalized = [_safe_path(item) for item in paths]
    if len(set(normalized)) != len(normalized):
        raise ProcedureError("duplicate repository path")
    return normalized


def _no_arguments(arguments):
    if arguments:
        raise ProcedureError("this procedure takes no arguments")
    return {}


def _portable_tests(arguments):
    if arguments.keys() != {"scope"}:
        raise ProcedureError("portable tests require exactly a scope")
    scope = arguments["scope"]
    if scope not in ("supervisor", "observer", "all"):
        raise ProcedureError("unsupported portable test scope")
    return {"scope": scope}


def _paths_only(arguments):
    return {"paths": _paths(arguments)}


def _pair(arguments):
    if arguments.keys() != {"expected", "actual"}:
        raise ProcedureError("fixture comparison requires expected and actual")
    return {"expected": _safe_path(arguments["expected"]),
            "actual": _safe_path(arguments["actual"])}


def _build_portable_tests(arguments, artifacts, working):
    argv = ["-m", "unittest", "discover", "-s", "tests/portable", "-v"]
    pattern = {"supervisor": "test_supervisor*.py", "observer": "test_observer*.py",
               "all": "test_*.py"}[arguments["scope"]]
    return [*argv, "-p", pattern]


def _build_nothing(arguments, artifacts, working):
    return []


def _build_hash(arguments, artifacts, working):
    return ["-I", "-c", HASH_SCRIPT, *arguments["paths"]]


def _build_compare(arguments, artifacts, working):
    return ["-I", "-c", COMPARE_SCRIPT, arguments["expected"], arguments["actual"]]


def _build_audit(arguments, artifacts, working):
    return ["-I", "-c", AUDIT_SCRIPT]


def _build_reuse(arguments, artifacts, working):
    return ["-m", "reuse", "lint"]


def _build_package(arguments, artifacts, working):
    return ["-m", "build", "--wheel", "--outdir", str(artifacts)]


_PROCEDURES = {
    "portable-tests": Procedure(
        "portable-tests", "Run a reviewed portable unittest discovery scope.",
        ("portable-tests",), 1800, ("scope",), _portable_tests, _build_portable_tests),
    "repository-audit": Procedure(
        "repository-audit", "Run the portable repository content audit.",
        ("source-read",), 600, (), _no_arguments, _build_audit),
    "reuse-lint": Procedure(
        "reuse-lint", "Run the REUSE/SPDX licensing declaration check.",
        ("source-read",), 600, (), _no_arguments, _build_reuse),
    "hash-files": Procedure(
        "hash-files", "Hash named tracked files and print a structured receipt.",
        ("source-read",), 300, ("paths",), _paths_only, _build_hash),
    "fixture-compare": Procedure(
        "fixture-compare", "Compare two files byte for byte and print a receipt.",
        ("source-read",), 300, ("expected", "actual"), _pair, _build_compare),
    "package-build": Procedure(
        "package-build", "Build a wheel into the attempt artifact directory.",
        ("portable-tests",), 900, (), _no_arguments, _build_package),
}


def names():
    return tuple(sorted(_PROCEDURES))


def get(name):
    """Return one reviewed procedure or refuse the request."""
    if type(name) is not str or not _ID.fullmatch(name) or name not in _PROCEDURES:
        raise ProcedureError("unknown or unsupported procedure")
    return _PROCEDURES[name]


def descriptor(name):
    """Public, reviewable description. Contains no local path or secret."""
    spec = get(name)
    return {"name": spec.name, "summary": spec.summary,
            "resources": list(spec.resources), "timeout_seconds": spec.timeout_seconds,
            "arguments": list(spec.arguments)}


def catalog():
    return [descriptor(name) for name in names()]


def validate(name, arguments):
    """Validate arguments without building an argument vector."""
    return get(name).normalize(arguments)


def build(name, arguments, *, artifacts, working_directory, interpreter=None):
    """Assemble the reviewed argument vector for one procedure invocation."""
    spec = get(name)
    interpreter = _interpreter() if interpreter is None else Path(interpreter)
    return spec.argv(arguments, interpreter=interpreter, artifacts=artifacts,
                     working_directory=working_directory)


def resources(name):
    return get(name).resources
