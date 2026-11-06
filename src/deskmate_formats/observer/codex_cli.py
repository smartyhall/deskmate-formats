"""Observe a deliberately launched, version-checked Codex CLI invocation."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

from ._private_storage import storage_directory
from .codex_exec import CodexExecAdapter, SUPPORTED_VERSION
from .event_cli import add_journal_options, journal_limits
from .events import EventError
from .journal import JournalBusy, JournalError, JournalLimits, publish_event, read_journal
from .process_health import process_claim

_HEARTBEAT_SECONDS = 5
_DRAIN_SECONDS = 2
_POLL_SECONDS = 0.02
_BUSY_SECONDS = 0.5
_CHUNK_BYTES = 16 * 1024


def _warn(message):
    try:
        print(f"Codex telemetry: {message}", file=sys.stderr, flush=True)
    except OSError:
        pass


def _when_unlocked(operation, *args, **kwargs):
    deadline = monotonic() + _BUSY_SECONDS
    while True:
        try:
            return operation(*args, **kwargs)
        except JournalBusy:
            # This exception guarantees no append was attempted.
            if monotonic() >= deadline:
                raise
            sleep(_POLL_SECONDS)


class _Publisher:
    def __init__(self, journal, limits, adapter):
        self.journal = journal
        self.limits = limits
        self.adapter = adapter
        self.enabled = True

    def write(self, payload):
        if self.enabled:
            try:
                _when_unlocked(publish_event, self.journal, payload, limits=self.limits)
            except (JournalError, EventError):
                self.enabled = False
                _warn("journal publication stopped; inspect the private journal before retrying")

    def event(self, kind, summary, **kwargs):
        if self.enabled:
            self.write(self.adapter.event(kind, summary, **kwargs))


@contextmanager
def _observe_console_interrupt():
    received = False

    def mark_received(*_):
        nonlocal received
        received = True

    # The child shares the foreground group and receives terminal Ctrl+C itself.
    # Only observe that signal here. There is no second interrupt or escalation.
    previous = signal.signal(signal.SIGINT, mark_received)
    try:
        yield lambda: received
    finally:
        signal.signal(signal.SIGINT, previous)


def _exit_was_interrupt(code):
    return (code & 0xFFFFFFFF) == 0xC000013A if os.name == "nt" else code == -signal.SIGINT


def _raw_stdout():
    stream = sys.stdout.buffer
    # A failed buffered flush can leave pending bytes and replace the child's
    # status with Python's shutdown error. Write directly to the binary sink.
    return getattr(stream, "raw", stream)


def _forward(output, data):
    remaining = memoryview(data)
    while remaining:
        count = output.write(remaining)
        if not count:
            raise OSError("raw stdout made no progress")
        remaining = remaining[count:]
    output.flush()


def _record_exit(publisher, code, end_reason, disconnected, interrupt_received):
    adapter = publisher.adapter
    details = {"exit_code": code, "turn_state": adapter.turn_state or "unreported",
               "unfinished_items": adapter.unfinished_items, "console_interrupt_received": interrupt_received}
    interrupted_turn = adapter.turn_state == "running" and _exit_was_interrupt(code)
    if interrupted_turn:
        publisher.event("turn.interrupted", "Codex process interrupted while turn was last reported open",
                        details={**details, "evidence": "os-interrupt-exit"}, severity="warning")
    elif adapter.turn_state not in ("completed", "failed"):
        publisher.event("source.error", "Codex exited without a reported turn outcome",
                        details=details, severity="warning")
    publisher.event("process.exited", f"Codex process exited (status {code})", details=details,
                    severity="error" if code and not _exit_was_interrupt(code) else "info")
    if not disconnected or interrupted_turn:
        publisher.event("source.disconnected", end_reason)


def _capture(child, publisher, raw_output, interrupted):
    fd = child.stdout.fileno()
    claim = process_claim(child.pid)
    publisher.event("process.heartbeat", "Codex child launched", process=claim,
                    details={"child_pid": child.pid})
    heartbeat_at = monotonic() + _HEARTBEAT_SECONDS
    drain_until = None
    interrupt_logged = False
    disconnected = False
    end_reason = None
    try:
        os.set_blocking(fd, False)
    except OSError:
        end_reason = "Codex JSONL pipe could not be configured"

    while True:
        code = child.poll()
        now = monotonic()
        if code is not None and drain_until is None:
            drain_until = now + _DRAIN_SECONDS
        if interrupted() and not interrupt_logged:
            publisher.event("source.error", "Console interrupt observed by the wrapper", severity="warning")
            interrupt_logged = True

        data = None
        if end_reason is None:
            if drain_until is not None and now >= drain_until:
                end_reason = "Codex JSONL drain deadline expired after child exit"
            else:
                try:
                    data = os.read(fd, _CHUNK_BYTES)
                except BlockingIOError:
                    pass
                except OSError:
                    end_reason = "Codex JSONL pipe read failed"
                else:
                    if not data:
                        end_reason = "Codex JSONL stdout closed"
        if data:
            if raw_output is not None:
                try:
                    _forward(raw_output, data)
                except OSError:
                    _warn("raw stdout forwarding stopped")
                    raw_output = None
            if publisher.enabled:
                for event in publisher.adapter.feed(data):
                    publisher.write(event)
                    if not publisher.enabled:
                        break
        elif end_reason is not None and not child.stdout.closed:
            child.stdout.close()
            if publisher.enabled and (tail := publisher.adapter.finish()) is not None:
                publisher.write(tail)
            if code is None:
                publisher.event("source.disconnected", end_reason)
                disconnected = True

        if end_reason is not None and code is not None:
            _record_exit(publisher, code, end_reason, disconnected, interrupted())
            return code
        if code is None and now >= heartbeat_at:
            claim = claim or process_claim(child.pid)
            publisher.event("process.heartbeat", "Codex child still running", process=claim)
            heartbeat_at = now + _HEARTBEAT_SECONDS
        if not data:
            sleep(_POLL_SECONDS)


def capture_codex(argv, journal, *, version, agent_id="codex", visibility="private",
                  limits=JournalLimits(), raw_output=None):
    """Launch one trusted argv, capture stdout, and return its exact Popen status.

    Run from the main thread. The CLI verifies the executable's version before
    calling this function. A caller can supply a synthetic child in offline tests.
    """
    adapter = CodexExecAdapter(version, run_id=f"codex-{uuid4().hex}", agent_id=agent_id, visibility=visibility)
    try:
        journal = storage_directory(journal, create=True)
    except OSError:
        raise JournalError("cannot prepare private journal storage") from None
    replay = _when_unlocked(read_journal, journal, limits=limits)
    if replay.corrupt_lines or replay.at_capacity or replay.capacity_exceeded:
        raise JournalError("private journal requires recovery or rollover before launch")
    publisher = _Publisher(journal, limits, adapter)
    with _observe_console_interrupt() as interrupted:
        try:
            child = subprocess.Popen(argv, stdout=subprocess.PIPE, bufsize=0)
        except OSError:
            publisher.event("source.error", "Codex child could not be launched", severity="error")
            raise
        with child:
            return _capture(child, publisher, raw_output, interrupted)


def _codex_version(executable):
    probe = subprocess.run([executable, "--version"], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=True)
    if probe.stdout.strip() != f"codex-cli {SUPPORTED_VERSION}".encode("ascii"):
        raise EventError(f"unsupported Codex exec version (requires {SUPPORTED_VERSION})")
    return SUPPORTED_VERSION


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        usage="%(prog)s [options] -- ABSOLUTE_CODEX_BINARY exec --json [Codex arguments]")
    add_journal_options(parser, publisher=True)
    parser.add_argument("--agent", default="codex", help="local agent ID (default codex)")
    parser.add_argument("--visibility", choices=("private", "observer"), default="private")
    parser.add_argument("--passthrough-stdout", action="store_true",
                        help="forward sensitive raw JSONL to your stdout")
    args = list(sys.argv[1:] if argv is None else argv)
    sep = args.index("--") if "--" in args else len(args)
    if sep == len(args) and "-h" not in args and "--help" not in args:
        parser.error("provide -- ABSOLUTE_CODEX_BINARY exec --json [Codex arguments]")
    options = parser.parse_args(args[:sep])
    command = args[sep + 1:]
    if command[1:3] != ["exec", "--json"]:
        parser.error("provide -- ABSOLUTE_CODEX_BINARY exec --json [Codex arguments]")
    executable = Path(command[0])
    if not executable.is_absolute() or (os.name == "nt" and executable.suffix.lower() != ".exe"):
        parser.error("specify an absolute path to the native Codex executable")
    journal = options.journal if options.journal is not None else os.environ.get("DESKMATE_OBSERVER_JOURNAL")
    if not journal:
        parser.error("set --journal or DESKMATE_OBSERVER_JOURNAL")
    limits = journal_limits(parser, options)
    try:
        version = _codex_version(command[0])
    except (OSError, subprocess.SubprocessError):
        _warn("could not verify Codex executable version")
        return 2
    except EventError as error:
        _warn(str(error))
        return 2
    try:
        code = capture_codex(command, journal, version=version, agent_id=options.agent,
                             visibility=options.visibility, limits=limits,
                             raw_output=_raw_stdout() if options.passthrough_stdout else None)
    except EventError as error:
        _warn(str(error))
        return 2
    except JournalError as error:
        _warn(str(error))
        return 1
    except OSError:
        _warn("could not launch the Codex executable")
        return 127
    return 128 - code if code < 0 and os.name != "nt" else code


if __name__ == "__main__":
    raise SystemExit(main())
