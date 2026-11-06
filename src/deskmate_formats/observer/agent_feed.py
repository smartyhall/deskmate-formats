"""Independent journal polling and publication of immutable, sanitized snapshots."""

from contextlib import nullcontext
from pathlib import Path
from threading import Event, Thread
from time import monotonic_ns

from .agents import AgentProjection
from .agent_http import MAX_PAGE
from .agent_publication import AgentPublication, AgentSnapshot
from .event_cli import add_journal_options, journal_limits
from .journal import JournalBusy, JournalError, JournalLimits, read_journal


class AgentJournalFeed:
    """Poll the local spool independently of browser traffic. Use as a context manager."""

    def __init__(self, path, *, limits=JournalLimits(), interval=1.0, quiet_seconds=120, stale_seconds=600):
        if not 0.05 <= interval <= 60:
            raise ValueError("invalid agent journal polling interval")
        self.publication = AgentPublication()
        self._path = Path(path).absolute()
        self._limits = limits
        self._interval = interval
        self._thresholds = {"quiet_seconds": quiet_seconds, "stale_seconds": stale_seconds}
        self._projection = AgentProjection((), started_ns=0, scanned_ns=0, **self._thresholds)
        self._replay = None
        self._collector = "waiting"
        self._stop = Event()
        self._thread = Thread(target=self._poll, name="observatory-agent-feed")

    def _refresh(self):
        previous = self._replay
        try:
            replay = read_journal(self._path, limits=self._limits, unchanged=previous.fingerprint if previous else None)
        except JournalBusy:
            collector = "busy"
        except JournalError:
            collector = "unavailable"
        else:
            if replay is None:
                collector = self._collector
            elif replay.fingerprint is None:
                collector = "unavailable" if previous else "waiting"
            elif previous and (replay.fingerprint[:2] != previous.fingerprint[:2]
                               or replay.records[:len(previous.records)] != previous.records):
                # Preserve the last publication if an active journal is replaced or edited.
                collector = "unavailable"
            else:
                self._projection = AgentProjection(replay.records, started_ns=self._started_ns,
                                                   scanned_ns=monotonic_ns(), **self._thresholds)
                self._replay = replay
                self._collector = ("degraded" if replay.corrupt_lines or replay.tail_bytes or replay.capacity_exceeded
                                   else "full" if replay.at_capacity else "ready")
                collector = self._collector
        self.publication._snapshot = AgentSnapshot(collector, self._projection.views(monotonic_ns()),
                                                   self._projection.events)

    def _poll(self):
        while not self._stop.wait(self._interval):
            self._refresh()

    def __enter__(self):
        if self._stop.is_set() or self._thread.is_alive():
            raise RuntimeError("agent feed contexts are single use")
        self._started_ns = monotonic_ns()
        self._refresh()
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()


def add_viewer_options(parser):
    add_journal_options(parser)
    parser.add_argument("--agent-page-limit", type=int, choices=range(1, MAX_PAGE + 1), default=MAX_PAGE,
                        metavar="1..100", help="maximum rows per agent or event response")
    parser.add_argument("--agent-quiet-seconds", type=float, default=120)
    parser.add_argument("--agent-stale-seconds", type=float, default=600)


def configured_feed(parser, args):
    limits = journal_limits(parser, args)
    if args.journal is None:
        return nullcontext(None)
    if not args.journal:
        parser.error("--journal requires a directory")
    try:
        return AgentJournalFeed(args.journal, limits=limits, quiet_seconds=args.agent_quiet_seconds,
                                stale_seconds=args.agent_stale_seconds)
    except ValueError as error:
        parser.error(str(error))
