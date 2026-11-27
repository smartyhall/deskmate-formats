"""Controlled experiment: campaign isolation with a conflicting installation.

Five things are demonstrated on the laboratory host, using the shipped
mechanism rather than a parallel copy of it:

E1  the host picture — interpreters, the package each one resolves, virtual
    environments, worktrees and every ``-I`` launch site in this checkout;
E2  two synthetic source checkouts whose implementations carry distinguishable
    markers, each provisioned into its own campaign environment by
    ``environment.provision`` from a real ``pip`` install, with a third marked
    copy standing in for another campaign's installation.  Every parent and
    isolated child must resolve its own checkout while ``PYTHONPATH`` names the
    conflict, and an unisolated control must reproduce the conflict — otherwise
    the experiment has not shown that isolation is what does the work;
E3  this repository qualified end to end: one campaign environment, a preflight
    run inside it (qualified), a preflight run from the shared interpreter
    (unqualified, interpreter mismatch), a preflight whose parent is the shared
    interpreter and which merely *names* the campaign interpreter (unqualified:
    a request is not evidence about the parent), and one with a conflicting
    ``PYTHONPATH`` (unqualified on package identity);
E4  environment ownership: an existing directory this campaign cannot prove it
    owns, a Windows junction at the target path, and an owned replacement that
    must not leave stale installed files behind;
E5  the installation boundary: the default provision of a campaign on this host
    has no build backend available and fails offline, and only an explicit
    ``allow_build_isolation=True`` reaches the network for one.  The historical
    run's build-isolation mode is reproduced that way and is never the default.

Each synthetic checkout is a copy of ``src/deskmate_formats`` with a
``CAMPAIGN_MARKER`` line appended to the campaign package, so the marker travels
through the real installation path instead of through a test double.

All raw output, including absolute paths and pip logs, is written under
``--output`` and stays private.  Only the redacted projection is printed, and
that is what the report and evidence file quote.

No emulator, model turn or unattended dispatch is involved.  The only network
access is pip fetching this project's declared build backend, and only in the
explicitly opted-in attempts.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from deskmate_formats.campaign_env import environment, identity, inventory, preflight, receipts

PACKAGE = "deskmate_formats"
MARKERS = {"alpha": "alpha-checkout-2", "beta": "beta-checkout-7"}
SHARED_MARKER = "shared-preinstalled-0"
CAMPAIGN = "campaign-python-environment"

MARKER_SCRIPT = (
    "import json, os, sys; "
    "import deskmate_formats as d; "
    "from deskmate_formats.campaign_env import CAMPAIGN_MARKER as m; "
    "print(json.dumps({'marker': m, 'origin': d.__file__, "
    "'isolated': bool(sys.flags.isolated), "
    "'pythonpath_present': 'PYTHONPATH' in os.environ}))"
)

PARENT = """\
import json
import os
import subprocess
import sys

import deskmate_formats
from deskmate_formats.campaign_env import CAMPAIGN_MARKER

environment = dict(os.environ)
environment["PYTHONPATH"] = sys.argv[1] if len(sys.argv) > 1 else ""
child = subprocess.run(
    [sys.executable, "-I", "-c", sys.argv[2]],
    capture_output=True, text=True, env=environment, timeout=180,
)
print(json.dumps({
    "parent_marker": CAMPAIGN_MARKER,
    "parent_origin": deskmate_formats.__file__,
    "parent_isolated": bool(sys.flags.isolated),
    "child_exit": child.returncode,
    "child": json.loads(child.stdout) if child.returncode == 0 else None,
    "child_stderr": child.stderr[-300:],
}))
"""

PYPROJECT = """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "deskmate-formats"
version = "{version}"
description = "Synthetic campaign isolation checkout; not a project release"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"*" = ["*.license"]
"deskmate_formats.observer" = ["dashboard.css", "dashboard.js"]
"deskmate_formats.supervisor" = ["codex-0.166.0.json", "CODEX-NOTICE.txt"]
"""


class ExperimentError(RuntimeError):
    """An expectation of the controlled experiment was not met."""


def _git(checkout: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "user.name=Campaign Experiment", "-c", "user.email=experiment@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.devnull, *arguments],
        cwd=str(checkout), capture_output=True, text=True, timeout=180,
    )
    if completed.returncode != 0:
        raise ExperimentError(f"git {arguments[0]} failed: {completed.stderr[-300:]}")
    return completed.stdout.strip()


def initialise_repository(checkout: Path, *, message: str = "synthetic campaign checkout") -> str:
    """A synthetic checkout needs its own repository.

    A directory created inside a Git checkout inherits the enclosing
    repository's ``HEAD``, so a copy that is not a repository itself would be
    provisioned against the experiment's own revision.  That is a real provenance
    hazard, not only an experiment detail, and the mechanism now refuses it.
    """
    _git(checkout, "init", "-q")
    _git(checkout, "add", "--", ".")
    _git(checkout, "commit", "-q", "-m", message)
    return _git(checkout, "rev-parse", "HEAD")


def marked_copy(source: Path, destination: Path, marker: str, version: str) -> Path:
    """Copy the package tree, then make this copy identifiable from inside itself."""
    (destination / "src").mkdir(parents=True)
    shutil.copytree(source / "src" / PACKAGE, destination / "src" / PACKAGE)
    package_init = destination / "src" / PACKAGE / "campaign_env" / "__init__.py"
    with package_init.open("a", encoding="utf-8") as stream:
        stream.write(f'\n\nCAMPAIGN_MARKER = "{marker}"\n')
    (destination / "pyproject.toml").write_text(PYPROJECT.format(version=version), encoding="utf-8")
    (destination / "parent.py").write_text(PARENT, encoding="utf-8")
    initialise_repository(destination, message=f"synthetic {marker} checkout")
    return destination


def marked_child(interpreter: Path, neutral: Path, *, isolated: bool, pythonpath: Path) -> dict:
    argv = [str(interpreter)] + (["-I"] if isolated else []) + ["-c", MARKER_SCRIPT]
    env = dict(os.environ) | {"PYTHONPATH": str(pythonpath), "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(argv, cwd=str(neutral), capture_output=True, text=True, env=env, timeout=300)
    if completed.returncode != 0:
        raise ExperimentError(f"child failed ({interpreter.name}): {completed.stderr[-400:]}")
    return json.loads(completed.stdout)


def marked_parent(interpreter: Path, checkout: Path, neutral: Path, hostile: Path) -> dict:
    env = dict(os.environ) | {"PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONPATH", None)
    completed = subprocess.run([str(interpreter), str(checkout / "parent.py"), str(hostile), MARKER_SCRIPT],
                               cwd=str(neutral), capture_output=True, text=True, env=env, timeout=300)
    if completed.returncode != 0:
        raise ExperimentError(f"parent failed: {completed.stderr[-400:]}")
    return json.loads(completed.stdout)


def host_inventory(repo: Path, root: Path) -> dict:
    record = inventory.inventory(repo, environment_roots=(str(repo), str(root)))
    record["launcher"] = inventory.launcher_identity(record["launch_sites"],
                                                     str(record["running_interpreter"]["executable"]))
    return record


def offline_attempt(repo: Path, root: Path, bootstrap: Path) -> dict:
    """The default provision on a host without a build backend must fail, not fetch."""
    checkout = marked_copy(repo, root / "offline", "offline-checkout-0", "0.0.0")
    try:
        record = environment.provision(checkout, "offline", root=root / "envs", python=bootstrap)
    except environment.CampaignEnvironmentError as error:
        return {
            "outcome": "refused",
            "reason": error.code,
            "detail": error.detail,
            "build_isolation_enabled": False,
            "target_created": environment.path_kind(
                environment.layout(checkout, "offline", root=root / "envs")["directory"]),
        }
    return {
        "outcome": "installed-offline",
        "reason": None,
        "detail": None,
        "build_isolation_enabled": record["installation"]["build_isolation_explicitly_enabled"],
        "install_mode": record["installation"]["install_mode"],
    }


def isolation_experiment(repo: Path, root: Path, bootstrap: Path) -> dict:
    """Two marked checkouts, one conflicting installation, the full launch matrix."""
    neutral = root / "neutral"
    neutral.mkdir()
    shared = marked_copy(repo, root / "shared", SHARED_MARKER, "0.0.0")
    campaigns: dict[str, dict] = {}
    for label in ("alpha", "beta"):
        checkout = marked_copy(repo, root / label, MARKERS[label], f"0.0.{1 if label == 'alpha' else 2}")
        # Explicitly opted in: this host has no build backend for the default
        # offline mode, and the historical run used the network-capable mode.
        record = environment.provision(checkout, label, root=root / "envs", python=bootstrap,
                                       allow_build_isolation=True)
        if record["verdict"] != "qualified":
            raise ExperimentError(f"{label} environment is not qualified: {record['reasons']}")
        if record["installation"]["build_isolation_explicitly_enabled"] is not True:
            raise ExperimentError(f"{label} provision does not record the explicit opt-in")
        campaigns[label] = {"checkout": checkout, "record": record,
                            "interpreter": Path(str(record["interpreter"]))}

    observations: dict[str, object] = {}
    for label, data in campaigns.items():
        other = "beta" if label == "alpha" else "alpha"
        own = MARKERS[label]
        with_shared = marked_child(data["interpreter"], neutral, isolated=True, pythonpath=shared)
        with_other = marked_child(data["interpreter"], neutral, isolated=True,
                                  pythonpath=campaigns[other]["checkout"] / "src")
        control = marked_child(data["interpreter"], neutral, isolated=False, pythonpath=shared / "src")
        parent = marked_parent(data["interpreter"], data["checkout"], neutral, shared / "src")
        observations[label] = {
            "own_marker": own,
            "isolated_child_with_shared_pythonpath": with_shared,
            "isolated_child_with_other_checkout_pythonpath": with_other,
            "unisolated_control": control,
            "parent_and_child": parent,
        }
        for name, report in (("shared", with_shared), ("other", with_other)):
            if report["marker"] != own:
                raise ExperimentError(f"{label} {name} resolved {report['marker']!r}, expected {own!r}")
            if not report["isolated"] or not report["pythonpath_present"]:
                raise ExperimentError(f"{label} {name} was not an isolated child with a set PYTHONPATH")
            if not identity.contained(report["origin"], str(campaigns[label]["record"]["site_packages"])):
                raise ExperimentError(f"{label} {name} imported outside its campaign environment")
        if control["marker"] != SHARED_MARKER:
            raise ExperimentError(f"{label} unisolated control did not reproduce the shared conflict")
        if parent["parent_marker"] != own or (parent["child"] or {}).get("marker") != own:
            raise ExperimentError(f"{label} parent/child pair did not stay on its own checkout")

    # The bootstrap interpreter is the laboratory's shared one; the synthetic
    # campaign must be invisible to it, which is what "separate environment" means.
    invisible = subprocess.run(
        [str(bootstrap), "-I", "-c", MARKER_SCRIPT], capture_output=True, text=True, timeout=120,
    )
    return {
        "kind": "campaign-env-isolation-experiment",
        "markers": MARKERS,
        "shared_conflict_marker": SHARED_MARKER,
        "campaigns": {label: {"checkout": str(data["checkout"]), "record": data["record"]}
                      for label, data in campaigns.items()},
        "observations": observations,
        "shared_interpreter_cannot_see_synthetic_campaign": invisible.returncode != 0,
        "shared_interpreter_stderr": invisible.stderr[-200:],
    }


def campaign_preflight(interpreter: Path, repo: Path, root: Path, *, campaign: str = CAMPAIGN,
                       pythonpath: "Path | None" = None,
                       requested_interpreter: "Path | None" = None) -> "tuple[dict, int]":
    """Run the shipped preflight as a child of one explicit interpreter."""
    env = dict(os.environ) | {"PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONPATH", None)
    if pythonpath is not None:
        env["PYTHONPATH"] = str(pythonpath)
    argv = [str(interpreter), "-m", "deskmate_formats.campaign_env.cli", "preflight",
            "--campaign", campaign, "--root", str(root)]
    if requested_interpreter is not None:
        argv += ["--interpreter", str(requested_interpreter)]
    completed = subprocess.run(argv, cwd=str(repo), capture_output=True, text=True, env=env, timeout=900)
    if not completed.stdout:
        raise ExperimentError(f"campaign preflight did not run: {completed.stderr[-400:]}")
    return json.loads(completed.stdout), completed.returncode


def qualification_experiment(repo: Path, root: Path, bootstrap: Path, shared: Path) -> dict:
    """Qualify this repository, then show four independent ways it is refused."""
    # This campaign's own environment may already exist from an earlier run of
    # this experiment; replacing it is explicit and staged.
    record = environment.provision(repo, CAMPAIGN, root=root, python=bootstrap,
                                   allow_build_isolation=True, replace=True)
    interpreter = Path(str(record["interpreter"]))
    qualified, qualified_status = campaign_preflight(interpreter, repo, root)
    conflicted, conflicted_status = campaign_preflight(interpreter, repo, root,
                                                       pythonpath=shared / "src")
    # The shared interpreter is whichever interpreter runs this experiment.
    from_shared = preflight.preflight(repo, campaign=CAMPAIGN, root=root)
    # A request naming the campaign interpreter, made by the shared parent: the
    # review's exact case, and the reason a request is never parent evidence.
    selection, selection_status = campaign_preflight(
        bootstrap, repo, root, pythonpath=repo / "src", requested_interpreter=interpreter)
    if qualified["verdict"] != preflight.QUALIFIED or qualified_status != 0:
        raise ExperimentError(f"campaign preflight is {qualified['verdict']}: {qualified['reasons']}")
    if conflicted["verdict"] != preflight.UNQUALIFIED or "parent-package" not in conflicted["reasons"]:
        raise ExperimentError("a conflicting PYTHONPATH was not refused on package identity")
    if from_shared["verdict"] != preflight.UNQUALIFIED or "parent-interpreter" not in from_shared["reasons"]:
        raise ExperimentError("preflight from the shared interpreter did not fail on the interpreter")
    selection_checks = {entry["check"]: entry for entry in selection["checks"]}
    if selection["verdict"] != preflight.UNQUALIFIED:
        raise ExperimentError("a shared parent that merely named the campaign interpreter qualified")
    if "parent-interpreter" not in selection["reasons"]:
        raise ExperimentError("the shared parent was accepted as the campaign interpreter")
    if selection_checks.get("requested-interpreter", {}).get("state") != preflight._PASS:
        raise ExperimentError("the requested interpreter was not recorded as an accepted selection")
    return {
        "kind": "campaign-env-qualification",
        "provision": record,
        "preflight_inside_environment": qualified,
        "preflight_with_conflicting_pythonpath": conflicted,
        "preflight_from_shared_interpreter": from_shared,
        "preflight_shared_parent_naming_the_environment": selection,
        "exit_status_inside": qualified_status,
        "exit_status_conflicted": conflicted_status,
        "exit_status_from_shared": preflight.exit_code(from_shared["verdict"]),
        "exit_status_selection": selection_status,
    }


def ownership_experiment(repo: Path, root: Path, bootstrap: Path) -> dict:
    """Refuse what cannot be proven owned; replace what can, without stale files."""
    checkout = marked_copy(repo, root / "ownership", "ownership-checkout-3", "0.0.3")
    envs = root / "envs"
    unowned_target = environment.layout(checkout, "squatter", root=envs)
    Path(str(unowned_target["directory"])).mkdir(parents=True)
    (Path(str(unowned_target["directory"])) / "someone-elses-notes.txt").write_text(
        "not this campaign's directory\n", encoding="utf-8")
    try:
        environment.provision(checkout, "squatter", root=envs, python=bootstrap,
                              allow_build_isolation=True)
    except environment.CampaignEnvironmentError as error:
        unowned = {"reason": error.code, "detail": error.detail}
    else:
        raise ExperimentError("an existing directory without a record was accepted")
    preserved = (Path(str(unowned_target["directory"])) / "someone-elses-notes.txt").is_file()

    junction: dict[str, object] = {"applicable": False}
    if os.name == "nt":
        elsewhere = root / "junction-destination"
        elsewhere.mkdir()
        junction_target = environment.layout(checkout, "junction-campaign", root=envs)
        Path(str(junction_target["root"])).mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction_target["directory"]), str(elsewhere)],
            capture_output=True, text=True,
        )
        if completed.returncode == 0:
            try:
                environment.provision(checkout, "junction-campaign", root=envs, python=bootstrap,
                                      allow_build_isolation=True)
            except environment.CampaignEnvironmentError as error:
                junction = {"applicable": True, "kind": environment.path_kind(junction_target["directory"]),
                            "reason": error.code, "detail": error.detail}
            else:
                raise ExperimentError("a junction at the target path was accepted")
        else:
            junction = {"applicable": False, "detail": "junction creation was refused"}

    first = environment.provision(checkout, "replaceable", root=envs, python=bootstrap,
                                  allow_build_isolation=True)
    stale = Path(str(first["venv"])) / "stale-installed-module.py"
    stale.write_text("STALE = True\n", encoding="utf-8")
    second = environment.provision(checkout, "replaceable", root=envs, python=bootstrap,
                                   allow_build_isolation=True, replace=True)
    replacement = {
        "first_ownership": first["ownership"]["mode"],
        "second_ownership": second["ownership"]["mode"],
        "stale_file_present_before": True,
        "stale_file_present_after": stale.is_file(),
        "retired_path_recorded": bool(second["ownership"]["retired_path"]),
        "verdict": second["verdict"],
    }
    if replacement["stale_file_present_after"]:
        raise ExperimentError("a replacement left a stale file in the new environment")
    if replacement["second_ownership"] != "replaced-owned":
        raise ExperimentError("a replacement was not recorded as replacing an owned environment")
    if replacement["verdict"] != "qualified":
        raise ExperimentError("the replacement environment did not qualify")
    return {
        "kind": "campaign-env-ownership",
        "unowned_directory": unowned,
        "unowned_directory_content_preserved": preserved,
        "junction": junction,
        "replacement": replacement,
    }


def metadata_failure_experiment(campaigns: dict, root: Path, campaign: str = "beta") -> dict:
    """Hide a provisioned checkout's Git metadata and require an unknown verdict."""
    data = campaigns[campaign]
    checkout = Path(data["checkout"])
    interpreter = Path(str(data["record"]["interpreter"]))
    hidden = checkout / ".git-hidden"
    (checkout / ".git").rename(hidden)
    try:
        receipt, status = campaign_preflight(interpreter, checkout, root, campaign=campaign)
        direct = identity.source_identity(checkout)
    finally:
        hidden.rename(checkout / ".git")
        restored = identity.source_identity(checkout)
    if receipt["verdict"] != preflight.UNKNOWN or "source-revision" not in receipt["reasons"]:
        raise ExperimentError("unreadable Git metadata did not yield an unknown verdict")
    if receipt["measurement_allowed"]:
        raise ExperimentError("an unestablished identity allowed a measurement")
    if direct["state"] == "git" or direct["revision"] is not None:
        raise ExperimentError("a checkout without readable metadata still reported a revision")
    if restored["state"] != "git":
        raise ExperimentError("restoring the metadata did not restore the identity")
    return {
        "kind": "campaign-env-metadata-failure",
        "campaign": campaign,
        "preflight": receipt,
        "exit_status": status,
        "source_while_hidden": direct,
        "source_after_restore": restored,
    }


def drift_experiment(campaigns: dict, root: Path, campaign: str = "alpha") -> dict:
    """Change a provisioned checkout, then commit, and see both refusals."""
    data = campaigns[campaign]
    checkout = Path(data["checkout"])
    interpreter = Path(str(data["record"]["interpreter"]))
    target = checkout / "src" / PACKAGE / "campaign_env" / "__init__.py"
    baseline_revision = _git(checkout, "rev-parse", "HEAD")
    with target.open("a", encoding="utf-8") as stream:
        stream.write("\nDRIFT_MARKER = 1\n")
    edited, edited_status = campaign_preflight(interpreter, checkout, root, campaign=campaign)
    _git(checkout, "add", "--", str(target.relative_to(checkout)))
    _git(checkout, "commit", "-q", "-m", "synthetic drift commit")
    committed_revision = _git(checkout, "rev-parse", "HEAD")
    committed, committed_status = campaign_preflight(interpreter, checkout, root, campaign=campaign)
    if "source-content" not in edited["reasons"]:
        raise ExperimentError("an edited checkout was not refused on content")
    if "source-revision" in edited["reasons"]:
        raise ExperimentError("an edit without a commit was reported as a revision change")
    for reason in ("source-content", "source-revision"):
        if reason not in committed["reasons"]:
            raise ExperimentError(f"a committed change did not report {reason}")
    return {
        "kind": "campaign-env-source-drift",
        "campaign": campaign,
        "baseline_revision": baseline_revision,
        "committed_revision": committed_revision,
        "after_edit": edited,
        "after_commit": committed,
        "after_edit_exit": edited_status,
        "after_commit_exit": committed_status,
        "revisions_differ": baseline_revision != committed_revision,
    }


def summarise(host: dict, isolation: dict, offline: dict, qualification: dict, ownership: dict,
              drift: dict, metadata: dict, elapsed: float) -> dict:
    record_of = lambda label: isolation["campaigns"][label]["record"]  # noqa: E731
    return {
        "kind": "campaign-env-experiment-summary",
        "conducted_utc": identity.utc_now(),
        "elapsed_seconds": round(elapsed, 3),
        "host": {
            "checkout": host["checkout"],
            "source": host["source"],
            "counts": host["counts"],
            "interpreters": [
                {"executable": entry.get("executable"), "version": entry.get("version"),
                 "state": entry.get("state"),
                 "virtual_environment": entry.get("virtual_environment"),
                 "package_origin": entry.get("package_origin"),
                 "deskmate_formats_version": (entry.get("distributions") or {}).get("present", {}).get(
                     "deskmate-formats")}
                for entry in host["interpreters"]
            ],
            "environments": [{"path": entry.get("path"), "package_origin": entry.get("package_origin")}
                             for entry in host["environments"]],
            "worktree_count": len(host["worktrees"]),
            "launch_sites": host["launch_sites"],
            "launcher": host["launcher"],
        },
        "installation_boundary": {
            "default_provision_outcome": offline["outcome"],
            "default_provision_reason": offline["reason"],
            "default_provision_detail": offline["detail"],
            "default_provision_build_isolation": offline["build_isolation_enabled"],
            "default_provision_target_kind": offline["target_created"],
            "campaign_install_modes": {label: record_of(label)["installation"]["install_mode"]
                                       for label in isolation["campaigns"]},
            "campaign_build_isolation_explicit": {
                label: record_of(label)["installation"]["build_isolation_explicitly_enabled"]
                for label in isolation["campaigns"]},
        },
        "isolation": {
            "markers": isolation["markers"],
            "shared_conflict_marker": isolation["shared_conflict_marker"],
            "shared_interpreter_cannot_see_synthetic_campaign":
                isolation["shared_interpreter_cannot_see_synthetic_campaign"],
            "observations": {
                label: {
                    "own_marker": data["own_marker"],
                    "isolated_child_with_shared_pythonpath_marker":
                        data["isolated_child_with_shared_pythonpath"]["marker"],
                    "isolated_child_with_other_checkout_pythonpath_marker":
                        data["isolated_child_with_other_checkout_pythonpath"]["marker"],
                    "isolated_child_reported_isolated":
                        data["isolated_child_with_shared_pythonpath"]["isolated"],
                    "unisolated_control_marker": data["unisolated_control"]["marker"],
                    "parent_marker": data["parent_and_child"]["parent_marker"],
                    "child_marker": (data["parent_and_child"]["child"] or {}).get("marker"),
                }
                for label, data in isolation["observations"].items()
            },
            "environment_verdicts": {label: record_of(label)["verdict"]
                                     for label in isolation["campaigns"]},
            "ownership_modes": {label: record_of(label)["ownership"]["mode"]
                                for label in isolation["campaigns"]},
            "source_tree_digests": {label: record_of(label)["source_package"]["tree_digest"]
                                    for label in isolation["campaigns"]},
            "source_revisions": {label: record_of(label)["source_before"]["revision"]
                                 for label in isolation["campaigns"]},
        },
        "ownership": ownership,
        "drift": {
            "campaign": drift["campaign"],
            "after_edit_verdict": drift["after_edit"]["verdict"],
            "after_edit_reasons": drift["after_edit"]["reasons"],
            "after_commit_verdict": drift["after_commit"]["verdict"],
            "after_commit_reasons": drift["after_commit"]["reasons"],
            "revisions_differ": drift["revisions_differ"],
            "exit_statuses": {"after_edit": drift["after_edit_exit"],
                              "after_commit": drift["after_commit_exit"]},
        },
        "metadata_failure": {
            "campaign": metadata["campaign"],
            "verdict": metadata["preflight"]["verdict"],
            "reasons": metadata["preflight"]["reasons"],
            "measurement_allowed": metadata["preflight"]["measurement_allowed"],
            "exit_status": metadata["exit_status"],
            "source_state_while_hidden": metadata["source_while_hidden"]["state"],
            "source_failure_while_hidden": metadata["source_while_hidden"]["failure"],
            "revision_while_hidden": metadata["source_while_hidden"]["revision"],
            "source_state_after_restore": metadata["source_after_restore"]["state"],
        },
        "qualification": {
            "campaign": CAMPAIGN,
            "provision_verdict": qualification["provision"]["verdict"],
            "install_mode": qualification["provision"]["installation"]["install_mode"],
            "inside_verdict": qualification["preflight_inside_environment"]["verdict"],
            "conflicted_verdict": qualification["preflight_with_conflicting_pythonpath"]["verdict"],
            "conflicted_reasons": qualification["preflight_with_conflicting_pythonpath"]["reasons"],
            "outside_verdict": qualification["preflight_from_shared_interpreter"]["verdict"],
            "outside_reasons": qualification["preflight_from_shared_interpreter"]["reasons"],
            "selection_verdict": qualification["preflight_shared_parent_naming_the_environment"]["verdict"],
            "selection_reasons":
                qualification["preflight_shared_parent_naming_the_environment"]["reasons"],
            "exit_statuses": {"inside": qualification["exit_status_inside"],
                              "conflicted": qualification["exit_status_conflicted"],
                              "outside": qualification["exit_status_from_shared"],
                              "selection": qualification["exit_status_selection"]},
            "checks_inside": qualification["preflight_inside_environment"]["checks"],
            "checks_conflicted": qualification["preflight_with_conflicting_pythonpath"]["checks"],
            "checks_outside": qualification["preflight_from_shared_interpreter"]["checks"],
            "checks_selection":
                qualification["preflight_shared_parent_naming_the_environment"]["checks"],
        },
    }


def run(repo: Path, output: Path, bootstrap: Path) -> dict:
    repo = repo.resolve()
    bootstrap = Path(bootstrap).resolve()
    if output.exists():
        raise ExperimentError("output directory must be new: private receipts are never overwritten")
    output.mkdir(parents=True)
    # Outside any checkout on purpose: Git identity is inherited by every
    # directory inside a repository, so a synthetic checkout created under this
    # one would answer revision queries with the experiment's own HEAD.
    experiment_root = Path(tempfile.mkdtemp(prefix="campaign-isolation-"))
    started = time.time()

    host = host_inventory(repo, experiment_root)
    receipts.write(output / "01-inventory.json", host)
    offline = offline_attempt(repo, experiment_root, bootstrap)
    receipts.write(output / "02-installation-boundary.json", offline)
    isolation = isolation_experiment(repo, experiment_root, bootstrap)
    receipts.write(output / "03-isolation.json", isolation)
    qualification = qualification_experiment(repo, environment.default_root(repo), bootstrap,
                                             experiment_root / "shared")
    receipts.write(output / "04-qualification.json", qualification)
    ownership = ownership_experiment(repo, experiment_root, bootstrap)
    receipts.write(output / "05-ownership.json", ownership)
    drift = drift_experiment(isolation["campaigns"], experiment_root / "envs")
    receipts.write(output / "06-drift.json", drift)
    metadata = metadata_failure_experiment(isolation["campaigns"], experiment_root / "envs")
    receipts.write(output / "07-metadata-failure.json", metadata)
    after = host_inventory(repo, experiment_root)
    receipts.write(output / "08-inventory-after.json", after)

    summary = summarise(host, isolation, offline, qualification, ownership, drift, metadata,
                        time.time() - started)
    summary["experiment_root"] = str(experiment_root)
    summary["host"]["after"] = {
        "counts": after["counts"],
        "environments": [{"path": entry.get("path"), "package_origin": entry.get("package_origin")}
                         for entry in after["environments"]],
    }
    receipts.write(output / "09-summary.json", summary)
    public = receipts.public(summary, roots=(str(repo), str(output), str(environment.default_root(repo))))
    receipts.write(output / "public-summary.json", public)
    return {"output": str(output), "public": public}


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="the campaign checkout to qualify")
    parser.add_argument("--output", type=Path, required=True, help="new private directory for receipts")
    parser.add_argument("--python", type=Path, default=Path(sys.executable),
                        help="bootstrap interpreter that already has pip")
    arguments = parser.parse_args(argv)
    try:
        result = run(arguments.repo, arguments.output.absolute(), arguments.python)
    except ExperimentError as error:
        print(json.dumps({"state": "failed", "reason": str(error)}))
        return 1
    print(json.dumps(result["public"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
