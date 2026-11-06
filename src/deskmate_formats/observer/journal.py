"""Private, bounded JSONL journal. Only local publishers can append records."""

from dataclasses import dataclass
from datetime import UTC, datetime
import errno
import os
from time import monotonic_ns

from ._private_storage import LockBusy, journal_lock, private_file, storage_directory
from .events import (
    EventError, IngestionOrder, MAX_RECORD_BYTES, MAX_SEQUENCE, decode_record, encode_json,
    envelope, normalize_event,
)

DEFAULT_MAX_BYTES = 16 * 1024 * 1024
MAX_STORAGE_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_RECORDS = 10000
_JOURNAL = "events.jsonl"


class JournalError(OSError):
    """Storage failure with a diagnostic safe for a local publisher to print."""


class JournalBusy(JournalError):
    """A cooperating reader or writer currently owns the spool lock."""


@dataclass(frozen=True)
class JournalLimits:
    max_bytes: int = DEFAULT_MAX_BYTES
    max_records: int = DEFAULT_MAX_RECORDS

    def __post_init__(self):
        if type(self.max_bytes) is not int or not 1 <= self.max_bytes <= MAX_STORAGE_BYTES:
            raise ValueError("invalid journal byte limit")
        if type(self.max_records) is not int or not 1 <= self.max_records <= DEFAULT_MAX_RECORDS:
            raise ValueError("invalid journal record limit")


@dataclass(frozen=True)
class Replay:
    """Private replay. Do not send its records directly to the observer."""

    records: tuple = ()
    fingerprint: tuple | None = None
    first_corrupt_line: int | None = None
    corrupt_lines: int = 0
    tail_bytes: int = 0
    capacity_exceeded: bool = False
    at_capacity: bool = False


@dataclass(frozen=True)
class Receipt:
    cursor: int
    event_id: str
    ingested_at_utc: str
    recovered_tail_bytes: int


def _fingerprint(stream):
    info = os.fstat(stream.fileno())
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _scan(stream, fingerprint, limits):
    size = fingerprint[2]
    order = IngestionOrder()
    records = []
    first_corrupt = None
    corrupt = tail = line_number = 0
    scanned_size = min(size, limits.max_bytes)
    capacity_exceeded = size > limits.max_bytes
    while stream.tell() < scanned_size:
        line_number += 1
        if line_number > limits.max_records + 1024:
            capacity_exceeded = True
            break
        start = stream.tell()
        line = stream.readline(min(MAX_RECORD_BYTES + 1, scanned_size - start))
        if not line:
            raise JournalError("journal changed while being read")
        last = line
        while not last.endswith(b"\n") and stream.tell() < scanned_size:
            last = stream.readline(min(MAX_RECORD_BYTES, scanned_size - stream.tell()))
            if not last:
                raise JournalError("journal changed while being read")
        if not last.endswith(b"\n"):
            if scanned_size == size:
                tail = size - start
            break
        try:
            record = decode_record(line)
            if len(records) >= limits.max_records:
                capacity_exceeded = True
                break
            order.accept(record)
        except EventError:
            corrupt += 1
            if first_corrupt is None:
                first_corrupt = line_number
        else:
            records.append(record)
    return Replay(tuple(records), fingerprint, first_corrupt, corrupt, tail, capacity_exceeded,
                  size >= limits.max_bytes or len(records) >= limits.max_records), order


def _storage_error(error):
    if isinstance(error, JournalError):
        return error
    if isinstance(error, LockBusy):
        return JournalBusy("event journal is busy; no append attempted")
    if error.errno in (errno.ENOSPC, getattr(errno, "EDQUOT", -1)):
        return JournalError("event journal storage is full")
    return JournalError("cannot access private journal storage; check location and permissions")


def read_journal(path, *, limits=JournalLimits(), unchanged=None):
    """Read committed records under the OS lock. Return None if unchanged."""
    try:
        directory = storage_directory(path)
        with journal_lock(directory), private_file(directory / _JOURNAL) as stream:
            fingerprint = _fingerprint(stream)
            if fingerprint == unchanged:
                return None
            return _scan(stream, fingerprint, limits)[0]
    except FileNotFoundError:
        return Replay()
    except OSError as error:
        raise _storage_error(error) from None


def publish_event(path, payload, *, limits=JournalLimits()):
    """Validate, serialize with other publishers, append, flush and acknowledge one event."""
    event = normalize_event(payload)
    try:
        directory = storage_directory(path, create=True)
        with journal_lock(directory, write=True), private_file(directory / _JOURNAL, write=True) as stream:
            replay, order = _scan(stream, _fingerprint(stream), limits)
            if replay.corrupt_lines:
                raise JournalError(f"journal corruption at line {replay.first_corrupt_line}; appends stopped")
            if replay.capacity_exceeded or order.cursor == MAX_SEQUENCE:
                raise JournalError("event journal retention limit reached")
            utc = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
            record = envelope(event, order.cursor + 1, utc, monotonic_ns())
            order.accept(record)
            line = encode_json(record) + b"\n"
            end = replay.fingerprint[2] - replay.tail_bytes
            if end + len(line) > limits.max_bytes or len(replay.records) >= limits.max_records:
                raise JournalError("event journal retention limit reached")
            try:
                fd = stream.fileno()
                if replay.tail_bytes:
                    os.ftruncate(fd, end)
                os.lseek(fd, end, os.SEEK_SET)
                # Bypass the read buffer so closing after an error cannot retry a write.
                if os.write(fd, line) != len(line):
                    raise OSError("short journal write")
                os.fsync(fd)
            except OSError as error:
                reason = "storage full" if error.errno in (errno.ENOSPC, getattr(errno, "EDQUOT", -1)) else "I/O error"
                raise JournalError(f"journal append {reason}; reconcile history before retrying") from None
            return Receipt(record["cursor"], record["event_id"], utc, replay.tail_bytes)
    except OSError as error:
        raise _storage_error(error) from None
