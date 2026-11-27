"""A campaign-owned interpreter, and this source installed into it.

A campaign environment is a virtual environment created *by* the campaign, in a
directory the campaign owns, holding a source-bound installation of this
checkout.  It exists so that an isolated child launched with
``<environment>/.../python -I`` resolves the campaign's code instead of
whatever wheel another campaign left in the shared interpreter.

Ownership is the part that had to be corrected twice.  A missing provisioning
record does **not** mean a directory is unowned: an existing directory without a
valid, matching record is refused.  The same applies to a symbolic link or a
Windows junction anywhere in the owned scope, to the environment root itself,
and to a record whose campaign, checkout, package or layout does not match.

Replacement is staged and provisional rather than in-place:

* a new environment is built under ``.staging-<campaign>-<uuid>`` inside the
  owned root and validated there;
* the campaign holds an exclusive lock for the whole provision, so another
  provision of the same campaign cannot change the target between the ownership
  check and the swap, and the target is revalidated — including the digest of
  the record that was checked — immediately before the swap;
* the previous environment is renamed aside, never edited, and is deleted only
  after the new installation has passed final verification and its receipt has
  been written durably;
* if final verification or the receipt write fails, the previous environment is
  restored; if that restoration cannot be established, the provision says so
  explicitly (``replacement-recovery-uncertain``) and keeps the retired
  environment and the previous receipt in place for a human;
* if the staged environment cannot be moved into place *and* the retired one
  cannot be moved back, both copies are still on disk and neither is known to be
  usable in place.  That is reported the same way —
  ``replacement-recovery-uncertain``, with a private recovery receipt naming both
  paths — and nothing is deleted, because deleting the copy that turns out to be
  the only intact one is the one mistake this path must not make.

Deliberate limits:

* the environment holds the package itself and nothing else.  Large immutable
  tools (Ruff, REUSE, build) are shared read-only from one tools environment
  instead of being copied into every campaign;
* a network-capable build-isolation fallback is **opt-in**, and the default
  offline mode passes ``--no-index`` as well as ``--no-build-isolation``, so it
  cannot reach a package index even indirectly;
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
RECOVERY_KIND = "campaign-environment-recovery"
RECOVERY_PREFIX = ".recovery-"

REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
JUNCTION_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", None)
REDIRECT_KINDS = frozenset({"symlink", "junction"})


class CampaignEnvironmentError(RuntimeError):
    """The campaign environment could not be created or does not hold this source.

    ``code`` is a short, publishable slug: the reason a provision or a preflight
    refused, without a private path in it.  ``detail`` is local diagnostic text.
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


def redirected_ancestor(path: "str | os.PathLike[str]", *,
                        within: "str | os.PathLike[str] | None" = None) -> "str | None":
    """The first redirecting component of a path, at or below the owned scope.

    ``os.path.abspath`` is used rather than ``resolve`` precisely because the
    question is whether a *named* location redirects somewhere else.  Resolving
    first would answer about the destination and hide the redirect.
    """
    target_path = Path(os.path.abspath(str(path)))
    boundary = Path(os.path.abspath(str(within))) if within is not None else None
    current = target_path
    while True:
        if path_kind(current) in REDIRECT_KINDS:
            return str(current)
        if current.parent == current or boundary is None:
            return None
        parent = current.parent
        try:
            parent.relative_to(boundary)
        except ValueError:
            return None
        current = parent


def default_root(checkout: "str | os.PathLike[str]") -> Path:
    """``local-results/campaign-envs`` inside the checkout, which Git ignores."""
    return Path(checkout).joinpath(*DEFAULT_ROOT_PARTS)


def layout(checkout: "str | os.PathLike[str]", campaign: str, *,
           root: "str | os.PathLike[str] | None" = None) -> dict[str, object]:
    """Where a campaign's environment lives, derived from its name alone.

    Paths are absolute but **unresolved**: the campaign root may be a redirect
    and the mechanism has to see it in order to refuse it.
    """
    if not isinstance(campaign, str) or not NAME_PATTERN.fullmatch(campaign):
        raise CampaignEnvironmentError("invalid-campaign-name")
    checkout_path = os.path.abspath(str(checkout))
    environment_root = (os.path.abspath(str(root)) if root is not None
                        else os.path.abspath(str(default_root(checkout_path))))
    directory = os.path.join(environment_root, campaign)
    venv = os.path.join(directory, VENV_NAME)
    interpreter = os.path.join(venv, "Scripts" if os.name == "nt" else "bin",
                               "python.exe" if os.name == "nt" else "python")
    return {
        "campaign": campaign,
        "checkout": checkout_path,
        "root": environment_root,
        "directory": directory,
        "venv": venv,
        "interpreter": interpreter,
        "record": os.path.join(directory, RECORD_NAME),
        "lock": os.path.join(environment_root, ".lock-" + campaign),
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
    """Install this checkout into ``target``, without an index unless explicitly allowed.

    ``--no-build-isolation`` alone stops pip from *creating* a build environment,
    but it does not stop pip from contacting an index.  The offline attempt
    therefore also passes ``--no-index``, so the default mode cannot depend on
    network access even unintentionally; only the explicit opt-in attempt may
    reach one, and every attempt records which mode ran.
    """
    attempts: list[dict[str, object]] = []
    base = [str(bootstrap_interpreter), "-m", "pip", "install", "--no-deps",
            "--disable-pip-version-check", "--no-compile", "--no-warn-script-location",
            "--target", str(target)]
    modes = ["offline"]
    if allow_build_isolation:
        modes.append("build-isolation")
    for mode in modes:
        flags = ["--no-index", "--no-build-isolation"] if mode == "offline" else []
        argv = base + flags + [str(checkout)]
        receipt = launch.run(argv, timeout=timeout)
        receipt["install_mode"] = mode
        receipt["index_access"] = mode != "offline"
        attempts.append(receipt)
        if receipt["exit_status"] == 0:
            return {"attempts": attempts, "install_mode": mode, "installed": True,
                    "index_access": mode != "offline",
                    "build_isolation_explicitly_enabled": bool(allow_build_isolation)}
    return {"attempts": attempts, "install_mode": None, "installed": False,
            "index_access": bool(allow_build_isolation),
            "build_isolation_explicitly_enabled": bool(allow_build_isolation)}


def source_drift(before: "dict[str, object]", after: "dict[str, object]",
                 digests_before: "dict[str, object]", digests_after: "dict[str, object]") -> "bool | None":
    """Whether the checkout changed while it was being installed.

    ``None`` means the evidence was not available — an unreadable revision or a
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
        return {"mode": "fresh", "kind": kind, "record": None, "record_sha256": None}
    if kind in REDIRECT_KINDS:
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
        raise CampaignEnvironmentError("existing-directory-with-foreign-record",
                                       ",".join(sorted(set(problems))))
    if path_kind(Path(str(target["interpreter"]))) != "file":
        raise CampaignEnvironmentError("existing-record-without-interpreter")
    return {"mode": "owned", "kind": kind, "record": record,
            "record_sha256": receipts.file_digest(record_path)}


def _acquire_lock(lock: Path) -> None:
    """One provision per campaign at a time, across processes.

    An exclusive create is the whole protocol: it is atomic on every platform we
    run on, it costs nothing, and it cannot be confused by a partially written
    file because nothing is read back.  The identifier written inside is for the
    operator, not for the algorithm.
    """
    try:
        handle = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise CampaignEnvironmentError("provisioning-in-progress", str(lock))
    try:
        os.write(handle, f"pid={os.getpid()} utc={identity.utc_now()}\n".encode("utf-8"))
    finally:
        os.close(handle)


def _release_lock(lock: Path) -> None:
    try:
        os.unlink(lock)
    except OSError:
        pass


def _discard_empty_directory(target: "dict[str, object]") -> None:
    """Remove the target directory a failed fresh provision created and left empty.

    Only an empty directory is removed: anything at all inside it is somebody's
    evidence, and a record-bearing directory is owned by another provision.
    """
    directory = Path(str(target["directory"]))
    try:
        if path_kind(directory) == "directory" and not any(directory.iterdir()):
            directory.rmdir()
    except OSError:
        pass


def _staging_directory(root: Path, campaign: str) -> Path:
    staging = root / f".staging-{campaign}-{uuid4().hex[:12]}"
    if path_kind(staging) != "absent":
        raise CampaignEnvironmentError("staging-path-already-exists")
    staging.mkdir(parents=True)
    return staging


def _rename(source: "str | os.PathLike[str]", destination: "str | os.PathLike[str]") -> None:
    """One directory rename: the only way an environment at the target changes.

    Named rather than called as ``os.replace`` inline so that each step of a
    deliberate sequence of renames can be exercised on its own, including the
    steps that are supposed to fail.
    """
    os.replace(source, destination)


def _swap_precondition(target: "dict[str, object]", campaign: str, checkout: Path, package: str,
                       expected_record_sha256: "str | None") -> None:
    """Revalidate ownership immediately before the target is changed.

    The classification performed before a long installation is not evidence
    about the target now.  The record digest is compared as well as the binding,
    so a concurrent provision that rewrote the record is refused instead of
    having its environment moved aside.
    """
    try:
        current = classify_target(target, campaign, checkout, package)
    except CampaignEnvironmentError as error:
        raise CampaignEnvironmentError("target-changed-during-provisioning", error.code)
    if expected_record_sha256 is None:
        if current["mode"] != "fresh":
            raise CampaignEnvironmentError("target-changed-during-provisioning",
                                           "target-appeared-during-provisioning")
        return
    if current["mode"] != "owned":
        raise CampaignEnvironmentError("target-changed-during-provisioning", "ownership-lost")
    if current.get("record_sha256") != expected_record_sha256:
        raise CampaignEnvironmentError("target-changed-during-provisioning",
                                       "record-changed-during-provisioning")


def _uncertain_swap(target: "dict[str, object]", *, campaign: str, checkout: Path, package: str,
                    staging: Path, retired: Path, venv: Path, swap_error: OSError,
                    restore_error: OSError,
                    expected_record_sha256: "str | None") -> CampaignEnvironmentError:
    """Report a swap that moved the old environment out and nothing back.

    Both the previous environment and the staged one are still on disk, and which
    of them is usable in place is exactly what this path cannot establish.  So
    nothing is deleted: a private recovery receipt records where each copy is and
    what failed, and the raised error carries the same paths so the evidence does
    not depend on that one file.
    """
    staged = staging / VENV_NAME
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": RECOVERY_KIND,
        "state": "uncertain",
        "created_utc": identity.utc_now(),
        "campaign": campaign,
        "package": package,
        "checkout": str(checkout),
        "root": str(target["root"]),
        "directory": str(target["directory"]),
        "venv": str(venv),
        "venv_kind": path_kind(venv),
        "retired_path": str(retired),
        "retired_kind": path_kind(retired),
        "staged_venv": str(staged),
        "staged_kind": path_kind(staged),
        "staging_path": str(staging),
        "record_path": str(target["record"]),
        "expected_record_sha256": expected_record_sha256,
        "failures": {"swap": type(swap_error).__name__, "restore": type(restore_error).__name__},
        "recovery": [
            "Nothing was deleted: check retired_kind and staged_kind before touching either path.",
            "A directory at retired_path is the previous environment; a directory at "
            "staged_venv is the new one, which was never verified in place.",
            "Move the copy you intend to keep to venv, or delete the target directory "
            "deliberately; a target without its venv is refused by design.",
            "record_path was never rewritten, so this campaign still owns the directory "
            "under the record it had before this provision ran.",
        ],
    }
    receipt: "dict[str, object] | None" = None
    try:
        receipt = receipts.write(Path(str(target["root"])) / (RECOVERY_PREFIX + campaign + "-"
                                                             + uuid4().hex[:12] + ".json"),
                                 record)
    except (OSError, ValueError, TypeError):
        receipt = None
    detail = {
        "reason": "swap-and-restore-both-failed",
        "error": "environment-swap-failed",
        "retired_path": str(retired),
        "retired_present": path_kind(retired) != "absent",
        "staged_path": str(staged),
        "staged_present": path_kind(staged) != "absent",
        "venv_path": str(venv),
        "venv_present": path_kind(venv) != "absent",
        "recovery_receipt": str(receipt["path"]) if receipt else None,
    }
    return CampaignEnvironmentError("replacement-recovery-uncertain",
                                    json.dumps(detail, sort_keys=True))


def _swap_into_place(staging: Path, target: "dict[str, object]", *, replace: bool,
                     campaign: str, checkout: Path, package: str,
                     expected_record_sha256: "str | None") -> "Path | None":
    """Move a validated staging environment into place, retiring the old one.

    The old environment is renamed aside, not deleted, and the old receipt is
    left untouched until a new one is written durably.  Every rename either
    completes or leaves a state this function can still describe: a failure of
    the first leaves the target completely untouched, and a failure of the second
    is undone by the restore or reported as uncertain with both copies kept.
    """
    _swap_precondition(target, campaign, checkout, package, expected_record_sha256)
    directory = Path(str(target["directory"]))
    venv = Path(str(target["venv"]))
    if path_kind(directory) == "absent":
        directory.mkdir(parents=True)
    retired: Path | None = None
    if path_kind(venv) != "absent":
        if not replace:
            raise CampaignEnvironmentError("existing-environment-not-replaceable")
        retired = directory.parent / f".retired-{campaign}-{uuid4().hex[:12]}"
        try:
            _rename(venv, retired)
        except OSError as error:
            # Nothing moved: the environment is still in place and the staged copy
            # is still whole, so this is an ordinary failure, not an uncertainty.
            raise CampaignEnvironmentError("environment-retirement-failed",
                                           type(error).__name__) from error
    try:
        _rename(staging / VENV_NAME, venv)
    except OSError as swap_error:
        if retired is None:
            raise CampaignEnvironmentError("environment-swap-failed",
                                           type(swap_error).__name__) from swap_error
        try:
            _rename(retired, venv)
        except OSError as restore_error:
            raise _uncertain_swap(target, campaign=campaign, checkout=checkout, package=package,
                                  staging=staging, retired=retired, venv=venv,
                                  swap_error=swap_error, restore_error=restore_error,
                                  expected_record_sha256=expected_record_sha256) from swap_error
        raise CampaignEnvironmentError(
            "environment-swap-failed",
            json.dumps({"reason": type(swap_error).__name__, "retired_path": str(retired),
                        "restored": True}, sort_keys=True)) from swap_error
    return retired


def _restore_previous(target: "dict[str, object]", retired: "Path | None") -> dict[str, object]:
    """Put the previous environment back after a failed finalisation.

    Nothing is deleted on the uncertain path: the retired environment and the
    failed new one stay where they are so a human can decide, and the state is
    reported rather than guessed.
    """
    directory = Path(str(target["directory"]))
    venv = Path(str(target["venv"]))
    if retired is None:
        try:
            if path_kind(venv) != "absent":
                shutil.rmtree(venv)
            if path_kind(directory) == "directory" and not any(directory.iterdir()):
                directory.rmdir()
        except OSError:
            return {"state": "uncertain", "reason": "fresh-environment-could-not-be-removed"}
        return {"state": "discarded-fresh"}
    result: dict[str, object] = {"state": "restored", "retired_path": str(retired)}
    failed: Path | None = None
    try:
        if path_kind(venv) != "absent":
            failed = directory.parent / f".failed-{target['campaign']}-{uuid4().hex[:12]}"
            os.replace(venv, failed)
        os.replace(retired, venv)
    except OSError as error:
        result.update(state="uncertain", reason=type(error).__name__,
                      retired_preserved=path_kind(retired) != "absent",
                      failed_path=str(failed) if failed is not None else None)
        return result
    # The restored environment is the one that matters; the abandoned new one was
    # never qualified, so it is removed once the restore has definitely happened.
    if failed is not None:
        shutil.rmtree(failed, ignore_errors=True)
    return result


def _finish_swap(retired: "Path | None") -> dict[str, object]:
    """Delete a retired environment once its replacement is durable."""
    if retired is None:
        return {"retired_removed": False, "retired_path": None}
    removed = True
    try:
        shutil.rmtree(retired)
    except OSError:
        removed = path_kind(retired) == "absent"
    return {"retired_removed": removed, "retired_path": str(retired)}


def _verify(target: "dict[str, object]", checkout_path: Path, package: str,
            source_package: "dict[str, object]",
            timeout: int) -> tuple[dict[str, object], dict[str, object], "list[str]", str]:
    """Final verification of the environment now sitting at the target path."""
    interpreter = str(target["interpreter"])
    installed_site = site_packages(interpreter)
    reasons: list[str] = []
    if identity.contained(installed_site, str(target["venv"])) is not True:
        raise CampaignEnvironmentError("site-packages-outside-environment")
    verification = launch.probe(interpreter, cwd=str(checkout_path), package=package,
                                timeout=min(timeout, 300))
    report = verification.get("report") or {}
    installed = report.get("package") or {}
    interpreter_identity = identity.interpreter_identity(interpreter)
    if not verification.get("report_parsed"):
        reasons.append("verification-probe-unparseable")
    elif installed.get("state") != "imported":
        reasons.append("installed-package-not-importable")
    elif installed.get("python_digest") != source_package["python_digest"]:
        reasons.append("installed-code-differs-from-source")
    elif identity.contained(installed.get("origin"), installed_site) is not True:
        reasons.append("installed-package-outside-environment")
    elif not identity.same_environment(interpreter_identity.get("prefix"), str(target["venv"])):
        reasons.append("interpreter-prefix-is-not-the-environment")
    elif not report.get("isolated"):
        reasons.append("verification-probe-was-not-isolated")
    return verification, installed, reasons, installed_site


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
    redirect = redirected_ancestor(root_path, within=checkout_path)
    if redirect is not None:
        raise CampaignEnvironmentError("redirected-environment-root", redirect)
    root_kind = path_kind(root_path)
    if root_kind not in {"absent", "directory"}:
        raise CampaignEnvironmentError("environment-root-is-not-a-directory", root_kind)
    root_path.mkdir(parents=True, exist_ok=True)
    lock = Path(str(target["lock"]))
    _acquire_lock(lock)
    try:
        return _provision_locked(checkout_path, campaign, target, python=python, replace=replace,
                                 package=package, allow_build_isolation=allow_build_isolation,
                                 accept_enclosing=accept_enclosing, timeout=timeout)
    finally:
        _release_lock(lock)


def _provision_locked(checkout_path: Path, campaign: str, target: "dict[str, object]", *,
                      python: "str | os.PathLike[str] | None", replace: bool, package: str,
                      allow_build_isolation: bool, accept_enclosing: bool,
                      timeout: int) -> dict[str, object]:
    owned = classify_target(target, campaign, checkout_path, package)
    if owned["mode"] == "owned" and not replace:
        raise CampaignEnvironmentError("environment-exists")
    source_before = identity.source_identity(checkout_path, accept_enclosing=accept_enclosing)
    if source_before["state"] != "git":
        raise CampaignEnvironmentError("source-identity-not-established", str(source_before["state"]))
    package_source = checkout_path / "src" / package
    digests_before = identity.package_digests(package_source)
    # The bootstrap is named, not resolved: a virtual environment's interpreter
    # is its invocation path, and resolving it would describe the base instead.
    bootstrap = os.path.abspath(str(python)) if python is not None else os.path.abspath(sys.executable)
    root_path = Path(str(target["root"]))

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

    try:
        retired = _swap_into_place(staging, target, replace=replace, campaign=campaign,
                                   checkout=checkout_path, package=package,
                                   expected_record_sha256=owned["record_sha256"])
    except CampaignEnvironmentError as error:
        if error.code == "replacement-recovery-uncertain":
            # The retired environment, the staged environment and the previous
            # receipt are the only record of what happened.  Removing either copy
            # here would turn a recoverable state into an unrecoverable one.
            raise
        shutil.rmtree(staging, ignore_errors=True)
        _discard_empty_directory(target)
        raise
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        _discard_empty_directory(target)
        raise
    shutil.rmtree(staging, ignore_errors=True)
    try:
        verification, installed, reasons, installed_site = _verify(target, checkout_path, package,
                                                                   digests_before, timeout)
        if reasons:
            raise CampaignEnvironmentError("verification-failed", ",".join(reasons))
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "kind": KIND,
            "campaign": campaign,
            "package": package,
            "checkout": str(checkout_path),
            "root": str(target["root"]),
            "directory": str(target["directory"]),
            "venv": str(target["venv"]),
            "interpreter": str(target["interpreter"]),
            "site_packages": installed_site,
            "record_path": str(target["record"]),
            "created_utc": identity.utc_now(),
            "ownership": {"mode": "replaced-owned" if retired else owned["mode"],
                          "previous_record_present": owned["record"] is not None,
                          "previous_record_sha256": owned["record_sha256"],
                          "retired_pending_removal": str(retired) if retired else None},
            "source_before": source_before,
            "source_after": source_after,
            "source_unchanged": True,
            "source_package": digests_before,
            "bootstrap_interpreter": bootstrap,
            "bootstrap_identity": identity.interpreter_identity(bootstrap),
            "environment_identity": identity.interpreter_identity(str(target["interpreter"])),
            "environment": venv_receipt,
            "installation": installation,
            "staged_probe": staged_probe,
            "verification_probe": verification,
            "installed": installed,
            "verdict": "qualified",
            "reasons": [],
        }
        record["receipt"] = receipts.write(str(target["record"]), record)
    except BaseException as error:
        if isinstance(error, CampaignEnvironmentError):
            failure_code = error.code
        elif isinstance(error, (KeyboardInterrupt, SystemExit)):
            failure_code = "interrupted"
        else:
            failure_code = "receipt-write-failed"
        recovery = _restore_previous(target, retired)
        if recovery["state"] == "uncertain":
            raise CampaignEnvironmentError(
                "replacement-recovery-uncertain",
                json.dumps({"reason": recovery.get("reason"),
                            "retired_path": recovery.get("retired_path"),
                            "failed_path": recovery.get("failed_path"),
                            "error": failure_code},
                           sort_keys=True)) from error
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(error, CampaignEnvironmentError):
            raise CampaignEnvironmentError(error.code, error.detail) from error
        raise CampaignEnvironmentError("receipt-write-failed", type(error).__name__) from error

    # Only now is the previous environment disposable: the new installation has
    # been verified and its receipt is durable.
    removal = _finish_swap(retired)
    record["ownership"].update(removal)
    record["ownership"]["recovery"] = None
    try:
        receipts.write(str(target["record"]), record)
    except OSError:
        # The durable receipt already records ``retired_pending_removal``; a
        # failed follow-up write must not fail a qualified provision.
        pass
    return record
