"""Checkout identity, interpreter identity and observed import origin.

Four facts are easy to conflate: the checkout a campaign *named*, the revision
that checkout is at, the content of the package tree, and the package a process
actually imported.  They are recorded separately here, because on a shared
laboratory VM the last routinely disagrees with the first, and an isolated
child (``python -I``) discards the environment variables that looked like they
would have fixed it.

Two rules keep this honest:

* a Git query that fails yields an explicit ``state`` and ``failure`` class
  rather than an empty revision that later reads as "no changes";
* digests are computed with one function on one tree, so a recorded value and
  an observed value are always comparable.  Nothing compares a source tree
  with an installed tree directly, because packaging legitimately changes the
  file set.

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


def source_identity(checkout: "str | os.PathLike[str]") -> dict[str, object]:
    """The checkout's revision, branch and dirtiness, or why they are unknown.

    A caller must treat any ``state`` other than ``"git"`` as "identity not
    established": ``revision`` is then ``None`` and no drift comparison may
    pass silently.
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
    identity["top_level"] = str(Path(str(top["stdout"])).resolve())
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


def import_identity(name: str = PACKAGE) -> dict[str, object]:
    """Which package the *running* interpreter actually resolves, and from where."""
    if not _MODULE.fullmatch(name):
        raise IdentityError("invalid module name")
    identity: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "state": "missing",
        "origin": None,
        "distribution_version": None,
        "distribution_name": None,
        "interpreter": str(Path(sys.executable).resolve()) if sys.executable else None,
        "prefix": sys.prefix,
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
        digests = package_digests(origin)
    except (IdentityError, OSError):
        identity["failure"] = "tree-unreadable"
        return identity
    identity.update(digests)
    return identity


def interpreter_identity(executable: "str | os.PathLike[str] | None" = None) -> dict[str, object]:
    """Describe an interpreter, including one other than the running process."""
    if executable is None:
        return {
            "executable": str(Path(sys.executable).resolve()) if sys.executable else None,
            "sha256": file_digest(sys.executable) if sys.executable else None,
            "version": sys.version.split()[0],
            "implementation": sys.implementation.name,
            "prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "virtual_environment": sys.prefix != sys.base_prefix,
            "observed_utc": utc_now(),
            "state": "running-interpreter",
        }
    path = Path(executable).resolve()
    result: dict[str, object] = {
        "executable": str(path),
        "sha256": None,
        "version": None,
        "implementation": None,
        "prefix": None,
        "base_prefix": None,
        "virtual_environment": None,
        "observed_utc": utc_now(),
        "state": "unavailable",
    }
    if not path.is_file():
        return result
    try:
        result["sha256"] = file_digest(path)
    except OSError:
        # An App Execution Alias on this host is a zero-byte reparse point that
        # opens as an invalid argument.  It is a candidate path, not an
        # interpreter, and it must not abort an inventory.
        result["state"] = "unreadable"
        return result
    script = (
        "import json, sys; print(json.dumps({'version': sys.version.split()[0], "
        "'implementation': sys.implementation.name, 'prefix': sys.prefix, "
        "'base_prefix': sys.base_prefix, 'isolated': bool(sys.flags.isolated)}))"
    )
    try:
        completed = subprocess.run(
            [str(path), "-I", "-c", script],
            capture_output=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return result
    if completed.returncode != 0:
        return result
    try:
        described = json.loads(completed.stdout.decode("utf-8", "replace"))
    except ValueError:
        return result
    result.update(
        version=described.get("version"),
        implementation=described.get("implementation"),
        prefix=described.get("prefix"),
        base_prefix=described.get("base_prefix"),
        virtual_environment=described.get("prefix") != described.get("base_prefix"),
        isolated_probe=described.get("isolated"),
        state="described",
    )
    return result


def matches(observed: "str | None", expected: "str | None") -> "bool | None":
    """Whether two paths name the same directory, without following into nothing."""
    if not observed or not expected:
        return None
    try:
        return Path(observed).resolve().samefile(Path(expected).resolve())
    except OSError:
        return os.path.normcase(str(observed)) == os.path.normcase(str(expected))


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
