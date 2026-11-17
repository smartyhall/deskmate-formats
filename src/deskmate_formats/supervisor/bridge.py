"""Manual S2 grants: one accepted Git revision to one owned S0 text-analysis turn."""

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from deskmate_formats.observer._private_storage import journal_lock, storage_directory
from deskmate_formats.observer.events import encode_json
from deskmate_formats.observer.journal import JournalError, publish_event

from .driver import DriverError, implementation_hashes, load_plan, preflight, prepare, read_record, run, status, write_record
from .protocol import PROFILE_SHA256
from .task_execution import task_prompt
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
    # _material revalidates Git bytes under these same queue/state locks.
    return {"queue_id": queue.queue_id, "sequence": row.sequence, "id": row.id,
            "revision": row.revision, "idempotency_key": row.idempotency_key,
            "review_token": row.candidate.review_token, "source": asdict(row.candidate.source)}


def _claim(binding):
    return sha256(encode_json([binding["queue_id"], binding["id"], binding["revision"]])).hexdigest()


def _state(directory, queue_id):
    root = storage_directory(directory, create=True)
    path = root / "binding.json"
    if path.exists():
        if read_record(path) not in ({"queue_id": queue_id, "worker": "synthetic-only"},
                                     {"queue_id": queue_id, "worker": "owned-one-shot"}):
            raise DriverError("bridge state belongs to another queue or worker")
    else:
        write_record(path, {"queue_id": queue_id, "worker": "owned-one-shot"})
    return root


def _dependencies(queue, root, manifest, *, live=False):
    """S1 dependency acceptance is necessary; S2 additionally requires completion."""
    results = []
    for dependency in manifest["dependencies"]:
        row = queue.get(dependency["id"], dependency["revision"])
        if (row is None or row.state != "accepted"
                or any(other.id == row.id and other.revision > row.revision for other in queue.list())):
            raise DriverError("dependency requires exact current S1 acceptance")
        claim = _claim({"queue_id": queue.queue_id, "id": row.id, "revision": row.revision})
        path = root / claim / "outcome.json"
        if not path.exists():
            raise DriverError("dependency has no completed S2 outcome")
        outcome = read_record(path)
        binding = outcome.get("binding") or {}
        if (outcome.get("state") != "completed" or binding.get("queue_id") != queue.queue_id
                or outcome.get("kind") != ("live" if live else "synthetic")
                or binding.get("review_token") != row.candidate.review_token
                or binding.get("sequence") != row.sequence):
            raise DriverError("dependency S2 outcome is incomplete or mismatched")
        results.append({**dependency, "claim": claim, "outcome_sha256": sha256(encode_json(outcome)).hexdigest()})
    return results


def _material(queue, root, binding, *, live=False):
    row = queue.get(binding["id"], binding["revision"])
    context = queue.execution_context(row.candidate)
    if context["class"] != "text-analysis-v1":
        raise DriverError("S2 text-analysis bridge refuses editing tasks; select S3 explicitly")
    task_prompt(context)  # Refuse unsupported resource requests and overlarge context before staging.
    return context, _dependencies(queue, root, row.candidate.manifest, live=live)


def grant(queue_directory, state_directory, identifier, revision, review_token, *, mode="success",
          executable=None, model=None, effort=None, profile=None, auth_file=None, timeout=10, deadline=60):
    """Freeze one reviewed Git task and S0 plan; never start an app-server or model."""
    with open_queue(queue_directory) as queue:
        binding = accepted(queue, identifier, revision, review_token)
        root = storage_directory(state_directory, create=True)
        with journal_lock(root, write=True):
            _state(root, queue.queue_id)
            run_directory = root / _claim(binding)
            if run_directory.exists():
                raise DriverError("task claim already prepared or attempted; inspect the permanent receipt")
            context, dependencies = _material(queue, root, binding, live=executable is not None)
            if executable is not None and profile != "experimental-lab":
                raise DriverError("live S2 requires explicit experimental-lab profile")
            if executable is not None:
                queue.verify_worker(binding["source"]["commit"],
                                    implementation_hashes() | {"supervisor/codex-0.166.0.json": PROFILE_SHA256})
            token = prepare(run_directory, binding=binding, mode=mode, task_context=context,
                            dependencies=dependencies, executable=executable,
                            model=model if executable is not None else "synthetic",
                            effort=effort if executable is not None else "low", profile=profile,
                            auth_file=auth_file, timeout=timeout, deadline=deadline)
            return {"claim": run_directory.name, "dispatch_token": token, "binding": binding,
                    "plan_sha256": token, "worker": "live" if executable is not None else "synthetic-only",
                    "dispatched": False}


def dispatch(queue_directory, state_directory, claim, authorization, *, live=False,
             model_authorization=None, lab_risk_ack=None, validate_only=False):
    """One manual dispatch. State and queue locks cover the single cooperating worker."""
    if type(claim) is not str or len(claim) != 64 or any(char not in "0123456789abcdef" for char in claim):
        raise DriverError("invalid dispatch claim")
    root = storage_directory(state_directory)
    with journal_lock(root):
        run_directory = root / claim
        plan, token = load_plan(run_directory)
        binding = plan["binding"]
        if (plan["kind"] != ("live" if live else "synthetic") or not binding
                or _claim(binding) != claim or (not validate_only and authorization != token)):
            raise DriverError("exact separately authorized dispatch grant and matching worker kind required")
        if live and not validate_only and model_authorization != token:
            raise DriverError("separate exact-plan model-use authorization required")
        if live and not validate_only and lab_risk_ack != token:
            raise DriverError("separate exact-plan experimental-lab risk acknowledgment required")
        if (run_directory / "attempt.json").exists():
            raise DriverError("task claim already attempted; replay is forbidden")
        with open_queue(queue_directory) as queue:
            _state(root, queue.queue_id)
            current = accepted(queue, binding["id"], binding["revision"], binding["review_token"])
            if current != binding:
                raise DriverError("accepted receipt no longer matches dispatch grant")
            if live:
                queue.verify_worker(binding["source"]["commit"],
                                    implementation_hashes() | {"supervisor/codex-0.166.0.json": PROFILE_SHA256})
            context, dependencies = _material(queue, root, current, live=live)
            if plan.get("task_context") != context or plan.get("dependencies") != dependencies:
                raise DriverError("frozen task context or dependency outcomes changed")
            if validate_only:
                report = preflight(run_directory)
                if not all(report["checks"].values()):
                    raise DriverError("S0 offline validation failed; inspect preflight checks")
                return {"claim": claim, "binding": current, "preflight": report,
                        "model_turns": 0, "app_server_launches": 0}
            # Queue remains read-only throughout. Its acceptance cannot be changed into a dispatch.
            outcome = run(run_directory, authorization=model_authorization if live else authorization,
                          accepted_binding=current, lab_risk_ack=lab_risk_ack, dispatch_authorization=authorization)
            try:
                publish_event(run_directory / "spool", {
                    "schema_version": 1, "source": "supervisor-s2-bridge",
                    "agent_id": "supervisor-s2-bridge", "run_id": plan["run_id"],
                    "origin_id": plan["run_id"], "source_sequence": 1,
                    "type": "agent.note", "visibility": "observer", "correlation": {"task": claim},
                    "summary": (("Live" if live else "Synthetic") + " dispatch completed; answer requires operator review"
                                if outcome["state"] == "completed" else
                                ("Live" if live else "Synthetic") + " dispatch blocked; operator inspection required"),
                })
            except (JournalError, ValueError):
                # Outcome was already committed. Do not replay dispatch after publication failure.
                write_record(run_directory / "publication-failed.json", {"dispatch_replay_permitted": False})
            return outcome


def inspect(state_directory, claim):
    if type(claim) is not str or len(claim) != 64 or any(char not in "0123456789abcdef" for char in claim):
        raise DriverError("invalid dispatch claim")
    return status(Path(state_directory) / claim)


def validate(queue_directory, state_directory, claim):
    """Offline exact Git/acceptance/dependency and S0 pin checks; no authorization."""
    view = inspect(state_directory, claim)
    return dispatch(queue_directory, state_directory, claim, None,
                    live=view["kind"] == "live", validate_only=True)
