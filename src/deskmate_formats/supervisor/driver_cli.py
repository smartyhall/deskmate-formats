"""Explicit local S0 preparation, synthetic execution and gated live canary."""

import argparse
import json
from pathlib import Path
import sys

from .driver import prepare, reconcile_synthetic, run, status
from .synthetic_peer import MODES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--run", type=Path, required=True, help="new dedicated private directory outside Git")
    commands = parser.add_subparsers(dest="action", required=True)
    prep = commands.add_parser("prepare", help="freeze plan; no app-server/model launch", allow_abbrev=False)
    prep.add_argument("--executable", type=Path, help="absolute pinned native codex.exe; omit for synthetic peer")
    prep.add_argument("--model", help="operator-selected live model; no default")
    prep.add_argument("--effort", choices=("low", "medium", "high"), help="reviewed live model reasoning effort; no default")
    prep.add_argument("--scenario", choices=MODES, default="success")
    commands.add_parser("status", help="offline private inspection / dry run", allow_abbrev=False)
    synthetic = commands.add_parser("synthetic", help="explicit synthetic dispatch", allow_abbrev=False)
    synthetic.add_argument("--authorize-plan", required=True)
    reconcile = commands.add_parser("reconcile-synthetic", help="read-only synthetic restart only", allow_abbrev=False)
    reconcile.add_argument("--authorize-plan", required=True)
    live = commands.add_parser("live", help="STOP: requires NEW explicit operator model-use authorization", allow_abbrev=False)
    live.add_argument("--authorize-live-plan", required=True,
                      help="exact digest reviewed in the separately authorized live experiment")
    live.add_argument("--isolation-reviewed", required=True, help="same plan digest after effective configuration review")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = {"plan_sha256": prepare(args.run, executable=args.executable, model=args.model, effort=args.effort, mode=args.scenario)}
        elif args.action == "status":
            result = status(args.run)
        else:
            current = status(args.run)
            if args.action == "reconcile-synthetic":
                result = reconcile_synthetic(args.run, authorization=args.authorize_plan)
            else:
                expected = "live" if args.action == "live" else "synthetic"
                if current["kind"] != expected:
                    parser.error("command and prepared worker kind differ")
                result = run(args.run, authorization=args.authorize_live_plan if expected == "live" else args.authorize_plan,
                             isolation_reviewed=getattr(args, "isolation_reviewed", None))
        print(json.dumps(result, sort_keys=True, indent=2))
        return 5 if isinstance(result, dict) and result.get("state") == "blocked" else 0
    except KeyboardInterrupt:
        print("Interrupted; inspect durable receipts. Do not redispatch.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        print("Driver refused or stopped; inspect private plan/receipts. No automatic retry.", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
