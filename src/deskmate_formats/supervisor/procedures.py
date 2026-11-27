"""Named, locally reviewed deterministic procedures.

This module is data and validation only. It never spawns a process and never
accepts a caller-supplied executable, argument vector or shell fragment. A
procedure is selected by name; the argument vector is assembled here from the
pinned interpreter and validated arguments.

A procedure id is a reviewed constant. Adding or changing one is a code review
event, not a task-authoring right, so arbitrary Git prose cannot turn into
execution authority.

Some procedures run reviewed repository code rather than only a fixed command.
``executes`` states which, because "no shell" is not the same claim as "runs no
repository code": ``portable-tests`` and ``package-build`` execute whatever is in
the working tree, and their approval must weigh that.
"""

from dataclasses import dataclass
import re
import sys
from pathlib import Path

MAX_ARGUMENTS = 8
MAX_PATHS = 64
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024

_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_DEVICE = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]", re.IGNORECASE)
_HOSTILE = re.compile(r'[<>:"|?*\x00-\x1f]')
_RESOURCES = frozenset(("source-read", "synthetic-fixtures", "portable-tests"))

FIXED_SCRIPT = "fixed-script"
REPOSITORY_CODE = "reviewed-repository-code"
THIRD_PARTY_TOOL = "third-party-tool-over-repository-data"

# Both scripts are bounded by the same reviewed limits the parent enforces, so
# the declared cap is the cap actually applied. They open with O_NOFOLLOW and
# check the opened descriptor, never a path that could change between check and
# use.
HASH_SCRIPT = """
import hashlib, json, os, stat, sys
per_file, aggregate = int(sys.argv[1]), int(sys.argv[2])
files, total = [], 0
for name in sys.argv[3:]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        handle = os.open(name, flags)
    except OSError:
        raise SystemExit("unreadable input: " + name)
    with os.fdopen(handle, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise SystemExit("not a regular file: " + name)
        if info.st_size > per_file:
            raise SystemExit("input exceeds the reviewed size limit: " + name)
        digest, size = hashlib.sha256(), 0
        while True:
            chunk = stream.read(1048576)
            if not chunk:
                break
            size += len(chunk)
            total += len(chunk)
            if size > per_file or total > aggregate:
                raise SystemExit("input exceeds the reviewed size limit: " + name)
            digest.update(chunk)
    files.append({"path": name, "size": size, "sha256": digest.hexdigest()})
print(json.dumps({"files": files}, sort_keys=True))
"""

COMPARE_SCRIPT = """
import hashlib, json, os, stat, sys
per_file, aggregate = int(sys.argv[1]), int(sys.argv[2])
left, right = sys.argv[3], sys.argv[4]
def opened(name):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        handle = os.open(name, flags)
    except OSError:
        raise SystemExit("unreadable input: " + name)
    stream = os.fdopen(handle, "rb")
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode):
        raise SystemExit("not a regular file: " + name)
    if info.st_size > per_file:
        raise SystemExit("input exceeds the reviewed size limit: " + name)
    return stream, info.st_size
a_stream, a_size = opened(left)
b_stream, b_size = opened(right)
if a_size + b_size > aggregate:
    raise SystemExit("inputs exceed the reviewed aggregate limit")
a_hash, b_hash = hashlib.sha256(), hashlib.sha256()
same, read = True, 0
while True:
    a_chunk, b_chunk = a_stream.read(1048576), b_stream.read(1048576)
    read += len(a_chunk) + len(b_chunk)
    if read > aggregate:
        raise SystemExit("inputs exceed the reviewed aggregate limit")
    a_hash.update(a_chunk)
    b_hash.update(b_chunk)
    if same and a_chunk != b_chunk:
        same = False
    if not a_chunk and not b_chunk:
        break
print(json.dumps({
    "same": same,
    "expected": {"path": left, "size": a_size, "sha256": a_hash.hexdigest()},
    "actual": {"path": right, "size": b_size, "sha256": b_hash.hexdigest()},
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
    executes: str = FIXED_SCRIPT
    inputs: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    network: str = "none"

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
    if _HOSTILE.search(value) or value.endswith((" ", ".")):
        raise ProcedureError(f"invalid {label}")
    for segment in value.split("/"):
        if (not _SEGMENT.fullmatch(segment) or segment.endswith((".", " "))
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
    return ["-I", "-c", HASH_SCRIPT, str(MAX_FILE_BYTES), str(MAX_TOTAL_BYTES),
            *arguments["paths"]]


def _build_compare(arguments, artifacts, working):
    return ["-I", "-c", COMPARE_SCRIPT, str(MAX_FILE_BYTES), str(MAX_TOTAL_BYTES),
            arguments["expected"], arguments["actual"]]


def _build_audit(arguments, artifacts, working):
    return ["-I", "-c", AUDIT_SCRIPT]


def _build_reuse(arguments, artifacts, working):
    return ["-m", "reuse", "lint"]


def _build_package(arguments, artifacts, working):
    # --no-isolation keeps the build on the already-installed toolchain instead
    # of creating a virtual environment and resolving build requirements from
    # the network. See ``network`` on the procedure.
    return ["-m", "build", "--wheel", "--no-isolation", "--outdir", str(artifacts)]


_PROCEDURES = {
    "portable-tests": Procedure(
        "portable-tests", "Run a reviewed portable unittest discovery scope.",
        ("portable-tests",), 1800, ("scope",), _portable_tests, _build_portable_tests,
        executes=REPOSITORY_CODE,
        inputs=("src/**/*.py", "tests/portable/**/*", "pyproject.toml"),
        modules=("unittest",)),
    "repository-audit": Procedure(
        "repository-audit", "Run the portable repository content audit.",
        ("source-read",), 600, (), _no_arguments, _build_audit,
        executes=REPOSITORY_CODE,
        inputs=("src/**/*", "tests/**/*", "docs/**/*", "tools/**/*", "*.md", "*.toml"),
        modules=("deskmate_formats.supervisor.repository_audit",)),
    "reuse-lint": Procedure(
        "reuse-lint", "Run the REUSE/SPDX licensing declaration check.",
        ("source-read",), 600, (), _no_arguments, _build_reuse,
        executes=THIRD_PARTY_TOOL,
        inputs=("**/*",), modules=("reuse",)),
    "hash-files": Procedure(
        "hash-files", "Hash named tracked files and print a structured receipt.",
        ("source-read",), 300, ("paths",), _paths_only, _build_hash),
    "fixture-compare": Procedure(
        "fixture-compare", "Compare two files byte for byte and print a receipt.",
        ("source-read",), 300, ("expected", "actual"), _pair, _build_compare),
    "package-build": Procedure(
        "package-build", "Build a wheel into the attempt artifact directory.",
        ("portable-tests",), 900, (), _no_arguments, _build_package,
        executes=REPOSITORY_CODE,
        inputs=("pyproject.toml", "README.md", "src/**/*", "LICENSES/**/*"),
        modules=("build",), network="no-isolation"),
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
            "arguments": list(spec.arguments), "executes": spec.executes,
            "inputs": list(spec.inputs), "modules": list(spec.modules),
            "network": spec.network,
            "limits": {"file_bytes": MAX_FILE_BYTES, "total_bytes": MAX_TOTAL_BYTES,
                       "paths": MAX_PATHS}}


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


def input_patterns(name, arguments=None):
    """The repository paths whose content must be bound to the plan.

    Named-file procedures bind exactly the reviewed arguments; tree procedures
    bind their declared patterns. A procedure that declares nothing binds
    nothing, which is visible in the plan rather than implied.
    """
    spec = get(name)
    if name == "hash-files":
        return tuple(spec.normalize(arguments)["paths"])
    if name == "fixture-compare":
        pair = spec.normalize(arguments)
        return (pair["expected"], pair["actual"])
    return spec.inputs


def module_origins(name):
    """Resolved module files a procedure imports, for binding and review."""
    return get(name).modules
