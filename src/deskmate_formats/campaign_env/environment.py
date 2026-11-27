"""A campaign-owned interpreter, and this source installed into it.

A campaign environment is a virtual environment created *by* the campaign, in a
directory the campaign owns, holding a source-bound installation of this
checkout.  It exists so that an isolated child launched with
``<environment>/.../python -I`` resolves the campaign's code instead of
whatever wheel another campaign left in the shared interpreter.

Ownership is the part that had to be corrected after review.  A missing
provisioning record does **not** mean a directory is unowned: an existing
directory without a valid, matching record is refused, because the alternative
is overwriting something this campaign cannot identify.  The same applies to a
symbolic link or a Windows junction at the target path, and to a record whose
campaign, checkout, package or layout does not match the request.

Replacement is staged rather than in-place: a new environment is built under a
fresh staging path inside the owned root, validated, and only then swapped into
place, with the previous environment renamed aside first.  An existing
installation is never modified, so stale files from an older install cannot
survive a replacement.

Deliberate limits:

* the environment holds the package itself and nothing else.  Large immutable
  tools (Ruff, REUSE, build) are shared read-only from one tools environment
  instead of being copied into every campaign, which is most of the disk and
  install time and adds no isolation;
* a network-capable build-isolation fallback is **opt-in**.  Without it, a
  missing build backend fails the provision instead of silently reaching the
  network;
* provisioning refuses to run without a Git-identified checkout whose root is
  the checkout itself, and refuses to proceed if the source changes while it is
  installing;
* the machine's global interpreter, global packages and every other campaign's
  environment are never written to.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from uuid import uuid4

from . import identity, launch, receipts

SCHEMA_VERSION = 1
KIND = "campaign-environment"
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
DEFAULT_ROOT_PARTS = ("local-results", "campaign-envs")
DEFAULT_TIMEOUT_SECONDS = 900
RECORD_NAME = "environment.json"
VENV_NAME = "venv"

REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
JUNCTION_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", None)


class CampaignEnvironmentError(RuntimeError):
    """The campaign environment could not be created or does not hold this source.

    ``code`` is a short, publishable slug: the reason a provision or a preflight
    refused, without a private path in it.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code + (": " + detail if detail else ""))


def path_kind(path: "str | os.PathLike[str]") -> str:
    """What is at this path, judged without following a redirect.

    ``os.path.islink`` reports ``False`` for a Windows junction, so the reparse
    attribute is inspected directly; a junction is a redirect to another
    directory and is refused wherever an owned directory is expected.
    """
    target = Path(path)
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unreadable"
    if REPARSE_POINT and getattr(info, "st_file_attributes", 0) & REPARSE_POINT:
        return "junction" if getattr(info, "st_reparse_tag", None) == JUNCTION_TAG else "symlink"
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "other"


def default_root(checkout: "str | os.PathLike[str]") -> Path:
    """``local-results/campaign-envs`` inside the checkout, which Git ignores."""
    return Path(checkout).joinpath(*DEFAULT_ROOT_PARTS)


def layout(checkout: "str | os.PathLike[str]", campaign: str, *,
           root: "str | os.PathLike[str] | None" = None) -> dict[str, object]:
    """Where a campaign's environment lives, derived from its name alone."""
    if not isinstance(campaign, str) or not NAME_PATTERN.fullmatch(campaign):
        raise CampaignEnvironmentError("invalid-campaign-name")
    checkout_path = Path(checkout).resolve()
    environment_root = Path(root).resolve() if root is not None else default_root(checkout_path).resolve()
    directory = environment_root / campaign
    venv = directory / VENV_NAME
    interpreter = venv / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )
    return {
        "campaign": campaign,
        "checkout": str(checkout_path),
        "root": str(environment_root),
        "directory": str(directory),
        "venv": str(venv),
        "interpreter": str(interpreter),
        "record": str(directory / RECORD_NAME),
    }


def record_problems(record: object, *, campaign: str, checkout: "str | os.PathLike[str]",
                    package: str, target: "dict[str, object]") -> "list[str]":
    """Every way a stored record fails to bind to the environment it claims.

    A record is accepted only when it describes *this* campaign, checkout,
    package and layout.  Anything else is an inconsistent ownership record, and
    an environment whose ownership cannot be established is not touched.
    """
    if not isinstance(record, dict):
        return ["record-not-an-object"]
    problems: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        problems.append("record-schema")
    if record.get("kind") != KIND:
        problems.append("record-kind")
    if record.get("campaign") != campaign:
        problems.append("record-campaign")
    if identity.same_path(record.get("checkout"), checkout) is not True:
        problems.append("record-checkout")
    if record.get("package") != package:
        problems.append("record-package")
    for name in ("directory", "venv", "interpreter"):
        if identity.same_path(record.get(name), target[name]) is not True:
            problems.append("record-" + name)
    if identity.contained(record.get("site_packages"), target["venv"]) is not True:
        problems.append("record-site-packages")
    return problems


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
        raise CampaignEnvironmentError("interpreter-paths-unavailable")
    paths = json.loads(completed.stdout.decode("utf-8", "replace"))
    purelib = paths.get("purelib")
    if not purelib or not Path(purelib).is_absolute():
        raise CampaignEnvironmentError("interpreter-reported-no-site-packages")
    return str(Path(purelib))


def create_venv(bootstrap_interpreter: "str | os.PathLike[str]", venv: "str | os.PathLike[str]",
                *, timeout: int = 300) -> dict[str, object]:
    """A virtual environment without ``ensurepip``; pip comes from the bootstrap."""
    completed = launch.run([str(bootstrap_interpreter), "-m", "venv", "--without-pip", str(venv)],
                           timeout=timeout)
    if completed["exit_status"] != 0:
        raise CampaignEnvironmentError("virtual-environment-creation-failed")
    if not Path(venv, "pyvenv.cfg").is_file():
        raise CampaignEnvironmentError("virtual-environment-left-no-pyvenv-cfg")
    return completed


def install_source(bootstrap_interpreter: "str | os.PathLike[str]", checkout: "str | os.PathLike[str]",
                   target: "str | os.PathLike[str]", *, timeout: int = DEFAULT_TIMEOUT_SECONDS,
                   allow_build_isolation: bool = False) -> dict[str, object]:
    """Install this checkout into ``target``, offline unless explicitly allowed otherwise.

    Build isolation downloads a build backend.  It is never used implicitly: the
    first and only attempt disables it unless the caller asked for the
    network-capable mode, and every attempt is recorded with its mode.
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
        receipt = launch.run(argv, timeout=timeout)
        receipt["install_mode"] = mode
        attempts.append(receipt)
        if receipt["exit_status"] == 0:
            return {"attempts": attempts, "install_mode": mode, "installed": True,
                    "build_isolation_explicitly_enabled": bool(allow_build_isolation)}
    return {"attempts": attempts, "install_mode": None, "installed": False,
            "build_isolation_explicitly_enabled": bool(allow_build_isolation)}


def _staging_directory(root: Path, campaign: str) -> Path:
    staging = root / f".staging-{campaign}-{uuid4().hex[:12]}"
    if path_kind(staging) != "absent":
        raise CampaignEnvironmentError("staging-path-already-exists")
    staging.mkdir(parents=True)
    return staging


def source_drift(before: "dict[str, object]", after: "dict[str, object]",
                 digests_before: "dict[str, object]", digests_after: "dict[str, object]") -> "bool | None":
    """Whether the checkout changed while it was being installed.

    ``None`` means the evidence was not available — an unreadable revision or an
    missing digest — and a caller must not treat that as equality.
    """
    if before.get("state") != "git" or after.get("state") != "git":
        return None
    if not before.get("revision") or not after.get("revision"):
        return None
    if not digests_before.get("tree_digest") or not digests_after.get("tree_digest"):
        return None
    return (before["revision"] != after["revision"]
            or digests_before["tree_digest"] != digests_after["tree_digest"])


def classify_target(target: "dict[str, object]", campaign: str, checkout: Path,
                    package: str) -> dict[str, object]:
    """Classify the target path and, if present, prove this campaign owns it."""
    directory = Path(str(target["directory"]))
    kind = path_kind(directory)
    if kind == "absent":
        return {"mode": "fresh", "kind": kind, "record": None}
    if kind in {"symlink", "junction"}:
        raise CampaignEnvironmentError("existing-redirect-at-target")
    if kind != "directory":
        raise CampaignEnvironmentError("unexpected-entry-at-target")
    record_path = Path(str(target["record"]))
    if path_kind(record_path) != "file" or path_kind(Path(str(target["venv"]))) != "directory":
        raise CampaignEnvironmentError("existing-directory-without-valid-record")
    try:
        record = receipts.read(record_path)
    except (OSError, ValueError):
        raise CampaignEnvironmentError("existing-directory-with-unreadable-record")
    problems = record_problems(record, campaign=campaign, checkout=checkout, package=package, target=target)
    if problems:
        raise CampaignEnvironmentError("existing-directory-with-foreign-record", ",".join(sorted(set(problems))))
    if not Path(str(target["interpreter"])).is_file():
        raise CampaignEnvironmentError("existing-record-without-interpreter")
    return {"mode": "owned", "kind": kind, "record": record}


def _swap_into_place(staging: Path, target: "dict[str, object]", *, replace: bool) -> str | None:
    """Move a validated staging environment into the target, retiring the old one."""
    directory = Path(str(target["directory"]))
    venv = Path(str(target["venv"]))
    directory.mkdir(parents=True, exist_ok=True)
    retired: Path | None = None
    if path_kind(venv) != "absent":
        if not replace:
            raise CampaignEnvironmentError("existing-environment-not-replaceable")
        retired = directory.parent / f".retired-{target['campaign']}-{uuid4().hex[:12]}"
        os.replace(venv, retired)
    try:
        os.replace(staging / VENV_NAME, venv)
    except OSError:
        if retired is not None:
            try:
                os.replace(retired, venv)
            except OSError:
                pass
        raise
    return str(retired) if retired is not None else None


def provision(checkout: "str | os.PathLike[str]", campaign: str, *,
              root: "str | os.PathLike[str] | None" = None,
              python: "str | os.PathLike[str] | None" = None,
              replace: bool = False,
              package: str = identity.PACKAGE,
              allow_build_isolation: bool = False,
              accept_enclosing: bool = False,
              timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, object]:
    """Create the campaign environment and record exactly what it holds."""
    checkout_path = Path(checkout).resolve()
    target = layout(checkout_path, campaign, root=root)
    root_path = Path(str(target["root"]))
    root_kind = path_kind(root_path)
    if root_kind not in {"absent", "directory"}:
        raise CampaignEnvironmentError("environment-root-is-not-a-directory", root_kind)
    owned = classify_target(target, campaign, checkout_path, package)
    if owned["mode"] == "owned" and not replace:
        raise CampaignEnvironmentError("environment-exists")
    source_before = identity.source_identity(checkout_path, accept_enclosing=accept_enclosing)
    if source_before["state"] != "git":
        raise CampaignEnvironmentError("source-identity-not-established", str(source_before["state"]))
    package_source = checkout_path / "src" / package
    digests_before = identity.package_digests(package_source)
    bootstrap = str(Path(python).resolve()) if python is not None else str(Path(sys.executable).resolve())
    root_path.mkdir(parents=True, exist_ok=True)

    staging = _staging_directory(root_path, campaign)
    try:
        venv_receipt = create_venv(bootstrap, str(staging / VENV_NAME), timeout=min(timeout, 300))
        staged_interpreter = staging / VENV_NAME / ("Scripts" if os.name == "nt" else "bin") / (
            "python.exe" if os.name == "nt" else "python"
        )
        staged_site = site_packages(staged_interpreter)
        if identity.contained(staged_site, str(staging / VENV_NAME)) is not True:
            raise CampaignEnvironmentError("site-packages-outside-staged-environment")
        installation = install_source(bootstrap, checkout_path, staged_site, timeout=timeout,
                                      allow_build_isolation=allow_build_isolation)
        if not installation["installed"]:
            raise CampaignEnvironmentError("installation-failed")
        staged_probe = launch.probe(str(staged_interpreter), cwd=str(checkout_path), package=package,
                                    timeout=min(timeout, 300))
        staged_package = (staged_probe.get("report") or {}).get("package") or {}
        if staged_package.get("state") != "imported":
            raise CampaignEnvironmentError("installed-package-not-importable")
        if staged_package.get("python_digest") != digests_before["python_digest"]:
            raise CampaignEnvironmentError("installed-code-differs-from-source")
        source_after = identity.source_identity(checkout_path, accept_enclosing=accept_enclosing)
        digests_after = identity.package_digests(package_source)
        drift = source_drift(source_before, source_after, digests_before, digests_after)
        if drift is not False:
            raise CampaignEnvironmentError(
                "source-changed-during-provisioning" if drift else
                "source-identity-unavailable-during-provisioning")
    except CampaignEnvironmentError:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    retired = _swap_into_place(staging, target, replace=replace)
    shutil.rmtree(staging, ignore_errors=True)
    interpreter = str(target["interpreter"])
    installed_site = site_packages(interpreter)
    if identity.contained(installed_site, str(target["venv"])) is not True:
        raise CampaignEnvironmentError("site-packages-outside-environment")
    verification = launch.probe(interpreter, cwd=str(checkout_path), package=package,
                                timeout=min(timeout, 300))
    report = verification.get("report") or {}
    installed = report.get("package") or {}
    interpreter_identity = identity.interpreter_identity(interpreter)
    reasons: list[str] = []
    if not verification.get("report_parsed"):
        reasons.append("verification-probe-unparseable")
    elif installed.get("state") != "imported":
        reasons.append("installed-package-not-importable")
    elif installed.get("python_digest") != digests_before["python_digest"]:
        reasons.append("installed-code-differs-from-source")
    elif identity.contained(installed.get("origin"), installed_site) is not True:
        reasons.append("installed-package-outside-environment")
    elif not identity.same_environment(interpreter_identity.get("prefix"), str(target["venv"])):
        reasons.append("interpreter-prefix-is-not-the-environment")
    elif not report.get("isolated"):
        reasons.append("verification-probe-was-not-isolated")

    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "campaign": campaign,
        "package": package,
        "checkout": str(checkout_path),
        "root": str(target["root"]),
        "directory": str(target["directory"]),
        "venv": str(target["venv"]),
        "interpreter": interpreter,
        "site_packages": installed_site,
        "record_path": str(target["record"]),
        "created_utc": identity.utc_now(),
        "ownership": {"mode": "replaced-owned" if retired else owned["mode"],
                      "previous_record_present": owned["record"] is not None,
                      "retired_path": retired},
        "source_before": source_before,
        "source_after": source_after,
        "source_unchanged": True,
        "source_package": digests_before,
        "bootstrap_interpreter": bootstrap,
        "bootstrap_identity": identity.interpreter_identity(bootstrap),
        "environment_identity": interpreter_identity,
        "environment": venv_receipt,
        "installation": installation,
        "staged_probe": staged_probe,
        "verification_probe": verification,
        "installed": installed,
        "verdict": "failed",
        "reasons": reasons,
    }
    record["verdict"] = "qualified" if not reasons else "failed"
    record["receipt"] = receipts.write(str(target["record"]), record)
    return record
