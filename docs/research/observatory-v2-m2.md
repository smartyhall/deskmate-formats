# Observatory v2 M2 Codex CLI telemetry

The opt-in wrapper observes one new `codex exec --json` invocation at a time.
It publishes through the existing private Observatory journal. The loopback
viewer reads the same immutable agent feed used by other producers. Install
the current DeskMate Formats package with Python 3.13 or later. The wrapper
requires no optional dependencies. [Journal and HTTP guide](observatory-v2-m0-m1.md)

## Start an opted-in invocation

In PowerShell, use the native Codex binary installed for your platform. An npm
installation on Windows places it under its architecture-specific vendor
directory. Pass the absolute path to the executable, then `exec --json` and the
arguments you would ordinarily pass to Codex. Set the same journal and limits
on the wrapper and the viewer. The journal belongs under a trusted local parent
outside Git.

```powershell
python -m pip install .
$spool = Join-Path $env:LOCALAPPDATA 'observatory-codex'
$codexBinary = 'D:\trusted-tools\codex.exe'  # Replace with the installed native binary
deskmate-86box-observer --journal $spool --text-only
```

In a second terminal with the same variables, use the following when you
intend to start a real Codex task. Codex still applies its own sandbox,
approval configuration and authentication. The wrapper passes argv, cwd,
environment and stdin through and inherits stderr. It probes the selected
executable with `--version` and refuses an unrecognized version before task
launch. It uses no shell to launch the task.

```powershell
deskmate-observer-codex --journal $spool --visibility observer -- $codexBinary exec --json 'Review this repository for broken documentation links.'
curl.exe 'http://127.0.0.1:8086/api/v1/agents/codex'
curl.exe 'http://127.0.0.1:8086/api/v1/agents/codex/events?after=0'
```

Omit `--visibility observer` for journal-only storage. Use
`--passthrough-stdout` only when forwarding raw JSONL to a private destination.
It forwards the original bytes available on the child pipe and is subject to
the destination's backpressure. Stderr is the child's original stream and
can also contain private information. The browser sees fixed summaries,
run and origin IDs, source/version, and short run-local item aliases.
The private journal retains bounded source IDs, line numbers and fingerprints,
outcome fields and escaped error excerpts. It drops command text, arguments,
output, filenames, plan text, prompts, tool results and reasoning text. The
private reasoning receipt is excluded from public history and freshness.
The repository audit permits only the four pinned synthetic JSONL fixtures.

## Source contract and mapping

M2 accepts exactly **Codex CLI 0.166.0**. The official non-interactive guide
documents JSONL on stdout and the top-level lifecycle, item and error families.
The pinned Rust source provides the actual field names, item variants and
emitter behavior. It supplies one thread ID and per-stream item IDs. Turn
events carry no turn ID or source sequence/time. The adapter uses
`session-1` and `turn-1` as run-local references, assigns one UUID-backed origin
and run per launch, and records stdout line order independently from the
journal's source sequence. No child-provided text determines a summary,
category, command, test outcome or approval. [OpenAI non-interactive guide](https://learn.chatgpt.com/docs/non-interactive-mode) · [Pinned event declarations](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/exec/src/exec_events.rs) · [Pinned emitter](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/exec/src/event_processor_with_jsonl_output.rs)

| Codex JSONL or host observation | Observatory record |
| --- | --- |
| `thread.started` | `session.started`. No explicit thread end is present in exec JSONL. |
| `turn.started`, `turn.completed`, `turn.failed` | The corresponding explicit turn events. A repeated start or outcome is diagnosed and ignored. |
| `item.started` / `item.completed` with `command_execution` | `command.started` / `command.completed`. Failure and decline remain distinct from success. The private record holds the source status and nullable command exit code. |
| `item.started` / `item.completed` with `mcp_tool_call`, `collab_tool_call`, or `file_change` | `tool.started`, `tool.completed` or `tool.failed`. Completion-only delivery retains its result with `start_observed=false`. A late start is rejected. |
| `item.started`, `item.updated`, `item.completed` with `todo_list` | `plan.updated` with private step counts. A closing plan snapshot does not imply every step succeeded. |
| `item.completed` with `agent_message` or `reasoning` | Fixed `agent.note` for the message receipt. A reasoning receipt is private. |
| Top-level `error` or `item.completed` with `error` | `source.error`. The diagnostic alone leaves the reported turn outcome unchanged. |
| Launch and periodic observation of the owned child | `process.heartbeat` with a creation-identity claim when verifiable. |
| Stdout closes or capture ends | `source.disconnected`. The process may still be alive when stdout closes. |
| OS reaps the child | `process.exited`. The exit status is distinct from any command exit code or reported turn outcome. |
| Child exits with OS interrupt status while its turn was last reported open | `turn.interrupted` with OS exit evidence. This is a wrapper observation, not a source notification. |

The pinned emitter can reconcile an open item at turn end by emitting
`item.completed` with an in-progress payload. M2 records that inconsistency
as a source diagnostic and leaves the item open. Web-search items are outside
the accepted subset. The pinned Rust types flatten both a wrapper item ID
and a web-search ID into the same object. M2 rejects duplicate JSON members,
including this shape. There is no dedicated test or approval event in the
exec schema. A declined command, a tool name, assistant text and quiet
periods do not create either event. Independent producers can still publish
explicit test and approval events through the M0/M1 contract. The app-server
protocol has different fields and explicit approval requests.

## Failure, recovery and scope

The wrapper reports the original numeric child exit code. On POSIX a child
terminated by a signal maps to the shell convention `128 + signal`, while the
journal stores the signed subprocess status. Foreground terminal Ctrl+C is
delivered to the existing process group. The wrapper observes the interrupt
and allows the child to exit. Codex 0.166.0 can handle Ctrl+C and return 1
without emitting a terminal JSONL event. In that case the wrapper records
the observed console interrupt and missing outcome separately. It cannot
distinguish a graceful internal interruption from another missing terminal
event using exit 1 alone. A signal aimed only at the wrapper PID, abrupt
wrapper death and descendant cleanup are outside the console handling.
[Pinned exec control and exit handling](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/exec/src/lib.rs)

The adapter accepts UTF-8 LF/CRLF records up to 1 MiB including the newline,
with at most 10,000 tracked item IDs per invocation. It skips malformed,
oversized, unsupported, duplicate-key, incompatible and unterminated records
with a bounded diagnostic. The pinned stream has no upstream sequence
numbers. The adapter can reject conflicting lifecycle transitions and exact
repeated updates, while it cannot recover lost events or determine the
original ordering of otherwise valid plan snapshots. The wrapper drains
the pipe for up to two seconds after observing child exit to avoid waiting
on an inherited handle. It reports truncation if the deadline expires.
Silence while the child lives has no deadline. A process exit without a
reported outcome never turns an open command or turn into a completion.

The journal can still reach capacity, fail a write or be unavailable.
The wrapper retries only known pre-append lock contention, for up to half
a second per write. It stops publication after an uncertain append or a
hard storage error, emits a generic stderr diagnostic, and continues
draining the child's output. The child exit status remains authoritative.
Inspect the private journal before attempting recovery. Restarting the
viewer replays committed events. A new wrapper invocation starts a new
origin. The wrapper never replays tasks or attaches to an existing session.
[M0/M1 journal recovery and rollover](observatory-v2-m0-m1.md#recovery-and-retention)

## Verification and provenance

The Windows 10 Pro x64 lab reported build 19045, Python 3.13.17 and
`codex-cli 0.166.0`. Repository baseline was
`2aa9bd537504211968faf0275c590ab2d9ebd884`. Commands executed against the
installed native CLI were `--version` and the equivalent installed
`codex exec --help`, `codex app-server --help`,
`codex app-server generate-json-schema --help` and
`codex app-server generate-json-schema --out <private-temp-directory>`.
The help advertised `--json`. Static generation confirmed the separate
app-server v2 schema has thread/turn references, an interrupted status, and
explicit approval requests. No Codex model turn, app-server session, desktop
attachment or emulator instance was started.

| Inspected input | SHA-256 |
| --- | --- |
| Installed native Windows x64 `codex.exe` | `9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42` |
| Generated `codex_app_server_protocol.v2.schemas.json` | `e025e54fb11354eb82767ea040b40efa17b34dfc706c9433a6115b5f4771c465` |
| Pinned `exec_events.rs` | `dafa872d7e86a099e56e28a329dcb9c03db90ed768c3b88cca8c91d46dc1d0e5` |
| Pinned `event_processor_with_jsonl_output.rs` | `41b9532fe9d480b3d427e487f3f3f940f96450e36e7d98ec8509615c9d563367` |
| Pinned exec `lib.rs` | `57a61d50995a365f7572d7eaa05de88054680ff339642b8a823a5c9198e4e012` |
| Pinned `event_processor_with_jsonl_output_tests.rs` | `d375e311c756e4675cd2083c56f63ffddb05e87535e34f35aa56ab00a4b1d2f5` |

The upstream `rust-v0.166.0` tag resolves to
`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`. Lifecycle/item mappings are
source findings, exercised with hand-authored fixtures. Exact live event
ordering, web search serialization in an actual turn, and the timing and
payload of graceful Windows Ctrl+C remain unmeasured. See the
[synthetic fixtures](../../tests/fixtures/codex-exec-0.166.0/README.md) and
[fixture hash audit](../../tools/audit_repository.py).

Run the offline demonstration and focused tests with an installed wheel.

```console
python -m unittest discover -s tests/portable -p "test_observer_codex_*.py" -v
```

The success child emitted 13 JSONL records and exited 0. The private
journal committed 16 records, including one launch heartbeat, one process
exit, one transport disconnect and the private reasoning receipt. The
existing HTTP API returned 15 sanitized records. The last activity was
`turn.completed`. The run reported completed, process stopped, transport
disconnected and zero pending approvals. Restarting the collector returned
byte-identical event history and marked the run historical. The live
silence fixture showed `alive-no-new-events`, then stopped after exit 7 with
the last reported turn still open. A configured synthetic native peer
accepted **zero** connections, authenticated **zero** times and received
**zero** commands. Synthetic elapsed guest time remained exactly **1,000 ms**
(delta **0 ms**), frame count **1**, reset count **1**. No real guest or
native emulator socket was observed or exercised.

## Handoff to supervisor S0

An S0 probe can use the M0/M1 envelope and private publisher for an owned
app-server stream through an independent, version-checked adapter. Its
private ledger would own task IDs, actual thread/turn IDs, authoritative
approval request IDs and restart reconciliation before any retry. The
observer consumes sanitized reports only. Queue ownership, task dispatch,
approval responses and any emulator lease remain outside the browser and
journal publication path. Start with a disposable, owned protocol fixture.
[Supervisor design](codex-supervisor-design.md)
