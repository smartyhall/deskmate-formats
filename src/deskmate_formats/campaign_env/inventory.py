"""Read-only inventory of interpreters, environments and isolated launch sites.

The defect this campaign exists to fix was invisible in the source: every
launch site looked isolated and correct, and the code they ran came from a
shared installation.  An inventory makes that visible by asking each
interpreter what it actually resolves, instead of reading the launch site and
assuming.

Nothing here writes: no environment is created, no package is installed, no
configuration is changed.  A query against another campaign's interpreter is a
bounded ``-I -c`` import-specification lookup that imports the package's
parent modules only.

Launch sites are found by scanning source text for an ``-I`` argument, then
recording the interpreter expression and target module in the same call.  That
is a static audit, so a site assembled from variables is reported as
"unresolved" rather than silently omitted.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from . import identity, receipts

SCHEMA_VERSION = 1
SCAN_DIRECTORIES = ("src", "tools", "tests")
_IGNORED_DIRECTORIES = frozenset({
    "__pycache__", ".git", "build", "dist", "local-results", "node_modules",
    ".ruff_cache", ".pytest_cache", "private-fixtures",
})
MAX_SCAN_FILES = 8000
MAX_INTERPRETERS = 8
MAX_WORKTREES = 64

_ISOLATED = re.compile(r"""["']-I["']""")
_MODULE = re.compile(r"""["'](?:-m|--module)["']\s*,\s*["']([A-Za-z_][A-Za-z0-9_.]*)["']""")
_CODE = re.compile(r"""["'](?:-c|--command)["']""")
_SYS_EXECUTABLE = re.compile(r"\bsys\.executable\b")
_LITERAL_PYTHON = re.compile(r"""["']([^"']*python(?:[0-9.]+)?(?:\.exe)?)["']""", re.IGNORECASE)
_LAUNCHER_LINE = re.compile(r"^\s*-V:(?P<version>[0-9.]+)\s*(?P<default>\*)?\s+(?P<path>.+?)\s*$", re.MULTILINE)

#: Distributions whose presence changes what a campaign can assume it has.
#: The full set is counted, not listed: most of it is unrelated to this project
#: and its exact composition is another campaign's business.
RELEVANT_DISTRIBUTIONS = (
    "deskmate-formats", "pip", "setuptools", "wheel", "build", "ruff", "reuse",
    "jsonschema", "mcp", "anyio", "pillow", "fonttools",
)

_DISTRIBUTION_LOOKUP = (
    "import importlib.metadata as m, json, sys\n"
    "names = sys.argv[1:]\n"
    "found = {}\n"
    "for name in names:\n"
    "    try:\n"
    "        found[name] = m.version(name)\n"
    "    except m.PackageNotFoundError:\n"
    "        found[name] = None\n"
    "found['__count__'] = len(list(m.distributions()))\n"
    "print(json.dumps(found))\n"
)

_MODULE_LOOKUP = (
    "import importlib.util, sys\n"
    "try:\n"
    "    spec = importlib.util.find_spec(sys.argv[1])\n"
    "except Exception as error:\n"
    "    print('error:' + type(error).__name__)\n"
    "    raise SystemExit(0)\n"
    "print(spec.origin if spec and spec.origin else 'missing')\n"
)


def module_origin(interpreter: "str | os.PathLike[str]", module: str) -> str:
    """Which file, if any, this interpreter resolves for ``module`` under ``-I``."""
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-c", _MODULE_LOOKUP, module],
            capture_output=True,
            timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        return "error:" + type(error).__name__
    if completed.returncode != 0:
        return "error:exit-" + str(completed.returncode)
    text = completed.stdout.decode("utf-8", "replace").strip()
    return text or "missing"


def distributions(interpreter: "str | os.PathLike[str]") -> dict[str, object]:
    """Relevant distribution versions this interpreter can see, plus how many exist."""
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-c", _DISTRIBUTION_LOOKUP, *RELEVANT_DISTRIBUTIONS],
            capture_output=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"state": "unavailable", "failure": type(error).__name__}
    if completed.returncode != 0:
        return {"state": "unavailable", "failure": "exit-" + str(completed.returncode)}
    import json

    try:
        values = json.loads(completed.stdout.decode("utf-8", "replace"))
    except ValueError:
        return {"state": "unavailable", "failure": "unparseable"}
    count = values.pop("__count__", None)
    return {"state": "observed", "present": {k: v for k, v in values.items() if v},
            "absent": sorted(k for k, v in values.items() if not v), "distribution_count": count}


def _py_launcher_interpreters() -> "list[str]":
    launcher = shutil.which("py")
    if launcher is None:
        return []
    try:
        completed = subprocess.run([launcher, "-0p"], capture_output=True, timeout=60,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    found = []
    for match in _LAUNCHER_LINE.finditer(completed.stdout.decode("utf-8", "replace")):
        candidate = match.group("path").strip()
        if candidate and Path(candidate).is_file():
            found.append(candidate)
    return found


def interpreter_candidates(extra: "tuple[str, ...]" = ()) -> "list[str]":
    """Every interpreter this host plausibly offers, resolved and deduplicated."""
    candidates: list[str] = [*extra, *_py_launcher_interpreters()]
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    if sys.executable:
        candidates.append(sys.executable)
    seen: dict[str, str] = {}
    for candidate in candidates:
        try:
            resolved = str(Path(candidate).resolve())
        except OSError:
            continue
        if Path(resolved).is_file():
            seen.setdefault(os.path.normcase(resolved), resolved)
    return list(seen.values())[:MAX_INTERPRETERS]


def interpreters(extra: "tuple[str, ...]" = (), *, include_launcher: bool = True) -> "list[dict[str, object]]":
    """Describe each interpreter, which package it resolves and what it has installed."""
    entries = []
    for path in interpreter_candidates(extra if include_launcher else ()):
        described = identity.interpreter_identity(path)
        described["package_origin"] = module_origin(path, identity.PACKAGE)
        described["distributions"] = distributions(path)
        entries.append(described)
    return entries


# ``local-results`` is deliberately walkable here: campaign environments live
# under it, and skipping it reported zero environments on a host that had one.
_ENVIRONMENT_IGNORED = frozenset({
    "__pycache__", ".git", "build", "dist", "node_modules", "private-fixtures",
    ".ruff_cache", ".pytest_cache", "website",
})
MAX_ENVIRONMENT_DIRECTORIES = 4000
ENVIRONMENT_SCAN_DEPTH = 5


def environments(candidates: "tuple[str, ...]" = ()) -> "list[dict[str, object]]":
    """Virtual environments at or below the given roots, bounded by a shallow walk.

    Campaign environments live at ``<checkout>/local-results/campaign-envs/<name>/venv``,
    which is four levels below the checkout, so a one-level listing would report
    ``0`` on a host that has several.  The walk is depth- and count-bounded and
    skips the directories that make a checkout large.
    """
    found: list[dict[str, object]] = []
    seen: set[str] = set()
    visited = 0

    def describe(directory: Path) -> None:
        interpreter = directory / ("Scripts" if os.name == "nt" else "bin") / (
            "python.exe" if os.name == "nt" else "python"
        )
        entry: dict[str, object] = {
            "path": str(directory.resolve()),
            "interpreter": str(interpreter) if interpreter.is_file() else None,
            "pyvenv_cfg": (directory / "pyvenv.cfg").read_text(
                encoding="utf-8", errors="replace").splitlines()[:8],
        }
        if interpreter.is_file():
            entry["identity"] = identity.interpreter_identity(interpreter)
            entry["package_origin"] = module_origin(interpreter, identity.PACKAGE)
        found.append(entry)

    for candidate in candidates:
        root = Path(candidate)
        if not root.is_dir():
            continue
        base_depth = len(root.parts)
        for directory, names, filenames in os.walk(root):
            visited += 1
            if visited > MAX_ENVIRONMENT_DIRECTORIES:
                return found
            current = Path(directory)
            names[:] = sorted(name for name in names if name not in _ENVIRONMENT_IGNORED)
            if "pyvenv.cfg" in filenames:
                key = os.path.normcase(str(current.resolve()))
                if key not in seen:
                    seen.add(key)
                    describe(current)
                names[:] = []
            elif len(current.parts) - base_depth >= ENVIRONMENT_SCAN_DEPTH:
                names[:] = []
    return found


def worktrees(checkout: "str | os.PathLike[str]") -> "list[dict[str, object]]":
    """This repository's worktrees, read from Git without touching them."""
    executable = shutil.which("git")
    if executable is None:
        return []
    try:
        completed = subprocess.run(
            [executable, "--no-replace-objects", "worktree", "list", "--porcelain"],
            cwd=str(checkout), env=identity.git_environment(), capture_output=True, timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    entries: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in completed.stdout.decode("utf-8", "replace").splitlines():
        if not line.strip():
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": value, "branch": None, "revision": None, "detached": False, "bare": False}
        elif key == "HEAD":
            current["revision"] = value
        elif key == "branch":
            current["branch"] = value
        elif key == "detached":
            current["detached"] = True
    if current:
        entries.append(current)
    return entries[:MAX_WORKTREES]


def launch_sites(checkout: "str | os.PathLike[str]", *,
                 directories: "tuple[str, ...]" = SCAN_DIRECTORIES) -> "list[dict[str, object]]":
    """Every source line that passes ``-I``, with its interpreter and target."""
    checkout = Path(checkout)
    sites: list[dict[str, object]] = []
    scanned = 0
    for directory in directories:
        for path in sorted((checkout / directory).rglob("*.py")):
            if _IGNORED_DIRECTORIES & set(path.parts):
                continue
            if scanned >= MAX_SCAN_FILES:
                return sites
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = text.splitlines()
            for index, line in enumerate(lines):
                if not _ISOLATED.search(line):
                    continue
                window = "\n".join(lines[index:index + 3])
                module = _MODULE.search(window)
                site = {
                    "path": path.relative_to(checkout).as_posix(),
                    "line": index + 1,
                    "module": module.group(1) if module else None,
                    "inline_code": bool(_CODE.search(window)),
                    "sys_executable": bool(_SYS_EXECUTABLE.search(window)),
                    "interpreter_expression": _interpreter_expression(window),
                }
                sites.append(site)
    return sites


def _interpreter_expression(window: str) -> str:
    if _SYS_EXECUTABLE.search(window):
        return "sys.executable"
    literal = _LITERAL_PYTHON.search(window)
    if literal:
        return "literal:" + literal.group(1)
    return "unresolved"


def launcher_identity(sites: "list[dict[str, object]]", interpreter: str) -> dict[str, object]:
    """Index how the same launch sites behave against one interpreter."""
    modules: dict[str, dict[str, object]] = {}
    for site in sites:
        module = site.get("module")
        if not module or module in modules:
            continue
        origin = module_origin(interpreter, str(module))
        package_root = module.split(".")[0]
        modules[str(module)] = {
            "origin": origin,
            "resolves": origin not in {"missing"} and not origin.startswith("error:"),
            "outside_package_root": None if origin.startswith("error:") or origin == "missing"
            else bool(Path(origin).parts and package_root not in Path(origin).parts),
        }
    package_origin = module_origin(interpreter, identity.PACKAGE)
    return {
        "interpreter": interpreter,
        "package_origin": package_origin,
        "modules": modules,
        "distinct_modules": len(modules),
        "sys_executable_sites": sum(1 for site in sites if site.get("sys_executable")),
        "unresolved_sites": sum(1 for site in sites if site.get("interpreter_expression") == "unresolved"),
    }


def inventory(checkout: "str | os.PathLike[str]" = ".", *, extra_interpreters: "tuple[str, ...]" = (),
              environment_roots: "tuple[str, ...] | None" = None) -> dict[str, object]:
    """The host picture a campaign needs before it can claim what it executed."""
    checkout_path = Path(checkout).resolve()
    sites = launch_sites(checkout_path)
    trees = worktrees(checkout_path)
    roots = environment_roots if environment_roots is not None else (str(checkout_path),)
    running = identity.interpreter_identity()
    described = interpreters(extra_interpreters)
    launcher = launcher_identity(sites, str(running.get("executable")))
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "campaign-environment-inventory",
        "observed_utc": identity.utc_now(),
        "checkout": str(checkout_path),
        "source": identity.source_identity(checkout_path),
        "running_interpreter": running,
        "package": identity.import_identity(),
        "interpreters": described,
        "distributions": distributions(str(running.get("executable"))),
        "environments": environments(roots),
        "worktrees": trees,
        "launch_sites": sites,
        "launcher": launcher,
        "counts": {
            "interpreters": len(described),
            "environments": len(environments(roots)),
            "worktrees": len(trees),
            "launch_sites": len(sites),
            "isolated_module_sites": launcher["distinct_modules"],
        },
        "private_paths": True,
    }


def publishable(record: dict[str, object], *, roots: "tuple[str, ...]" = ()) -> dict[str, object]:
    """Convenience wrapper: the redacted projection of an inventory."""
    return receipts.public(record, roots=roots)
