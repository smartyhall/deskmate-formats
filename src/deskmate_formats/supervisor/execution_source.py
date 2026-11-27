"""Which source a production launch executes, and the binding that proves it.

The Supervisor starts children.  Before this module, the *interpreter* those
children ran was recorded but the *source* they would import was not, and two
facts were silently conflated:

* ``sys.executable`` is the controller's interpreter.  A child launched with it
  imports the installed ``deskmate_formats``, which is the controller's pinned
  implementation — not the accepted checkout the task named.
* ``-I`` discards ``PYTHONPATH``.  A launch that set ``PYTHONPATH`` to the
  accepted checkout's ``src`` and then passed ``-I`` did not import that
  checkout at all; the variable was decorative.

The consequence was a publication audit that could report a verdict about the
installed wheel while its receipt named the accepted workspace.  Removing
``-I`` would trade one defect for a worse one: the child would then read
``PYTHONPATH`` and the user site directory from the ambient environment.

So there are two mechanisms here, and they are deliberately separate:

``binding``
    a record of the intended source: the accepted checkout's revision and
    package digests, and the campaign-owned interpreter that will run it, with
    its own prefix, invocation path and executable digest.  A plan freezes this,
    and :func:`verify_execution` re-establishes every field before dispatch.
``bootstrap``
    a reviewed, stdlib-only launcher passed as ``python -I -c <bootstrap>``.
    It inserts the bound ``src`` at the head of ``sys.path`` (the explicit
    alternative to an ignored ``PYTHONPATH``), imports the package, and checks
    both the import origin and the Python content digest *before* running the
    reviewed target.  A mismatch exits ``78`` and the procedure never runs.
    It also redirects that launch's bytecode cache to a fresh private
    directory and refuses sourceless bytecode in the bound tree: ``-I`` does
    not stop the import system from *reading* a ``.pyc``, and the content
    digest covers source only, so a stale cache could otherwise execute old
    code while the digest of the new source passed.

The bootstrap is controller code: it is fixed here, digested into the plan, and
contains no caller-supplied behaviour.  The target it runs is workspace code,
and that is exactly what the binding makes attributable.

``LAUNCH_SITES`` is the inventory required by issue #207.  Each entry names the
caller, how the vector is constructed, which source class the launch is
intended to execute, how the source is actually resolved, what the receipt
records, and what happens when the binding cannot be established.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from deskmate_formats.campaign_env import environment as campaign_environment
from deskmate_formats.campaign_env import identity as campaign_identity
from deskmate_formats.campaign_env import receipts as campaign_receipts

SCHEMA_VERSION = 1
PACKAGE = "deskmate_formats"
SOURCE_PACKAGE = ("src", PACKAGE)

#: A launch whose code is the controller's pinned implementation (class A).
CONTROLLER = "controller"
#: A launch whose code is the accepted task workspace (class B).
WORKSPACE = "workspace"
#: A launch of an immutable external tool (class C).
EXTERNAL = "external"
#: A launch whose source cannot be established before it runs (class D).
UNRESOLVED = "unresolved"

SOURCES = (CONTROLLER, WORKSPACE, EXTERNAL, UNRESOLVED)

#: The reviewed target refused its binding.  Distinct from any ordinary exit so
#: a mismatch can never be read as a successful measurement.
REFUSED_EXIT = 78

BOOTSTRAP = '''\
"""Insert one bound checkout at the head of sys.path, verify it, then run."""
import hashlib
import json
import os
import runpy
import shutil
import sys
import tempfile


def _write(path, value):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _python_digest(directory):
    entries = []
    for current, names, files in os.walk(directory):
        names[:] = sorted(name for name in names if name != "__pycache__")
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(current, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as stream:
                data = stream.read()
            entries.append((os.path.relpath(path, directory).replace(os.sep, "/"),
                            len(data), hashlib.sha256(data).hexdigest()))
    digest = hashlib.sha256()
    for name, size, value in sorted(entries):
        digest.update((name + "\\0" + str(size) + "\\0" + value + "\\n").encode("utf-8"))
    return digest.hexdigest()


def _outside(path, root):
    if not path:
        return False
    try:
        real = os.path.realpath(path)
        return os.path.commonpath([real, os.path.realpath(root)]) != os.path.realpath(root)
    except ValueError:
        # Different drives: provably not inside the bound source.
        return True


def _bytecode(root, checkout):
    """Count ignored caches and name bytecode that no source can account for."""
    caches, sourceless = 0, []
    for current, names, files in os.walk(root):
        for name in list(names):
            if name == "__pycache__":
                names.remove(name)
                try:
                    caches += len(os.listdir(os.path.join(current, name)))
                except OSError:
                    pass
        for name in sorted(files):
            if not name.endswith((".pyc", ".pyo")):
                continue
            source = os.path.join(current, name.rsplit(".", 1)[0] + ".py")
            if not os.path.exists(source):
                sourceless.append(os.path.relpath(os.path.join(current, name), root))
    # The checkout root is also on sys.path, for ``src.*`` imports. Only a
    # top-level bytecode file can shadow a module there, so it alone is checked.
    try:
        top = sorted(os.listdir(checkout))
    except OSError:
        top = []
    for name in top:
        if name.endswith((".pyc", ".pyo")) and not os.path.exists(
                os.path.join(checkout, name.rsplit(".", 1)[0] + ".py")):
            sourceless.append(name)
    return caches, sourceless


root = os.path.abspath(sys.argv[1])
expected = sys.argv[2]
report_path = sys.argv[3]
mode = sys.argv[4]
target = sys.argv[5]
arguments = sys.argv[6:]
checkout = os.path.dirname(root)
# ``-I`` ignores PYTHON* variables, including PYTHONDONTWRITEBYTECODE, so the
# checkout must be protected from bytecode caches explicitly. A checkpoint that
# dirtied the tree it was validating would be a different attempt.
sys.dont_write_bytecode = True
# ``-I`` does not stop the import system from *reading* a .pyc, and the content
# digest covers source files only. A cache whose stored size and timestamp still
# match can therefore execute old code while the digest of the new source
# passes. A fresh, empty, private cache prefix makes every import in this launch
# compile from the bound source, and nothing is written back.
try:
    private_cache = tempfile.mkdtemp(prefix="deskmate-source-")
    cache_empty = not os.listdir(private_cache)
except OSError:
    private_cache, cache_empty = None, False
if cache_empty:
    sys.pycache_prefix = private_cache
# The package tree, and the checkout root that repository tests import as
# ``src.*``. Both are the bound checkout; neither is ambient.
sys.path.insert(0, root)
sys.path.insert(1, checkout)
caches, sourceless = _bytecode(root, checkout)
report = {
    "schema_version": 1,
    "role": "workspace-child",
    "state": "unverified",
    "isolated": bool(sys.flags.isolated),
    "pythonpath_present": "PYTHONPATH" in os.environ,
    "interpreter": os.path.abspath(sys.executable) if sys.executable else None,
    "prefix": sys.prefix,
    "bound_root": root,
    "bound_checkout": checkout,
    "expected_python_digest": expected,
    "dont_write_bytecode": bool(sys.dont_write_bytecode),
    "pycache_prefix": private_cache,
    "pycache_empty": bool(cache_empty),
    "pycache_redirected": bool(cache_empty) and sys.pycache_prefix == private_cache,
    "pycache_outside_root": _outside(private_cache, root),
    "bytecode_caches": caches,
    "sourceless_bytecode": sourceless,
}
try:
    if not report["pycache_redirected"] or not report["pycache_outside_root"]:
        report["state"] = "bytecode-cache-unavailable"
    elif sourceless:
        report["state"] = "sourceless-bytecode"
    else:
        try:
            import deskmate_formats
            origin = os.path.realpath(os.path.dirname(deskmate_formats.__file__))
            inside = os.path.commonpath([origin, os.path.realpath(root)]) == os.path.realpath(root)
            observed = _python_digest(origin)
            report.update(origin=origin, python_digest=observed, origin_inside_root=inside)
            if not inside:
                report["state"] = "origin-outside-bound-source"
            elif observed != expected:
                report["state"] = "content-mismatch"
            else:
                report["state"] = "bound"
        except (ImportError, OSError, ValueError):
            report["state"] = "package-not-importable"
    _write(report_path, report)
    if report["state"] != "bound":
        raise SystemExit(78)
    sys.argv = [target, *arguments]
    if mode == "module":
        runpy.run_module(target, run_name="__main__", alter_sys=True)
    elif mode == "code":
        exec(compile(target, "<bound-workspace-code>", "exec"), {"__name__": "__main__"})
    else:
        raise SystemExit(79)
finally:
    if private_cache:
        shutil.rmtree(private_cache, ignore_errors=True)
'''


class ExecutionSourceError(ValueError):
    """The launch could not be bound to a positively identified source.

    ``code`` is a short publishable slug; ``detail`` is local diagnostic text and
    may name a path, so it is never placed in a public projection.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code + (": " + detail if detail else ""))


@dataclass(frozen=True, slots=True)
class LaunchSite:
    """One audited production launch site.

    ``intended`` is the source class the launch is *for*; ``resolution`` is how
    the source is actually resolved at run time.  Where those disagreed before
    issue #207 the entry says so in ``correction``.
    """

    identifier: str
    caller: str
    construction: str
    intended: str
    resolution: str
    receipt: str
    failure: str
    correction: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


#: The production inventory.  Test fixtures and experimental tooling are listed
#: separately in ``NON_PRODUCTION_SITES`` so that their absence from the
#: production table is a visible decision rather than an omission.
LAUNCH_SITES = (
    LaunchSite(
        "procedures.hash-files", "procedures._build_hash",
        "selected interpreter + -I -c <reviewed HASH_SCRIPT> <limits> <paths>",
        CONTROLLER,
        "fixed script text from this module; reads accepted-checkout files as data",
        "plan.execution (controller implementation digest, interpreter identity)",
        "refused before preparation if a named input cannot be bound"),
    LaunchSite(
        "procedures.fixture-compare", "procedures._build_compare",
        "selected interpreter + -I -c <reviewed COMPARE_SCRIPT> <limits> <pair>",
        CONTROLLER,
        "fixed script text from this module; reads two accepted-checkout files",
        "plan.execution (controller implementation digest, interpreter identity)",
        "refused before preparation if a named input cannot be bound"),
    LaunchSite(
        "procedures.repository-audit", "procedures._build_audit",
        "campaign interpreter + -I -c <bootstrap> <src> <digest> <report> code <AUDIT_SCRIPT>",
        WORKSPACE,
        "bootstrap inserts the bound src, verifies import origin and Python digest, then imports "
        "deskmate_formats.supervisor.repository_audit from that checkout",
        "plan.execution (workspace revision/digests, environment record, child report)",
        "refused at preparation without a qualified environment; exit 78 if the child resolves "
        "another implementation",
        "was -I -c AUDIT_SCRIPT with sys.executable and PYTHONPATH: -I ignored the path and the "
        "shared installation executed"),
    LaunchSite(
        "procedures.portable-tests", "procedures._build_portable_tests",
        "campaign interpreter + -I -c <bootstrap> <src> <digest> <report> module unittest ...",
        WORKSPACE,
        "bootstrap inserts the bound src, verifies it, then runpy runs unittest discovery from the "
        "accepted working directory",
        "plan.execution plus child report",
        "refused at preparation without a qualified environment; exit 78 before any test runs",
        "was -m unittest with PYTHONPATH, so the package came from whatever the interpreter had "
        "installed"),
    LaunchSite(
        "procedures.package-build", "procedures._build_package",
        "campaign interpreter + -I -c <bootstrap> <src> <digest> <report> module build "
        "--wheel --no-isolation --outdir <artifacts>",
        WORKSPACE,
        "bootstrap binds the checkout, then the installed build frontend imports it",
        "plan.execution plus child report and artifact hashes",
        "refused at preparation without a qualified environment; a build failure is a failed outcome",
        "was -m build with PYTHONPATH"),
    LaunchSite(
        "procedures.reuse-lint", "procedures._build_reuse",
        "selected interpreter + -m reuse lint",
        EXTERNAL,
        "REUSE from the selected interpreter's installation; reads checkout files only",
        "plan.execution (interpreter identity; no repository code executes)",
        "a missing tool is a non-zero exit, never a passed check"),
    LaunchSite(
        "workspace.test-step", "workspace._step_argv",
        "campaign interpreter + -I -c <bootstrap> ... module unittest <profile arguments>",
        WORKSPACE,
        "bootstrap binds and verifies the disposable S3 workspace before discovery starts",
        "validation[] step receipt (argv, interpreter identity, fresh per-step child report)",
        "checkpoint records a failed step and blocks; never retried"),
    LaunchSite(
        "workspace.publication-audit", "workspace._step_argv",
        "campaign interpreter + -I -c <bootstrap> ... code <AUDIT>",
        WORKSPACE,
        "bootstrap binds and verifies the S3 workspace, then the audit runs against Path.cwd()",
        "validation[] step receipt (fresh per-step child report)",
        "exit 78 is a failed validation step and blocks the checkpoint",
        "was [sys.executable, -I, -c, AUDIT] with PYTHONPATH: the shared wheel was audited and the "
        "receipt named the workspace"),
    LaunchSite(
        "workspace.reuse-step", "workspace._step_argv",
        "controller interpreter + -m reuse lint",
        EXTERNAL,
        "REUSE from the controller's installation; it reads workspace files and executes no "
        "repository code",
        "validation[] step receipt",
        "non-zero exit blocks the checkpoint"),
    LaunchSite(
        "driver.synthetic-peer", "driver.prepare",
        "sys.executable + -I -m deskmate_formats.supervisor.synthetic_peer <evidence> <mode>",
        CONTROLLER,
        "the controller's own installed package, verified by driver file hashes",
        "plan.argv, plan.executable_sha256, driver implementation hashes",
        "refused at run if the executable or implementation digest changed"),
    LaunchSite(
        "driver.codex-app-server", "driver.prepare / protocol.AppServer",
        "reviewed native executable + app-server --listen stdio://",
        EXTERNAL,
        "hash-pinned native executable; no Python source is resolved",
        "plan.executable_sha256, native pin",
        "refused before launch on any pin or version mismatch"),
    LaunchSite(
        "console-entry-points", "operator shell",
        "deskmate-supervisor-* / deskmate-campaign-env from PATH",
        UNRESOLVED,
        "the operator's interpreter and PATH decide; a plan does not bind the console script",
        "the plan binds its own interpreter and implementation after it starts",
        "operations that need a bound source refuse until an environment is selected",
    ),
)

#: Not production execution: they either create the identity evidence or run
#: only inside tests, so binding them to a task workspace would be a category
#: error.  Listed so the boundary is reviewable.
NON_PRODUCTION_SITES = (
    ("campaign_env.identity", "describes an interpreter under -I; launches no repository code"),
    ("campaign_env.environment", "creates a venv and runs pip from the bootstrap; provisioning only"),
    ("campaign_env.launch", "the probe runner; it is the measurement, not a task launch"),
    ("supervisor.task_git / workspace.git", "pinned Git binary over reviewed objects"),
    ("deterministic._git", "read-only Git identity helper"),
    ("tests/**", "fixtures and synthetic checks; never a production receipt"),
    ("tools/campaign_environment_experiment.py", "one-off laboratory instrumentation"),
)


def bootstrap_digest() -> str:
    return sha256(BOOTSTRAP.encode("utf-8")).hexdigest()


def inventory() -> dict[str, object]:
    """The publishable inventory: production launches and the excluded sites."""
    return {
        "schema_version": SCHEMA_VERSION,
        "package": PACKAGE,
        "bootstrap_sha256": bootstrap_digest(),
        "sources": list(SOURCES),
        "sites": [site.as_dict() for site in LAUNCH_SITES],
        "non_production": [{"site": name, "reason": reason}
                           for name, reason in NON_PRODUCTION_SITES],
    }


def _package_tree(working: "str | os.PathLike[str]") -> Path:
    return Path(working) / SOURCE_PACKAGE[0] / SOURCE_PACKAGE[1]


def bind_workspace(working: "str | os.PathLike[str]", *, revision: "str | None" = None,
                   report_path: "str | os.PathLike[str] | None" = None) -> dict[str, object]:
    """Bind a checkout's revision and Python content; refuse anything unproven.

    ``revision`` is the revision the caller intends to execute (for an accepted
    task, the commit the plan was prepared for).  A checkout at another revision
    is not the same source and is refused rather than noted.
    """
    working_path = Path(working)
    if not working_path.is_dir():
        raise ExecutionSourceError("workspace-missing", str(working_path))
    source = campaign_identity.source_identity(working_path)
    if source["state"] != "git":
        raise ExecutionSourceError("workspace-source-unknown", str(source["state"]))
    if revision is not None and source["revision"] != revision:
        raise ExecutionSourceError("workspace-revision-mismatch",
                                   f"{source['revision']} != {revision}")
    package = _package_tree(working_path)
    try:
        digests = campaign_identity.package_digests(package)
    except (campaign_identity.IdentityError, OSError):
        raise ExecutionSourceError("workspace-package-unreadable", str(package)) from None
    return {
        "path": str(working_path.resolve()),
        "src": str(package.parent.resolve()),
        "revision": source["revision"],
        "branch": source["branch"],
        "dirty": source["dirty"],
        "package": {
            "name": PACKAGE,
            "origin": str(package.resolve()),
            "tree_digest": digests["tree_digest"],
            "python_digest": digests["python_digest"],
            "file_count": digests["file_count"],
        },
        "report_path": str(report_path) if report_path is not None else None,
    }


def select_environment(campaign: str, checkout: "str | os.PathLike[str]", *,
                       root: "str | os.PathLike[str] | None" = None,
                       revision: "str | None" = None) -> dict[str, object]:
    """Read a campaign environment record and prove it describes this interpreter.

    This consumes the campaign-environment mechanism rather than provisioning a
    second one: it uses that module's layout, ownership record validation,
    interpreter description and receipt digests.  It never creates, repairs or
    replaces an environment.
    """
    try:
        target = campaign_environment.layout(checkout, campaign, root=root)
    except campaign_environment.CampaignEnvironmentError as error:
        raise ExecutionSourceError("environment-selection-invalid", error.code) from None
    record_path = Path(str(target["record"]))
    try:
        record = campaign_receipts.read(record_path)
    except FileNotFoundError:
        raise ExecutionSourceError("environment-record-missing", str(record_path)) from None
    except (OSError, ValueError):
        raise ExecutionSourceError("environment-record-unreadable", str(record_path)) from None
    if record.get("verdict") != "qualified":
        raise ExecutionSourceError("environment-not-qualified", str(record.get("verdict")))
    problems = campaign_environment.record_problems(
        record, campaign=campaign, checkout=checkout, package=PACKAGE, target=target)
    if problems:
        raise ExecutionSourceError("environment-record-mismatch", ",".join(sorted(set(problems))))
    interpreter = record.get("interpreter")
    described = campaign_identity.interpreter_identity(interpreter)
    if described.get("state") != "described":
        raise ExecutionSourceError("environment-interpreter-unavailable", str(described.get("state")))
    recorded_identity = record.get("environment_identity") or {}
    checks = {
        "prefix_matches": campaign_identity.same_environment(
            described.get("prefix"), record.get("venv")),
        "invocation_path_matches": campaign_identity.same_invocation_path(
            described.get("executable"), interpreter),
        "executable_digest_matches": bool(recorded_identity.get("executable_sha256"))
        and described.get("executable_sha256") == recorded_identity.get("executable_sha256"),
        "site_packages_inside_environment": campaign_identity.contained(
            described.get("site_packages"), record.get("venv")),
    }
    if not all(value is True for value in checks.values()):
        raise ExecutionSourceError("environment-interpreter-mismatch",
                                   ",".join(name for name, value in checks.items() if value is not True))
    source = record.get("source_before") or {}
    if source.get("state") != "git" or not source.get("revision"):
        raise ExecutionSourceError("environment-source-unknown", str(source.get("state")))
    if revision is not None and source["revision"] != revision:
        raise ExecutionSourceError("environment-source-mismatch",
                                   f"{source['revision']} != {revision}")
    return {
        "campaign": campaign,
        "checkout": os.path.abspath(str(checkout)),
        "root": str(target["root"]),
        "record_path": str(record_path),
        "record_sha256": campaign_receipts.file_digest(record_path),
        "interpreter": interpreter,
        "interpreter_sha256": recorded_identity.get("executable_sha256"),
        "prefix": described.get("prefix"),
        "site_packages": record.get("site_packages"),
        "revision": source["revision"],
        "source_package": record.get("source_package") or {},
        "verdict": record.get("verdict"),
        "version": described.get("version"),
        "implementation": described.get("implementation"),
        "checks": checks,
    }


def controller_execution(*, interpreter: "str | os.PathLike[str] | None",
                         implementation: "dict[str, object]") -> dict[str, object]:
    """Bind the controller's own implementation and the interpreter that runs it.

    The code is the reviewed script text in :mod:`procedures`; the plan's
    ``implementation`` digest covers it.  The interpreter is a runtime fact and
    is recorded as such, never attributed to the task workspace.
    """
    described = campaign_identity.interpreter_identity(
        None if interpreter is None else str(interpreter))
    if described.get("state") != "described":
        raise ExecutionSourceError("controller-interpreter-unavailable",
                                   str(described.get("state")))
    package = campaign_identity.import_identity(PACKAGE)
    if package.get("state") != "imported":
        raise ExecutionSourceError("controller-package-unavailable", str(package.get("state")))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": CONTROLLER,
        "executes": "reviewed-supervisor-script",
        "package": {"name": PACKAGE, "origin": package.get("origin"),
                    "python_digest": package.get("python_digest"),
                    "tree_digest": package.get("tree_digest")},
        "implementation_sha256": implementation["sha256"],
        "interpreter": {
            "path": described.get("executable"),
            "sha256": described.get("executable_sha256"),
            "prefix": described.get("prefix"),
            "version": described.get("version"),
            "implementation": described.get("implementation"),
        },
    }


def tool_execution(*, interpreter: "str | os.PathLike[str]", tool: str | None) -> dict[str, object]:
    """Bind an installed third-party tool and the interpreter that provides it.

    No repository code executes, so there is no workspace claim to make: the
    tool's own module origin is already bound separately by the plan's module
    binding, and only the interpreter is selected here.
    """
    described = campaign_identity.interpreter_identity(str(interpreter))
    if described.get("state") != "described":
        raise ExecutionSourceError("tool-interpreter-unavailable", str(described.get("state")))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": EXTERNAL,
        "executes": "installed-tool",
        "tool": tool,
        "interpreter": {
            "path": described.get("executable"),
            "sha256": described.get("executable_sha256"),
            "prefix": described.get("prefix"),
            "version": described.get("version"),
            "implementation": described.get("implementation"),
        },
    }


def workspace_execution(working: "str | os.PathLike[str]", *,
                        environment: dict[str, object],
                        revision: "str | None" = None,
                        report_path: "str | os.PathLike[str]") -> dict[str, object]:
    """Bind the accepted checkout, the campaign interpreter and the bootstrap."""
    workspace = bind_workspace(working, revision=revision, report_path=report_path)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": WORKSPACE,
        "executes": "accepted-checkout",
        "workspace": workspace,
        "environment": environment,
        "bootstrap": {
            "script_sha256": bootstrap_digest(),
            "isolation": "-I",
            "refused_exit": REFUSED_EXIT,
            "report_path": workspace["report_path"],
        },
    }


def verify_execution(execution: object, *, allow_workspace_change: bool = False) -> None:
    """Re-establish every bound identity, or refuse the launch.

    Called after the plan is read and before the child is spawned, so a source
    change, a replaced interpreter or a rewritten environment record between
    preparation and dispatch stops the attempt instead of being reported later.

    ``allow_workspace_change`` exists for exactly one caller: the S3 checkpoint
    runs after authorized edits, so its content digests must be re-derived while
    the interpreter, the environment record and the base revision are still
    proven unchanged.  It never relaxes those three.
    """
    if type(execution) is not dict or execution.get("schema_version") != SCHEMA_VERSION:
        raise ExecutionSourceError("execution-binding-missing")
    source = execution.get("source")
    if source in (CONTROLLER, EXTERNAL):
        if source == CONTROLLER and execution.get("implementation_sha256") is None:
            raise ExecutionSourceError("controller-implementation-unbound")
        interpreter = execution.get("interpreter") or {}
        described = campaign_identity.interpreter_identity(interpreter.get("path"))
        if described.get("state") != "described":
            raise ExecutionSourceError("controller-interpreter-changed",
                                       str(described.get("state")))
        if (described.get("executable_sha256") != interpreter.get("sha256")
                or campaign_identity.same_environment(
                    described.get("prefix"), interpreter.get("prefix")) is not True):
            raise ExecutionSourceError("controller-interpreter-changed")
        return
    if source != WORKSPACE:
        raise ExecutionSourceError("execution-source-unknown", str(source))
    environment = execution.get("environment") or {}
    observed = select_environment(str(environment.get("campaign")),
                                  str(environment.get("checkout")),
                                  root=environment.get("root"))
    for name in ("record_sha256", "interpreter", "interpreter_sha256", "prefix", "revision"):
        if observed.get(name) != environment.get(name):
            raise ExecutionSourceError("environment-changed-after-preparation", name)
    workspace = execution.get("workspace") or {}
    observed_workspace = bind_workspace(workspace.get("path"), revision=workspace.get("revision"),
                                        report_path=workspace.get("report_path"))
    if allow_workspace_change:
        if (observed_workspace["path"] != workspace.get("path")
                or observed_workspace["src"] != workspace.get("src")
                or observed_workspace["revision"] != workspace.get("revision")):
            raise ExecutionSourceError("workspace-changed-after-preparation")
    elif observed_workspace != workspace:
        raise ExecutionSourceError("workspace-changed-after-preparation")
    if (execution.get("bootstrap") or {}).get("script_sha256") != bootstrap_digest():
        raise ExecutionSourceError("bootstrap-changed")


def rebind_workspace(execution: dict[str, object],
                     working: "str | os.PathLike[str]") -> dict[str, object]:
    """Re-derive the content half of a workspace binding from the current tree.

    Used by the checkpoint after authorized edits.  The revision, the path and
    the environment come from the frozen binding, not from the caller, so this
    cannot be used to point an attempt at another checkout or another
    interpreter.
    """
    if execution.get("source") != WORKSPACE:
        raise ExecutionSourceError("workspace-binding-required", str(execution.get("source")))
    workspace = execution.get("workspace") or {}
    refreshed = bind_workspace(working, revision=workspace.get("revision"),
                               report_path=workspace.get("report_path"))
    updated = dict(execution)
    updated["workspace"] = refreshed
    return updated


def step_execution(execution: dict[str, object],
                   report_path: "str | os.PathLike[str]") -> dict[str, object]:
    """A per-launch view of a workspace binding with its own child report path.

    A checkpoint runs several steps against one frozen binding.  Sharing one
    report path meant a step whose child wrote nothing read the preceding step's
    report and inherited its verification.  Each step therefore launches with a
    path no earlier step used, and the caller removes any file left there by an
    earlier attempt before the child starts.
    """
    if execution.get("source") != WORKSPACE:
        raise ExecutionSourceError("workspace-binding-required", str(execution.get("source")))
    if not str(report_path):
        raise ExecutionSourceError("child-report-path-required")
    updated = dict(execution)
    updated["bootstrap"] = dict(execution.get("bootstrap") or {},
                                report_path=str(report_path))
    return updated


def bound_argv(execution: dict[str, object], *, mode: str, target: str,
               arguments: "list[str] | tuple[str, ...]" = ()) -> list[str]:
    """Assemble ``interpreter -I -c bootstrap ... mode target``."""
    if execution.get("source") != WORKSPACE:
        raise ExecutionSourceError("workspace-binding-required", str(execution.get("source")))
    if mode not in ("module", "code"):
        raise ExecutionSourceError("invalid-bootstrap-mode", str(mode))
    workspace = execution["workspace"]
    return [str(execution["environment"]["interpreter"]), "-I", "-c", BOOTSTRAP,
            str(workspace["src"]), str(workspace["package"]["python_digest"]),
            str(execution["bootstrap"]["report_path"]), mode, str(target),
            *(str(argument) for argument in arguments)]


def read_child_report(execution: dict[str, object]) -> dict[str, object]:
    """Read and judge the child's own account of what it imported.

    A report that is absent, unparseable or disagrees with the binding is not
    evidence of a qualified result: the caller must treat the attempt as failed
    rather than as a successful measurement of unknown provenance.
    """
    path = Path(str((execution.get("bootstrap") or {}).get("report_path")))
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"verified": False, "state": "report-missing", "path": str(path)}
    if type(report) is not dict:
        return {"verified": False, "state": "report-invalid", "path": str(path)}
    workspace = execution.get("workspace") or {}
    environment = execution.get("environment") or {}
    checks = {
        "state_bound": report.get("state") == "bound",
        "isolated": report.get("isolated") is True,
        "origin_inside_bound_source": report.get("origin_inside_root") is True,
        "python_digest_matches": (report.get("python_digest")
                                  == (workspace.get("package") or {}).get("python_digest")),
        "interpreter_matches": campaign_identity.same_invocation_path(
            report.get("interpreter"), environment.get("interpreter")),
        # A cached .pyc is not covered by the source digest, so a launch that
        # could have read one has not proven which code ran.
        "bytecode_caches_bypassed": report.get("pycache_redirected") is True,
        "bytecode_prefix_outside_source": report.get("pycache_outside_root") is True,
        "sourceless_bytecode_absent": report.get("sourceless_bytecode") == [],
    }
    return {
        "verified": all(value is True for value in checks.values()),
        "state": report.get("state"),
        "path": str(path),
        "checks": checks,
        "isolated": report.get("isolated"),
        "pythonpath_present": report.get("pythonpath_present"),
        "origin": report.get("origin"),
        "python_digest": report.get("python_digest"),
        "interpreter": report.get("interpreter"),
        "prefix": report.get("prefix"),
        "bytecode_caches": report.get("bytecode_caches"),
        "sourceless_bytecode": report.get("sourceless_bytecode"),
    }


def main(argv: "list[str] | None" = None) -> int:
    """Print the inventory, so a reviewer need not read this file to audit it."""
    import argparse

    parser = argparse.ArgumentParser(prog="python -m deskmate_formats.supervisor.execution_source")
    parser.add_argument("--json", action="store_true", help="emit the inventory as JSON")
    parser.parse_args(sys.argv[1:] if argv is None else argv)
    print(json.dumps(inventory(), indent=2, sort_keys=True))
    return 0


def public_execution(execution: object) -> object:
    """Project a binding so no private lab path is published.

    The digest fields are the evidence; the paths are not.  Unknown keys are
    kept only when they are neither a path field nor a string containing one.
    """
    if isinstance(execution, dict):
        return {name: public_execution(value) for name, value in execution.items()
                if name not in ("report_path",)}
    if isinstance(execution, list):
        return [public_execution(item) for item in execution]
    if isinstance(execution, str):
        return "<path>" if os.path.isabs(execution) else execution
    return execution


if __name__ == "__main__":
    raise SystemExit(main())
