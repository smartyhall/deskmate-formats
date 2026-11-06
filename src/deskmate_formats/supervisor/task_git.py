"""Explicit offline discovery from one configured Git branch."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

from deskmate_formats.observer._private_storage import _is_redirect
from deskmate_formats.observer.events import encode_json

from .task_manifest import MAX_MANIFEST_BYTES, TaskError, manifest_path, validate_manifest


_REPOSITORY = re.compile(r"https://[a-z0-9][a-z0-9.-]{0,127}/"
                         r"[a-z0-9][a-z0-9_-]{0,63}/[a-z0-9][a-z0-9_.-]{0,99}\.git")
_BRANCH = re.compile(r"[a-z0-9][a-z0-9/_-]{0,127}")
_OBJECT_ID = re.compile(r"[a-f0-9]{40}(?:[a-f0-9]{24})?")
MAX_INSTRUCTION_BYTES = 128 * 1024


@dataclass(frozen=True, slots=True)
class Provenance:
    repository: str
    branch: str
    commit: str
    path: str
    blob: str
    sha256: str


@dataclass(frozen=True, slots=True)
class Candidate:
    source: Provenance
    raw: bytes

    @property
    def manifest(self):
        return validate_manifest(self.raw)

    @property
    def review_token(self):
        return sha256(encode_json(asdict(self.source))).hexdigest()


class TrustedSource:
    """Use a trusted local clone and full object IDs. Never fetch or check out."""

    def __init__(self, checkout, repository, branch, anchor):
        if (type(repository) is not str or not _REPOSITORY.fullmatch(repository)
                or ".." in repository or repository.endswith("..git")):
            raise TaskError("expected one canonical HTTPS repository identity")
        if (type(branch) is not str or not _BRANCH.fullmatch(branch)
                or any(not part or not part[0].isalnum() for part in branch.split("/"))):
            raise TaskError("invalid trusted branch name")
        if type(anchor) is not str or not _OBJECT_ID.fullmatch(anchor):
            raise TaskError("expected a full trust-anchor object ID")
        try:
            provided = Path(checkout).absolute()
            if any(_is_redirect(parent.lstat()) for parent in (provided, *provided.parents)):
                raise TaskError("Git checkout path uses a filesystem redirect")
            path = provided.resolve(strict=True)
            self.directory = path / ".git"
            for location in (path, self.directory, self.directory / "objects"):
                info = location.lstat()
                if _is_redirect(info) or not stat.S_ISDIR(info.st_mode):
                    raise TaskError("expected a standalone local Git checkout")
            config = (self.directory / "config").lstat()
            if _is_redirect(config) or not stat.S_ISREG(config.st_mode):
                raise TaskError("expected a regular local Git config")
        except OSError:
            raise TaskError("cannot open configured Git checkout") from None
        self.repository = repository
        self.branch = branch
        self.anchor = anchor
        self.checkout = path
        self._git = shutil.which("git")
        if not self._git:
            raise TaskError("Git executable unavailable")

    @property
    def binding(self):
        return (str(self.checkout), self.repository, self.branch, self.anchor)

    def _run(self, *args, allowed=(0,)):
        env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_SYSTEM=os.devnull, GIT_ALLOW_PROTOCOL="", GIT_NO_LAZY_FETCH="1",
                   GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
        try:
            result = subprocess.run(
                [self._git, "--no-replace-objects", "--literal-pathspecs",
                 "--git-dir", str(self.directory), *args],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=5, env=env,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise TaskError("Git inspection failed or timed out") from None
        if result.returncode not in allowed:
            raise TaskError("configured Git source or object could not be verified")
        return result

    def _oid(self, value):
        if (type(value) is not str or len(value) != len(self.anchor)
                or not _OBJECT_ID.fullmatch(value)):
            raise TaskError("expected a full Git object ID")
        return value

    def _check_repository(self):
        for name in ("commondir", "shallow", "info/grafts", "objects/info/alternates",
                     "objects/info/http-alternates"):
            if os.path.lexists(self.directory / name):
                raise TaskError("Git source uses redirected or incomplete history")
        urls = self._run("config", "--local", "--no-includes", "--null",
                         "--get-all", "remote.origin.url").stdout
        if urls != self.repository.encode("ascii") + b"\0":
            raise TaskError("Git origin is ambiguous or differs from configured identity")
        if self._run("config", "--local", "--no-includes", "--name-only", "--get-regexp",
                     r"^(include\.|includeif\.)", allowed=(0, 1)).returncode == 0:
            raise TaskError("Git source uses included configuration")

    def _tip(self):
        ref = "refs/heads/" + self.branch
        if self._run("symbolic-ref", "--quiet", "--no-recurse", ref, allowed=(0, 1)).returncode != 1:
            raise TaskError("trusted branch must be a direct branch reference")
        try:
            return self._oid(self._run("show-ref", "--verify", "--hash", ref).stdout.strip().decode("ascii"))
        except UnicodeError:
            raise TaskError("invalid branch object ID") from None

    def _require_tip(self, commit):
        if self._tip() != commit:
            raise TaskError("pinned commit is not the configured branch tip")

    def verify(self):
        """Check configuration and ancestry before creating a queue."""
        self._check_repository()
        self.require_descendant(self._tip(), self.anchor)

    def require_descendant(self, commit, ancestor):
        for oid in (commit, ancestor):
            if self._run("cat-file", "-t", self._oid(oid)).stdout != b"commit\n":
                raise TaskError("pinned Git object must be a commit")
        if self._run("merge-base", "--is-ancestor", ancestor, commit, allowed=(0, 1)).returncode:
            raise TaskError("branch history diverges from the recorded trust point")

    def _blob(self, commit, path, limit):
        entry = self._run("ls-tree", "-z", "--full-tree", commit, "--", path).stdout
        header, separator, name = entry.partition(b"\t")
        fields = header.split()
        if (not separator or name != path.encode("ascii") + b"\0"
                or len(fields) != 3 or fields[:2] != [b"100644", b"blob"]):
            raise TaskError("expected one tracked regular, non-executable blob at the exact path")
        try:
            blob = self._oid(fields[2].decode("ascii"))
            size = int(self._run("cat-file", "-s", blob).stdout)
        except ValueError:
            raise TaskError("invalid Git blob metadata") from None
        if not 0 < size <= limit:
            raise TaskError("Git blob is empty or exceeds the byte limit")
        raw = self._run("cat-file", "blob", blob).stdout
        if len(raw) != size:
            raise TaskError("Git blob size changed")
        return blob, raw

    def discover(self, commit, path, *, previous=None):
        """Verify the exact branch tip, source bytes and referenced document hashes."""
        self._oid(commit)
        manifest_path(path)
        self._check_repository()
        self._require_tip(commit)
        self.require_descendant(commit, previous if previous is not None else self.anchor)
        blob, raw = self._blob(commit, path, MAX_MANIFEST_BYTES)
        value = validate_manifest(raw)
        if path != f"ops/tasks/{value['id']}.json":
            raise TaskError("task identity does not match its canonical manifest path")
        for reference in value.get("instructions", ()):
            _, document = self._blob(commit, reference["path"], MAX_INSTRUCTION_BYTES)
            if sha256(document).hexdigest() != reference["sha256"]:
                raise TaskError("tracked instruction digest differs from manifest")
        self._require_tip(commit)
        return Candidate(Provenance(self.repository, self.branch, commit, path, blob,
                                    sha256(raw).hexdigest()), raw)
