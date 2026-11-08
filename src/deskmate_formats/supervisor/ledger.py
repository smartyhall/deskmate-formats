"""Private operation receipts, independent of the Observatory event journal."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

from deskmate_formats.observer._private_storage import journal_lock, private_file, storage_directory

from .protocol import entity_id


DATABASE = "operations.sqlite3"
MUTATIONS = {"thread/start", "thread/resume", "turn/start", "turn/steer", "turn/interrupt"}
IN_FLIGHT = ("sent-unknown", "acknowledged", "running")
TRANSITIONS = {
    "prepared": {"sent-unknown"},
    "sent-unknown": {"acknowledged", "failed", "needs-reconciliation"},
    "acknowledged": {"running", "completed", "failed", "needs-reconciliation"},
    "running": {"completed", "failed", "needs-reconciliation"},
    "needs-reconciliation": {"completed", "failed"},
}
_SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE sessions (
    generation TEXT PRIMARY KEY,
    pid INTEGER NOT NULL,
    process_identity TEXT NOT NULL
) STRICT;
CREATE TABLE operations (
    operation_id TEXT PRIMARY KEY,
    method TEXT NOT NULL,
    generation TEXT NOT NULL REFERENCES sessions,
    request_id INTEGER NOT NULL,
    thread_id TEXT,
    turn_id TEXT,
    state TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    evidence TEXT NOT NULL,
    evidence_generation TEXT NOT NULL REFERENCES sessions,
    UNIQUE (generation, request_id)
) STRICT;
PRAGMA user_version = 1;
COMMIT;
"""


class LedgerError(OSError):
    """The private receipt store refused an operation."""


@dataclass(frozen=True, slots=True)
class Receipt:
    operation_id: str
    method: str
    generation: str
    request_id: int
    thread_id: str | None
    turn_id: str | None
    state: str
    acknowledged: int
    evidence: str
    evidence_generation: str


@contextmanager
def open_ledger(directory, *, create=False):
    """Hold the exclusive local writer lock for the lifetime of the ledger."""
    directory = storage_directory(directory, create=create)
    with journal_lock(directory, write=True):
        path = Path(directory) / DATABASE
        if create and path.exists():
            raise FileExistsError("operation ledger already exists")
        with private_file(path, write=create) as stream:
            if not create and stream.read(16) != b"SQLite format 3\0":
                raise LedgerError("operation ledger header is missing or damaged")
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=0, autocommit=True)
        try:
            if db.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                raise LedgerError("operation ledger could not select rollback journaling")
            db.execute("PRAGMA synchronous=EXTRA")
            db.execute("PRAGMA foreign_keys=ON")
            if create:
                db.executescript(_SCHEMA)
            if (db.execute("PRAGMA user_version").fetchone() != (1,)
                    or db.execute("PRAGMA quick_check").fetchall() != [("ok",)]):
                raise LedgerError("operation ledger is damaged or unsupported")
            yield Ledger(db)
        except sqlite3.Error:
            raise LedgerError("operation ledger storage failure") from None
        finally:
            db.close()


class Ledger:
    def __init__(self, db):
        self._db = db
        self._failed = False

    def _query(self, sql, args=()):
        if self._failed:
            raise LedgerError("operation ledger must be reopened after storage failure")
        try:
            return self._db.execute(sql, args)
        except sqlite3.Error:
            self._failed = True
            raise LedgerError("operation ledger storage failure") from None

    def register(self, client):
        self._query("INSERT INTO sessions VALUES (?, ?, ?)",
                    (client.generation, client.pid, client.process_identity))

    def process_for(self, generation):
        return self._query("SELECT pid, process_identity FROM sessions WHERE generation = ?",
                           (generation,)).fetchone()

    def get(self, operation_id):
        row = self._query("SELECT * FROM operations WHERE operation_id = ?", (operation_id,)).fetchone()
        return Receipt(*row) if row is not None else None

    def receipts(self):
        """Return durable receipts for offline operator inspection."""
        return [Receipt(*row) for row in self._query("SELECT * FROM operations ORDER BY rowid").fetchall()]

    def sessions(self):
        """Return saved process claims; these never authorize killing a PID."""
        return self._query("SELECT generation, pid, process_identity FROM sessions").fetchall()

    def prepare(self, operation_id, method, generation, request_id, thread_id, turn_id):
        if type(operation_id) is not str or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", operation_id):
            raise LedgerError("invalid local operation ID")
        if method not in MUTATIONS or self.get(operation_id) is not None:
            raise LedgerError("operation ID already recorded or method is unsupported")
        self._query(
            """INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, 'prepared', 0, 'local', ?)""",
            (operation_id, method, generation, request_id, thread_id, turn_id, generation),
        )
        return self.get(operation_id)

    def transition(self, receipt, state, evidence, generation, *, thread_id=None, turn_id=None):
        if state not in TRANSITIONS.get(receipt.state, ()):
            raise LedgerError("invalid operation state transition")
        thread_id = _associate(receipt.thread_id, thread_id)
        turn_id = _associate(receipt.turn_id, turn_id)
        changed = self._query(
            """UPDATE operations SET state = ?, evidence = ?, evidence_generation = ?,
                acknowledged = ?, thread_id = ?, turn_id = ?
                WHERE operation_id = ? AND state = ?""",
            (state, evidence, generation, int(receipt.acknowledged or state == "acknowledged"),
             thread_id, turn_id, receipt.operation_id, receipt.state),
        ).rowcount
        if changed != 1:
            raise LedgerError("operation receipt changed")
        return self.get(receipt.operation_id)

    def uncertain(self, generation):
        """Move current or previous in-flight receipts to operator reconciliation."""
        self._query(
            """UPDATE operations SET state = 'needs-reconciliation', evidence = 'connection-lost',
               evidence_generation = generation
               WHERE state IN (?, ?, ?) AND (? IS NULL OR generation = ?)""",
            (*IN_FLIGHT, generation, generation),
        )

    def matching_turn(self, generation, thread_id, turn_id):
        rows = self._query(
            """SELECT * FROM operations WHERE generation = ? AND thread_id = ? AND turn_id = ?
               AND method IN ('turn/start', 'turn/interrupt') AND state IN ('acknowledged', 'running')""",
            (generation, thread_id, turn_id),
        ).fetchall()
        return [Receipt(*row) for row in rows]


def _associate(saved, reported):
    if reported is None:
        return saved
    entity_id(reported)
    if saved is not None and saved != reported:
        raise LedgerError("reported identity disagrees with operation receipt")
    return reported
