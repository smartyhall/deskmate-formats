# Supervisor S0 first live canary — operator runbook

**Later operator risk acceptance — 2026-11-11:**
The [lab posture](experimental-lab-operating-posture.md) supersedes the
earlier **policy** demand for a new VM or extensive OS confinement before a
one-turn, explicitly authorized S0 protocol experiment. The existing
research VM is accepted for ordinary local permissions; it is **not a
proven stronger sandbox**. Preserve rollback, actual host/external exposure
review, durable protocol evidence and exact model-use authorization.
Historical procedure below is retained, not a workaround: the driver
still refuses live launch until a reviewed experimental-mode change.

**Current decision: [BLOCKED — readiness audit](codex-supervisor-s0-readiness.md).**
The driver exists, but live launch is disabled pending externally enforced
isolation and descendant containment. The procedure below retains historical
experiment design; it does not override that gate. Use the readiness report's
offline `preflight` command and exact candidate receipt before further decisions.

**Status: preparation only; NOT EXECUTED.** Supports
[issue 58](https://github.com/smartyhall/deskmate-formats/issues/58).
Writing, reviewing or merging this document does not authorize execution.
Every action labeled **OPERATOR-AUTHORIZED ONLY** requires a separate grant
for the specific experiment, including model usage and owned-child teardown.
Do not run all code blocks as a script.

Baseline inspected: `0d8c9e9cb538c65c382cd4f5478048e4397c6bb7`.
Contracts: [S0](codex-supervisor-s0.md), [S1](codex-supervisor-s1.md),
[design](codex-supervisor-design.md),
[reuse decision](agent-orchestrator-reuse-assessment.md), and
[Observatory v2](observatory-v2-spec.md).
S1 acceptance is not dispatch authority. No S2 scheduler is needed here.

## Scope and gates

Test A establishes ordinary runtime compatibility: one disposable owned
app-server generation, one persistent synthetic thread, one short turn, then
controlled shutdown. A second generation is permitted only for read-only
history verification after the first child has exited. Never overlap children
or create a second thread/turn during recovery. Do not attach to desktop Codex.

Test B, a deliberately lost acknowledgement, is a separate future experiment.
Do not attempt B until A passes and a reviewed transport fault control exists.
Neither a failed A nor an uncertain B permits another mutation send.

Use the existing Windows 10 lab with no emulator resources. Do not launch
86Box, connect to its socket, inspect guest state through a new connection,
change VM media/configuration, alter services/firewall rules, install packages,
upgrade Codex, purchase credits, enable approvals or dispatch/retry work.
The prompt is a behavioral request, not a security boundary: review the actual
child configuration before authorization. Never inherit emulator tokens,
automation configuration or privileged tool access.

**Execution readiness:** an installable operator command and synthetic-only S2
bridge now exist; see the [operator driver runbook](codex-supervisor-operator-driver.md).
That document supplies exact preparation, status, explicit execution and failure
commands. The fragments below explain the original API sequence. Effective live
launch isolation still needs review, and **new explicit single-model-canary
authorization remains required**. No live run was performed by implementing the
driver. Stop at an unmet gate; do not patch private attributes or borrow fixture helpers.

## 1. Preflight and private preparation (no model calls)

Record UTC start/end, Windows edition/build/architecture, Python executable
and version, SQLite/jsonschema versions, repository HEAD and clean status,
installed module paths and their hashes. The historical S0 environment was
Windows 10 build 19045, Python 3.13.17, SQLite 3.50.4, jsonschema 4.26.0;
record differences rather than claiming an identical machine.

Commands currently available from the checkout:

```powershell
git status --short
git rev-parse HEAD
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
python --version
python -c "import sys,sqlite3,importlib.metadata as m; import deskmate_formats.supervisor.protocol as p; print(sys.executable); print(sqlite3.sqlite_version); print(m.version('jsonschema')); print(p.__file__); print(p.VERSION,p.PROFILE_SHA256); p.Schema()"
Get-Command codex -All | Select-Object Name,Source
```

Missing imports or an installed module from another revision block the run.
Do not install or upgrade dependencies as part of this experiment. In a future
driver, use the reviewed checkout's `src` via an explicit import path and record
the resolved paths; do not silently rely on an older installed wheel.

Resolve the native executable from the installed npm launcher's package layout
by inspection. Do not pass `codex.ps1`, `codex.cmd`, Node or a PATH-only name to
`AppServer`. It requires an absolute executable path. Use the literal reviewed
path below; the placeholder deliberately fails until supplied.

```powershell
$codexExe = 'C:\REPLACE-WITH-REVIEWED-NATIVE-PATH\codex.exe'
$expectedHash = '9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42'
if (-not (Test-Path -LiteralPath $codexExe -PathType Leaf)) { throw 'Missing native binary' }
if ((Get-FileHash -LiteralPath $codexExe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) { throw 'Binary pin mismatch' }
$version = & $codexExe --version
if ($LASTEXITCODE -ne 0 -or $version -ne 'codex-cli 0.166.0') { throw 'Version mismatch' }
Get-FileHash -LiteralPath src/deskmate_formats/supervisor/codex-0.166.0.json -Algorithm SHA256
```

Expected profile SHA-256:
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
The complete generated inventory and pinned upstream source hashes are in S0;
do not regenerate or substitute a newer protocol. Binary `--version` is a
non-model check; no app-server is launched by the commands above.

Choose a fresh run ID and a fixed-local-drive private parent outside every Git
tree, cloud sync and web document root. Protect the parent first. Require real
directories without reparse points, regular files with one hard link, and the
project's protected inheritable Windows DACL:
`D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)`
(owner, SYSTEM and administrators only). Do not loosen a refused DACL.
Inspect ACLs locally with `Get-Acl`; keep account details private.

Under that parent, create a new run directory containing separate `receipts`,
`spool`, `evidence`, `scratch` and `codex-home` directories. The scratch directory
is empty and disposable, with no Git checkout, instructions, symlinks, private
data or native tools. Keep evidence/receipts outside scratch. A preparation
example using the existing internal storage API (not a new CLI):

```powershell
$env:S0_CANARY_ROOT = 'C:\PRIVATE-LAB-PARENT\s0-REPLACE-WITH-UNIQUE-RUN-ID'
@'
import os
from pathlib import Path
from deskmate_formats.observer._private_storage import storage_directory
from deskmate_formats.supervisor.ledger import open_ledger
root = Path(os.environ['S0_CANARY_ROOT'])
if root.exists():
    raise SystemExit('Refuse reuse of an experiment directory')
storage_directory(root, create=True)  # Parent must already exist and be protected.
for name in ('spool', 'evidence', 'scratch', 'codex-home'):
    storage_directory(root / name, create=True)
with open_ledger(root / 'receipts', create=True):
    pass
'@ | python -
Get-Acl -LiteralPath $env:S0_CANARY_ROOT | Format-List
```

This historical API example creates private files only; prefer the driver's
`prepare` command for a new integrated run. Never rerun it over
an existing run. The later owner opens the ledger with `create=False`.
Back up any existing configuration before changing it; preferably change none.
Have the operator provision authentication privately for the dedicated home,
using an existing authorized account with sufficient included allocation.
Do not print/copy credentials into this repository, browser or transcript.
No authentication bootstrap or paid-credit fallback is authorized here.

**Launch configuration review gate:** `AppServer(argv, timeout=..., cwd=..., env=...)`
can set the scratch cwd and an explicitly constructed environment. Its RPC
allowlist cannot set model, sandbox, approval policy, tools or turn budgets.
Before execution, review the pinned binary's local non-launch help and
version-matched configuration contract; prepare and hash an isolated config
with a read-only sandbox, no approval escalation, no MCP/native tools and an
operator-selected available model. Record exact argv, safe environment names,
model/effort and effective policy privately. A dedicated `CODEX_HOME` alone
does not prove isolation from machine/project settings or inherited secrets.
The driver supplies a hashed template and sanitized environment, with a distinct
exact-plan isolation-review gate. Its template alone does not qualify effective
machine settings or tool isolation. If effective isolation
cannot be established, stop before launch. Check the `thread/start` result's
cwd/model/provider/sandbox/approval policy before sending any model input.

## 2. Normal successful-turn test A

**OPERATOR-AUTHORIZED ONLY — launches real app-server and may terminate its
owned child during initialization failure or cleanup.** The reviewed driver
must instantiate `AppServer` with absolute native argv for
`app-server --listen stdio://`, the approved configuration, scratch cwd and
sanitized environment. No WebSocket/listening control port is needed.
Use `timeout=10` seconds per RPC and a 60-second overall turn observation
deadline, with event waits at most one second. These are host observation
bounds, not a provider token/cost cap. There is no S0 hard model-budget API.

Expected handshake: newline-delimited JSON-RPC without a `jsonrpc` member;
client `initialize` (initial client request ID 0), capabilities
`experimentalApi: false`; correlated result with `userAgent` matching build
0.166.0; then client `initialized` notification. The constructor performs
this handshake and profile validation. It does not expose the initialization
result for evidence capture; record constructor success and the exact binary
pin, without claiming a saved raw handshake. A future bounded recorder is
needed if the raw handshake is an acceptance requirement.

The following are **Python API sequence fragments**, not a runnable driver.
Imports are from `deskmate_formats.supervisor.protocol` (`AppServer`, `Approval`),
`.ledger` (`open_ledger`), `.operations` (`Operations`) and `.telemetry`
(`AppServerTelemetry`). Variables denote the reviewed owner objects/paths.
The driver must handle exceptions, deadlines, private evidence and finalization.

1. Open the existing ledger once; keep its writer lock through the session.
   Construct `Operations(client, ledger)`. Record generation, PID and creation
   identity from `client`, and verify `ledger.process_for(client.generation)`.
   Construct telemetry with the separate spool and those same identities.
   Call `telemetry.connected()` and `telemetry.sample_process()` explicitly.
2. **OPERATOR-AUTHORIZED ONLY — mutating app-server request:**

   ```python
   thread = ops.execute("s0-a-thread", "thread/start", {"ephemeral": False})
   thread_id = thread["thread"]["id"]
   ```

   Save the private result and receipt before proceeding. Verify the effective
   policy and scratch cwd. The persistent thread is necessary for later reads.
3. **OPERATOR-AUTHORIZED ONLY — one model turn and mutating request:**

   ```python
   result = ops.execute("s0-a-turn", "turn/start", {
       "threadId": thread_id,
       "input": [{"type": "text", "text":
           "Reply exactly S0_CANARY_OK. Do not use tools, read or write files, "
           "run commands, access the network, or request approval."}],
   })
   turn_id = result["turn"]["id"]
   telemetry.bind(ledger.get("s0-a-turn"))
   ```

   Never use a raw `client.request` for mutations. Operation IDs are fixed for
   this run, not regenerated after a failure. Inspect receipts with
   `ledger.get("s0-a-thread")` and `ledger.get("s0-a-turn")`; they contain IDs,
   acknowledgement/state/evidence, not the full request/response bodies.
4. Drain through `ops.next_event(timeout=1)`, then deliver each returned
   validated event to `telemetry.observe(event)`. Stop at an exact terminal
   notification or the overall deadline. Do not stop just because one wait
   returns `None`. Sample host process health separately. Check
   `telemetry.publication_failed` after publications.
5. Expected notifications include `thread/started`, `turn/started`, optional
   text/item activity and `turn/completed` with exact IDs and terminal
   `completed` status. Replies and notifications may interleave; events queued
   before the turn reply must be drained after telemetry binds. Do not impose
   fixture-specific item ordering or require tool events for this text turn.
   Unknown notifications are discarded by S0. Malformed supported frames,
   unknown server requests, overflow or wrong IDs fail the connection.
6. Verify the reply privately is exactly the requested sentinel, no tool or
   approval activity occurred, and the turn receipt is `completed` with
   acknowledged=1 and matching thread/turn/generation. A successful start reply
   or `inProgress` status alone does not pass the terminal gate. An approval
   request fails this harmless test: preserve it and stop. **Never use
   `_take_synthetic_approval`, `SyntheticServer.decline` or a fixture to answer
   a real approval.** There is no production approval sender.

Read-only identity checks (Python APIs currently available):

```python
view = client.request("thread/read", {"threadId": thread_id})
page = client.request("thread/turns/list", {
    "threadId": thread_id, "itemsView": "notLoaded", "limit": 50,
})
```

Require `view['thread']['id'] == thread_id` and exactly one matching `turn_id`
with terminal `completed`. Save results privately. Missing/paginated/ambiguous
evidence is inconclusive, not proof of nonexecution. No resume is required:
`thread/resume` is a mutation and is excluded from read-only recovery.

## 3. Controlled shutdown and restart

After terminal evidence is durable, record the intended shutdown. Call
`ops.disconnect()` to mark any in-flight receipts uncertain and
`telemetry.disconnected()` to publish transport closure. These calls do not
close a pipe or kill a process; call them only as part of actual shutdown/loss.

**OPERATOR-AUTHORIZED ONLY — `client.close()` and context-manager exit may
terminate the direct child.** On the owning Python thread, close that exact
`AppServer` instance. It closes its own stdin, waits up to 0.5 seconds, then
uses its retained `Popen` child handle to kill/wait if necessary. A timed-out
writer causes kill before pipe close. Initialization exceptions also call
`close()`. Authorize this behavior before construction. Sample process health
afterwards; save exit/liveness evidence and close the ledger cleanly.

**Ownership finding:** this close path targets the direct child launched by
this object, not a name match, enumerated Codex process or stored PID alone.
It can induce a real owned-session disconnect without selecting an unrelated
desktop process. It cannot promise a transport-only cut with the child alive,
preserve a lost reply at a precise point, or clean up real descendants safely.
No public detach/close-transport-only API exists. Do not use `Stop-Process`,
`taskkill /IM`, process-tree kills, stale PID kills or private pipe access.
If the owner object is lost or process identity is unknown, preserve evidence
and require a separately reviewed recovery control; do not guess a target.

**OPERATOR-AUTHORIZED ONLY — restart creates one new owned app-server child**
with the same pinned argv, configuration, isolated home and scratch cwd, and a
fresh generation. Verify
the old child exited first; reopen the original ledger without `create=True`.
Construct `Operations` to register the new process and mark surviving
in-flight receipts `needs-reconciliation`. No thread/start or turn/start now.
Use the saved exact IDs for the two read-only RPCs above. For a normally
completed A receipt, `ops.reconcile("s0-a-turn")` is a no-op: perform those
explicit reads to verify persisted history rather than claiming reconciliation
performed new queries. Close this second child under the same authorized rule.

For an acknowledged but unresolved turn, `ops.reconcile(operation_id)` verifies
the thread and searches one bounded 50-turn page. Exact terminal history can
settle it; missing IDs, old `inProgress`, read errors and unacknowledged starts
remain unresolved. Original generation stays fixed; `evidence_generation`
records the new observer. Saved acknowledgements can settle thread start,
resume and steer receipts. Do not infer interruption causality from status.
Do not force an otherwise completed A receipt back into uncertainty to test
this path. A real unresolved recovery exercise belongs to separately approved B.

## 4. Observatory verification without native access

Telemetry is explicit wiring, not an automatic subscriber. Expect fixed-summary
`source.reconnected`, `process.heartbeat`, `turn.started`, `turn.completed`,
`source.disconnected` and verified `process.exited` as applicable. Host liveness,
source connectivity and turn lifecycle are independent facts. No approval/tool
events are expected in A. A disconnected publisher cannot keep observing a turn.
An uncertain turn cannot be bound to telemetry; publish connection/health only.
A new generation/origin must not imply a second turn or a recovered terminal
event that was never observed. Publication failure does not roll back receipts.

Inspect the private spool with `observer.journal.read_journal`; the browser
must receive only the immutable `AgentJournalFeed.publication` through
`ObserverServer`. Do not serve the spool, ledger or evidence as static files.
An existing CLI can provide an isolated loopback viewer with fictional machines:

```powershell
python -m deskmate_formats.observer.demo --text-only --port 0 --journal "$env:S0_CANARY_ROOT\spool"
```

This viewer does not connect to native 86Box; its displayed guest counters are
fictional and must not be used as real guest-time evidence. Use its printed
loopback URL/port. Do not start the native observer/adapter or add LAN exposure.
Archive bounded GET responses from `/api/v1/agents`,
`/api/v1/agents/codex-supervisor` and `/api/v1/events`. Confirm generation,
sequence, opaque turn correlation and fixed summaries against the journal.
Confirm prompt sentinel, raw thread/turn/item/request IDs, config/auth material,
paths, commands and model output are absent from all browser responses.
Generation/run IDs and sampled process identity are intentional metadata.
Check unavailable operation/approval routes and read-only behavior against the
existing HTTP contract (operations GET 404, events POST 405, decision query
400). Before/after browser checks, keep the owner idle and compare ledger
hashes and mutation-send evidence. Browser refresh must not trigger protocol
writes. Stop the fictional viewer normally when done; do not target processes
by name. An isolated Python viewer composition is also possible; no S0 CLI
automatically launches or connects one.

## 5. Deferred lost-acknowledgement test B

**Not part of the first live canary.** Synthetic `lost-ack` persists a fake
turn then exits; `lost-ack-live` sends malformed output and remains alive.
Crash tests kill a retained synthetic subprocess. These demonstrate local
receipt behavior, not a real Codex transport fault or real process-tree safety.

A future small experiment-only transport interposer must forward one mutation
once, record bounded private send evidence, and suppress the exact reply without
replay. It needs reviewed ownership/close semantics before any live use.
**OPERATOR-AUTHORIZED ONLY:** forwarding a real mutation, dropping its reply,
interrupting a turn or terminating a child are separately scoped actions.
Do not implement the cut using private client members or unrelated process
termination. `Operations.disconnect()` alone is not fault injection.

Expected B outcome: `sent-unknown` becomes `needs-reconciliation`; a turn/start
with no acknowledged exact turn ID stays unresolved even if history contains a
plausible matching turn. No prompt/time-based identity guesses, automatic
resume, new operation ID or retry. Preserve the same ledger on restart.
Separately test acknowledged exact-ID terminal recovery; do not conflate it
with proving an unacknowledged start. S0 has no server idempotency transaction.

## 6. Abort, cleanup and evidence

Abort on version/hash/policy mismatch, unexpected tools/approval, auth/quota
failure, wrong identity, schema/transport/storage/publication error or deadline.
Stop dependent sends immediately. Record the exception class and private
receipts. `ops.disconnect()` marks uncertainty; it does not stop the model.
Do not keep waiting indefinitely or declare timeout equivalent to interruption.

**OPERATOR-AUTHORIZED ONLY — optional exact-turn interrupt:** if the approved
abort plan permits it and transport is usable, use `ops.execute` with a fixed
new abort operation ID, `turn/interrupt` and the saved exact thread/turn IDs.
An empty acknowledgement is not proof of interruption; observe/reconcile the
target's terminal state. Never retry an uncertain interrupt. Otherwise use
the already authorized owned-child close path. No real approval replies.
If neither action is authorized, stop sends, preserve uncertainty and obtain
operator intervention; do not silently kill a running turn.

Preserve the complete closed receipt directory (including any rollback journal),
spool, isolated home/history/config and evidence under the private run archive.
Do not delete an uncertain run or replace its ledger with a fresh database.
Copy/hash SQLite only with its owner stopped, or use a consistent backup;
never call an arbitrary live database byte copy a validated recovery image.
Record SHA-256 for the binary, profile, driver/config, original request/result
captures, event journal, database and archived artifacts. Record commands,
controlled variables, model/effort, deadlines, host elapsed time, generation,
PID/creation identity, operation/request/thread/turn IDs, state transitions,
browser checks, deviations and observation limits. Raw protocol captures need
a reviewed bounded recorder; current stderr is discarded by `AppServer`.
Keep credentials separately protected and out of reports even in the archive.

After archive verification, remove only the explicitly identified disposable
scratch data, or retain the whole run for review. Verify resolved paths remain
inside this run before removal; no recursive delete command is supplied.
Do not change shared Codex state, guest media, config/NVRAM or unrelated children.

## 7. Acceptance record

For each row record **PASS / FAIL / NOT RUN / INCONCLUSIVE**, evidence path/hash
and observation interval. NOT RUN and INCONCLUSIVE do not pass the live gate.
All runtime fields are currently **NOT RUN**. Static source findings and
previous synthetic tests above are not observations of this experiment.

| Criterion | A: ordinary turn | B / failure extension |
| --- | --- | --- |
| 1. Exact pin/protocol | Native SHA-256 and `codex-cli 0.166.0`, profile hash and stable handshake pass; no upgrade | Same pin on recovery |
| 2. Exclusive ownership | One direct child at a time; one thread/start and one turn/start; recovery child only after exit | No unrelated process selected; no second mutation |
| 3. Exact identity | Ledger session PID/creation stamp and generation match client; response, notification and receipt thread/turn IDs agree | Preserve original IDs and distinguish evidence generation |
| 4. Terminal status | Exact successful terminal notification and receipt, sentinel reply, no tool/approval; start ack alone fails | Interrupted/failed differs from success; timeout remains uncertain |
| 5. Accurate private events | Correct origin/run/sequence/correlation, truthful lifecycle/connectivity/health; publication flag healthy | No invented start/completion for unknown turn |
| 6. Browser privacy | All inspected responses omit private content; read-only routes; idle receipts unchanged | Same after loss/restart |
| 7. No duplicate mutation | Exactly one send per stable thread/turn operation ID in bounded driver evidence, consistent ledger/history | Ambiguous send never retried, even under a new ID |
| 8. Authoritative restart | Explicit read-only history verifies exact completed A turn in second generation | Exact acknowledged terminal evidence settles eligible unresolved receipt |
| 9. Insufficient evidence | Missing A history blocks restart acceptance; no guess | Unacknowledged ID, missing page or old running evidence stays `needs-reconciliation` |
| 10. No emulator effect | Zero native connections/commands attributable to driver/viewer; no emulator launch or guest-time advancement caused by canary | Same throughout loss/recovery |

Criterion 10 uses reviewed imports/config/argv, sanitized resources and retained
host evidence or already available independent logs. Do not create a native
connection just to measure it. Expected attributable elapsed emulated time is
**0 ms**; actual guest-counter delta is **NOT MEASURED** unless independent
existing evidence establishes it. An unrelated running guest can advance on
its own; neither fictional counters nor wall time proves its delta. State
the observation limit and leave an unsupported measurement inconclusive.

## 8. Capability inventory and minimum follow-up

| Capability | Current status / operator consequence |
| --- | --- |
| Preflight, hash, ACL, scratch/ledger preparation | Existing shell/Python operations above; no model needed |
| Owned stable stdio, bounded RPC/event reads | `AppServer` API; constructor/close have child-lifecycle effects |
| Receipted mutations and reconciliation | `Operations`/`Ledger` APIs; caller supplies stable IDs; no operator CLI or receipt listing command |
| S1 CLI | Intake/review/publication only; cannot dispatch a canary |
| Approval responses | Synthetic harness only; production sender absent; abort real requests |
| Integrated bounded experiment owner | Missing small reviewed driver: configuration gate, deadlines, receipt export, notification-to-telemetry wiring, cleanup and restart modes |
| Raw handshake/send evidence | No public bounded recorder; driver can record API intents/results, but exact wire send/cut auditing needs a small future hook/interposer |
| Observable hard model budget | Not exposed by S0 allowlist; select a short prompt, bound host waiting and authorize usage/abort policy explicitly |
| Transport-only deliberate disconnect | Missing; owned `close()` safely selects its direct child but may kill it; live descendant ownership unverified |
| Observatory | Publisher, journal, feed and loopback demo viewer exist; manually compose, no native adapter |

Minimum later operator-authorized work: review the small driver and isolated
launch policy, verify pins/authentication and resources, grant one short model
turn plus owned-child teardown, run A once, then authorize the read-only
restart and preserve/review its private evidence. Any gaps that cannot be
closed by review block execution. Grant B separately only after ordinary
compatibility passes and fault/ownership controls have been implemented and
tested synthetically. This documentation adds no application implementation.
