"""Synthetic checkouts and qualified campaign environments for binding tests.

The point of these fixtures is that the *conflicting* installation is real: a
disposable virtual environment is given a ``deskmate_formats`` whose audit
marker differs from both synthetic checkouts, and the environment record is
written by the same mechanism provisioning writes.  Nothing here touches the
laboratory's shared interpreter, and no test requires the network.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import venv

from deskmate_formats.campaign_env import environment, identity, receipts

PACKAGE_INIT = '"""Synthetic implementation for source-binding tests."""\n\nMARKER = "{marker}"\n'
AUDIT_MODULE = (
    '"""Synthetic publication audit with an observable marker."""\n\n'
    'from deskmate_formats import MARKER\n\n'
    'ROOT = None\n\n\n'
    'def audit():\n'
    '    return "audit:" + MARKER\n'
)


def git(checkout, *arguments):
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Synthetic Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="Synthetic Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
    return subprocess.run(["git", *arguments], cwd=str(checkout), check=True,
                          capture_output=True, env=env, timeout=60).stdout


def write_package(package, marker):
    """Write the minimal package shape the audit and the bootstrap import."""
    package = Path(package)
    (package / "supervisor").mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(PACKAGE_INIT.format(marker=marker), encoding="utf-8")
    (package / "supervisor" / "__init__.py").write_text("", encoding="utf-8")
    (package / "supervisor" / "repository_audit.py").write_text(AUDIT_MODULE, encoding="utf-8")
    return package


def make_checkout(path, *, marker, tests=None):
    """A Git checkout root holding ``src/deskmate_formats`` with this marker."""
    checkout = Path(path)
    checkout.mkdir(parents=True)
    write_package(checkout / "src" / "deskmate_formats", marker)
    (checkout / "pyproject.toml").write_text(
        "[project]\nname = \"synthetic-checkout\"\nversion = \"0\"\n", encoding="utf-8")
    for name, source in (tests or {}).items():
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    git(checkout, "init", "-q", "-b", "main")
    git(checkout, "config", "core.autocrlf", "false")
    git(checkout, "config", "commit.gpgsign", "false")
    git(checkout, "add", "-A")
    git(checkout, "commit", "-q", "-m", "Synthetic source revision")
    revision = git(checkout, "rev-parse", "HEAD").decode("ascii").strip()
    return checkout, revision


def install_conflict(interpreter, *, marker="shared-preinstalled"):
    """Put a conflicting package into a disposable environment's site-packages.

    This is the "unrelated package installed in the interpreter" condition,
    reproduced without modifying the laboratory's shared installation.
    """
    site = Path(environment.site_packages(interpreter))
    return write_package(site / "deskmate_formats", marker)


def binding_stub(interpreter=None, *, src="/bound/src", python_digest="b" * 64):
    """A structurally valid binding for pure argument-vector tests.

    It names no real checkout, so it is only used where no child is launched;
    every behavioural test builds a real environment instead.
    """
    return {
        "schema_version": 1,
        "source": "workspace",
        "workspace": {"path": "/bound", "src": src, "revision": "a" * 40,
                      "branch": "main", "dirty": False,
                      "report_path": "/bound/report.json",
                      "package": {"python_digest": python_digest}},
        "environment": {"interpreter": interpreter or str(Path(sys.executable).resolve())},
        "bootstrap": {"report_path": "/bound/report.json"},
    }


def make_environment(*, root, checkout, campaign, revision=None):
    """A campaign-owned venv plus the qualified record provisioning would write.

    Only the fields the binding reads are populated; the interpreter identity is
    described from the real environment, so a wrong interpreter cannot pass.
    """
    target = environment.layout(checkout, campaign, root=root)
    venv.EnvBuilder(with_pip=False, clear=True).create(str(target["venv"]))
    site = environment.site_packages(target["interpreter"])
    package = Path(checkout) / "src" / "deskmate_formats"
    digests = (identity.package_digests(package) if package.is_dir()
               else {"tree_digest": "0" * 64, "python_digest": "0" * 64, "file_count": 0})
    described = identity.interpreter_identity(target["interpreter"])
    source = identity.source_identity(checkout)
    if revision is not None:
        source = dict(source, revision=revision)
    record = {
        "schema_version": 1,
        "kind": "campaign-environment",
        "campaign": campaign,
        "package": "deskmate_formats",
        "checkout": str(Path(checkout).resolve()),
        "root": target["root"],
        "directory": target["directory"],
        "venv": target["venv"],
        "interpreter": target["interpreter"],
        "site_packages": site,
        "record_path": target["record"],
        "created_utc": identity.utc_now(),
        "source_before": source,
        "source_after": source,
        "source_unchanged": True,
        "source_package": digests,
        "installed": {"tree_digest": digests["tree_digest"],
                      "python_digest": digests["python_digest"]},
        "environment_identity": {"prefix": described.get("prefix"),
                                 "executable": described.get("executable"),
                                 "executable_sha256": described.get("executable_sha256")},
        "verdict": "qualified",
        "reasons": [],
    }
    receipts.write(target["record"], record)
    selection = {"campaign": campaign, "checkout": str(Path(checkout)), "root": target["root"]}
    return selection, target, record
