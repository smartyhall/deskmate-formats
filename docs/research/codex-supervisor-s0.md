# Supervisor S0 app-server protocol

This is the offline portion of [issue 58](https://github.com/smartyhall/deskmate-formats/issues/58),
based on DeskMate Formats commit `92e29550efd1453dcaa26936813e7100d4afaab0`.
See the [supervisor design](codex-supervisor-design.md) and
[Observatory event contract](observatory-v2-spec.md).

## Installed inputs

On Windows 10 build 19045 with Python 3.13.17, the installed npm launcher
reported `codex-cli 0.166.0`. The native Windows executable SHA-256 was
`9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`.
Inspected `codex app-server --help` and
`codex app-server generate-json-schema --help`. The documented transport
for this client is `stdio://`. The generator was run twice into fresh
private temporary directories with default features, without `--experimental`.
Both runs produced the same 321 paths and SHA-256 hashes.

~~~powershell
codex --version
codex app-server --help
codex app-server generate-json-schema --help
codex app-server generate-json-schema --out $privateExport
python tools/pin_app_server_schema.py $privateExport $profileOutput $inventoryOutput
~~~

The [inventory](codex-app-server-0.166.0.json) records all generated paths
and byte hashes. Its SHA-256 is
`994ccd7691cdb81096b5c83bb2a4ce67c01ba5b935339367aedae7bb77839f24`.
The v2 bundle SHA-256 is
`e025e54fb11354eb82767ea040b40efa17b34dfc706c9433a6115b5f4771c465`.
The packaged profile SHA-256 is
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
It selects stable method and notification schemas, removes documentation
annotations and deduplicates identical definitions. The full export stays
private. The profile is derived from OpenAI Codex under Apache-2.0.
The package includes the upstream NOTICE and Apache license.

## Pinned source findings

Upstream tag `rust-v0.166.0` peels to
[`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`](https://github.com/openai/codex/tree/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856).
The following paths are relative to `codex-rs/`.

| Source file | SHA-256 | Finding |
| --- | --- | --- |
| `app-server-protocol/src/protocol/common.rs` | `b7f0a90dcc822962e59890b252a43142a113cb1355f333d8c6b0f704b97f89f7` | Method table, experimental gates and per-thread routing. |
| `app-server/src/request_processors/initialize_processor.rs` | `8350444d71a45b45bd53274910dfe247674041d655f8b4dc76a328253adc2f66` | Client-declared capabilities and server handshake metadata. |
| `login/src/auth/default_client.rs` | `acfc0eba844d9ba02c9830c66a19ab920b51d8f3a516b95ccf5066f94ef53fcd` | User-agent prefix contains the build version. |
| `app-server/src/request_processors/thread_processor.rs` | `c03d31e07c8831c7cf153e6429f4ab908d1035b21ba593e701d5a3767121b5a8` | Reads distinguish loaded and stored thread views. |

The [official app-server documentation](https://learn.chatgpt.com/docs/app-server)
describes newline-framed JSON-RPC with the version member omitted. Each
connection starts with `initialize`, then the client sends `initialized`.
`initialize` has no server method discovery or version negotiation field.
The client can check the version in `userAgent`, leave experimental
capabilities disabled, and admit only its supported method subset. A
successful handshake does not establish runtime availability of every method.
The request ID is a string or signed 64-bit integer. Client and server
request IDs have separate roles, including when their values coincide.

Thread start and resume return a thread. Turn start returns a turn.
`turn/steer` requires `expectedTurnId`. An interrupt acknowledgement is
an empty result. Completion and interruption are evidenced separately by
turn status. Stored turns may be paginated. A missing turn in a read or
page does not establish that a request did not execute. Command and file
approval requests include a thread, turn, item, and independent request ID.
Their decision vocabularies differ. S0 restricts synthetic decisions to
one-shot accept, decline, and cancel.

These are local generator observations and upstream source findings.
The generator does not start an app-server session or make a model turn.
This protocol is separate from the Observatory M2 `codex exec --json` stream.

## Owned stdio and approvals

`AppServer` owns a direct child, one local thread of control, one in-flight
client RPC, and a fresh generation UUID. The OS process identity combines the
PID with its creation stamp. The handshake checks the reported build version
and requests the stable API. The client validates supported messages with the
packaged JSON Schema profile and applies stricter local rules for request IDs,
outbound fields, and plain-text input. The coordinator uses only supported
fields from schema-valid results. Unknown notifications are discarded.
Unknown server requests, malformed frames and unexpected response IDs break
the connection. An exact JSON-RPC error is reported separately. It establishes
the RPC's reported failure, with no claim that server-side effects rolled back.

Frames are limited to 256 KiB including the delimiter, with depth, queue and
time bounds. A transport failure invalidates the generation for further
requests. The owner closes stdin, waits briefly, and terminates the direct
child if needed. The synthetic child has no descendants. Real process-tree
ownership and recovery remain unverified.

The protocol represents command and file approval requests with their typed
request ID, session generation, thread, turn and item. The synthetic
authorization check requires the exact outstanding request object and
independently supplied expected scope. Duplicates, stale generations, resolved
requests and unsupported decisions are rejected. The test harness alone writes
an explicitly authorized, one-shot decline. It uses the exact string or integer
ID from the request, including when that ID matches an in-flight client RPC ID.
The production API exposes no approval sender. Request resolution can race a
response on any bidirectional transport. The harness checks already queued
resolutions before writing and never resends a decision.

## Private operation receipts

`Operations.execute` is the receipt-aware entry point for the supported
mutations. The raw stdio client is also used by the protocol fixture. Callers
supply stable local operation IDs. Keep one cooperating owner per ledger and
use a dedicated private local directory outside Git and separate from the
Observatory spool. The first open explicitly creates the store. Subsequent
opens require the existing database and check its schema version and integrity.
An OS lock is held across the session. SQLite uses rollback journaling and
`synchronous=EXTRA`. An operation row has the original generation, request ID,
thread and turn where known, acknowledgement bit, and last evidence with its
generation. The session table links each generation to the child PID and
creation stamp. The store carries identifiers and state, without request
bodies or tool content.

| Receipt state | Durable evidence |
| --- | --- |
| `prepared` | Local operation identity reserved, before the send gate. |
| `sent-unknown` | Write-ahead record committed before any pipe bytes. A crash here can leave zero, partial, or all bytes delivered. |
| `acknowledged` | Exact correlated successful response persisted. |
| `running` | The server reported the acknowledged turn in progress. |
| `completed` | A successful terminal turn, a completed non-turn RPC, or an acknowledged interrupt with the target observed interrupted. |
| `failed` | A correlated RPC error or an explicitly failed/interrupted started turn. |
| `needs-reconciliation` | Connection loss, restart with in-flight work, or an inconclusive interrupt outcome. |

The send gate rejects every previously recorded operation ID, including a
prepared ID. A failed gate leaves the wire untouched. A failed write after
the send gate can leave the server outcome unknown. This is local deduplication
under a caller-supplied stable ID. App-server provides no transaction spanning
the local database and the remote mutation.

On opening a new generation, in-flight receipts become
`needs-reconciliation`. Reconciliation is explicit and uses saved evidence
or read-only RPCs. For an acknowledged turn, it verifies the thread ID via
`thread/read` and looks for the exact turn ID in one bounded
`thread/turns/list` page. Only an exact terminal record can settle a turn
across generations. Missing results, unacknowledged starts, old in-progress
history and ambiguous interrupts stay unresolved. A previously acknowledged
thread start, resume or steer can be settled from its saved response receipt.
Interrupt evidence describes the target status and cannot prove causal
attribution. The tests exercise supervisor termination and injected write
failures, with no power-loss or storage-controller fault simulation.

## Observatory boundary

`AppServerTelemetry` consumes validated notifications and approval
representations explicitly delivered by the protocol owner after receipt
processing. Each publication origin tracks one acknowledged turn in one
generation, or connection and host health alone if the turn ID is uncertain.
It emits fixed summaries and opaque correlation IDs into the existing private
event journal. Source activity, pending approvals, terminal lifecycle,
connection state and host liveness use separate existing event types. Pending
approvals shown after disconnect are the last observed state for that generation.
Terminal events close that turn's pending approvals without assigning an
approval decision. Raw messages, prompts, commands and tool results stay
outside the journal and HTTP projection. Publication failure stops that
publisher independently of the operation receipts. HTTP receives only the
existing immutable Observatory publication.

## Offline acceptance and next gate

~~~powershell
python -m build
python tools/install_wheel.py --observer
python -m pip install 'jsonschema>=4.23,<5'
python -m pip install 'dist/deskmate_formats-0.1.0.dev0-py3-none-any.whl[mcp]'
python tools/check_install.py
python -m unittest discover -s tests/portable -v
python -m unittest discover -s deployment/windows10/tests -v
& deployment/windows10/tests/test_appraiser_state.ps1
python -m ruff check src tests/portable tools
python -m reuse lint
python tools/audit_repository.py
~~~

Windows verification used SQLite 3.50.4, jsonschema 4.26.0, Pillow 13.0.0,
MCP SDK 2.3.0, Ruff 0.17.3 and REUSE 6.3.0. The portable suite ran 266
tests including 19 S0 cases. The deployment suite ran 31 tests with two
symlink tests skipped for Windows host permissions. The separate Appraiser
script, package checks, Ruff, REUSE and repository/archive audit passed.

The synthetic fixture uses only stdio and disposable local state. The HTTP
tests use the actual loopback read-only server and an untouched synthetic
native peer. Before and after, the peer reported zero connections, zero
authentications and zero commands, with the counter at exactly 1000 ms.
Elapsed emulated time was **0 ms**. No native 86Box endpoint, desktop session
or model turn was opened. The browser reads preserved the operation database
and fake-server state byte-for-byte, and could not write a protocol frame.

S1 needs a trusted task manifest, stable operation IDs derived from task
identity, and an operator workflow for unresolved receipts. A separate
operator-authorized real smoke test would establish whether an owned thread's
actual notifications and persisted turn history support the same recovery
observations. Runtime compatibility and crash behavior of a real Codex child
remain unverified.
