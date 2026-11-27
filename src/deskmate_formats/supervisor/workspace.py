"""Disposable S3 clones, actual validation and single-use local checkpoints.

Cooperating-owner custody, not OS confinement. Never pushes or repairs a workspace.
"""

from hashlib import sha256
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from uuid import uuid4

from deskmate_formats.observer._private_storage import _is_redirect, storage_directory
from . import execution_source
from .driver import DriverError, digest, write_record
from .task_manifest import development_path

#: ``(module, arguments)`` for one reviewed discovery scope. The module is run by
#: the bound source bootstrap, never by an ambient interpreter search path.
TEST_PROFILES = {
    "portable-full": ("unittest", ["discover", "-s", "tests/portable", "-v"]),
    "synthetic-unit": ("unittest", ["discover", "-s", "tests/portable", "-p",
                                    "test_s3_sample.py", "-v"]),
}
# Supervisor-owned limits, pinned by the exact plan's implementation hashes.
COMMAND_TIMEOUTS = {"test-portable-full": 1800}
DEFAULT_COMMAND_TIMEOUT = 600
AUDIT = ("from pathlib import Path; from deskmate_formats.supervisor import repository_audit as a; "
         "a.ROOT=Path.cwd(); print(a.audit())")


def environment():
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="",
               GIT_AUTHOR_NAME="DeskMate Supervisor", GIT_AUTHOR_EMAIL="supervisor@example.invalid",
               GIT_COMMITTER_NAME="DeskMate Supervisor", GIT_COMMITTER_EMAIL="supervisor@example.invalid",
               PYTHONDONTWRITEBYTECODE="1")
    # No PYTHONPATH: an isolated workspace launch inserts and verifies the bound
    # checkout explicitly. Exporting a search path that -I discards was the
    # defect, and exporting one that -I honours would be an ambient source.
    return env


def git(workspace, *args, data=None):
    result = subprocess.run([shutil.which("git"), "--no-replace-objects", "--literal-pathspecs",
                             "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
                             "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
                            cwd=workspace, env=environment(), input=data, capture_output=True, timeout=30)
    if result.returncode:
        raise DriverError("workspace Git operation failed; preserve workspace for inspection")
    return result.stdout


def inventory(workspace, *, metadata=False):
    base = Path(workspace) / ".git" if metadata else Path(workspace)
    if _is_redirect(base.lstat()) or not base.is_dir():
        raise DriverError("workspace metadata directory redirected")
    result = {}
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if not metadata and rel.parts[0] == ".git":
            continue
        info = path.lstat()
        if _is_redirect(info) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise DriverError("workspace redirect or special file refused")
        if path.is_file():
            if info.st_nlink != 1:
                raise DriverError("workspace hardlink refused")
            result[rel.as_posix()] = {"sha256": digest(path), "size": info.st_size,
                                      "executable": bool(info.st_mode & 0o111) if os.name != "nt" else False}
    return result


def create_workspace(source, commit, parent, binding, development):
    """No shared Git directory, object alternates, hardlinks, remote or main branch."""
    parent = storage_directory(parent, create=True)
    identity = uuid4().hex
    workspace = parent.resolve() / ("task-" + identity)
    if workspace.exists():
        raise DriverError("workspace already exists")
    # --no-local copies objects through upload-pack; disables local hardlink/alternate optimization.
    env = environment() | {"GIT_ALLOW_PROTOCOL": "file"}
    result = subprocess.run([shutil.which("git"), "clone", "--no-local", "--no-checkout", "--no-tags",
                             "--", str(source.checkout), str(workspace)], env=env,
                            capture_output=True, timeout=60)
    if result.returncode:
        raise DriverError("disposable clone failed; retain partial clone")
    source.require_descendant(binding["source"]["commit"], commit)
    branch = "s3/" + identity
    git(workspace, "checkout", "-B", branch, commit)
    for ref in git(workspace, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes").decode().splitlines():
        if ref != "refs/heads/" + branch:
            git(workspace, "update-ref", "-d", ref)
    git(workspace, "remote", "remove", "origin")
    git(workspace, "config", "core.autocrlf", "false")
    git(workspace, "config", "core.filemode", "true")
    if git(workspace, "status", "--porcelain", "--untracked-files=all"):
        raise DriverError("new workspace is dirty")
    files = inventory(workspace)
    for name in development["modify"]:
        if name not in files or git(workspace, "ls-tree", commit, "--", name).split()[0] != b"100644":
            raise DriverError("modification scope must name existing ordinary files")
    if any(name in files for name in development["create"]):
        raise DriverError("new file scope already exists")
    return {"identity": identity, "path": str(workspace), "branch": branch, "initial_head": commit,
            "binding": binding, "development": development, "initial_files": files,
            "initial_tracked_state": git(workspace, "ls-files", "--stage").decode(),
            "metadata": inventory(workspace, metadata=True)}


def verify_workspace(record, *, pristine=False):
    workspace = Path(record["path"])
    if workspace.resolve() != workspace or _is_redirect(workspace.lstat()):
        raise DriverError("workspace relocated or redirected")
    if inventory(workspace, metadata=True) != record["metadata"]:
        raise DriverError("workspace Git metadata changed")
    if (git(workspace, "rev-parse", "HEAD").decode().strip() != record["initial_head"]
            or git(workspace, "symbolic-ref", "--short", "HEAD").decode().strip() != record["branch"]):
        raise DriverError("workspace Git metadata changed")
    files = inventory(workspace)
    if pristine and files != record["initial_files"]:
        raise DriverError("workspace is dirty or conflicts with the prepared source")
    return files


def changes(record):
    files = verify_workspace(record)
    original = record["initial_files"]
    changed = sorted(p for p in files.keys() | original.keys() if files.get(p) != original.get(p))
    if not changed:
        raise DriverError("no source changes to checkpoint")
    dev = record["development"]
    for name in changed:
        development_path(name)
        if name not in dev["modify"] + dev["create"] or name not in files:
            raise DriverError("unauthorized, unexpected or deleted file")
        if name not in original and name not in dev["create"]:
            raise DriverError("unexpected new file")
        if files[name]["executable"]:
            raise DriverError("executable development file refused")
        raw = (Path(record["path"]) / name).read_bytes()
        if len(raw) > 512 * 1024 or b"\0" in raw or raw.startswith(b"MZ"):
            raise DriverError("binary or oversized development output")
        raw.decode("utf-8")
    return {name: files[name] for name in changed}


def _step_argv(execution, step):
    """Assemble one validation step from the bound source, never from ambient state."""
    if type(step) is not tuple or not step:
        raise DriverError("unsupported validation step")
    if step[0] == "module":
        return execution_source.bound_argv(execution, mode="module", target=step[1],
                                           arguments=step[2])
    if step[0] == "code":
        return execution_source.bound_argv(execution, mode="code", target=step[1])
    if step[0] == "tool":
        # An immutable third-party tool from the controller's installation. No
        # repository code executes, so no workspace claim is made for this step.
        return [str(Path(sys.executable).resolve()), *step[1:]]
    raise DriverError("unsupported validation step")


def command(root, workspace, label, step, *, execution):
    """Fixed supervisor-selected Python argv. Actual output retained, never agent claims."""
    timeout = COMMAND_TIMEOUTS.get(label, DEFAULT_COMMAND_TIMEOUT)
    output = root / (label + ".output")
    launched = execution
    report_path = None
    if type(step) is tuple and step and step[0] != "tool":
        # Each step launches with its own report path, and any file left at that
        # path by an earlier attempt is removed first: a step whose child wrote
        # nothing must read as missing evidence, never as a preceding step's
        # verified report.
        report_path = root / (label + ".child.json")
        try:
            launched = execution_source.step_execution(execution, report_path)
        except execution_source.ExecutionSourceError as error:
            raise DriverError("validation step could not be bound: " + error.code) from None
        try:
            os.unlink(report_path)
        except FileNotFoundError:
            pass
        except OSError:
            raise DriverError(
                "a child report from an earlier attempt could not be cleared") from None
    try:
        argv = _step_argv(launched, step)
    except execution_source.ExecutionSourceError as error:
        raise DriverError("validation step could not be bound: " + error.code) from None
    from deskmate_formats.observer._private_storage import private_file
    with private_file(output, write=True) as stream:
        try:
            result = subprocess.run(argv, cwd=workspace, env=environment(), stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    child = None
    if step[0] != "tool":
        child = execution_source.read_child_report(launched)
    receipt = {"argv": argv, "interpreter_sha256": digest(argv[0]), "cwd": str(workspace),
               "source": "workspace" if step[0] != "tool" else execution_source.EXTERNAL,
               "execution_binding": launched, "child": child,
               "child_report_path": None if report_path is None else str(report_path),
               "execution_verified": True if child is None else child["verified"],
               "exit_status": code, "timeout_seconds": timeout,
               "output_sha256": digest(output), "output_path": str(output)}
    write_record(root / (label + ".json"), receipt)
    return receipt


def checkpoint(root, record, authorization, plan_digest, worker_outcome, *, execution):
    """One checkpoint attempt, including failed/interrupted validation; no automatic retry.

    Every validation step is bound to the accepted source through an explicit
    campaign environment, so a step can never execute another installation and
    still be recorded against this workspace.
    """
    if authorization != plan_digest:
        raise DriverError("separate exact-plan checkpoint authorization required")
    if execution is None:
        raise DriverError("source-bound validation requires an explicit execution binding")
    workspace_path = Path(record["path"]).resolve()
    try:
        # The checkpoint runs *after* authorized edits, so workspace content is
        # expected to differ from the pristine plan; the interpreter, the
        # environment record and the base revision may not.
        execution_source.verify_execution(execution, allow_workspace_change=True)
    except execution_source.ExecutionSourceError as error:
        raise DriverError("bound execution source changed: " + error.code) from None
    if (execution.get("workspace") or {}).get("path") != str(workspace_path):
        raise DriverError("the execution binding names another workspace")
    if (execution.get("workspace") or {}).get("revision") != record["initial_head"]:
        raise DriverError("the execution binding names another source revision")
    write_record(root / "checkpoint-intent.json", {"plan_sha256": plan_digest, "workspace": record["identity"]})
    steps = [("test-" + name, ("module", *TEST_PROFILES[name]))
             for name in record["development"]["test_profiles"]]
    steps += [("publication-audit", ("code", AUDIT)),
              ("reuse", ("tool", "-m", "reuse", "lint"))]
    outcome = {"state": "blocked", "reason": "checkpoint-interrupted",
               "validation": [{"step": label, "state": "not-run", "reason": "validation-not-reached"} for label, _ in steps],
               "workspace": record["identity"], "binding": record["binding"], "parent": record["initial_head"]}
    try:
        if worker_outcome["state"] != "completed":
            raise DriverError("worker incomplete; changes retained")
        identities = changes(record)
        workspace = Path(record["path"])
        diff = git(workspace, "diff", "--binary", record["initial_head"], "--").decode("utf-8")
        write_record(root / "diff.json", {"tracked_diff": diff, "files": identities})
        # Re-derive the content half of the binding from the authorized changed
        # files; the environment and revision halves were verified above.
        execution = execution_source.rebind_workspace(execution, workspace)
        outcome["execution"] = execution
        failed = False
        for index, (label, step) in enumerate(steps):
            receipt = command(root, workspace, label, step, execution=execution)
            passed = receipt["exit_status"] == 0 and receipt["execution_verified"]
            outcome["validation"][index] = {
                "step": label, "state": "passed" if passed else "failed", **receipt}
            failed |= not passed
        if failed:
            raise DriverError("validation failed; changes and diagnostics retained")
        if changes(record) != identities:
            raise DriverError("files changed during validation")
        git(workspace, "add", "--", *sorted(identities))
        staged = git(workspace, "diff", "--cached", "--name-only", "-z").decode().rstrip("\0").split("\0")
        if sorted(staged) != sorted(identities):
            raise DriverError("staged files differ from inspected identities")
        for name in staged:
            if git(workspace, "ls-files", "--stage", "--", name).split()[0] != b"100644":
                raise DriverError("staged file is executable or special")
            if sha256(git(workspace, "show", ":" + name)).hexdigest() != identities[name]["sha256"]:
                raise DriverError("staged bytes differ from validated bytes")
        tree = git(workspace, "write-tree").decode().strip()
        write_record(root / "checkpoint-staged.json", {"tree": tree, "files": identities})
        message = (f"S3 checkpoint: {record['binding']['id']} revision {record['binding']['revision']}\n\n"
                   f"Accepted task: {record['binding']['source']['commit']}\nSource: {record['initial_head']}\n")
        # commit-tree avoids hooks and leaves an object receipt before updating the task ref.
        commit = git(workspace, "commit-tree", tree, "-p", record["initial_head"], data=message.encode()).decode().strip()
        write_record(root / "checkpoint-object.json", {"commit": commit, "tree": tree, "parent": record["initial_head"]})
        git(workspace, "update-ref", "refs/heads/" + record["branch"], commit, record["initial_head"])
        if (git(workspace, "rev-parse", "HEAD^").decode().strip() != record["initial_head"]
                or git(workspace, "status", "--porcelain", "--untracked-files=all")):
            raise DriverError("checkpoint ref or final state incomplete")
        outcome.update(state="completed", reason="validated-local-checkpoint", commit=commit, tree=tree, files=identities)
    except (OSError, ValueError, RuntimeError) as error:
        outcome["reason"] = str(error) if isinstance(error, DriverError) else "checkpoint-failed-inspect-private-evidence"
    finally:
        write_record(root / "checkpoint-outcome.json", outcome)
    return outcome
