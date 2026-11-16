# First real supervisor-owned S0 canary — observed policy mismatch

**S0 LIVE CANARY FAILED OR INCOMPLETE.** One native app-server invocation
initialized and created one persistent empty thread, then stopped before
`turn/start`. **Zero model turns were submitted.** This is a real native
observation, not a synthetic run. It supports [issue 58](https://github.com/smartyhall/deskmate-formats/issues/58).

## Identity and verification

Executed on November 15, 2026, America/New_York (November 16 UTC), from reviewed
merge `36cbad1e4e390bbfee57e22d099a18f94bf20694` ([PR 93](https://github.com/smartyhall/deskmate-formats/pull/93)).
The existing prepared run was `s0-experimental-lab-20261112/canary-reviewed`
beneath the protected laboratory archive. Canonical plan SHA-256:

`8226d264f380810230dd6443787dd8d46b17f252322c1a5559588a68dc809085`

All 54 installed project Python module hashes matched the Git blobs at that
merge, and the installed protocol profile matched the merged blob and its pin.
No installation refresh was necessary. The pinned native installation was
unchanged: Codex CLI **0.166.0**, executable SHA-256
`9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`;
protocol profile SHA-256
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.

Offline CLI status and preflight returned exit 0. All seven preflight checks
passed: profile, installed implementation, executable, configuration, staged
authentication, empty scratch and never attempted. Status independently showed
no attempt, no operations and no outcome. The digest, fixed prompt, model
`gpt-6-luna`, effort `low`, 10-second RPC bound, 60-second turn observation
bound and null S2 binding matched the authorization. Credential bytes and hashes
remain private.

The operator explicitly accepted the documented lab risk and separately
authorized this exact invocation. The [prior bounded inventory](codex-supervisor-experimental-lab-validation.md)
was retained: no demonstrated mapped host share or hypervisor control endpoint;
GitHub CLI configuration remained an outside-lab credential exposure. Recovery
procedure: retain evidence, power off the VM and restore the selected
pre-experiment snapshot using the host VMware snapshot manager. The snapshot
identifier was unavailable from the guest and restoration was not tested.
These accepted limitations were not re-audited.

## Commands actually executed

The following driver commands were executed in order using the runbook's
verification interpreter. `$lab` denotes the existing protected archive parent;
this public rendering omits account-specific native paths and raw private data.
The native identity check inside preflight/live ran only pinned `--version`.

```powershell
$lab = 'C:\DeskMateLab\private-evidence\s0-experimental-lab-20261112'
$py = Join-Path $lab 'verify\Scripts\python.exe'
$run = Join-Path $lab 'canary-reviewed'
$digest = '8226d264f380810230dd6443787dd8d46b17f252322c1a5559588a68dc809085'
& $py -m deskmate_formats.supervisor.driver_cli --run $run status
& $py -m deskmate_formats.supervisor.driver_cli --run $run preflight
& $py -m deskmate_formats.supervisor.driver_cli --run $run live --authorize-live-plan $digest --accept-lab-risk $digest
& $py -m deskmate_formats.supervisor.driver_cli --run $run status
```

Private Python wrappers captured each command's argv, output, exit code and
verification results. The live wrapper called `subprocess.run` once, with no
retry. Source verification used `git show REV:src/deskmate_formats/PATH` for
every installed module and the schema, hashing the returned bytes. Post-run
inspection read local receipts and called `verify_process` for the recorded
owned-child identity; it made no new app-server connection.

## Observed lifecycle and failure

| Step | Actual evidence |
| --- | --- |
| Launch/initialize | Owned-child evidence exists after the checked AppServer constructor; telemetry reports completed protocol handshake. Constructor checks initialize response schema and 0.166.0 user-agent version, then sends `initialized`. Raw initialize reply is not retained. |
| Thread | One acknowledged `thread/start`, request ID 1, durable ledger state `completed`, evidence `remote-result`. Returned thread was persistent (`ephemeral=false`) with zero turns and matching scratch cwd. |
| Model/policy | Returned model `gpt-6-luna`, provider `openai`, reasoning effort `low`, approval policy `never`, approvals reviewer `user`. |
| Mismatch | Returned sandbox was `{"networkAccess":false,"type":"readOnly"}`. Driver demanded exact equality with `{"type":"readOnly"}`. This was the only compared policy difference. |
| Turn/sentinel/history | No `turn/start` intent or operation. No sentinel output, terminal turn notification, `thread/read` or `thread/turns/list`; persisted history verification was not reached. |
| Outcome | CLI exit **5**, `state=blocked`, `error_type=DriverError`, reason `effective thread policy differs from reviewed plan`. |
| Teardown | Outcome `child_status=stopped`; telemetry reports process exit; later identity check returned `not-found`. No teardown exception or telemetry publication failure. |

The pinned schema's `SandboxPolicy` readOnly variant explicitly permits optional
boolean `networkAccess`. The native response passed schema validation. The
failure is a **driver policy-comparison defect exposed by the native response**,
not an initialize/schema incompatibility or demonstrated weaker policy.
`networkAccess=false` is reported policy, not proof of OS/network confinement.

The thread reply accepted the requested model configuration. **Provider-side
model availability and credential validity remain untested**, because no turn
was submitted. No usage was reported; this does not assert provider billing
behavior. There is no model completion to recognize or reconcile.

Four numbered evidence records were saved: launch intent, owned child,
thread request intent and thread result. No native event record was saved:
the policy check rejected the reply before the notification-drain loop.
Thus no unexpected tool or approval event was captured, but absence from these
records does not prove absence of queued/startup events. Telemetry contains,
in order, `source.reconnected`, `process.heartbeat`, `source.disconnected`,
`process.exited`, and `agent.note` reporting the blocked driver.

## Timing, receipts and limits

Live CLI boundaries were **2026-11-16 03:37:22.151372 UTC** to
**03:37:28.756108 UTC**. Captured command elapsed time was
**6.604760200018063 host seconds**; the owner's separately measured lifecycle
was **2.4945982999633998 seconds**. The latter excludes earlier CLI validation.
No emulated execution occurred: **0 ms attributable emulated time**, guest
counter delta not measured.

The original protected run retains its unchanged plan, permanent attempt fence,
`receipts/operations.sqlite3`, four numbered evidence records, blocked outcome,
Codex home and telemetry spool. The adjacent private `live-result-20261115`
archive retains offline command outputs, authorization/verification record,
UTC/elapsed/exit command receipt, post-run status and process check, and
SHA-256/size inventories of all run files. Private helper scripts and their
inventory are retained there as experimental provenance. No raw credentials,
history, process identity or other excluded evidence is published.

The driver confirms direct-child disappearance but does not persist the native
exit code or whether its EOF grace period required kill fallback. Consequently
**normal clean native exit is unproved**, although owned-child teardown and
process exit were observed. Descendant cleanup, OS confinement, cloud
cancellation and spending caps remain unverified. Local observation deadlines
are neither cancellation evidence nor hard usage caps. No retry, replacement
plan, alternate model, live restart, S2 dispatch, emulator operation or security
setting change occurred. Issue 86 remains open.

## Smallest next step

Review a narrow policy-validator correction that accepts the schema-valid
readOnly policy with explicit `networkAccess=false`, while rejecting enabled
network access and other policy mismatches. Add focused regression coverage
using this sanitized observed policy shape. Preserve this attempted run;
changed implementation bytes require a fresh plan digest and separate operator
authorization before another live invocation. This report changes no driver
code and grants no second attempt.
