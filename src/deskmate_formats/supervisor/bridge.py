"""S2 foundation: explicit accepted-revision grants to the S0 synthetic peer only."""

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from deskmate_formats.observer._private_storage import journal_lock, storage_directory
from deskmate_formats.observer.events import encode_json
from deskmate_formats.observer.journal import JournalError, publish_event

from .driver import DriverError, load_plan, prepare, read_record, run, status, write_record
from .task_manifest import utc_now
from .task_queue import open_queue


def accepted(queue, identifier, revision, review_token):
    """Read the existing immutable S1 acceptance, never accept or rediscover it."""
    row = queue.get(identifier, revision)
    if (row is None or row.state != "accepted" or row.candidate.review_token != review_token
            or any(other.state == "unresolved" or other.id == identifier and other.revision > revision
                   for other in queue.list())):
        raise DriverError("exact current accepted revision required; unresolved/superseded tasks block dispatch")
    manifest = row.candidate.manifest
    if manifest.get("expires_at", "9999") <= utc_now():
        raise DriverError("accepted revision expired")
    return {"queue_id": queue.queue_id, "sequence": row.sequence, "id": row.id,
            "revision": row.revision, "idempotency_key": row.idempotency_key,
            "review_token": row.candidate.review_token, "source": asdict(row.candidate.source)}


def _claim(binding):
    return sha256(encode_json([binding["queue_id"], binding["id"], binding["revision"]])).hexdigest()


def _state(directory, queue_id):
    root = storage_directory(directory, create=True)
    path = root / "binding.json"
    if path.exists():
        if read_record(path) != {"queue_id": queue_id, "worker": "synthetic-only"}:
            raise DriverError("bridge state belongs to another queue or worker")
    else:
        write_record(path, {"queue_id": queue_id, "worker": "synthetic-only"})
    return root


def grant(queue_directory, state_directory, identifier, revision, review_token, *, mode="success"):
    """Prepare a separately reviewed synthetic dispatch intent; do not start a worker."""
    with open_queue(queue_directory) as queue:
        binding = accepted(queue, identifier, revision, review_token)
        root = storage_directory(state_directory, create=True)
        with journal_lock(root, write=True):
            _state(root, queue.queue_id)
            run_directory = root / _claim(binding)
            token = prepare(run_directory, binding=binding, mode=mode)
            return {"claim": run_directory.name, "dispatch_token": token, "binding": binding,
                    "worker": "synthetic-only", "dispatched": False}


def dispatch(queue_directory, state_directory, claim, authorization):
    """One manual synthetic dispatch. Holding the state lock forbids concurrent workers."""
    if type(claim) is not str or len(claim) != 64 or any(char not in "0123456789abcdef" for char in claim):
        raise DriverError("invalid dispatch claim")
    root = storage_directory(state_directory)
    with journal_lock(root):
        run_directory = root / claim
        plan, token = load_plan(run_directory)
        binding = plan["binding"]
        if plan["kind"] != "synthetic" or not binding or _claim(binding) != claim or authorization != token:
            raise DriverError("exact separately authorized synthetic grant required")
        with open_queue(queue_directory) as queue:
            _state(root, queue.queue_id)
            current = accepted(queue, binding["id"], binding["revision"], binding["review_token"])
            if current != binding:
                raise DriverError("accepted receipt no longer matches dispatch grant")
            # Queue remains read-only throughout. Its acceptance cannot be changed into a dispatch.
            outcome = run(run_directory, authorization=authorization, accepted_binding=current)
            try:
                publish_event(run_directory / "spool", {
                    "schema_version": 1, "source": "supervisor-synthetic-bridge",
                    "agent_id": "supervisor-synthetic-bridge", "run_id": plan["run_id"],
                    "origin_id": plan["run_id"], "source_sequence": 1,
                    "type": "agent.note", "visibility": "observer", "correlation": {"task": claim},
                    "summary": "Synthetic dispatch completed" if outcome["state"] == "completed" else "Synthetic dispatch blocked; operator inspection required",
                })
            except (JournalError, ValueError):
                # Outcome was already committed. Do not replay dispatch after publication failure.
                write_record(run_directory / "publication-failed.json", {"dispatch_replay_permitted": False})
            return outcome


def inspect(state_directory, claim):
    if type(claim) is not str or len(claim) != 64 or any(char not in "0123456789abcdef" for char in claim):
        raise DriverError("invalid dispatch claim")
    return status(Path(state_directory) / claim)
