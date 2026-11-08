"""Offline-only S2: separate preparation, authorization and synthetic dispatch."""

import argparse
import json
from pathlib import Path
import sys

from .bridge import dispatch, grant, inspect
from .synthetic_peer import MODES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--state", type=Path, required=True, help="one dedicated private bridge directory per S1 queue")
    commands = parser.add_subparsers(dest="action", required=True)
    prep = commands.add_parser("prepare-synthetic", help="accepted receipt to unconsumed dispatch grant", allow_abbrev=False)
    prep.add_argument("--queue", type=Path, required=True)
    prep.add_argument("id")
    prep.add_argument("revision", type=int)
    prep.add_argument("--accepted-review-token", required=True)
    prep.add_argument("--scenario", choices=MODES, default="success")
    send = commands.add_parser("dispatch-synthetic", help="explicit one-shot gate; never triggered by Git", allow_abbrev=False)
    send.add_argument("--queue", type=Path, required=True)
    send.add_argument("claim")
    send.add_argument("--authorize-dispatch", required=True)
    view = commands.add_parser("inspect", help="offline durable receipt", allow_abbrev=False)
    view.add_argument("claim")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare-synthetic":
            result = grant(args.queue, args.state, args.id, args.revision, args.accepted_review_token, mode=args.scenario)
        elif args.action == "dispatch-synthetic":
            result = dispatch(args.queue, args.state, args.claim, args.authorize_dispatch)
        else:
            result = inspect(args.state, args.claim)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 5 if result.get("state") == "blocked" else 0
    except KeyboardInterrupt:
        print("Interrupted; inspect the dispatch receipt, never automatically redispatch.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        print("Bridge refused or stopped; inspect the private accepted receipt and dispatch grant.", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
