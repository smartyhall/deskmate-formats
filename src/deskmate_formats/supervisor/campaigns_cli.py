"""Local campaign ownership and resource-lease commands.

This is the operator-facing view of the private registry. It is not a remote
service and it never publishes local paths or process identities: ``export``
writes a public-safe summary for the read-only Observatory projection.
"""

import argparse
import json
from pathlib import Path
import sys

from deskmate_formats.observer.process_health import process_claim

from . import campaigns


def _json(value):
    print(json.dumps(value, sort_keys=True, indent=2, default=str))


def _campaign(record):
    return {"id": record.id, "owner": record.owner, "provider": record.provider,
            "branch": record.branch, "status": record.status,
            "base_commit": record.base_commit, "created_at": record.created_at,
            "updated_at": record.updated_at}


def _lease(lease):
    return None if lease is None else {
        "resource": lease.resource, "campaign": lease.campaign, "expires_at": lease.expires_at,
        "stale": lease.stale, "owner_alive": lease.owner_alive}


def _parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--registry", type=Path, required=True, help="private registry directory")
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("init", allow_abbrev=False)
    register = actions.add_parser("register", allow_abbrev=False)
    register.add_argument("id")
    register.add_argument("--owner", required=True)
    register.add_argument("--provider", required=True)
    register.add_argument("--branch", required=True)
    register.add_argument("--worktree", required=True)
    register.add_argument("--purpose", required=True)
    register.add_argument("--base-commit")
    register.add_argument("--status", default="active")
    actions.add_parser("list", allow_abbrev=False)
    status = actions.add_parser("set-status", allow_abbrev=False)
    status.add_argument("id")
    status.add_argument("status")
    status.add_argument("--reason")
    handoff = actions.add_parser("handoff", allow_abbrev=False)
    handoff.add_argument("id")
    handoff.add_argument("--owner", required=True)
    lease = actions.add_parser("lease", allow_abbrev=False)
    lease.add_argument("id")
    lease.add_argument("--resource", required=True)
    lease.add_argument("--ttl", type=float, default=900)
    release = actions.add_parser("release", allow_abbrev=False)
    release.add_argument("id")
    release.add_argument("--resource", required=True)
    reclaim = actions.add_parser("reclaim", allow_abbrev=False)
    reclaim.add_argument("id")
    reclaim.add_argument("--resource", required=True)
    reclaim.add_argument("--reason", required=True)
    export = actions.add_parser("export", allow_abbrev=False)
    export.add_argument("--output", type=Path, required=True)
    return parser


def _run(args):
    if args.action == "init":
        with campaigns.open_registry(args.registry, create=True):
            pass
        print("Initialized private campaign registry")
        return 0
    with campaigns.open_registry(args.registry) as registry:
        if args.action == "register":
            _json(_campaign(registry.register(
                args.id, owner=args.owner, provider=args.provider, branch=args.branch,
                worktree=args.worktree, purpose=args.purpose,
                base_commit=args.base_commit, status=args.status)))
        elif args.action == "list":
            _json({"campaigns": [_campaign(item) for item in registry.campaigns()],
                   "leases": [_lease(item) for item in registry.leases()]})
        elif args.action == "set-status":
            _json(_campaign(registry.set_status(args.id, args.status, reason=args.reason)))
        elif args.action == "handoff":
            _json(_campaign(registry.handoff(args.id, owner=args.owner)))
        elif args.action == "lease":
            claim = process_claim()
            if claim is None:
                raise campaigns.RegistryError("could not establish the owning process identity")
            _json(_lease(registry.acquire(args.resource, args.id, pid=claim["pid"],
                                          process_identity=claim["identity"],
                                          ttl_seconds=args.ttl)))
        elif args.action == "release":
            _json({"released": registry.release(args.resource, args.id)})
        elif args.action == "reclaim":
            _json(_lease(registry.reclaim(args.resource, args.id,
                                          operator_reason=args.reason)))
        else:
            _json(campaigns.export(registry, args.output))
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        return _run(args)
    except campaigns.RegistryBusy as error:
        print(str(error), file=sys.stderr)
        return 4
    except campaigns.RegistryError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("Private registry storage is unavailable or busy", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("Interrupted; inspect the registry before retrying", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
