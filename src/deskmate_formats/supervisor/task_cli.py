"""Local, explicit task review commands."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .task_git import TrustedSource
from .task_manifest import MAX_MANIFEST_BYTES, TaskError, validate_manifest
from .task_queue import MAX_RECORDS, QueueError, QueueUnresolved, open_queue


def _json(value):
    print(json.dumps(value, sort_keys=True, indent=2))


def _candidate(candidate):
    return {"source": asdict(candidate.source), "review_token": candidate.review_token,
            "manifest": candidate.manifest}


def _receipt(receipt):
    return {
        **_candidate(receipt.candidate),
        "sequence": receipt.sequence, "state": receipt.state,
        "requested": receipt.requested, "reason": receipt.reason,
        "prepared_at": receipt.prepared_at, "resolved_at": receipt.resolved_at,
        "recovery_reason": receipt.recovery_reason,
    }


def _reason():
    raw = sys.stdin.buffer.read(2051)
    if len(raw) > 2050:
        raise TaskError("operator reason exceeds byte limit")
    try:
        text = raw.decode("utf-8")
        return text[:-2] if text.endswith("\r\n") else text.removesuffix("\n")
    except UnicodeError:
        raise TaskError("expected a UTF-8 operator reason on stdin") from None


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--queue", type=Path, help="dedicated private queue directory")
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("init", help="create a queue and bind its trusted source", allow_abbrev=False)
    create.add_argument("--checkout", type=Path, required=True)
    create.add_argument("--repository", required=True, help="canonical HTTPS origin")
    create.add_argument("--branch", required=True, help="name under refs/heads")
    create.add_argument("--anchor", required=True, help="full trusted Git commit ID")
    create.add_argument("--capacity", type=int, default=MAX_RECORDS)
    actions.add_parser("validate", help="validate manifest JSON on stdin", allow_abbrev=False)
    actions.add_parser("list", help="list private queue receipts and counts", allow_abbrev=False)
    for action in ("discover", "accept", "reject"):
        command = actions.add_parser(action, allow_abbrev=False)
        command.add_argument("commit", help="full Git commit ID of the configured branch tip")
        command.add_argument("path", help="exact path under ops/tasks")
        if action != "discover":
            command.add_argument("--review-token", required=True)
            command.add_argument("--reason-stdin", action="store_true", required=True,
                                 help="read the required UTF-8 decision reason from stdin")
    for action in ("inspect", "abandon"):
        command = actions.add_parser(action, allow_abbrev=False)
        command.add_argument("id")
        command.add_argument("revision", type=int)
        if action == "abandon":
            command.add_argument("--review-token", required=True)
            command.add_argument("--reason-stdin", action="store_true", required=True,
                                 help="read the required UTF-8 recovery reason from stdin")
    return parser


def _operate(args):
    if args.action == "validate":
        _json(validate_manifest(sys.stdin.buffer.read(MAX_MANIFEST_BYTES + 1)))
        return 0
    if args.action == "init":
        source = TrustedSource(args.checkout, args.repository, args.branch, args.anchor)
        with open_queue(args.queue, source=source, capacity=args.capacity):
            pass
        print("Initialized private task queue")
        return 0
    reason = _reason() if getattr(args, "reason_stdin", False) else None
    with open_queue(args.queue) as queue:
        if args.action == "discover":
            _json(_candidate(queue.discover(args.commit, args.path)))
        elif args.action == "list":
            print(f"{'Task':64} {'Revision':>10} {'State':12} Timestamp (UTC)")
            for row in queue.list():
                print(f"{row.id:64} {row.revision:10} {row.state:12} {row.resolved_at or row.prepared_at}")
            counts = queue.counts()
            print(", ".join(f"{state}={count}" for state, count in counts.items()))
        elif args.action == "inspect":
            row = queue.get(args.id, args.revision)
            if row is None:
                print("Task revision is absent", file=sys.stderr)
                return 3
            _json(_receipt(row))
        elif args.action == "abandon":
            _json(_receipt(queue.abandon(args.id, args.revision, args.review_token, reason)))
        else:
            decision = {"accept": "accepted", "reject": "rejected"}[args.action]
            row, created = queue.decide(args.commit, args.path, args.review_token, decision, reason)
            _json({**_receipt(row), "created": created})
    return 0


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action != "validate" and args.queue is None:
        parser.error("--queue is required for this command")
    try:
        return _operate(args)
    except (TaskError, QueueError) as error:
        print(str(error), file=sys.stderr)
        if isinstance(error, TaskError):
            return 2
        return 5 if isinstance(error, QueueUnresolved) else 4
    except KeyboardInterrupt:
        print("Interrupted; inspect the private queue before retrying a decision", file=sys.stderr)
        return 130
    except OSError:
        print("Local input or output failed; inspect the private queue before retrying a decision",
              file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
