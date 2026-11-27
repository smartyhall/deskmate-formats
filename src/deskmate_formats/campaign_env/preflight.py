"""Compare the requested identity with the observed one; refuse to qualify.

``preflight`` answers one question for a measurement about to be taken: do the
parent process, the isolated child and the checkout all belong to the same
source revision, and is that the revision this campaign recorded when it
provisioned?  Anything it cannot establish is ``unknown``, and anything that
disagrees is ``unqualified``.  Only a fully established match is
``qualified``, and only ``qualified`` may be reported as a campaign
measurement.

Two corrections from review are structural rather than cosmetic:

* an explicitly supplied ``--interpreter`` is recorded as a **selection**, and
  can never stand in for the parent's actual identity.  The parent check reads
  the running process's own prefix and invocation path;
* package identity is a **positive content match**.  Being located inside the
  expected installation directory proves nothing on its own, so the parent's
  and the child's Python digests must equal the digest the provisioning receipt
  recorded.  Location is reported as an observation, not as evidence.

A receipt is also bound to its schema, campaign, checkout, package and expected
layout before any of it is believed.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import environment, identity, launch, receipts

SCHEMA_VERSION = 1
QUALIFIED = "qualified"
UNQUALIFIED = "unqualified"
UNKNOWN = "unknown"
EXIT_CODES = {QUALIFIED: 0, UNQUALIFIED: 1, UNKNOWN: 2}

CHECKS = (
    "environment-record",
    "checkout-root",
    "parent-interpreter",
    "requested-interpreter",
    "parent-package",
    "source-revision",
    "source-content",
    "child-interpreter",
    "observed-origin",
    "observed-content",
    "child-isolation",
)

_PASS = "pass"
_FAIL = "fail"
_UNKNOWN = "unknown"


def _check(name: str, state: str, detail: str, **observed: object) -> dict[str, object]:
    return {"check": name, "state": state, "detail": detail, **observed}


def exit_code(verdict: object) -> int:
    return EXIT_CODES.get(str(verdict), 2)


def preflight(checkout: "str | os.PathLike[str]" = ".", *, campaign: str,
              root: "str | os.PathLike[str] | None" = None,
              interpreter: "str | os.PathLike[str] | None" = None,
              package: str = identity.PACKAGE,
              accept_enclosing: bool = False,
              timeout: int = 300) -> dict[str, object]:
    """Observe parent, child and checkout, and return a provenance receipt."""
    checkout_path = Path(checkout).resolve()
    target = environment.layout(checkout_path, campaign, root=root)
    record_path = Path(str(target["record"]))
    checks: list[dict[str, object]] = []
    record: dict[str, object] | None = None
    read_failure: str | None = None
    try:
        record = receipts.read(record_path)
    except FileNotFoundError:
        read_failure = "record-missing"
    except (OSError, ValueError):
        read_failure = "record-unreadable"

    current_source = identity.source_identity(checkout_path, accept_enclosing=accept_enclosing)
    parent_package = identity.import_identity(package)
    parent_identity = identity.describe_running_interpreter()
    # Named, not resolved: on POSIX the resolved path of any virtual
    # environment's interpreter is the base interpreter, which would make two
    # different environments indistinguishable here.
    requested = os.path.abspath(str(interpreter)) if interpreter is not None else None

    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "campaign-environment-preflight",
        "campaign": campaign,
        "package": package,
        "observed_utc": identity.utc_now(),
        "checkout": str(checkout_path),
        "root": str(target["root"]),
        "directory": str(target["directory"]),
        "record_path": str(record_path),
        "record_read_failure": read_failure,
        "source": current_source,
        "parent": {"package": parent_package, "interpreter": parent_identity},
        "requested_interpreter": {"path": requested, "supplied": requested is not None},
        "expected": None,
        "child": None,
        "checks": checks,
        "verdict": UNKNOWN,
        "reasons": [],
        "measurement_allowed": False,
    }

    if record is None:
        checks.append(_check("environment-record", _FAIL,
                             "no usable campaign environment record", failure=read_failure))
        receipt["reasons"] = ["environment-not-provisioned"]
        return receipt

    expected_interpreter = record.get("interpreter")
    expected_venue = record.get("venv")
    expected_site = record.get("site_packages")
    expected_source = record.get("source_before") or {}
    expected_package = record.get("source_package") or {}
    installed = record.get("installed") or {}
    environment_identity = record.get("environment_identity") or {}
    receipt["expected"] = {
        "interpreter": expected_interpreter,
        "venv": expected_venue,
        "site_packages": expected_site,
        "prefix": environment_identity.get("prefix"),
        "executable_sha256": environment_identity.get("executable_sha256"),
        "revision": expected_source.get("revision"),
        "source_state": expected_source.get("state"),
        "dirty": expected_source.get("dirty"),
        "source_package": expected_package,
        "installed": installed,
        "provisioned_utc": record.get("created_utc"),
        "verdict": record.get("verdict"),
        "campaign": record.get("campaign"),
        "package": record.get("package"),
        "checkout": record.get("checkout"),
    }

    problems = environment.record_problems(record, campaign=campaign, checkout=checkout_path,
                                           package=package, target=target)
    if record.get("verdict") != "qualified":
        problems.append("record-unqualified")
    checks.append(_check(
        "environment-record",
        _PASS if not problems else _FAIL,
        "record binds to this campaign, checkout, package and layout" if not problems
        else "record does not bind to this environment",
        problems=sorted(set(problems)),
    ))
    if problems:
        receipt["verdict"] = UNQUALIFIED
        receipt["reasons"] = ["environment-record"]
        return receipt

    # The checkout must be the root of its own repository: a directory inside
    # another checkout answers revision queries with that repository's HEAD.
    exact_root = current_source.get("exact_checkout_root")
    if current_source["state"] == "enclosing-repository" or exact_root is False:
        checks.append(_check("checkout-root", _FAIL,
                             "the checkout is not the root of its own Git repository",
                             source_state=current_source["state"],
                             exact_checkout_root=exact_root,
                             top_level=current_source.get("top_level")))
    elif exact_root is not True:
        # Absent, unreadable or unavailable Git metadata is missing evidence, not
        # a contradiction: it must not be reported as an established identity.
        checks.append(_check("checkout-root", _UNKNOWN,
                             "the repository root could not be established",
                             source_state=current_source["state"],
                             failure=current_source.get("failure")))
    else:
        checks.append(_check("checkout-root", _PASS,
                             "the checkout is the root of its own Git repository",
                             exact_checkout_root=True))

    # The actual running parent.  `--interpreter` is never consulted here, and a
    # passing prefix alone is not enough: an interpreter path is compared as it
    # was named, and the digest of the invoked file must match the record too.
    parent_prefix = parent_identity.get("prefix")
    expected_prefix = environment_identity.get("prefix") or str(expected_venue)
    recorded_executable = environment_identity.get("executable_sha256")
    parent_prefix_ok = identity.same_environment(parent_prefix, expected_prefix)
    parent_path_ok = identity.same_invocation_path(parent_identity.get("executable"),
                                                   str(expected_interpreter))
    parent_digest_ok = (bool(recorded_executable)
                        and parent_identity.get("executable_sha256") == recorded_executable)
    parent_ok = parent_prefix_ok is True and parent_path_ok is True and parent_digest_ok
    if parent_ok:
        parent_detail = "the running parent is the recorded interpreter in the recorded environment"
    elif parent_prefix_ok is not True:
        parent_detail = "the running parent is not in the campaign environment"
    elif parent_path_ok is not True:
        parent_detail = "the running parent was invoked by a different interpreter path"
    elif not recorded_executable:
        parent_detail = "the record holds no executable digest to compare"
    else:
        parent_detail = "the running parent's executable digest differs from the record"
    checks.append(_check(
        "parent-interpreter",
        _PASS if parent_ok else _FAIL,
        parent_detail,
        parent_prefix=parent_prefix,
        expected_prefix=expected_prefix,
        parent_invocation_path=parent_identity.get("executable"),
        expected_interpreter=expected_interpreter,
        prefix_matches=parent_prefix_ok,
        invocation_path_matches=parent_path_ok,
        executable_digest_matches=parent_digest_ok,
        parent_executable_sha256=parent_identity.get("executable_sha256"),
        expected_executable_sha256=recorded_executable,
    ))

    if requested is None:
        checks.append(_check("requested-interpreter", _PASS,
                             "no child interpreter was requested", supplied=False))
    else:
        # The selection is verified by describing that interpreter, independently
        # of the parent: its own prefix, its own invocation path and its own
        # digest.  Comparing executable identity would accept another POSIX
        # virtual environment that shares the base interpreter.
        described_request = identity.interpreter_identity(requested)
        requested_prefix_ok = identity.same_environment(described_request.get("prefix"),
                                                        expected_prefix)
        requested_path_ok = identity.same_invocation_path(requested, str(expected_interpreter))
        requested_digest_ok = (bool(recorded_executable) and described_request.get("state") == "described"
                               and described_request.get("executable_sha256") == recorded_executable)
        selected = (described_request.get("state") == "described" and requested_prefix_ok is True
                    and requested_path_ok is True and requested_digest_ok)
        if selected:
            selection_detail = "the requested child interpreter is the recorded one"
        elif described_request.get("state") != "described":
            selection_detail = "the requested child interpreter could not be described"
        elif requested_prefix_ok is not True:
            selection_detail = "the requested child interpreter is in a different environment"
        elif requested_path_ok is not True:
            selection_detail = "the requested child interpreter path differs from the record"
        else:
            selection_detail = "the requested child interpreter's digest differs from the record"
        checks.append(_check(
            "requested-interpreter",
            _PASS if selected else _FAIL,
            selection_detail,
            supplied=True,
            selection_only=True,
            requested_state=described_request.get("state"),
            requested_prefix=described_request.get("prefix"),
            expected_prefix=expected_prefix,
            prefix_matches=requested_prefix_ok,
            invocation_path_matches=requested_path_ok,
            executable_digest_matches=requested_digest_ok,
        ))

    # Positive content match: location inside the environment is an observation,
    # not evidence that the same code ran.
    parent_inside = identity.contained(parent_package.get("origin"), str(expected_site))
    parent_code = parent_package.get("python_digest")
    recorded_code = installed.get("python_digest")
    parent_same = bool(recorded_code) and parent_code == recorded_code
    if parent_package.get("state") != "imported":
        checks.append(_check("parent-package", _FAIL, "the parent could not import the package",
                             parent_package_state=parent_package.get("state")))
    elif parent_package.get("name") != package:
        checks.append(_check("parent-package", _FAIL, "the parent imported a different package",
                             parent_package_name=parent_package.get("name")))
    elif not parent_same:
        checks.append(_check("parent-package", _FAIL,
                             "the parent's package content does not match the receipt",
                             inside_campaign_environment=parent_inside, same_code=False))
    else:
        checks.append(_check("parent-package", _PASS,
                             "the parent's package content matches the receipt",
                             inside_campaign_environment=parent_inside, same_code=True))

    recorded_revision = expected_source.get("revision")
    if current_source["state"] != "git" or expected_source.get("state") != "git" or not recorded_revision:
        checks.append(_check("source-revision", _UNKNOWN, "Git metadata was not available",
                             source_state=current_source["state"],
                             failure=current_source.get("failure")))
    elif current_source["revision"] != recorded_revision:
        checks.append(_check("source-revision", _FAIL, "Git HEAD moved since provisioning",
                             recorded_revision=recorded_revision,
                             observed_revision=current_source["revision"]))
    else:
        checks.append(_check("source-revision", _PASS, "Git HEAD matches the recorded revision",
                             revision=recorded_revision))

    current_package = None
    try:
        current_package = identity.package_digests(checkout_path / "src" / package)
    except (identity.IdentityError, OSError):
        current_package = None
    if current_package is None or not expected_package.get("tree_digest"):
        checks.append(_check("source-content", _UNKNOWN,
                             "the source package tree could not be digested"))
    elif current_package["tree_digest"] != expected_package.get("tree_digest"):
        checks.append(_check("source-content", _FAIL,
                             "checkout content changed since provisioning; the installation is stale",
                             recorded_tree_digest=expected_package.get("tree_digest"),
                             observed_tree_digest=current_package["tree_digest"]))
    else:
        checks.append(_check("source-content", _PASS,
                             "checkout content matches the installed source",
                             tree_digest=current_package["tree_digest"]))

    child = launch.probe(str(expected_interpreter), cwd=str(checkout_path), package=package,
                         timeout=timeout)
    report = child.get("report") or {}
    child_package = report.get("package") or {}
    receipt["child"] = child
    if not child.get("report_parsed"):
        for name in ("child-interpreter", "observed-origin", "observed-content", "child-isolation"):
            checks.append(_check(name, _FAIL, "the isolated child reported nothing parseable",
                                 exit_status=child.get("exit_status")))
    else:
        child_environment = identity.same_environment(report.get("prefix"), str(expected_venue))
        child_path = identity.same_invocation_path(report.get("interpreter"), str(expected_interpreter))
        child_digest = report.get("interpreter_sha256")
        recorded_digest = environment_identity.get("executable_sha256")
        digest_matches = bool(recorded_digest) and child_digest == recorded_digest
        if child_environment is not True:
            checks.append(_check("child-interpreter", _FAIL,
                                 "the child ran in a different environment",
                                 child_prefix=report.get("prefix"), expected_prefix=expected_venue))
        elif child_path is not True or not digest_matches:
            checks.append(_check("child-interpreter", _FAIL,
                                 "the child's interpreter path or digest differs from the receipt",
                                 invocation_path_matches=child_path,
                                 executable_digest_matches=digest_matches))
        else:
            checks.append(_check("child-interpreter", _PASS,
                                 "the child ran the recorded interpreter in the recorded environment",
                                 invocation_path_matches=True, executable_digest_matches=True))

        child_inside = identity.contained(child_package.get("origin"), str(expected_site))
        child_code = child_package.get("python_digest")
        child_same = bool(recorded_code) and child_code == recorded_code
        if child_package.get("state") != "imported":
            checks.append(_check("observed-origin", _FAIL, "the child could not import the package",
                                 child_package_state=child_package.get("state")))
        elif not child_same:
            checks.append(_check("observed-origin", _FAIL,
                                 "the child imported package content that does not match the receipt",
                                 inside_campaign_environment=child_inside, same_code=False))
        else:
            checks.append(_check("observed-origin", _PASS,
                                 "the child imported the recorded package content",
                                 inside_campaign_environment=child_inside, same_code=True))

        recorded_tree = installed.get("tree_digest")
        if not recorded_tree or not child_package.get("tree_digest"):
            checks.append(_check("observed-content", _UNKNOWN,
                                 "installed content was not recorded with a comparable digest"))
        else:
            same = child_package["tree_digest"] == recorded_tree
            checks.append(_check(
                "observed-content", _PASS if same else _FAIL,
                "installed content matches the provisioning receipt" if same
                else "installed content changed after provisioning",
                recorded_tree_digest=recorded_tree,
                observed_tree_digest=child_package.get("tree_digest")))

        isolated = bool(report.get("isolated"))
        checks.append(_check(
            "child-isolation", _PASS if isolated else _FAIL,
            "the child ran under -I" if isolated else "the child was not isolated; PYTHONPATH applies",
            pythonpath_present=report.get("pythonpath_present")))

    failures = [entry["check"] for entry in checks if entry["state"] == _FAIL]
    unknowns = [entry["check"] for entry in checks if entry["state"] == _UNKNOWN]
    if failures:
        receipt["verdict"] = UNQUALIFIED
        receipt["reasons"] = failures
    elif unknowns:
        receipt["verdict"] = UNKNOWN
        receipt["reasons"] = unknowns
    else:
        receipt["verdict"] = QUALIFIED
        receipt["reasons"] = []
    receipt["measurement_allowed"] = receipt["verdict"] == QUALIFIED
    return receipt
