"""Compare the requested identity with the observed one; refuse to qualify.

``preflight`` answers one question for a measurement about to be taken: do the
parent process, the isolated child and the checkout all belong to the same
source revision, and is that the revision this campaign recorded when it
provisioned?  Anything it cannot establish is ``unknown``, and anything that
disagrees is ``unqualified``.  Only a fully established match is
``qualified``, and only ``qualified`` may be reported as a campaign
measurement.

Each check is a small, named observation.  A verdict carries the failing check
names, so a report can say *why* it is not a measurement instead of omitting
it.
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
    "interpreter",
    "parent-origin",
    "source-revision",
    "source-content",
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
              timeout: int = 300) -> dict[str, object]:
    """Observe parent, child and checkout, and return a provenance receipt."""
    checkout_path = Path(checkout).resolve()
    target = environment.layout(checkout_path, campaign, root=root)
    record_path = Path(str(target["record"]))
    checks: list[dict[str, object]] = []
    record: dict[str, object] | None = None
    try:
        record = receipts.read(record_path)
    except (FileNotFoundError, ValueError):
        record = None

    current_source = identity.source_identity(checkout_path)
    parent_package = identity.import_identity(package)
    parent_interpreter = identity.interpreter_identity()

    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "campaign-environment-preflight",
        "campaign": campaign,
        "observed_utc": identity.utc_now(),
        "checkout": str(checkout_path),
        "root": str(target["root"]),
        "directory": str(target["directory"]),
        "record_path": str(record_path),
        "source": current_source,
        "parent": {"package": parent_package, "interpreter": parent_interpreter},
        "expected": None,
        "child": None,
        "checks": checks,
        "verdict": UNKNOWN,
        "reasons": [],
        "measurement_allowed": False,
    }

    if record is None:
        checks.append(_check("environment-record", _FAIL, "no campaign environment record"))
        receipt["verdict"] = UNKNOWN
        receipt["reasons"] = ["environment-not-provisioned"]
        return receipt

    observed_package = str(record.get("package") or package)
    expected_interpreter = record.get("interpreter")
    expected_site = record.get("site_packages")
    expected_source = record.get("source") or {}
    expected_package = record.get("source_package") or {}
    installed = record.get("installed") or {}
    receipt["expected"] = {
        "interpreter": expected_interpreter,
        "site_packages": expected_site,
        "revision": expected_source.get("revision"),
        "source_state": expected_source.get("state"),
        "dirty": expected_source.get("dirty"),
        "source_package": expected_package,
        "installed": installed,
        "provisioned_utc": record.get("created_utc"),
        "verdict": record.get("verdict"),
    }

    record_state = record.get("verdict")
    checks.append(_check(
        "environment-record",
        _PASS if record_state == "qualified" else _FAIL,
        "recorded environment is qualified" if record_state == "qualified"
        else "recorded environment is not qualified",
        recorded_verdict=record_state,
    ))

    # The parent must be the campaign's interpreter.  A shared interpreter can
    # import the campaign's code and still produce a child that does not.
    selected = str(Path(interpreter).resolve()) if interpreter is not None else None
    same_as_record = identity.matches(
        selected or str(parent_interpreter.get("executable")), str(expected_interpreter)
    )
    checks.append(_check(
        "interpreter",
        _PASS if same_as_record else _FAIL,
        "running interpreter is the recorded campaign interpreter" if same_as_record
        else "running interpreter is not the recorded campaign interpreter",
        running_in_campaign_environment=same_as_record,
        explicit_interpreter=selected is not None,
    ))

    # The parent's *interpreter* can be right while its imported package is not:
    # an exported PYTHONPATH precedes site-packages inside one interpreter.  The
    # rule is content, not location: the same bytes from the checkout are the
    # campaign's code, different bytes from anywhere else are not.
    parent_origin = parent_package.get("origin")
    if parent_package.get("state") != "imported":
        checks.append(_check("parent-origin", _FAIL, "the parent could not import the package",
                             parent_package_state=parent_package.get("state")))
    else:
        parent_inside = identity.contained(parent_origin, str(expected_site))
        recorded_code = installed.get("python_digest")
        parent_code = parent_package.get("python_digest")
        same_code = bool(recorded_code) and parent_code == recorded_code
        if parent_inside:
            checks.append(_check("parent-origin", _PASS, "the parent imported the campaign installation",
                                 inside_campaign_environment=True, same_code=same_code))
        elif same_code:
            checks.append(_check("parent-origin", _PASS,
                                 "the parent imported identical code from outside the environment",
                                 inside_campaign_environment=False, same_code=True))
        else:
            checks.append(_check("parent-origin", _FAIL,
                                 "the parent imported different code outside the campaign environment",
                                 inside_campaign_environment=False, same_code=False))

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

    source_matches = None
    try:
        current_package = identity.package_digests(checkout_path / "src" / observed_package)
    except (identity.IdentityError, OSError):
        current_package = None
    if current_package is None or not expected_package.get("tree_digest"):
        checks.append(_check("source-content", _UNKNOWN, "the source package tree could not be digested",
                             source_state=current_source["state"]))
    else:
        source_matches = current_package["tree_digest"] == expected_package.get("tree_digest")
        checks.append(_check(
            "source-content",
            _PASS if source_matches else _FAIL,
            "checkout content matches the installed source" if source_matches
            else "checkout content changed since provisioning; the installation is stale",
            recorded_tree_digest=expected_package.get("tree_digest"),
            observed_tree_digest=current_package["tree_digest"],
        ))

    child = launch.probe(str(expected_interpreter) if expected_interpreter else str(parent_interpreter["executable"]),
                         cwd=str(checkout_path), package=observed_package, timeout=timeout)
    report = child.get("report") or {}
    child_package = report.get("package") or {}
    receipt["child"] = child
    if not child.get("report_parsed"):
        checks.append(_check("observed-origin", _FAIL, "the isolated child reported nothing parseable",
                             exit_status=child.get("exit_status")))
        checks.append(_check("observed-content", _UNKNOWN, "no child observation"))
        checks.append(_check("child-isolation", _UNKNOWN, "no child observation"))
    else:
        in_environment = identity.contained(child_package.get("origin"), str(expected_site))
        if child_package.get("state") != "imported":
            checks.append(_check("observed-origin", _FAIL, "the isolated child could not import the package",
                                 child_package_state=child_package.get("state")))
        elif in_environment is not True:
            checks.append(_check("observed-origin", _FAIL,
                                 "the isolated child imported a package outside the campaign environment",
                                 inside_campaign_environment=in_environment))
        else:
            checks.append(_check("observed-origin", _PASS,
                                 "the isolated child imported from the campaign environment",
                                 inside_campaign_environment=True))
        recorded_installed_digest = installed.get("tree_digest")
        if not recorded_installed_digest or not child_package.get("tree_digest"):
            checks.append(_check("observed-content", _UNKNOWN,
                                 "installed content was not recorded with a comparable digest"))
        else:
            same = child_package["tree_digest"] == recorded_installed_digest
            checks.append(_check(
                "observed-content",
                _PASS if same else _FAIL,
                "installed content matches the provisioning receipt" if same
                else "installed content changed after provisioning",
                recorded_tree_digest=recorded_installed_digest,
                observed_tree_digest=child_package.get("tree_digest"),
            ))
        isolated = bool(report.get("isolated"))
        checks.append(_check(
            "child-isolation",
            _PASS if isolated else _FAIL,
            "the child ran under -I" if isolated else "the child was not isolated; PYTHONPATH applies",
            pythonpath_present=report.get("pythonpath_present"),
        ))

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
