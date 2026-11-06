# Observatory v2 event feed and private journal

M0/M1 adds a standalone event publisher, a private JSONL journal and a
localhost browser feed. The event publisher and its Python API work without
86Box, DeskMate, Codex, Ghidra, Pillow or MCP. The original [machine observer](86box-observer-design.md)
and [native owner's approval policy](86box-readonly-mcp.md#enable-browser-publication)
remain separate from agent events. This guide describes the implemented subset
of the [v2 specification](observatory-v2-spec.md). M2 adds the
[Codex CLI adapter and wrapper](observatory-v2-m2.md) as another publisher.

## Run a synthetic demonstration

Install the package, then pick a new spool directory with an existing, trusted
parent outside Git. For example, in PowerShell use two terminals with the same
`$spool` value. The first publisher creates the directory and the viewer can
start before it exists.

```powershell
$spool = Join-Path $env:LOCALAPPDATA 'observatory-example'
deskmate-86box-observer --journal $spool --text-only --instances 2
```

Open `http://127.0.0.1:8086/` and run the publisher in the second terminal.
The modern dashboard shows the newest runs and events. The classic HTML, text,
PNG and GIF behavior follows the original machine observer. Omit `--text-only`
after installing `deskmate-formats[observer]` to see synthetic frames.

```powershell
deskmate-observer-event --journal $spool --agent synthetic-a --origin example-a --run example-run --seq 1 --type session.started --machine synthetic-rsx --visibility observer --summary 'Synthetic session started'
deskmate-observer-event --journal $spool --agent synthetic-b --origin example-b --run example-run --seq 1 --type test.completed --machine synthetic-at --visibility observer --summary 'Four synthetic checks passed'
deskmate-observer-event --journal $spool --agent synthetic-c --origin example-c --run example-run --seq 1 --type approval.requested --correlate approval=example-1 --visibility observer --summary 'Simulated checkpoint approval'
```

For a real, configured machine observer, pass `--journal <directory>` to
`deskmate-86box-mcp --config <private-config>` with the existing observer enabled.
One background reader refreshes a sanitized immutable snapshot once per second.
It never uses the native owner. A browser GET or HEAD only reads the latest
snapshot and the already-published machine data. Closing a browser changes
neither publication schedule. Stop the synthetic observer with Ctrl+C and the
MCP listener by closing its stdio client. Both stop their event reader and
close their listener. Starting either again replays committed history.

## Publisher contract

Use `--journal` or set `DESKMATE_OBSERVER_JOURNAL` for the publisher. The
observer requires the explicit flag. The concise CLI supplies schema version
`1` and source `explicit`. `--json` reads one complete UTF-8 event object from
standard input through EOF and is mutually exclusive with event flags. Use it
for structured or sensitive fields to keep them out of process arguments.

```powershell
@'
{"schema_version":1,"source":"test-runner","origin_id":"synthetic-tests-01","agent_id":"synthetic-tests","run_id":"test-run-01","source_sequence":1,"type":"test.completed","summary":"Synthetic tests finished","details":{"passed":4,"failed":0,"skipped":1}}
'@ | deskmate-observer-event --journal $spool --json
```

Exit `0` prints a JSON receipt with `cursor`, `event_id`, `ingested_at_utc`
and `recovered_tail_bytes`. Exit `2` rejects input or usage. Exit `1` reports
lock contention, retention or an I/O failure. A busy error explicitly indicates
that no append was attempted. After an uncertain append, inspect the private
replay for the intended origin/sequence before resubmitting. The CLI never
prints details or raw records in an acknowledgement or diagnostic.

For Python publishers, use `publish_event(path, payload, limits=...)` from
`deskmate_formats.observer.journal`. It returns a `Receipt`. Catch `EventError`
for invalid input or sequence, `JournalBusy` for a busy lock and `JournalError`
for other storage failures. `read_journal(path, limits=...)` is a **private**
operator/library interface. Its `Replay.records` include source metadata and
details. `process_claim(pid)` from `deskmate_formats.observer.process_health`
can supply the optional `process` object of a `process.heartbeat` for a live
local PID. It returns `None` if identity cannot be established.

```python
from deskmate_formats.observer.journal import publish_event

receipt = publish_event(spool_directory, {
    "schema_version": 1,
    "source": "experiment-script",
    "origin_id": "sample-publisher-01",
    "agent_id": "sample-agent",
    "run_id": "sample-run",
    "source_sequence": 1,
    "type": "experiment.checkpoint",
    "summary": "Reached fictional baseline",
    "visibility": "observer",
    "correlation": {"experiment": "sample"},
})
```

| Field | Validation and meaning |
| --- | --- |
| `schema_version` | Required integer `1`. Unsupported versions and unknown fields are rejected. |
| `source`, `origin_id`, `run_id`, `agent_id` | Required identifiers of 1–64 ASCII characters. They start with a lowercase letter or digit and may continue with those characters, dots, underscores and hyphens. Allocate one origin per producer/run and keep source, agent and run fixed for that origin. Independent producers may use the same agent and run with distinct origins. |
| `source_sequence` | Required integer `1..9007199254740991`, increasing within an origin. Gaps are accepted. Duplicate, conflicting and older sequences are rejected without moving the cursor. |
| `type` | Required exact normalized vocabulary in the specification, including lifecycle, plan, milestones, commands, tools, tests, Git, experiments, approvals and publication signals. |
| `summary`, `severity` | Required single printable summary of up to 240 characters. Severity defaults to `info` and accepts `debug`, `info`, `warning` or `error`. |
| `machine_ids` | Optional list of up to eight unique IDs, default empty. Machine IDs are associations, including IDs absent from the local registry. Each run row shows the latest visible association. |
| `source_time_utc` | Optional ISO UTC string ending in `Z` with up to six fractional digits. Valid dates can be arbitrarily skewed. They do not affect event order, liveness or elapsed time. |
| `correlation` | Optional map of `session`, `turn`, `command`, `tool`, `experiment`, `task`, `approval` and `test` to identifiers. Approval events require an `approval` ID. Use one approval ID for each request/resolution pair. |
| `details` | Optional private JSON object, up to 256 nodes, depth five below the root, up to 32 items per container and 1,024 printable characters per string value. Integers are exact up to `2^53−1` in magnitude and floats must be finite. Input and normalized event each have an 8,192-byte limit. |
| `process` | Optional `{"pid": ..., "identity": ...}` on `process.heartbeat` only. A PID alone is insufficient. The monitor verifies creation identity via a local Windows process handle or Linux boot ID and `/proc` start ticks. No executable paths or process identity tokens appear in the viewer. |
| `visibility` | `private` by default. `observer` opts the summary, IDs, severity, type and safe ingestion metadata into the local feed. Private events affect neither public history nor public agent state. Details and upstream timestamps stay private for both classes. Review visible fields before publishing. |

### Recovery and retention

The spool uses `events.jsonl` and a stable `writer.lock`. On POSIX the directory
and regular single-link files must be owned by the current account and have no
group or other permissions. On Windows a new directory receives a protected
DACL for its owner, local administrators and SYSTEM on a fixed drive, and
files must carry private ACLs. Use a trusted local parent and an ACL-capable
filesystem such as NTFS or a local POSIX filesystem. All publishers and readers
must use the same physical directory and cap settings. Git working trees,
redirected spool directories and linked journal files are rejected. Use the
same trusted OS account or an account with the explicitly granted Windows
rights. Origin IDs are producer declarations within that boundary. Repository
and distribution audits reject the spool filenames. Loopback HTTP is readable
by other local clients, so only opt in data safe for those clients.

One kernel lock serializes each read or write transaction (Windows byte-range
lock or POSIX `flock`). Writers validate before creating or modifying storage,
then verify source order and retention under the lock. An append writes a
bounded LF-delimited UTF-8 record and calls `fsync` before acknowledging. The
collector assigns a monotonically increasing cursor, ID, wall-clock UTC time
and host monotonic timestamp. One interleaved file preserves total ingestion
order across all origins and run IDs. The journal reader replays on changes
and the HTTP workers see only its published projection.

An unterminated final line is excluded from replay even if its JSON parses.
The next valid append truncates only that uncommitted tail and reports the
byte count. An LF-terminated malformed or logically inconsistent record is
skipped during replay so valid records can still be inspected. The writer
refuses to append to a journal with complete corruption, since a damaged line
may have held an acknowledged cursor or source sequence. Preserve that spool
for investigation and start a new epoch if needed. The reader exposes a
generic health status, and the private library reports the first corrupt line,
corruption count and tail size. A live reader preserves its last snapshot if
its spool disappears or prior committed records are edited.

The default cap is 16 MiB and 10,000 records, whichever comes first. Set the
same `--journal-max-bytes` (up to 100 MiB) and `--journal-max-records` (up to
10,000) on the viewer and every publisher if changing defaults. The cap fails
closed and preserves evidence. M0/M1 uses operator-controlled archive and
rollover instead of automatic size or age eviction. With all publishers and
readers stopped, archive the whole spool privately and switch to a new
directory. Set any age policy at this archive step. An epoch has its own
cursor namespace, so reset client cursors when switching spool directories.
Automatic retention across epochs would need a durable high-water index to
avoid cursor reuse and duplicate acceptance after removing source history.

A process crash releases the lock. Tests demonstrate recovery from a killed
writer and simulated partial writes. A flush error can leave a complete
record visible to replay even though the caller received an error. File sync
does not independently verify the drive write cache, a newly created directory
entry after power loss, or multi-host filesystem lock semantics. Power-loss
durability and hostile edits by principals with spool write access are outside
the guarantees. Keep private backups appropriate to the experiment.

## Read-only HTTP queries

All routes support GET and HEAD with the existing loopback Host and Origin
checks, no-store responses and bounded workers. Example queries follow.

```console
curl.exe "http://127.0.0.1:8086/api/v1/agents"
curl.exe "http://127.0.0.1:8086/api/v1/agents/synthetic-a"
curl.exe "http://127.0.0.1:8086/api/v1/agents/synthetic-a/events?after=0&limit=10"
curl.exe "http://127.0.0.1:8086/api/v1/events?after=2&limit=10&category=test"
```

Responses have `schema_version`, `collector`, effective `limit` and `has_more`.
Event responses have `events` in ascending cursor order and `next_cursor`.
Pass the last `next_cursor` as `after` to backfill or poll for new records.
Omitting `after` starts at zero. Gaps are normal since private records are
omitted. `tail=1` selects the newest matches and cannot be combined with
`after`. On a tail page `has_more` refers to older events. Agent responses
have `agents` ordered by newest run update and `next_before` for paging older
rows. The live ordering can change between agent pages. Both accept `agent`,
`run`, `origin` and `machine` filters. Event queries also accept `type`,
`category` (the prefix before the first dot) and `severity`. The default
request page size is 50, capped by `--agent-page-limit` (default and maximum
100). The collector status is `disabled`, `waiting`, `ready`, `busy`,
`degraded`, `full` or `unavailable`.

`reported_lifecycle` is derived only from explicit lifecycle events. A first
compatible turn outcome takes precedence until a new turn starts. A session
end closes the run and preserves a failed or interrupted outcome. Conflicting
events remain in history. `pending_approval_count` and the last eight pending
IDs are reported independently. Resolution affects only its correlated ID,
and ending the session clears outstanding approvals for that run. No browser
operation can resolve them.

`process`, `transport` and `last_activity` are independent. Process heartbeat
and exit records refresh publication freshness but are excluded from actual
activity along with `source.*` events. A producer that directly waits for a
child can publish `process.exited` to report that it stopped. The run keeps its
last reported turn outcome, and the exit report does not verify a currently
live PID. Use a fresh origin for each process lifetime. Liveness can be unknown
if the source supplies no identity, access is denied, the platform is unsupported, or the probe budget
of 64 distinct process claims per refresh is reached. A dead or reused PID
does not imply a failed turn. Activity and heartbeat ages use the host
monotonic clock and are unknown for events from before the reader started.
Historic nonterminal runs remain disconnected until a new visible signal
arrives. An explicit source disconnect requires a reconnect or actual
activity before it clears. The quiet and stale thresholds default to 120 and
600 seconds, configurable with `--agent-quiet-seconds` and
`--agent-stale-seconds`. Silence is never interpreted as thinking.

## Reproduce the acceptance checks

Run the following with the installed wheel and optional image and MCP extras
for full coverage. The synthetic publisher fixture is generated by
`tests/portable/observatory_fixture.py` with three independent origins and
deterministic source timestamps. The focused tests inject a complete bad line,
an unterminated record, a short write, a failed sync and a killed writer. The
synthetic native peer test makes 320 requests in two phases, held and after
owner disconnect. It asserts zero new native socket attempts or commands and
no change in synthetic guest time, frame count or reset counters. The reported
1,000 ms baseline and 0 ms delta are synthetic observations.

```console
python -m unittest discover -s tests/portable -v
python -m unittest discover -s deployment/windows10/tests -v
python -m ruff check src tests/portable tools
python -m reuse lint
python -m build
python tools/check_install.py
python tools/audit_repository.py
```
