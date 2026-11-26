"""Private campaign registry and exclusive resource leases.

The registry is operator-owned private state: it records who is writing a
worktree, who owns an emulator socket and which machine is holding an
account allowance. It is deliberately outside Git, because it contains local
paths and process identities that must not be published.

A lease is a coordination promise between cooperating agents, not an operating
system sandbox and not a security boundary. It prevents accidental concurrent
mutation of the same resource. Taking a lease away from a live owner is never
implicit: reclaim requires an expired lease, a positively verified dead owner
and an explicit operator reason, and it leaves a durable takeover record.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re

from deskmate_formats.observer._private_storage import LockBusy, journal_lock, private_file, storage_directory
from deskmate_formats.observer.events import EventError, decode_json, encode_json
from deskmate_formats.observer.process_health import verify_process

FILE = "campaigns.json"
MAX_RECORDS = 256
MAX_BYTES = 1024 * 1024
MAX_TTL_SECONDS = 7 * 24 * 3600
MAX_RESOURCES = 16

SCHEMA_VERSION = 1
PROVIDERS = frozenset(("codex", "freebuff", "chatgpt", "operator", "deterministic"))
STATUSES = frozenset(("planning", "active", "blocked", "paused", "completed", "abandoned"))
_CAMPAIGN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_OWNER = re.compile(r"[\x20-\x7e]{1,120}")
_COMMIT = re.compile(r"[a-f0-9]{40}")
_BRANCH = re.compile(r"[a-z0-9][a-z0-9/_-]{0,127}")
_RESOURCE = re.compile(r"[a-z][a-z0-9.-]{0,31}:[a-z0-9][a-z0-9._-]{0,63}")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class RegistryError(ValueError):
    """The registry refused a record. Diagnostics omit private values."""


class RegistryBusy(RegistryError):
    """Another cooperating process holds the registry writer lock."""


class LeaseConflict(RegistryError):
    """Another campaign currently owns the requested resource."""


def utcnow():
    return datetime.now(UTC).replace(microsecond=0)


def _stamp(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _text(value, limit, label, *, optional=False):
    if value is None and optional:
        return None
    if type(value) is not str or not 0 < len(value) <= limit or not value.isprintable():
        raise RegistryError(f"invalid {label}")
    return value


def campaign_id(value):
    if type(value) is not str or not _CAMPAIGN.fullmatch(value):
        raise RegistryError("invalid campaign identity")
    return value


def resource_name(value):
    if type(value) is not str or not _RESOURCE.fullmatch(value):
        raise RegistryError("invalid resource name")
    return value


def _resources(values):
    if type(values) not in (list, tuple) or len(values) > MAX_RESOURCES:
        raise RegistryError("invalid resource list")
    normalized = [resource_name(item) for item in values]
    if len(set(normalized)) != len(normalized):
        raise RegistryError("duplicate resource")
    return normalized


def _ttl(value):
    if type(value) not in (int, float) or not 0 < value <= MAX_TTL_SECONDS:
        raise RegistryError("invalid lease duration")
    return float(value)


def _worktree(value):
    """Private locator: recorded exactly, never published by the projection."""
    if type(value) is not str or not 0 < len(value) <= 260:
        raise RegistryError("invalid worktree locator")
    path = Path(value)
    if not path.is_absolute():
        raise RegistryError("worktree locator must be absolute")
    return value


@dataclass(frozen=True, slots=True)
class Campaign:
    id: str
    owner: str
    provider: str
    base_commit: str | None
    branch: str
    worktree: str
    purpose: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class Lease:
    resource: str
    campaign: str
    pid: int
    process_identity: str
    acquired_at: str
    expires_at: str
    stale: bool
    owner_alive: str


def _empty():
    return {"schema_version": SCHEMA_VERSION, "campaigns": {}, "leases": {}, "takeovers": []}


def _load(path):
    if not path.exists():
        return _empty()
    with private_file(path) as stream:
        raw = stream.read(MAX_BYTES + 1)
    try:
        value = decode_json(raw, MAX_BYTES)
    except EventError:
        raise RegistryError("campaign registry is unreadable") from None
    if (type(value) is not dict or value.keys() != _empty().keys()
            or value["schema_version"] != SCHEMA_VERSION
            or type(value["campaigns"]) is not dict or type(value["leases"]) is not dict
            or type(value["takeovers"]) is not list
            or len(value["campaigns"]) > MAX_RECORDS or len(value["leases"]) > MAX_RECORDS
            or len(value["takeovers"]) > MAX_RECORDS):
        raise RegistryError("campaign registry is damaged or unsupported")
    return value


def _save(path, value):
    raw = encode_json(value)
    if len(raw) > MAX_BYTES:
        raise RegistryError("campaign registry exceeds its size limit")
    with private_file(path, write=True) as stream:
        stream.seek(0)
        stream.truncate()
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def open_registry(directory, *, create=False):
    """Open the exclusive writer lock for the lifetime of this block."""
    root = storage_directory(directory, create=create)
    path = root / FILE
    if create and path.exists():
        raise RegistryError("campaign registry already exists")
    try:
        with journal_lock(root, write=True):
            data = _load(path)
            if create:
                _save(path, data)
            yield Registry(path, data)
    except LockBusy:
        raise RegistryBusy("campaign registry is busy") from None


class Registry:
    """Mutating view. Every mutation is written through to the private file."""

    def __init__(self, path, data):
        self._path = path
        self._data = data

    def _commit(self):
        _save(self._path, self._data)

    # ---- campaigns -----------------------------------------------------
    def register(self, identifier, *, owner, provider, branch, worktree,
                 purpose, base_commit=None, status="active"):
        identifier = campaign_id(identifier)
        if identifier in self._data["campaigns"]:
            raise RegistryError("campaign is already registered")
        if provider not in PROVIDERS:
            raise RegistryError("unsupported provider")
        if status not in STATUSES:
            raise RegistryError("unsupported campaign status")
        if base_commit is not None and (type(base_commit) is not str or not _COMMIT.fullmatch(base_commit)):
            raise RegistryError("expected a full base commit")
        if type(branch) is not str or not _BRANCH.fullmatch(branch):
            raise RegistryError("invalid campaign branch")
        if len(self._data["campaigns"]) >= MAX_RECORDS:
            raise RegistryError("campaign registry limit reached")
        now = _stamp(utcnow())
        record = asdict(Campaign(identifier, _text(owner, 120, "owner"), provider, base_commit,
                                 branch, _worktree(worktree), _text(purpose, 240, "purpose"),
                                 status, now, now))
        self._data["campaigns"][identifier] = record
        self._commit()
        return Campaign(**record)

    def campaign(self, identifier):
        record = self._data["campaigns"].get(campaign_id(identifier))
        return None if record is None else Campaign(**record)

    def campaigns(self):
        return [Campaign(**record) for record in
                sorted(self._data["campaigns"].values(), key=lambda item: item["created_at"])]

    def set_status(self, identifier, status, *, reason=None):
        record = self._data["campaigns"].get(campaign_id(identifier))
        if record is None:
            raise RegistryError("unknown campaign")
        if status not in STATUSES:
            raise RegistryError("unsupported campaign status")
        _text(reason, 240, "status reason", optional=True)
        record["status"] = status
        record["updated_at"] = _stamp(utcnow())
        self._commit()
        return Campaign(**record)

    def handoff(self, identifier, *, owner):
        """Reassign the writing owner. Leases stay with the resource, not the owner."""
        record = self._data["campaigns"].get(campaign_id(identifier))
        if record is None:
            raise RegistryError("unknown campaign")
        record["owner"] = _text(owner, 120, "owner")
        record["updated_at"] = _stamp(utcnow())
        self._commit()
        return Campaign(**record)

    # ---- leases --------------------------------------------------------
    def acquire(self, resource, identifier, *, pid, process_identity, ttl_seconds, now=None):
        resource = resource_name(resource)
        identifier = campaign_id(identifier)
        if identifier not in self._data["campaigns"]:
            raise RegistryError("unknown campaign")
        if type(pid) is not int or not 1 <= pid < 2**31:
            raise RegistryError("invalid owning PID")
        _text(process_identity, 128, "process identity")
        ttl = _ttl(ttl_seconds)
        now = now or utcnow()
        current = self._data["leases"].get(resource)
        if current is not None:
            same = (current["campaign"], current["pid"], current["process_identity"])
            if same != (identifier, pid, process_identity):
                # An expired lease still blocks implicit takeover: the previous
                # owner's process may simply be unreachable from here.
                raise LeaseConflict("resource is leased; reconcile before reserving again")
        self._data["leases"][resource] = {
            "resource": resource, "campaign": identifier, "pid": pid,
            "process_identity": process_identity, "acquired_at": _stamp(now),
            "expires_at": _stamp(now + timedelta(seconds=ttl)), "ttl_seconds": ttl,
        }
        self._commit()
        return self.lease(resource, now=now)

    def renew(self, resource, identifier, *, ttl_seconds, now=None):
        resource = resource_name(resource)
        current = self._data["leases"].get(resource)
        if current is None or current["campaign"] != campaign_id(identifier):
            raise RegistryError("no lease owned by that campaign")
        ttl = _ttl(ttl_seconds)
        now = now or utcnow()
        current["expires_at"] = _stamp(now + timedelta(seconds=ttl))
        current["ttl_seconds"] = ttl
        self._commit()
        return self.lease(resource, now=now)

    def release(self, resource, identifier):
        resource = resource_name(resource)
        current = self._data["leases"].get(resource)
        if current is None:
            return False
        if current["campaign"] != campaign_id(identifier):
            raise RegistryError("cannot release another campaign's lease")
        del self._data["leases"][resource]
        self._commit()
        return True

    def lease(self, resource, *, now=None, probe=verify_process):
        resource = resource_name(resource)
        current = self._data["leases"].get(resource)
        if current is None:
            return None
        now = now or utcnow()
        expires = datetime.fromisoformat(current["expires_at"].replace("Z", "+00:00"))
        return Lease(current["resource"], current["campaign"], current["pid"],
                     current["process_identity"], current["acquired_at"], current["expires_at"],
                     now >= expires, probe(current["pid"], current["process_identity"]))

    def leases(self, *, now=None, probe=verify_process):
        return [self.lease(name, now=now, probe=probe) for name in sorted(self._data["leases"])]

    def reserve(self, resources, identifier, *, pid, process_identity, ttl_seconds, now=None):
        """Acquire every resource or none, leaving the registry unchanged on conflict."""
        names = _resources(resources)
        now = now or utcnow()
        taken = []
        try:
            for name in names:
                self.acquire(name, identifier, pid=pid, process_identity=process_identity,
                             ttl_seconds=ttl_seconds, now=now)
                taken.append(name)
        except RegistryError:
            for name in taken:
                self._data["leases"].pop(name, None)
            self._commit()
            raise
        return [self.lease(name, now=now) for name in names]

    def reclaim(self, resource, identifier, *, operator_reason, now=None, probe=verify_process):
        """Take over an expired lease only from a positively dead owner.

        ``verify_process`` returning ``unknown`` or ``identity-mismatch`` is not
        proof of death, so the request is refused. The takeover is recorded.
        """
        resource = resource_name(resource)
        identifier = campaign_id(identifier)
        if identifier not in self._data["campaigns"]:
            raise RegistryError("unknown campaign")
        current = self._data["leases"].get(resource)
        if current is None:
            raise RegistryError("no lease to reclaim")
        reason = _text(operator_reason, 240, "operator reason")
        if not reason.strip():
            raise RegistryError("operator reason must not be blank")
        now = now or utcnow()
        expires = datetime.fromisoformat(current["expires_at"].replace("Z", "+00:00"))
        if now < expires:
            raise RegistryError("lease has not expired; wait or coordinate with the owner")
        observed = probe(current["pid"], current["process_identity"])
        if observed not in ("stopped", "not-found"):
            raise RegistryError("owner process is not positively stopped; reconcile explicitly")
        if len(self._data["takeovers"]) >= MAX_RECORDS:
            raise RegistryError("takeover record limit reached")
        self._data["takeovers"].append({
            "resource": resource, "previous_campaign": current["campaign"],
            "previous_pid": current["pid"], "previous_identity": current["process_identity"],
            "new_campaign": identifier, "reason": reason, "observed_owner": observed,
            "taken_at": _stamp(now),
        })
        del self._data["leases"][resource]
        self._commit()
        return self.acquire(resource, identifier, pid=1, process_identity="reclaimed",
                            ttl_seconds=3600, now=now)

    def takeovers(self):
        return list(self._data["takeovers"])


def summarize(registry, *, now=None, probe=verify_process):
    """Public-safe campaign summary: no local paths, PIDs or process identities."""
    now = now or utcnow()
    leases = {lease.resource: lease for lease in registry.leases(now=now, probe=probe)}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _stamp(now),
        "campaigns": [
            {"id": record.id, "owner": record.owner, "provider": record.provider,
             "branch": record.branch, "status": record.status,
             "base_commit": record.base_commit, "created_at": record.created_at,
             "updated_at": record.updated_at,
             "resources": [{"name": lease.resource, "campaign": lease.campaign,
                            "expires_at": lease.expires_at, "stale": lease.stale,
                            "owner_alive": lease.owner_alive}
                           for lease in leases.values() if lease.campaign == record.id]}
            for record in registry.campaigns()
        ],
        "lease_count": len(leases),
        "stale_leases": sorted(name for name, lease in leases.items() if lease.stale),
        "takeover_count": len(registry.takeovers()),
    }


def export(registry, path, *, now=None):
    """Write a public-safe summary for the read-only Observatory projection."""
    summary = summarize(registry, now=now)
    raw = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8")
    target = Path(path)
    temp = target.with_name(target.name + ".tmp")
    with private_file(temp, write=True) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)
    return summary
