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
from .driver import DriverError, digest, write_record
from .task_manifest import development_path

TEST_PROFILES = {
    "portable-full": ["-m", "unittest", "discover", "-s", "tests/portable", "-v"],
    "synthetic-unit": ["-m", "unittest", "discover", "-s", "tests/portable", "-p", "test_s3_sample.py", "-v"],
}
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


def command(root, workspace, label, args):
    """Fixed supervisor-selected Python argv. Actual output retained, never agent claims."""
    output = root / (label + ".output")
    argv = [str(Path(sys.executable).resolve()), *args]
    from deskmate_formats.observer._private_storage import private_file
    env = environment()
    env["PYTHONPATH"] = str(Path(workspace) / "src")
    with private_file(output, write=True) as stream:
        try:
            result = subprocess.run(argv, cwd=workspace, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=600)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    receipt = {"argv": argv, "interpreter_sha256": digest(argv[0]), "cwd": str(workspace),
               "exit_status": code, "output_sha256": digest(output), "output_path": str(output)}
    write_record(root / (label + ".json"), receipt)
    return receipt


def checkpoint(root, record, authorization, plan_digest, worker_outcome):
    """One checkpoint attempt, including failed/interrupted validation; no automatic retry."""
    if authorization != plan_digest:
        raise DriverError("separate exact-plan checkpoint authorization required")
    write_record(root / "checkpoint-intent.json", {"plan_sha256": plan_digest, "workspace": record["identity"]})
    steps = [("test-" + name, TEST_PROFILES[name]) for name in record["development"]["test_profiles"]]
    steps += [("publication-audit", ["-I", "-c", AUDIT]), ("reuse", ["-m", "reuse", "lint"])]
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
        failed = False
        for index, (label, args) in enumerate(steps):
            receipt = command(root, workspace, label, args)
            outcome["validation"][index] = {"step": label, "state": "passed" if receipt["exit_status"] == 0 else "failed", **receipt}
            failed |= receipt["exit_status"] != 0
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
