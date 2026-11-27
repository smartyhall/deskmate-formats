"""A campaign-owned interpreter, and this source installed into it.

A campaign environment is a virtual environment created *by* the campaign, in
a directory the campaign owns, holding a source-bound installation of this
checkout.  It exists so that an isolated child launched with
``<environment>/.../python -I`` resolves the campaign's code instead of
whatever wheel another campaign left in the shared interpreter.

Deliberate limits:

* the environment holds the package itself and nothing else.  Large immutable
  tools (Ruff, REUSE, build) are shared read-only from one tools environment
  instead of being copied into every campaign, which is most of the disk and
  install time and adds no isolation;
* installation goes through ``pip --target`` into the new environment's
  ``site-packages`` from a bootstrap interpreter that already has pip, so a
  fresh environment costs one directory walk rather than an ``ensurepip``
  bootstrap;
* provisioning refuses to run without a Git-identified checkout, and refuses
  to replace an existing environment unless that is explicitly requested;
* the machine's global interpreter, global packages and every other
  campaign's environment are never written to.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import re
import subprocess
import sys

from . import identity, launch, receipts

SCHEMA_VERSION = 1
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
DEFAULT_ROOT_PARTS = ("local-results", "campaign-envs")
DEFAULT_TIMEOUT_SECONDS = 900


class CampaignEnvironmentError(RuntimeError):
    """The campaign environment could not be created or does not hold this source."""


def default_root(checkout: "str | os.PathLike[str]") -> Path:
    """``local-results/campaign-envs`` inside the checkout, which Git ignores."""
    return Path(checkout).joinpath(*DEFAULT_ROOT_PARTS)


def layout(checkout: "str | os.PathLike[str]", campaign: str, *,
           root: "str | os.PathLike[str] | None" = None) -> dict[str, object]:
    """Where a campaign's environment lives, derived from its name alone."""
    if not isinstance(campaign, str) or not NAME_PATTERN.fullmatch(campaign):
        raise CampaignEnvironmentError("campaign names are lower-case identifiers")
    checkout = Path(checkout).resolve()
    environment_root = Path(root).resolve() if root is not None else default_root(checkout).resolve()
    directory = environment_root / campaign
    venv = directory / "venv"
    interpreter = venv / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )
    return {
        "campaign": campaign,
        "checkout": str(checkout),
        "root": str(environment_root),
        "directory": str(directory),
        "venv": str(venv),
        "interpreter": str(interpreter),
        "record": str(directory / "environment.json"),
    }


def _command(argv: "list[str]", *, timeout: int) -> dict[str, object]:
    completed = launch.run(argv, timeout=timeout)
    return completed


def site_packages(interpreter: "str | os.PathLike[str]") -> str:
    """The environment's own ``site-packages``, as that interpreter computes it."""
    script = "import json, sysconfig; print(json.dumps(sysconfig.get_paths()))"
    completed = subprocess.run(
        [str(interpreter), launch.ISOLATION_FLAG, "-c", script],
        capture_output=True,
        timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        raise CampaignEnvironmentError("the campaign interpreter could not report its paths")
    paths = json.loads(completed.stdout.decode("utf-8", "replace"))
    purelib = paths.get("purelib")
    if not purelib or not Path(purelib).is_absolute():
        raise CampaignEnvironmentError("the campaign interpreter reported no site-packages")
    return str(Path(purelib))


def create_venv(bootstrap_interpreter: "str | os.PathLike[str]", venv: "str | os.PathLike[str]",
                *, timeout: int = 300) -> dict[str, object]:
    """A virtual environment without ``ensurepip``; pip comes from the bootstrap."""
    completed = _command([str(bootstrap_interpreter), "-m", "venv", "--without-pip", str(venv)],
                         timeout=timeout)
    if completed["exit_status"] != 0:
        raise CampaignEnvironmentError("virtual environment creation failed; nothing was installed")
    if not Path(venv, "pyvenv.cfg").is_file():
        raise CampaignEnvironmentError("virtual environment creation left no pyvenv.cfg")
    return completed


def install_source(bootstrap_interpreter: "str | os.PathLike[str]", checkout: "str | os.PathLike[str]",
                   target: "str | os.PathLike[str]", *, timeout: int = DEFAULT_TIMEOUT_SECONDS,
                   allow_build_isolation: bool = True) -> dict[str, object]:
    """Install this checkout into ``target``, preferring an offline build.

    Build isolation downloads a build backend.  The first attempt therefore
    disables it, using the bootstrap interpreter's existing setuptools; only a
    failure falls back to isolation, and both attempts are recorded.
    """
    attempts: list[dict[str, object]] = []
    base = [str(bootstrap_interpreter), "-m", "pip", "install", "--no-deps",
            "--disable-pip-version-check", "--no-compile", "--no-warn-script-location",
            "--target", str(target)]
    modes = ["no-build-isolation"]
    if allow_build_isolation:
        modes.append("build-isolation")
    for mode in modes:
        argv = base + (["--no-build-isolation"] if mode == "no-build-isolation" else []) + [str(checkout)]
        receipt = _command(argv, timeout=timeout)
        receipt["install_mode"] = mode
        attempts.append(receipt)
        if receipt["exit_status"] == 0:
            return {"attempts": attempts, "install_mode": mode, "installed": True}
    return {"attempts": attempts, "install_mode": None, "installed": False}


def provision(checkout: "str | os.PathLike[str]", campaign: str, *,
              root: "str | os.PathLike[str] | None" = None,
              python: "str | os.PathLike[str] | None" = None,
              replace: bool = False,
              package: str = identity.PACKAGE,
              allow_build_isolation: bool = True,
              timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, object]:
    """Create the campaign environment and record exactly what it holds."""
    checkout = Path(checkout).resolve()
    target = layout(checkout, campaign, root=root)
    record_file = Path(str(target["record"]))
    if record_file.exists() and not replace:
        raise CampaignEnvironmentError(
            "a campaign environment already exists; pass replace to rebuild it")
    source = identity.source_identity(checkout)
    if source["state"] != "git":
        raise CampaignEnvironmentError("source identity was not established; nothing was provisioned")
    package_source = checkout / "src" / package
    digests = identity.package_digests(package_source)
    bootstrap = str(Path(python).resolve()) if python is not None else str(Path(sys.executable).resolve())
    created = identity.interpreter_identity(bootstrap)

    venv_receipt = create_venv(bootstrap, str(target["venv"]), timeout=min(timeout, 300))
    interpreter = str(target["interpreter"])
    if not Path(interpreter).is_file():
        raise CampaignEnvironmentError("the campaign interpreter is missing after creation")
    environment_interpreter = identity.interpreter_identity(interpreter)
    site = site_packages(interpreter)
    installation = install_source(bootstrap, checkout, site, timeout=timeout,
                                  allow_build_isolation=allow_build_isolation)

    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "campaign-environment",
        "campaign": campaign,
        "package": package,
        "checkout": str(checkout),
        "root": str(target["root"]),
        "directory": str(target["directory"]),
        "venv": str(target["venv"]),
        "interpreter": interpreter,
        "site_packages": site,
        "record_path": str(record_file),
        "created_utc": identity.utc_now(),
        "source": source,
        "source_package": digests,
        "bootstrap_interpreter": bootstrap,
        "bootstrap_identity": created,
        "environment_identity": environment_interpreter,
        "environment": venv_receipt,
        "installation": installation,
        "installed": None,
        "content": None,
        "verdict": "failed",
        "reasons": [],
    }
    reasons: list[str] = []
    if not installation["installed"]:
        reasons.append("installation-failed")
    else:
        probe = launch.probe(interpreter, cwd=str(checkout), package=package, timeout=min(timeout, 300))
        report = probe.get("report") or {}
        package = report.get("package") or {}
        record["provision_probe"] = probe
        record["installed"] = package
        if not probe.get("report_parsed"):
            reasons.append("provision-probe-unparseable")
        elif package.get("state") != "imported":
            reasons.append("installed-package-not-importable")
        elif identity.contained(package.get("origin"), site) is not True:
            reasons.append("installed-package-outside-campaign-environment")
        elif package.get("python_digest") != digests["python_digest"]:
            # Code identity is the claim that matters.  A bundle difference is
            # recorded, not fatal: packaging may legitimately omit a data file
            # while every Python module that can run is byte-identical.
            reasons.append("installed-code-differs-from-source")
        elif not report.get("isolated"):
            reasons.append("provision-probe-was-not-isolated")
        else:
            record["content"] = {
                "python_digest_matches": package.get("python_digest") == digests["python_digest"],
                "bundle_digest_matches": package.get("tree_digest") == digests["tree_digest"],
                "source_file_count": digests["file_count"],
                "installed_file_count": package.get("file_count"),
            }
    record["reasons"] = reasons
    record["verdict"] = "qualified" if not reasons else "failed"
    record["receipt"] = receipts.write(record_file, record)
    return record
