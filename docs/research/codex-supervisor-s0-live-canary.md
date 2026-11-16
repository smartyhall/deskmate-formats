# Supervisor S0 first live canary — experimental lab runbook

**Second real invocation passed — November 16, 2026 UTC.** See the
[second observed result](codex-supervisor-s0-second-live-result-20261116.md) and
[sanitized evidence](../evidence/supervisor-s0-second-live-20261116.json).
The authorized second plan is permanently attempted and completed; do not rerun
it. No additional model invocation, native restart/resume or S2 dispatch is
authorized by this result. The preparation instructions below describe the
historical workflow and require a new separate grant for any future experiment.

**Historical first invocation stopped before a model turn.**
See the [November 15 observed result](codex-supervisor-s0-live-result-20261115.md).
The historical prepared plan is now permanently attempted; do not execute it again.
Its digest is `8226d264f380810230dd6443787dd8d46b17f252322c1a5559588a68dc809085`;
retain its attempt marker, receipts and authorization unchanged. The November 15
failure report remains historical evidence and is not revised by this correction.
Supports [issue 58](https://github.com/smartyhall/deskmate-formats/issues/58) and
[issue 86](https://github.com/smartyhall/deskmate-formats/issues/86).
Preparation and offline inspection consume no model turn. The `live` command
below consumes usage and requires a separate operator grant after review/merge.
Do not run every code block as a script.

The [accepted laboratory posture](experimental-lab-operating-posture.md) permits
ordinary local permissions in the existing recoverable Windows 10 research VM.
`experimental-lab` is explicit risk acceptance, **not verified OS isolation**.
The [November 11 audit](codex-supervisor-s0-readiness.md) remains historical
negative evidence; its former demand for additional confinement is superseded.
The [driver guide](codex-supervisor-operator-driver.md) describes receipts,
telemetry, synthetic reconciliation and the unchanged synthetic-only S2 bridge.

## Policy-validation correction and next experiment

The first native reply reported `{"type":"readOnly","networkAccess":false}`.
It passed the pinned schema but the driver's exact dictionary comparison rejected
the optional field. The corrected driver checks meaningful policy properties:
`type` must be `readOnly`; `networkAccess` may be absent or exactly boolean
`false`; no other sandbox attributes are accepted. Enabled network access,
strings, integers and null remain rejected. Schema validation and all other
model/provider, approval/reviewer, effort, cwd and empty persistent thread checks
remain in place. Reported policy still does not prove OS/network confinement.

Regression coverage uses an owned synthetic stdio child through the production
experimental-lab launch path, replacing only native identity and child image.
Both read-only representations must reach `turn/start`, sentinel completion and
history verification; invalid policies must stop before model input. These are
synthetic observations, not a successful native canary. This correction initiates
no real app-server model turn and changes neither the native nor schema pin.

After independent review and merge, the next step is section 1: build/install
the corrected reviewed wheel, verify installed source/pins, and prepare a fresh
directory and plan. Examine its offline status/preflight, then obtain **both new
exact-plan operator grants** in section 3 before executing section 4 once.
The old plan and grants cannot be reused. This bug-fix assignment authorizes no
live invocation; no new security prerequisites or laboratory changes are added.

## 1. Prepare a fresh experiment — no model usage

Install the reviewed wheel with the supervisor extra into a verification venv;
retain commit, wheel/sdist hashes, Python/dependency versions and build logs.
Do not attach to desktop Codex, start a service, use 86Box/Ghidra, change guest
media or host security settings, or upgrade the pinned Codex binary.

Use the existing lab's protected fixed-local-drive archive outside Git, cloud
sync and web roots. The storage API creates/checks private DACLs and rejects
redirected or linked evidence files. It cannot protect files from a child
running as the same user. Preserve partial directories after preparation errors.

The candidate is **`gpt-6-luna`, Low reasoning**: the pinned 0.166.0 source catalog
and November 12 local cache both list it with Low support. The local cache came
from CLI 0.167.0, so it alone does not establish pinned-client compatibility.
Official [model selection guidance](https://learn.chatgpt.com/docs/model-selection)
identifies Luna as the economical choice. Runtime account/model acceptance is
unverified until the separately authorized canary. Do not substitute the model
used for this development conversation. No automatic alternate-model fallback.

The native pin is Codex CLI **0.166.0**, SHA-256
`9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`.
The packaged protocol profile SHA-256 is
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
Resolve the actual native npm installation by inspection, not a PATH shim.
For the current lab, the following commands use environment-relative paths to
avoid embedding an account-specific installation path in public documentation:

```powershell
Set-Location C:\DeskMateLab\sources\deskmate-formats
$py = 'C:\DeskMateLab\private-evidence\s0-experimental-lab-20261112\verify\Scripts\python.exe'
$codexExe = Join-Path $env:APPDATA 'npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe'
$authFile = Join-Path $env:USERPROFILE '.codex\auth.json'
$run = Join-Path 'C:\DeskMateLab\private-evidence\s0-experimental-lab-20261112' ('canary-' + [guid]::NewGuid().ToString('N'))
git rev-parse HEAD
git status --short
& $py tools/check_install.py
$prepared = & $py -m deskmate_formats.supervisor.driver_cli --run $run prepare --profile experimental-lab --executable $codexExe --model gpt-6-luna --effort low --auth-file $authFile | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Preparation refused; preserve partial directory' }
$digest = $prepared.plan_sha256
& $py -m deskmate_formats.supervisor.driver_cli --run $run status
& $py -m deskmate_formats.supervisor.driver_cli --run $run preflight
```

Use a freshly built/installed reviewed version of `$py` after merge. The dated
venv is the development verification installation, not proof that a future
installation is current. The module CLI and `deskmate-supervisor-s0` entry point
are equivalent. Preparation runs only hash-verified `--version`; it never starts
an app-server session. `status` is offline. `preflight` repeats pins and reports
requested configuration, **not** discovered effective configuration.

`--auth-file` explicitly copies only the selected existing credential JSON into
the new private Codex home and binds its bytes privately in the plan. No secrets
appear in plan, diagnostics or public telemetry; never publish the home or its
credential hash. Source credentials are unchanged. There is no login/bootstrap,
keyring lookup or inherited API key/proxy fallback; config requests file storage.
Codex may refresh the staged copy. Keep it private and do not copy it back as
recovery. Missing/changed credentials require a fresh preparation and new grant,
not editing an authorized plan. Existing auth presence does not prove validity.

## 2. Examine the plan and practical lab readiness

Privately inspect `plan.json`, config and `preflight`: exact profile, model,
effort, executable/schema/config/module/authentication hashes, run ID, paths,
environment, fixed prompt, timeout **10 seconds per RPC**, turn observation
**60 seconds**, null S2 binding and no prior attempt/operations. Default and
unsupported live profiles remain blocked. `experimental-lab-awaiting-authorization`
means local checks passed and both grants are still needed.

Record the existing VM recovery procedure/snapshot with the operator. On VMware,
use the host's snapshot manager to restore the selected pre-experiment snapshot
with the VM powered off, retaining external evidence first. This campaign does
not operate the hypervisor or take/restore snapshots. Record the actual available
rollback point; do not invent a snapshot identifier or treat a guest app-disk
baseline as a VM backup.

Perform a brief guest-side inventory of mapped drives/shared-folder exposure,
known hypervisor-control tools and unrelated credential locations relevant to
this account. Keep target/account details private. Resolve a demonstrated
high-consequence path outside the lab proportionately. No exhaustive search,
second VM, new user or broad network restriction is a prerequisite. The
[November 12 validation report](codex-supervisor-experimental-lab-validation.md)
records actual findings and their observation limits.

Config requests OpenAI, Low effort, `approval_policy="never"`, read-only policy,
disabled web search and empty MCP configuration. Environment includes only
Windows system-directory variables and the new home/temp paths. These are
requested settings and hygiene, not enforced confinement. Same-user files,
credentials, loopback and network can remain accessible; merged machine/cloud
configuration and built-in tools are not completely inventoried. The driver
checks reported thread policy before model input and rejects reported tools or
approvals; that reaction cannot undo activity already performed.

The sole prompt is exactly:

> Reply exactly S0_CANARY_OK. Do not use tools, read or write files, run commands, access the network, or request approval.

## 3. Confirm lab risk and separately authorize model usage

The operator must approve the concrete reviewed plan, not this example or a
historical plan. Replace `<PLAN_SHA256>` and `<RUN_DIRECTORY>` with `status`
values, and record both statements privately:

> I acknowledge the experimental-lab risk for plan <PLAN_SHA256> in
> <RUN_DIRECTORY>. I accept ordinary Windows 10 VM permissions, accessible local
> files/credentials/network, unverified OS confinement and descendant containment,
> and the documented outside-lab inventory and rollback limits. This is risk
> acceptance, not an isolation attestation.

> I separately authorize exactly one supervisor-owned Codex 0.166.0 app-server
> invocation for plan <PLAN_SHA256> in <RUN_DIRECTORY>, using gpt-6-luna with Low
> reasoning, one new persistent thread and exactly the fixed S0 sentinel prompt
> once. I authorize the resulting model usage and owned direct-child teardown,
> including failure cleanup. Use 10-second per-RPC and 60-second turn-observation
> bounds. They do not cap provider spending or guarantee cancellation. No retry,
> alternate model, live restart, S2 dispatch or emulator operation is authorized.

Both digest arguments below are local exact-intent confirmations, not signatures
or authentication of an operator identity. An old `--isolation-reviewed` argument
cannot enable default live mode or replace the lab-risk acknowledgment.
Preparation, PR approval and merge do not grant this model invocation.

## 4. Execute once — OPERATOR-AUTHORIZED MODEL USAGE ONLY

Only after the specific grant above and reviewed installation:

```powershell
# This command starts the owned process and can consume model usage.
& $py -m deskmate_formats.supervisor.driver_cli --run $run live --authorize-live-plan $digest --accept-lab-risk $digest
$executionExit = $LASTEXITCODE
# Offline inspection is safe after success, failure or interruption:
& $py -m deskmate_formats.supervisor.driver_cli --run $run status
```

The owner permanently fsyncs `attempt.json` containing both grants before
constructing one child. It initializes the pinned protocol, starts one persistent
empty thread, sends one turn, observes allowed notifications, requires exact
`S0_CANARY_OK` output and successful terminal receipt, then reads the same thread's
full persisted turn history. Success requires exactly that one completed turn
and sentinel, no history cursor/extra turn/tool, and verified direct-child exit.
There is no second process for history verification in this first experiment.

## 5. Inspect and preserve evidence; handle blocked/uncertain outcomes

Keep the entire directory, including plan, attempt, bounded private numbered
evidence, `receipts/operations.sqlite3`, outcome, Codex home/history and telemetry
spool. Record UTC boundaries, exit code, host elapsed seconds and SHA-256 inventory
in the protected archive. Review any public summary independently; never publish
credentials, private paths, raw history, screenshots or commercial inputs.

Exit 0 with `state=completed` requires terminal, sentinel, full history and direct
child checks. Exit 4 means refusal/error (inspect whether an attempt exists);
5 means durable blocked outcome; 130 means interrupted. An attempt without
outcome is incomplete evidence and uncertain execution. Lost acknowledgments
remain `needs-reconciliation`; absence of an acknowledgment does not mean the
mutation failed. Preserve evidence before any recovery decision.

Never rerun an attempted directory, delete its fence, replay the turn or create a
new run to disguise a retry. No live resume/reconciliation is exposed. A new
experiment or read-only recovery process needs a separately reviewed operator
grant. Teardown owns only the direct child handle; descendant cleanup, cloud
cancellation, power-loss behavior and events after the observation window remain
unverified. Raw invalid frames, stderr and initialize wire replies are not saved;
constructor success establishes the checked handshake. Constructor/owner failure
can leave incomplete process evidence; the permanent fence remains.

The synthetic commands remain available without a profile flag. Real S2 dispatch
stays disabled until the real S0 result has been completed and independently
reviewed, followed by separate implementation/authorization. This development
campaign performs no real model invocation and no emulator interaction:
**0 ms attributable emulated time; guest counter delta not measured**.
