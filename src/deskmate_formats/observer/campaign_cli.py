"""Render a frozen campaign snapshot for operators. Read-only by construction."""

import argparse
from datetime import UTC, datetime
import sys

from . import campaigns


def _now(value):
    if value is None:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise campaigns.CampaignSnapshotError("--now must be an ISO UTC timestamp") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--snapshot", required=True, help="frozen campaign snapshot JSON")
    parser.add_argument("--format", choices=("json", "text", "html"), default="text")
    parser.add_argument("--now", help="ISO UTC reference time for freshness")
    parser.add_argument("--stale-seconds", type=float, default=campaigns.MAX_STALE_SECONDS)
    args = parser.parse_args(argv)
    try:
        snapshot = campaigns.load(args.snapshot)
        view = campaigns.projection(snapshot, now=_now(args.now),
                                    stale_seconds=args.stale_seconds)
        _, body = campaigns.render(view, args.format)
    except (campaigns.CampaignSnapshotError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
