"""Checkout identity, interpreter identity and observed import origin.

Four facts are easy to conflate: the checkout a campaign *named*, the revision
that checkout is at, the content of the package tree, and the package a process
actually imported.  They are recorded separately here, because on a shared
laboratory VM the last routinely disagrees with the first, and an isolated
child (``python -I``) discards the environment variables that looked like they
would have fixed it.

Three rules keep this honest, each of them the correction of a measured defect:

* an interpreter is identified by its **environment prefix** and its
  **invocation path**, never by executable inode identity.  On POSIX a virtual
  environment's ``bin/python`` is a symlink to the base interpreter, so two
  environments share one executable inode while running different
  ``site-packages``; a ``samefile`` comparison would call them equal;
* the interpreter that is *running* is described without resolving its path, so
  a caller cannot substitute a requested path for the parent's actual identity;
* a checkout must be the root of its own Git repository.  A directory inside
  another checkout inherits that repository's ``HEAD``, which is not evidence
  about a separate campaign's tree.

Failure classes are type names or short literals, never exception text: Git's
stderr quotes the paths this module is meant to keep private.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig

PACKAGE = "deskmate_formats"
DISTRIBUTION = "deskmate-formats"
SCHEMA_VERSION = 1

MAX_TREE_FILES = 20000
MAX_TREE_BYTES = 64 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 30

_SKIP_DIRECTORIES = frozenset({"__pycache__", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache"})
_SKIP_SUFFIXES = (".pyc", ".pyo")
_REVISION = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_MODULE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]{0,200}")

#: Reported by a child under ``-I``; every value describes that child.
_DESCRIBE_SCRIPT = (
    "import json, sys, sysconfig\n"
    "print(json.dumps({\n"
    "    'version': sys.version.split()[0],\n"
    "    'implementation': sys.implementation.name,\n"
    "    'executable': sys.executable,\n"
    "    'base_executable': getattr(sys, '_base_executable', None),\n"
    "    'prefix': sys.prefix,\n"
    "    'base_prefix': sys.base_prefix,\n"
    "    'isolated': bool(sys.flags.isolated),\n"
    "    'site_packages': sysconfig.get_paths().get('purelib'),\n"
    "    'prefix': sys.prefix,\n"
    "}))\n"
)


class IdentityError(RuntimeError):
    """Identity could not be established; callers must not guess it."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_digest(path: "str | os.PathLike[str]", *, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def tree_inventory(root: "str | os.PathLike[str]", *, suffixes: "tuple[str, ...] | None" = None,
                   limit_bytes: int = MAX_TREE_BYTES) -> "dict[str, dict[str, object]]":
    """Relative path, size and SHA-256 for every regular file under ``root``.

    ``__pycache__`` and bytecode are skipped: an installed tree and a checkout
    generate them independently, and they say nothing about which source ran.
    """
    root = Path(root)
    if not root.is_dir():
        raise IdentityError("tree-missing")
    files: dict[str, dict[str, object]] = {}
    total = 0
    for directory, names, filenames in os.walk(root):
        names[:] = sorted(name for name in names if name not in _SKIP_DIRECTORIES)
        for name in sorted(filenames):
            if name.endswith(_SKIP_SUFFIXES) or (suffixes and not name.endswith(suffixes)):
                continue
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue
            size = path.stat().st_size
            total += size
            if len(files) >= MAX_TREE_FILES or total > limit_bytes:
                raise IdentityError("tree-too-large")
            files[path.relative_to(root).as_posix()] = {"size": size, "sha256": file_digest(path)}
    return files


def tree_digest(root: "str | os.PathLike[str]", *, suffixes: "tuple[str, ...] | None" = None) -> str:
    """One digest over names, sizes and contents of a tree."""
    inventory = tree_inventory(root, suffixes=suffixes)
    digest = hashlib.sha256()
    for name in sorted(inventory):
        entry = inventory[name]
        digest.update(f"{name}\0{entry['size']}\0{entry['sha256']}\n".encode("utf-8"))
    return digest.hexdigest()


def package_digests(root: "str | os.PathLike[str]") -> dict[str, object]:
    """The bundle digest and the Python-only digest of a package tree."""
    root = Path(root)
    return {
        "tree_digest": tree_digest(root),
        "python_digest": tree_digest(root, suffixes=(".py",)),
        "file_count": len(tree_inventory(root)),
    }


def git_environment() -> dict[str, str]:
    """A read-only Git environment that cannot reach the network or take locks.

    The ambient configuration is deliberately *kept*: whether a checkout looks
    dirty depends on ``core.autocrlf`` and on ignore rules, and a reader that
    redirects the global configuration reports a different answer from the one
    the operator sees.  Measured on this host, committing under the ambient
    ``core.autocrlf=true`` and then reading with the global configuration
    redirected reported a clean file as modified.

    Hooks and the filesystem monitor are disabled per command instead, and no
    built-in Git command can be shadowed by an alias, so reading identity runs
    no repository code.
    """
    env = dict(os.environ)
    env.update(
        GIT_TERMINAL_PROMPT="0",
        GIT_NO_LAZY_FETCH="1",
        GIT_ALLOW_PROTOCOL="",
        GIT_OPTIONAL_LOCKS="0",
    )
    return env


def _git(checkout: Path, *arguments: str) -> dict[str, object]:
    executable = shutil.which("git")
    if executable is None:
        return {"code": None, "stdout": "", "failure": "git-unavailable"}
    try:
        result = subprocess.run(
            [executable, "--no-replace-objects", "-c", "core.fsmonitor=false",
             "-c", "core.hooksPath=" + os.devnull, *arguments],
            cwd=str(checkout),
            env=git_environment(),
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"code": None, "stdout": "", "failure": type(error).__name__}
    return {
        "code": result.returncode,
        "stdout": result.stdout.decode("utf-8", "replace").strip(),
        "failure": None,
    }


def same_path(observed: "str | os.PathLike[str] | None",
              expected: "str | os.PathLike[str] | None") -> "bool | None":
    """Whether two paths name the same file or directory, without following away."""
    if not observed or not expected:
        return None
    try:
        return Path(observed).resolve().samefile(Path(expected).resolve())
    except OSError:
        return os.path.normcase(os.path.normpath(str(observed))) == os.path.normcase(
            os.path.normpath(str(expected)))


def contained(observed: "str | None", directory: "str | None") -> "bool | None":
    """Whether ``observed`` is ``directory`` or a subdirectory of it."""
    if not observed or not directory:
        return None
    try:
        candidate = Path(observed).resolve()
        parent = Path(directory).resolve()
    except OSError:
        return None
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def source_identity(checkout: "str | os.PathLike[str]", *,
                    accept_enclosing: bool = False) -> dict[str, object]:
    """The checkout's revision, branch and dirtiness, or why they are unknown.

    ``accept_enclosing`` exists for a documented synthetic layout — a tree that
    is deliberately a subdirectory of a repository under test.  It is off by
    default: a directory inside another checkout answers revision queries with
    the enclosing repository's ``HEAD``, so accepting it silently would attribute
    a different tree's revision to this one.

    A caller must treat any ``state`` other than ``"git"`` as "identity not
    established": ``revision`` is then ``None`` and no drift comparison may pass
    silently.
    """
    checkout = Path(checkout)
    identity: dict[str, object] = {
        "state": "unknown",
        "revision": None,
        "branch": None,
        "detached": None,
        "dirty": None,
        "changed_file_count": None,
        "untracked_file_count": None,
        "top_level": None,
        "exact_checkout_root": None,
        "accept_enclosing": accept_enclosing,
        "failure": None,
        "observed_utc": utc_now(),
    }
    if not checkout.is_dir():
        identity.update(state="missing", failure="checkout-missing")
        return identity
    top = _git(checkout, "rev-parse", "--show-toplevel")
    if top["code"] is None:
        identity.update(state="git-unavailable", failure=top["failure"])
        return identity
    if top["code"] != 0 or not top["stdout"]:
        identity.update(state="not-a-repository", failure="rev-parse-failed")
        return identity
    top_level = Path(str(top["stdout"])).resolve()
    identity["top_level"] = str(top_level)
    exact = same_path(top_level, checkout.resolve())
    identity["exact_checkout_root"] = exact
    if exact is not True and not accept_enclosing:
        identity.update(state="enclosing-repository", failure="checkout-not-repository-root")
        return identity
    head = _git(checkout, "rev-parse", "HEAD")
    if head["code"] is None:
        identity.update(state="git-unavailable", failure=head["failure"])
        return identity
    if head["code"] != 0:
        identity.update(state="no-commit", failure="rev-parse-head-failed")
        return identity
    revision = str(head["stdout"]).strip().lower()
    if not _REVISION.fullmatch(revision):
        identity.update(state="unreadable-revision", failure="revision-format")
        return identity
    identity["revision"] = revision
    branch = _git(checkout, "symbolic-ref", "--short", "-q", "HEAD")
    if branch["code"] is None:
        identity.update(state="git-unavailable", failure=branch["failure"])
        return identity
    identity["detached"] = branch["code"] != 0
    identity["branch"] = str(branch["stdout"]) if branch["code"] == 0 and branch["stdout"] else None
    status = _git(checkout, "status", "--porcelain", "--untracked-files=normal", "--ignore-submodules=all")
    if status["code"] is None or status["code"] != 0:
        identity.update(state="status-failed", failure=status["failure"] or "status-failed")
        return identity
    lines = [line for line in str(status["stdout"]).splitlines() if line.strip()]
    identity["changed_file_count"] = len([line for line in lines if not line.startswith("??")])
    identity["untracked_file_count"] = len([line for line in lines if line.startswith("??")])
    identity["dirty"] = bool(lines)
    identity["state"] = "git"
    return identity


def _digest_or_none(path: "str | None") -> "str | None":
    if not path:
        return None
    try:
        return file_digest(path)
    except OSError:
        return None


def describe_running_interpreter() -> dict[str, object]:
    """The interpreter that is actually running, with its invocation path unresolved.

    ``sys.executable`` is recorded as invoked.  Resolving it would be wrong on
    POSIX, where every virtual environment's ``bin/python`` points at the base
    interpreter: the resolved path says nothing about which ``site-packages``
    this process uses.  ``prefix`` is that answer.
    """
    executable = sys.executable
    absolute = os.path.abspath(executable) if executable else None
    paths = sysconfig.get_paths()
    return {
        "state": "running-interpreter",
        "executable": absolute,
        "executable_realpath": os.path.realpath(absolute) if absolute else None,
        "executable_is_symlink": os.path.islink(absolute) if absolute else None,
        "executable_sha256": _digest_or_none(absolute),
        "version": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "prefix": sys.prefix,
        "prefix_resolved": os.path.realpath(sys.prefix),
        "environment_name": Path(sys.prefix).name,
        "base_prefix": sys.base_prefix,
        "virtual_environment": sys.prefix != sys.base_prefix,
        "site_packages": paths.get("purelib"),
        "site_packages_inside_prefix": contained(paths.get("purelib"), sys.prefix),
        "isolated": bool(sys.flags.isolated),
        "no_user_site": bool(sys.flags.no_user_site),
        "base_executable": getattr(sys, "_base_executable", None),
        "observed_utc": utc_now(),
    }


def interpreter_identity(executable: "str | os.PathLike[str] | None" = None) -> dict[str, object]:
    """Describe an interpreter: its invocation path, prefix and site-packages.

    ``executable=None`` describes the running interpreter.  Otherwise the given
    path is launched **as given** (made absolute, not resolved) under ``-I``, so
    the report describes the environment that path selects.  Two symlinked
    virtual environments therefore produce two different ``prefix`` values and
    the same ``executable_realpath``.
    """
    if executable is None:
        return describe_running_interpreter()
    absolute = os.path.abspath(str(executable))
    described: dict[str, object] = {
        "state": "unavailable",
        "executable": absolute,
        "executable_realpath": os.path.realpath(absolute),
        "executable_is_symlink": os.path.islink(absolute),
        "executable_sha256": None,
        "version": None,
        "implementation": None,
        "prefix": None,
        "prefix_resolved": None,
        "environment_name": None,
        "base_prefix": None,
        "virtual_environment": None,
        "site_packages": None,
        "site_packages_inside_prefix": None,
        "isolated": None,
        "base_executable": None,
        "observed_utc": utc_now(),
    }
    if not Path(absolute).is_file():
        return described
    try:
        described["executable_sha256"] = file_digest(absolute)
    except OSError:
        # An App Execution Alias on this host is a zero-byte reparse point that
        # opens as an invalid argument.  It is a candidate path, not an
        # interpreter, and it must not abort an inventory.
        described["state"] = "unreadable"
        return described
    try:
        completed = subprocess.run(
            [absolute, "-I", "-c", _DESCRIBE_SCRIPT],
            capture_output=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        described["state"] = type(error).__name__
        return described
    if completed.returncode != 0:
        described["state"] = "exit-" + str(completed.returncode)
        return described
    try:
        values = json.loads(completed.stdout.decode("utf-8", "replace"))
    except ValueError:
        described["state"] = "unparseable"
        return described
    prefix = values.get("prefix")
    described.update(
        state="described",
        version=values.get("version"),
        implementation=values.get("implementation"),
        prefix=prefix,
        prefix_resolved=os.path.realpath(prefix) if isinstance(prefix, str) else None,
        environment_name=Path(prefix).name if isinstance(prefix, str) else None,
        base_prefix=values.get("base_prefix"),
        virtual_environment=prefix != values.get("base_prefix"),
        site_packages=values.get("site_packages"),
        site_packages_inside_prefix=contained(values.get("site_packages"), prefix),
        isolated=values.get("isolated"),
        base_executable=values.get("base_executable"),
    )
    return described


def same_environment(observed_prefix: "str | None", expected_prefix: "str | None") -> "bool | None":
    """Whether two ``sys.prefix`` values name the same environment.

    Prefix equality is the identity that matters.  Executable identity is not:
    two POSIX virtual environments share the base interpreter's inode.
    """
    if not observed_prefix or not expected_prefix:
        return None
    return os.path.normcase(os.path.normpath(observed_prefix)) == os.path.normcase(
        os.path.normpath(expected_prefix))


def import_identity(name: str = PACKAGE) -> dict[str, object]:
    """Which package the *running* interpreter actually resolves, and from where."""
    if not _MODULE.fullmatch(name):
        raise IdentityError("invalid module name")
    executable = sys.executable
    identity: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "state": "missing",
        "origin": None,
        "distribution_version": None,
        "distribution_name": None,
        "interpreter": os.path.abspath(executable) if executable else None,
        "interpreter_resolved": os.path.realpath(executable) if executable else None,
        "prefix": sys.prefix,
        "prefix_resolved": os.path.realpath(sys.prefix),
        "base_prefix": sys.base_prefix,
        "in_virtual_environment": sys.prefix != sys.base_prefix,
        "isolated": bool(sys.flags.isolated),
        "no_user_site": bool(sys.flags.no_user_site),
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "tree_digest": None,
        "python_digest": None,
        "file_count": None,
        "failure": None,
    }
    try:
        module = importlib.import_module(name)
    except ImportError:
        identity["failure"] = "module-not-importable"
        return identity
    module_file = getattr(module, "__file__", None)
    if not module_file:
        identity.update(state="namespace-package", failure="no-origin-file")
        return identity
    origin = Path(str(module_file)).resolve().parent
    identity["origin"] = str(origin)
    identity["state"] = "imported"
    root_name = name.partition(".")[0]
    try:
        identity["distribution_name"] = root_name.replace("_", "-")
        identity["distribution_version"] = importlib.metadata.version(identity["distribution_name"])
    except importlib.metadata.PackageNotFoundError:
        identity["distribution_version"] = None
    try:
        identity.update(package_digests(origin))
    except (IdentityError, OSError):
        identity["failure"] = "tree-unreadable"
        return identity
    return identity
