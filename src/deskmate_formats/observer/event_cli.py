"""Publish one explicit event to a private local Observatory journal."""

import argparse
from dataclasses import asdict
import json
import os
import sys

from .events import EVENT_TYPES, MAX_INPUT_BYTES, SCHEMA_VERSION, SEVERITIES, EventError, decode_json
from .journal import DEFAULT_MAX_BYTES, DEFAULT_MAX_RECORDS, JournalError, JournalLimits, publish_event


def add_journal_options(parser, *, publisher=False):
    parser.add_argument("--journal", help="private journal directory outside Git" + (
        " (or DESKMATE_OBSERVER_JOURNAL)" if publisher else " (explicitly enables the agent feed)"
    ))
    parser.add_argument("--journal-max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help="shared journal byte cap (default 16 MiB)")
    parser.add_argument("--journal-max-records", type=int, default=DEFAULT_MAX_RECORDS,
                        help="shared journal record cap (default 10000)")


def journal_limits(parser, args):
    try:
        return JournalLimits(args.journal_max_bytes, args.journal_max_records)
    except ValueError as error:
        parser.error(str(error))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    add_journal_options(parser, publisher=True)
    parser.add_argument("--json", action="store_true", help="read a single UTF-8 event object from stdin")
    parser.add_argument("--agent", dest="agent_id")
    parser.add_argument("--origin", dest="origin_id")
    parser.add_argument("--run", dest="run_id")
    parser.add_argument("--seq", dest="source_sequence", type=int)
    parser.add_argument("--type", choices=sorted(EVENT_TYPES))
    parser.add_argument("--summary")
    parser.add_argument("--source")
    parser.add_argument("--severity", choices=sorted(SEVERITIES))
    parser.add_argument("--machine", dest="machine_ids", action="append")
    parser.add_argument("--visibility", choices=("private", "observer"))
    parser.add_argument("--correlate", action="append", metavar="KIND=ID")
    args = parser.parse_args(argv)
    journal = args.journal if args.journal is not None else os.environ.get("DESKMATE_OBSERVER_JOURNAL")
    if not journal:
        parser.error("set --journal or DESKMATE_OBSERVER_JOURNAL")
    limits = journal_limits(parser, args)
    fields = {key: value for key, value in vars(args).items() if value is not None and key not in (
        "journal", "journal_max_bytes", "journal_max_records", "json", "correlate",
    )}
    if args.json and (fields or args.correlate):
        parser.error("--json cannot be combined with event flags")
    try:
        if args.json:
            payload = decode_json(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        else:
            payload = {"schema_version": SCHEMA_VERSION, "source": "explicit", **fields}
            if args.correlate:
                correlation = {}
                for pair in args.correlate:
                    key, separator, value = pair.partition("=")
                    if not separator or key in correlation:
                        raise EventError("expected unique --correlate KIND=ID values")
                    correlation[key] = value
                payload["correlation"] = correlation
        receipt = publish_event(journal, payload, limits=limits)
    except EventError as error:
        print(f"event rejected: {error}", file=sys.stderr)
        return 2
    except JournalError as error:
        print(f"event journal: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("event input could not be read", file=sys.stderr)
        return 1
    print(json.dumps(asdict(receipt), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
