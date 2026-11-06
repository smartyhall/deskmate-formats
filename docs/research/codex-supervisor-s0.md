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
