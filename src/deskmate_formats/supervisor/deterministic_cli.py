"""Local, explicit deterministic attempt commands.

Every mutation has two steps, matching the existing supervisor discipline:
prepare freezes an immutable plan and prints its digest, and run requires that
exact digest back. Nothing is dispatched by inspecting a plan.
"""

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from deskmate_formats.observer.process_health import process_claim

from . import campaigns, deterministic, procedures
from .task_manifest import TaskError
from .task_queue import QueueError, QueueUnresolved, open_queue


def _json(value):
    print(json.dumps(value, sort_keys=True, indent=2, default=str))


def _arguments(raw):
    try:
        value = json.loads(raw)
    except ValueError:
        raise TaskError("--arguments must be a JSON object") from None
    if type(value) is not dict:
        raise TaskError("--arguments must be a JSON object")
    return value


def _reservation(registry_directory, ttl_seconds):
    """Lease the owned worktree for the duration of one attempt."""
    def reserve(plan):
        claim = process_claim(os.getpid())
        if claim is None:
            raise TaskError("could not establish the owning process identity")
        resource = f"worktree:{plan['campaign']}"
        with campaigns.open_registry(registry_directory) as registry:
            registry.acquire(resource, plan["campaign"], pid=claim["pid"],
                             process_identity=claim["identity"], ttl_seconds=ttl_seconds)

        def release():
            with campaigns.open_registry(registry_directory) as registry:
                registry.release(resource, plan["campaign"])
        return release
    return reserve


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("procedures", help="list reviewed deterministic procedures", allow_abbrev=False)
    prepare = actions.add_parser("prepare", help="freeze a local attempt plan", allow_abbrev=False)
    prepare.add_argument("--state", type=Path, required=True)
    prepare.add_argument("--campaign", required=True)
    prepare.add_argument("--procedure", required=True)
    prepare.add_argument("--arguments", default="{}")
    prepare.add_argument("--working-directory", type=Path, required=True)
    prepare.add_argument("--source-commit")
    prepare.add_argument("--timeout", type=float)
    task = actions.add_parser("prepare-task", help="freeze an accepted trusted Git task",
                              allow_abbrev=False)
    task.add_argument("--state", type=Path, required=True)
    task.add_argument("--campaign", required=True)
    task.add_argument("--queue", type=Path, required=True)
    task.add_argument("--working-directory", type=Path, required=True)
    task.add_argument("id")
    task.add_argument("revision", type=int)
    task.add_argument("--review-token", required=True)
    task.add_argument("--timeout", type=float)
    for action in ("run", "status", "recover"):
        command = actions.add_parser(action, allow_abbrev=False)
        command.add_argument("--state", type=Path, required=True)
        if action == "run":
            command.add_argument("--authorization", required=True)
            command.add_argument("--registry", type=Path)
            command.add_argument("--lease-seconds", type=float, default=900)
    cancel = actions.add_parser("cancel", allow_abbrev=False)
    cancel.add_argument("--state", type=Path, required=True)
    cancel.add_argument("--authorization", required=True)
    return parser


def _run(args):
    if args.action == "procedures":
        _json({"procedures": procedures.catalog()})
        return 0
    if args.action == "prepare":
        attempt = deterministic.prepare(
            args.state, campaign=args.campaign, procedure=args.procedure,
            arguments=_arguments(args.arguments), working_directory=str(args.working_directory),
            source_commit=args.source_commit, timeout_seconds=args.timeout)
        _json({"attempt_id": attempt.attempt_id, "procedure": attempt.procedure,
               "plan_sha256": attempt.plan_sha256, "state": attempt.state,
               "authorization_required": True})
        return 0
    if args.action == "prepare-task":
        with open_queue(args.queue) as queue:
            binding = deterministic.accepted(queue, args.id, args.revision, args.review_token)
            context = queue.execution_context(queue.get(args.id, args.revision).candidate)
            if context["class"] != "deterministic-v1":
                raise TaskError("accepted revision is not a deterministic task")
            attempt = deterministic.prepare(
                args.state, campaign=args.campaign, procedure=binding["procedure"],
                arguments=binding["arguments"], working_directory=str(args.working_directory),
                source_commit=binding["source"]["commit"], timeout_seconds=args.timeout)
        _json({"attempt_id": attempt.attempt_id, "procedure": attempt.procedure,
               "plan_sha256": attempt.plan_sha256, "state": attempt.state,
               "binding": binding, "authorization_required": True})
        return 0
    if args.action == "run":
        reservation = None
        if args.registry is not None:
            reservation = _reservation(args.registry, args.lease_seconds)
        _json(deterministic.run(args.state, authorization=args.authorization,
                                reservation=reservation))
        return 0
    if args.action == "status":
        view = deterministic.status(args.state)
        _json(view)
        return 0 if not view["requires_inspection"] else 3
    if args.action == "cancel":
        deterministic.cancel(args.state, authorization=args.authorization)
        _json({"cancel_requested": True})
        return 0
    _json(deterministic.recover(args.state))
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        return _run(args)
    except campaigns.RegistryBusy as error:
        print(str(error), file=sys.stderr)
        return 4
    except (TaskError, deterministic.DeterministicError, procedures.ProcedureError,
            campaigns.RegistryError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except QueueUnresolved as error:
        print(str(error), file=sys.stderr)
        return 5
    except (QueueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("Interrupted; inspect the attempt directory before retrying", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
