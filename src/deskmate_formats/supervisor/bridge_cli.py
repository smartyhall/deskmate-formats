"""Manual S2: separate Git acceptance, frozen preparation and one-shot dispatch."""

import argparse
import json
from pathlib import Path
import sys

from .bridge import dispatch, grant, inspect, validate
from .driver import DriverError
from .task_manifest import TaskError
from .synthetic_peer import MODES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--state", type=Path, required=True, help="one dedicated private bridge directory per S1 queue")
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare-synthetic", "prepare-live"):
        prep = commands.add_parser(name, help="freeze accepted text-analysis task; no model usage", allow_abbrev=False)
        prep.add_argument("--queue", type=Path, required=True)
        prep.add_argument("id")
        prep.add_argument("revision", type=int)
        prep.add_argument("--accepted-review-token", required=True)
        if name == "prepare-synthetic":
            prep.add_argument("--scenario", choices=MODES, default="success")
        else:
            prep.add_argument("--executable", type=Path, required=True)
            prep.add_argument("--profile", choices=("experimental-lab",), required=True)
            prep.add_argument("--auth-file", type=Path, required=True)
            prep.add_argument("--model", required=True, help="exact operator-selected model; no fallback")
            prep.add_argument("--effort", choices=("low", "medium", "high"), required=True)
    for name in ("dispatch-synthetic", "dispatch-live"):
        send = commands.add_parser(name, help="explicit one-shot gate; never triggered by Git", allow_abbrev=False)
        send.add_argument("--queue", type=Path, required=True)
        send.add_argument("claim")
        send.add_argument("--authorize-dispatch", required=True)
        if name == "dispatch-live":
            send.add_argument("--authorize-live-plan", required=True, help="separate exact-plan model-use grant")
            send.add_argument("--accept-lab-risk", required=True, help="separate exact-plan experimental lab acknowledgment")
    check = commands.add_parser("validate", help="offline Git, acceptance, dependency and S0 pin checks", allow_abbrev=False)
    check.add_argument("--queue", type=Path, required=True)
    check.add_argument("claim")
    view = commands.add_parser("inspect", help="offline durable receipt", allow_abbrev=False)
    view.add_argument("claim")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare-synthetic":
            result = grant(args.queue, args.state, args.id, args.revision, args.accepted_review_token, mode=args.scenario)
        elif args.action == "prepare-live":
            result = grant(args.queue, args.state, args.id, args.revision, args.accepted_review_token,
                           executable=args.executable, profile=args.profile, model=args.model,
                           effort=args.effort, auth_file=args.auth_file)
        elif args.action == "dispatch-synthetic":
            result = dispatch(args.queue, args.state, args.claim, args.authorize_dispatch)
        elif args.action == "dispatch-live":
            result = dispatch(args.queue, args.state, args.claim, args.authorize_dispatch, live=True,
                              model_authorization=args.authorize_live_plan, lab_risk_ack=args.accept_lab_risk)
        elif args.action == "validate":
            result = validate(args.queue, args.state, args.claim)
        else:
            result = inspect(args.state, args.claim)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 5 if result.get("state") == "blocked" else 0
    except KeyboardInterrupt:
        print("Interrupted; inspect the dispatch receipt, never automatically redispatch.", file=sys.stderr)
        return 130
    except (DriverError, TaskError) as error:
        # These diagnostics are fixed descriptions; never echo lower-trust task text.
        print(str(error), file=sys.stderr)
        return 4
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        print("Bridge refused or stopped; inspect the private accepted receipt and dispatch grant.", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
