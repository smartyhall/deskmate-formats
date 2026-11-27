"""Disposable, deterministic Git input for offline supervisor tests.

Every fixture repository is byte-identical: the same empty tree, the same
frozen author and committer dates and the same remote.  Building it with seven
Git invocations per test therefore repeats work that cannot change, and on a
contended Windows host each invocation costs far more than the repository it
creates.  One template repository is built per process and copied for each
test, which keeps isolation (every test owns its own directory and objects)
while removing the repeated process creation.
"""

import atexit
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from deskmate_formats.supervisor.task_git import TrustedSource


REPOSITORY = "https://example.invalid/lab/synthetic.git"
TASK_PATH = "ops/tasks/sample.json"

_TEMPLATE_LOCK = threading.Lock()
_TEMPLATE: tuple[Path, str] | None = None


def manifest(**changes):
    return {
        "schema_version": 1, "id": "sample", "revision": 1,
        "idempotency_key": "sample-1", "title": "Synthetic inspection",
        "description": "Inspect fixture metadata.", "category": "verification",
        "profile": "offline", "resources": ["source-read"], "dependencies": [],
    } | changes


def git_environment():
    """Host-independent Git environment shared by the fixture and its template."""
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Synthetic Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="Synthetic Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
               GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
    return env


def _run_git(directory, *args, data=None):
    return subprocess.run(["git", *args], cwd=directory, check=True, input=data,
                          capture_output=True, env=git_environment(), timeout=60).stdout


def _build_template(directory: Path) -> str:
    directory.mkdir()
    _run_git(directory, "init", "-q", "-b", "main", "--object-format=sha1")
    _run_git(directory, "config", "core.autocrlf", "false")
    _run_git(directory, "config", "commit.gpgsign", "false")
    _run_git(directory, "remote", "add", "origin", REPOSITORY)
    _run_git(directory, "commit", "-q", "--allow-empty", "-m", "Synthetic trust anchor")
    return _run_git(directory, "rev-parse", "HEAD").decode("ascii").strip()


def _template() -> tuple[Path, str]:
    """Build the shared template once per process; every test copies it."""
    global _TEMPLATE
    with _TEMPLATE_LOCK:
        if _TEMPLATE is None:
            root = Path(tempfile.mkdtemp(prefix="deskmate-task-template-"))
            atexit.register(shutil.rmtree, root, True)
            template = root / "repo"
            _TEMPLATE = (template, _build_template(template))
        return _TEMPLATE


class TaskRepo:
    def __init__(self, path):
        template, anchor = _template()
        self.path = Path(path)
        shutil.copytree(template, self.path)
        self.anchor = anchor

    def git(self, *args, data=None):
        return _run_git(self.path, *args, data=data)

    def head(self):
        return self.git("rev-parse", "HEAD").decode("ascii").strip()

    def stage(self, path, data, mode="100644"):
        blob = self.git("hash-object", "-w", "--stdin", data=data).decode("ascii").strip()
        self.git("update-index", "--add", "--cacheinfo", f"{mode},{blob},{path}")
        return blob

    def commit(self, value=None, *, path=TASK_PATH, mode="100644"):
        if value is not None:
            raw = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
            self.stage(path, raw, mode)
        self.git("commit", "-q", "--allow-empty", "-m", "Synthetic task revision")
        return self.head()

    def source(self, *, repository=REPOSITORY, branch="main", anchor=None):
        return TrustedSource(self.path, repository, branch, anchor or self.anchor)
