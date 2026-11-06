"""Private intake receipts with a durable, operator-resolved decision intent."""

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from deskmate_formats.observer._private_storage import LockBusy, journal_lock, private_file, storage_directory

from .task_git import Candidate, Provenance, TrustedSource
from .task_manifest import TaskError, plain_text, revision, task_id, utc_now


DATABASE = "task-queue.sqlite3"
MAX_RECORDS = 1000
_APPLICATION_ID = 0x44534D51
_MAX_PAGES = 8192  # With the fixed 4096-byte page size, at most 32 MiB.
_SCHEMA = f"""
CREATE TABLE settings (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    queue_id TEXT NOT NULL,
    checkout TEXT NOT NULL,
    repository TEXT NOT NULL,
    branch TEXT NOT NULL,
    anchor TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity BETWEEN 1 AND {MAX_RECORDS})
) STRICT;
CREATE TABLE tasks (
    sequence INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    commit_id TEXT NOT NULL,
    path TEXT NOT NULL,
    blob TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    raw BLOB NOT NULL,
    requested TEXT NOT NULL CHECK (requested IN ('accepted', 'rejected')),
    reason TEXT NOT NULL,
    prepared_at TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('unresolved', 'accepted', 'rejected', 'abandoned')),
    resolved_at TEXT,
    recovery_reason TEXT,
    UNIQUE (id, revision),
    CHECK ((state = 'unresolved' AND resolved_at IS NULL AND recovery_reason IS NULL)
        OR (state = requested AND resolved_at IS NOT NULL AND recovery_reason IS NULL)
        OR (state = 'abandoned' AND resolved_at IS NOT NULL AND recovery_reason IS NOT NULL))
) STRICT;
CREATE UNIQUE INDEX one_intent ON tasks(state) WHERE state = 'unresolved';
PRAGMA application_id = {_APPLICATION_ID};
PRAGMA user_version = 1;
"""


class QueueError(OSError):
    """Private queue unavailable or busy."""


class QueueUnresolved(QueueError):
    """Inspect the queue and reconcile the exact decision before trying again."""


@dataclass(frozen=True, slots=True)
class TaskReceipt:
    sequence: int
    id: str
    revision: int
    idempotency_key: str
    candidate: Candidate
    requested: str
    reason: str
    prepared_at: str
    state: str
    resolved_at: str | None
    recovery_reason: str | None


def _directory(value, create):
    path = Path(value).absolute().resolve()
    for parent in (path, *path.parents):
        if (parent / "HEAD").is_file() and (parent / "objects").is_dir():
            raise QueueError("private queue must be outside Git repositories")
    directory = storage_directory(value, create=create)
    allowed = {DATABASE, DATABASE + "-journal", "writer.lock"}
    if any(item.name not in allowed for item in directory.iterdir()):
        raise QueueError("expected a dedicated private queue directory")
    return directory


@contextmanager
def open_queue(directory, *, source=None, capacity=MAX_RECORDS):
    """Initialize only with an explicit source; otherwise open an existing queue."""
    create = source is not None
    if create and (type(capacity) is not int or not 1 <= capacity <= MAX_RECORDS):
        raise TaskError("invalid queue capacity")
    if create:
        source.verify()
    try:
        directory = _directory(directory, create)
        with journal_lock(directory, write=create):
            path = directory / DATABASE
            rollback = directory / (DATABASE + "-journal")
            if create and (os.path.lexists(path) or os.path.lexists(rollback)):
                raise QueueError("task queue already exists or has incomplete initialization")
            with private_file(path, write=create) as stream:
                if not create and stream.read(16) != b"SQLite format 3\0":
                    raise QueueError("task queue header is missing or damaged")
            if os.path.lexists(rollback):
                with private_file(rollback):
                    pass
            db = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=0, autocommit=True)
            try:
                db.execute("PRAGMA trusted_schema=OFF")
                db.execute("PRAGMA synchronous=EXTRA")
                if create:
                    db.execute("PRAGMA page_size=4096")
                if (db.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",)
                        or db.execute("PRAGMA page_size").fetchone() != (4096,)
                        or db.execute("PRAGMA page_count").fetchone()[0] > _MAX_PAGES):
                    raise QueueError("unsupported queue storage configuration")
                db.execute(f"PRAGMA max_page_count={_MAX_PAGES}")
                if create:
                    db.executescript("BEGIN IMMEDIATE;\n" + _SCHEMA)
                    db.execute("INSERT INTO settings VALUES (1, ?, ?, ?, ?, ?, ?)",
                               (uuid4().hex, *source.binding, capacity))
                    db.execute("COMMIT")
                if (db.execute("PRAGMA application_id").fetchone() != (_APPLICATION_ID,)
                        or db.execute("PRAGMA user_version").fetchone() != (1,)
                        or db.execute("PRAGMA quick_check(1)").fetchall() != [("ok",)]):
                    raise QueueError("task queue is damaged or unsupported")
                yield TaskQueue(db)
            finally:
                db.close()
    except LockBusy:
        raise QueueError("task queue is busy; no decision attempted") from None
    except QueueError:
        raise
    except (sqlite3.Error, OSError):
        raise QueueError("cannot access private queue; check storage and permissions") from None


class TaskQueue:
    def __init__(self, db):
        self._db = db
        self._failed = False
        settings = db.execute(
            "SELECT queue_id, checkout, repository, branch, anchor, capacity FROM settings WHERE singleton=1"
        ).fetchone()
        if settings is None:
            raise QueueError("task queue configuration is missing")
        self.queue_id, *binding, self.capacity = settings
        self._binding = tuple(binding)

    def _check_open(self):
        if self._failed:
            raise QueueUnresolved("decision outcome unknown; reopen and inspect the queue")

    def _receipt(self, row):
        sequence, identifier, rev, key, commit, path, blob, digest, raw, *decision = row
        candidate = Candidate(Provenance(self._binding[1], self._binding[2], commit, path, blob, digest), raw)
        return TaskReceipt(sequence, identifier, rev, key, candidate, *decision)

    def list(self):
        self._check_open()
        rows = self._db.execute("SELECT * FROM tasks ORDER BY sequence LIMIT ?", (self.capacity + 1,)).fetchall()
        if len(rows) > self.capacity:
            raise QueueError("queue record limit exceeded")
        return [self._receipt(row) for row in rows]

    def get(self, identifier, rev):
        self._check_open()
        row = self._db.execute("SELECT * FROM tasks WHERE id=? AND revision=?",
                               (task_id(identifier), revision(rev))).fetchone()
        return self._receipt(row) if row is not None else None

    def counts(self):
        self._check_open()
        return {"accepted": 0, "rejected": 0, "unresolved": 0, "abandoned": 0} | dict(
            self._db.execute("SELECT state, COUNT(*) FROM tasks GROUP BY state")
        )

    def discover(self, commit, path):
        self._check_open()
        source = TrustedSource(*self._binding)
        latest = self._db.execute("SELECT commit_id FROM tasks ORDER BY sequence DESC LIMIT 1").fetchone()
        return source.discover(commit, path, previous=latest[0] if latest else None)

    @contextmanager
    def _write(self):
        self._check_open()
        try:
            self._db.execute("BEGIN IMMEDIATE")
            yield
            self._db.execute("COMMIT")
        except BaseException as error:
            self._failed = True
            # Do not issue another write or infer the commit outcome from the error.
            # Closing the connection releases it and rolls back any active transaction.
            if isinstance(error, (sqlite3.Error, OSError, KeyboardInterrupt)):
                raise QueueUnresolved("decision outcome unknown; reopen and inspect the queue") from None
            raise

    def _complete(self, sequence, state, recovery_reason=None):
        with self._write():
            result = self._db.execute(
                """UPDATE tasks SET state=?, resolved_at=?, recovery_reason=?
                   WHERE sequence=? AND state='unresolved'""",
                (state, utc_now(), recovery_reason, sequence),
            )
            if result.rowcount != 1:
                raise QueueUnresolved("decision intent changed; reopen and inspect the queue")

    def decide(self, commit, path, review_token, decision, reason):
        """Re-verify the reviewed candidate and durably accept or reject it."""
        if decision not in ("accepted", "rejected"):
            raise TaskError("invalid operator decision")
        plain_text(reason, 512, "operator reason")
        self._check_open()
        if self._db.execute("SELECT 1 FROM tasks WHERE state='unresolved'").fetchone():
            raise QueueUnresolved("an unresolved decision requires operator reconciliation")
        candidate = self.discover(commit, path)
        _verify_token(candidate, review_token)
        manifest = candidate.manifest
        identifier, rev, key = (manifest[field] for field in ("id", "revision", "idempotency_key"))
        existing = self.get(identifier, rev)
        if existing is not None:
            if existing.candidate.source.sha256 != candidate.source.sha256:
                raise TaskError("manifest bytes conflict with the recorded task revision")
            if existing.state != decision:
                raise TaskError("task revision already has a different outcome")
            return existing, False
        previous = self._db.execute("SELECT MAX(revision) FROM tasks WHERE id=?", (identifier,)).fetchone()[0]
        if rev != (previous or 0) + 1:
            raise TaskError("task revisions must start at one and increase by one")
        if self._db.execute("SELECT 1 FROM tasks WHERE idempotency_key=?", (key,)).fetchone():
            raise TaskError("idempotency key already belongs to another task revision")
        if sum(self.counts().values()) >= self.capacity:
            raise TaskError("task queue record limit reached")
        if decision == "accepted":
            expiry = manifest.get("expires_at")
            if expiry and expiry <= utc_now():
                raise TaskError("task manifest has expired")
            for dependency in manifest["dependencies"]:
                receipt = self.get(dependency["id"], dependency["revision"])
                if receipt is None or receipt.state != "accepted":
                    raise TaskError("dependency revision has no prior acceptance")
        provenance = candidate.source
        with self._write():
            sequence = self._db.execute(
                """INSERT INTO tasks
                   (id, revision, idempotency_key, commit_id, path, blob, sha256, raw,
                    requested, reason, prepared_at, state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unresolved')""",
                (identifier, rev, key, provenance.commit, provenance.path, provenance.blob,
                 provenance.sha256, candidate.raw, decision, reason, utc_now()),
            ).lastrowid
        self._complete(sequence, decision)
        return self.get(identifier, rev), True

    def abandon(self, identifier, rev, review_token, reason):
        """Close an interrupted intent without applying its requested decision."""
        plain_text(reason, 512, "reconciliation reason")
        existing = self.get(identifier, rev)
        if existing is None or existing.state != "unresolved":
            raise TaskError("no unresolved decision for that task revision")
        _verify_token(existing.candidate, review_token)
        self._complete(existing.sequence, "abandoned", reason)
        return self.get(identifier, rev)


def _verify_token(candidate, value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value) or value != candidate.review_token:
        raise TaskError("review token does not match the exact candidate")
