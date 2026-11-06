"""Disposable, deterministic Git input for offline supervisor tests."""

import json
import os
from pathlib import Path
import subprocess

from deskmate_formats.supervisor.task_git import TrustedSource


REPOSITORY = "https://example.invalid/lab/synthetic.git"
TASK_PATH = "ops/tasks/sample.json"


def manifest(**changes):
    return {
        "schema_version": 1, "id": "sample", "revision": 1,
        "idempotency_key": "sample-1", "title": "Synthetic inspection",
        "description": "Inspect fixture metadata.", "category": "verification",
        "profile": "offline", "resources": ["source-read"], "dependencies": [],
    } | changes


class TaskRepo:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir()
        self.git("init", "-q", "-b", "main", "--object-format=sha1")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "commit.gpgsign", "false")
        self.git("remote", "add", "origin", REPOSITORY)
        self.git("commit", "-q", "--allow-empty", "-m", "Synthetic trust anchor")
        self.anchor = self.head()

    def git(self, *args, data=None):
        env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_AUTHOR_NAME="Synthetic Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Synthetic Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                   GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
        return subprocess.run(["git", *args], cwd=self.path, check=True, input=data,
                              capture_output=True, env=env, timeout=10).stdout

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
