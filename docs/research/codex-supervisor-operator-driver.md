# Supervisor operator driver and offline S2 foundation

This implements the offline Stage 1 and synthetic portion of Stage 3 in
[issue 86](https://github.com/smartyhall/deskmate-formats/issues/86).
**No live canary has been executed. Real S2 dispatch is disabled.**
The next live run requires new explicit authorization, review of this change,
and the isolation checks below. S1 acceptance never authorizes dispatch.

The implementation reuses `AppServer`, `Operations`, the S0 ledger,
`AppServerTelemetry`, S1 Git discovery/acceptance, private-storage protections,
and the existing Observatory journal/feed/HTTP projection. It adds no listener,
approval sender, scheduler, service, desktop automation or emulator adapter.
The [reuse ADR](agent-orchestrator-reuse-assessment.md) remains the architecture
decision. [S0](codex-supervisor-s0.md), [S1](codex-supervisor-s1.md),
[M0–M1](observatory-v2-m0-m1.md), and [M2](observatory-v2-m2.md) retain their roles.

## Installation and commands

Use Python 3.13 or later on native Windows or Linux. Build the reviewed
revision and install its wheel with the `supervisor` extra. The driver uses
standard-library process/SQLite APIs and the existing jsonschema dependency;
no POSIX process commands, shell invocation or host input injection are used.

```powershell
python -m build
python -m pip install --force-reinstall 'dist/deskmate_formats-0.1.0.dev0-py3-none-any.whl[supervisor]'
deskmate-supervisor-s0 --help
deskmate-supervisor-s2 --help
```

Installation, imports, help, preparation and status do not start an app-server
or model turn. Live preparation runs only the already hash-verified native
executable's bounded `--version` check. Synthetic execution is explicit too.
CLI output is **private**: redirect it only into the protected lab archive.
Exit codes are 0 for success/inspection, 4 for refusal/storage failure,
5 for a durable blocked outcome, 130 for interruption (argparse errors use 2).
CLI errors omit submitted values; inspect private receipts for details.

Choose a new absolute run directory under an existing protected fixed-local-drive
parent outside Git, cloud synchronization and web roots. The existing storage
API creates/validates private directories and files, rejects reparse points and
hard-linked files, and requires the protected Windows DACL documented in the
[live-canary runbook](codex-supervisor-s0-live-canary.md). Do not loosen a refused
DACL. Each run has separate scratch, codex-home, evidence, receipts and spool
directories. Preserve partial directories after a failed preparation.

```powershell
$run = 'C:\PRIVATE-LAB-PARENT\s0-synthetic-UNIQUE'
$prepared = deskmate-supervisor-s0 --run $run prepare | ConvertFrom-Json
deskmate-supervisor-s0 --run $run status
# Explicit synthetic authorization, after reviewing the private plan:
deskmate-supervisor-s0 --run $run synthetic --authorize-plan $prepared.plan_sha256
deskmate-supervisor-s0 --run $run status
```

`prepare --scenario` supports success, lost-ack, delayed-ack, driver-approval,
unknown-request, mismatched/duplicate reply, early exit, stale-turn, history-only
and other fault fixtures; see help for exact names. The installed peer is the
existing S0 test peer moved into the package, with additional driver scenarios.
The test entry point delegates to it. It has no network or model implementation.

## Durable ordering, evidence and limits

`plan.json` freezes the exact executable/interpreter hash, version and schema
pin, module hashes, runtime versions, argv, environment, prompt, config hash,
scratch path, run ID and optional accepted-task binding. Its digest is the
dispatch authorization token. An authorization digest is a local exact-intent
confirmation, not a remote authentication mechanism or a signature.

The driver locks one run and its operation ledger for the whole session.
It permanently writes/fsyncs `attempt.json` **before constructing the child**.
Even a crash before the first RPC forbids rerunning that intent. This deliberately
trades availability for avoiding replay. Request intent and exact parameters
are saved/fsynced before `Operations.execute`; the existing ledger reserves a
stable `<run-id>.thread` or `<run-id>.turn` identity and commits `sent-unknown`
before any pipe write. Successful responses are persisted as receipts before
dependent requests. A crash can leave evidence behind the ledger; the ledger
and exact server evidence govern reconciliation, never a missing evidence file.

There is at most one direct child per driver and one request at a time. The
existing native process claim binds its PID, creation stamp and generation.
Normal execution performs exactly `thread/start`, then `turn/start`, then
read-only `thread/read` and `thread/turns/list`. It checks the returned cwd,
model/provider, `approvalPolicy=never`, and exact read-only sandbox before the
turn. Unknown approvals are preserved and blocked without any response.
Unexpected tools, stale identities and malformed/duplicate responses stop the
canary. Effective configuration and tool restrictions still require operator
review: reacting to a tool event cannot undo a tool that already executed.

A completed canary requires the exact terminal notification, completed durable
turn receipt, one exact sentinel agent message, and exact completed history.
The sentinel is `S0_CANARY_OK`. An acknowledgement alone cannot pass. The private
task outcome can be blocked even when a turn receipt records observed completion
(for example, a bad sentinel or a failed later history check).

On timeout, approval, disconnect, interruption or failure, in-flight operations
become `needs-reconciliation`. An absent acknowledgement never proves no effect.
There is no retry, automatic interrupt, resume, approval, recovery mutation or
force-clear command. Every previously recorded operation ID is refused.
`status` is offline and does not alter operation database bytes. An owner crash
can leave an attempt with no outcome; that is unresolved, never dispatchable.

Private evidence contains bounded schema-validated results/events, launch/request
intents and the child claim, with at most 512 records / 4 MiB per normal attempt.
The protocol independently bounds frames, queues and waits. Raw invalid frames,
stderr and raw initialize replies are not captured; constructor success records
the verified handshake, not a saved wire transcript. `outcome.json` includes
private receipts, host elapsed seconds and verified direct-child exit status.
Filesystem flushes and SQLite `synchronous=EXTRA` were exercised; power-loss and
storage-controller guarantees were not tested.

Teardown closes only the retained `AppServer` object's direct-child handle. It
closes stdin, waits briefly, then kills/waits that child when needed. It never
looks up a process by executable name or kills a saved PID. Descendant ownership
and cleanup remain unqualified for a real child; this is not service recovery.
The driver does not remove scratch, evidence, authentication or guest resources.

One explicit synthetic read-only restart is available:

```powershell
deskmate-supervisor-s0 --run $run reconcile-synthetic --authorize-plan $prepared.plan_sha256
```

It verifies old saved process claims are no longer live, writes a permanent
reconciliation intent and starts a fresh synthetic generation. Only existing
`Operations.reconcile` reads/saved acknowledgements may settle receipts. A lost
turn acknowledgement without exact IDs remains unresolved even if the synthetic
peer contains a turn. Missing history/in-progress history remains unresolved.
There is no live restart CLI; a second real child needs a separate reviewed and
authorized read-only experiment, as specified in the original runbook.

## S2 manual synthetic gate

Use the existing `deskmate-supervisor-task` commands to initialize the trusted
source, discover the exact `ops/tasks/*.json` Git blob and explicitly accept
its review token. No task queue behavior changes. Discovery, acceptance,
grant preparation and dispatch are four separate actions.

```powershell
$state = 'C:\PRIVATE-LAB-PARENT\s2-state-UNIQUE'
$queue = 'C:\PRIVATE-LAB-PARENT\s1-queue'
# $acceptedToken comes from the exact existing S1 discovery/acceptance receipt.
$grant = deskmate-supervisor-s2 --state $state prepare-synthetic --queue $queue sample 1 --accepted-review-token $acceptedToken | ConvertFrom-Json
deskmate-supervisor-s2 --state $state inspect $grant.claim
# Distinct dispatch grant, reviewed separately from S1 acceptance:
deskmate-supervisor-s2 --state $state dispatch-synthetic --queue $queue $grant.claim --authorize-dispatch $grant.dispatch_token
deskmate-supervisor-s2 --state $state inspect $grant.claim
```

Use **one protected bridge state directory per S1 queue**, preserving it across
restarts. Its binding records the queue ID. A deterministic claim for
queue/task/revision permits one prepared plan; repeating preparation or dispatch
is refused, including after an uncertain attempt. Keep that directory and queue
under the same trusted local operator custody: copying/deleting state or using
a different state root is outside this cooperating-owner deduplication boundary.
It is not a host-wide resource lease or protection against the local administrator.

Dispatch rechecks accepted state, exact review token, source provenance/content
digest, queue ID, sequence, idempotency key, expiry, superseding revisions and
unresolved decisions. It holds the bridge lock across the worker, preventing a
second cooperating child. S1 is read-only throughout dispatch. Direct S0 CLI use
of a task-bound plan is refused; the bridge supplies the current acceptance check.
A Git change does nothing by itself. The bridge has no live worker option.

This foundation binds and observes a task; it does **not** execute task prose,
instruction references, portable-test commands or arbitrary Git hooks. Every
synthetic worker receives the fixed harmless canary prompt. Worktree execution,
real task prompts, live dispatch and follow-ups await successful authorized S0
acceptance and later review. No synthetic pass establishes those capabilities.

## Observatory and reproduction

The owner feeds validated lifecycle events to the existing allowlisted telemetry
publisher. Fixed summaries and salted opaque correlations exclude prompts,
raw thread/turn/item/approval IDs, commands, paths, configuration and model output.
A fixed driver outcome note distinguishes blocked/completed from turn lifecycle.
S2 adds a separate fixed synthetic-dispatch outcome note after committing its
private receipt. Publication failure cannot authorize another dispatch.
An owner crash can leave no terminal publication; inspect the private attempt.

```powershell
python -m deskmate_formats.observer.demo --text-only --port 0 --journal "$run\spool"
python tools/experimental/supervisor_offline_demo.py --private-root 'C:\PRIVATE-LAB-PARENT\s2-demo-UNIQUE'
```

The viewer is loopback/read-only and shows fictional machines. Its requests use
only immutable publication snapshots; it has no queue, driver or protocol handle.
The reproducible demo uses installed public CLIs, deterministic local synthetic Git
objects, discovery, acceptance, separate grant, explicit dispatch, terminal/history
evidence, durable outcome and actual HTTP GET/denial checks. It archives commands,
stdout/stderr and HTTP bodies privately; its `summary.json` is separately reviewed
for publication. HTTP reads must preserve queue, ledger, outcome and peer hashes.
No emulator time is measured. No emulator is launched or contacted.

## Accepted offline evidence

Implementation checkpoint: `ac858742b9c81d943351d4957fbab40a4fc4789b`, based on
fetched `origin/main` `22357a5524ddb56ae27b809479983a69b5360a0c`.
The [2026-11-08 receipt](../evidence/supervisor-offline-driver-20261108.json)
pins commands, module/package/log SHA-256 values, runtime versions and the
redacted synthetic demonstration. Private command/stdout/stderr/HTTP evidence
is preserved in the lab archives named by that receipt.

Windows 10 build 19045, AMD64, Python 3.13.17 and SQLite 3.50.4 were used.
The resolved npm native Codex executable still matched 0.166.0 and its
historical SHA-256; no compatibility drift was found in that selected input.
Preflight performed hash checking, `--version` and packaged schema validation
only, with zero real app-server launches and zero model turns.

The frozen implementation passed 58 focused Supervisor tests in 161.104 host
seconds and 375 portable tests in 197.592 host seconds. Deployment checks
passed 31 tests in 1.319 host seconds, with two Windows symlink-permission
skips. Ruff, REUSE, installed entry-point checks, repository/archive audit,
`git diff --check` and `git fsck --full` passed. Git reported existing dangling
objects, without integrity failure. Preliminary development failures were
retained privately; one intermediate run correctly refused implementation
changes after plan preparation. Accepted runs used frozen source bytes, all
nine implementation files independently matched against the committed blobs.

The synthetic Git demo used task commit
`6e79a5a417994dedeb5c82a7786cfd89c61ad2d9`, blob
`57a58c5df7df58c5b1f6021da209a9275d306dea`, and exactly 264 manifest bytes,
SHA-256 `0721517346befae87a276957d3f3e24972652a62b5ac91358fbb3ff4756f5057`.
Its one `thread/start` and one `turn/start` completed with one persisted synthetic
turn and stopped direct child. The driver elapsed exactly 0.7585974999819882
host seconds in that run. Actual HTTP checks returned 200 for events/agents,
405 for event POST and 404 for dispatch/operations. Queue, ledger, outcome and
peer-state hashes were unchanged by the HTTP reads. These are synthetic local
runtime observations, not evidence of real Codex execution or emulator timing.

Follow-up implementation `a0842d3bbbb31539b1a654049105942cbec6dad9` creates peer
state exclusively with owner-only file permissions and flushes/fsyncs it before
replacement. The success regression now reads that state through the private
evidence reader, including on Unix. All 375 portable tests passed again in
177.450 host seconds, and the CLI/HTTP demo completed again with unchanged
private hashes across browser reads. The receipt's `private_peer_followup`
preserves this run separately, with updated source/package/log hashes. The prior
evidence checkpoint also passed all four Windows/Ubuntu Python 3.13/3.14 CI jobs.

## Next separately authorized single live canary

**STOP before `live`. This document, tests, PR and prior grants do not authorize it.**
Use the original [live runbook](codex-supervisor-s0-live-canary.md) for host and
private-archive preparation. Review this driver and install the exact reviewed
wheel first. Preserve Git commit, package hashes, machine build, private evidence
and the plan digest. Do not attach to desktop Codex.

1. Resolve the absolute native `codex.exe`, not an npm shim or PATH alias. The
   driver requires version 0.166.0 and the historical native SHA-256
   `9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`.
   Drift is a stop, never an invitation to upgrade or replace the schema.
2. Prepare a new live plan with an explicitly available operator-selected model:

   ```powershell
   $liveRun = 'C:\PRIVATE-LAB-PARENT\s0-live-UNIQUE'
   $plan = deskmate-supervisor-s0 --run $liveRun prepare --executable $codexExe --model $operatorSelectedModel --effort $operatorSelectedEffort | ConvertFrom-Json
   deskmate-supervisor-s0 --run $liveRun status
   ```

3. Privately provision existing authorized authentication into the dedicated home,
   without login/bootstrap, new credits or credential logging in this experiment.
   Review the generated config and all effective machine/managed/ancestor settings
   against the pinned binary's non-launch help and version-matched sources. The
   template selects OpenAI, read-only sandbox, `never` approvals, disabled web search
   and an empty MCP table. The environment admits only Windows system-directory
   variables plus private home/temp paths; no inherited PATH, API keys, proxies,
   emulator credentials or project configuration. **An empty MCP table/dedicated
   home does not prove machine-policy/tool isolation.** Establish that there are no
   external/native tools or privileged settings; if that cannot be established,
   the precise blocker is effective launch isolation, and launch remains prohibited.
   The official [configuration reference](https://developers.openai.com/codex/config-reference)
   is current guidance, not proof of the pinned release's effective behavior.
4. Obtain a **new explicit operator authorization** naming this exact plan digest,
   model, one persistent new synthetic thread, one short paid/read-only turn,
   the observation bounds (10 s/RPC, 60 s turn observation) and owned direct-child
   teardown, including failure cleanup. These are host deadlines, not a provider
   token or spending cap. Record the authorization privately. The separate
   isolation-review digest is an operator attestation, not a bypass for step 3.
5. Only under that new grant, invoke exactly once:

   ```powershell
   deskmate-supervisor-s0 --run $liveRun live --authorize-live-plan $plan.plan_sha256 --isolation-reviewed $plan.plan_sha256
   deskmate-supervisor-s0 --run $liveRun status
   ```

6. Require completed receipt, exact sentinel, history confirmation, verified child
   exit and bounded private evidence. Validate redaction through the read-only
   viewer. Preserve failures/uncertainty; never rerun that intent or turn it into
   a fresh run as recovery. A separate live history/restart/lost-ack experiment
   is not authorized by this single-run grant. S2 remains synthetic-only even
   after a successful live S0 canary until separately reviewed and authorized.

If compatibility drift appears, preserve the installed binary/version hashes,
compare the new release's generated stable schema and source with the pinned
inventory, review wire/approval/ownership changes, update attribution/profile
and adversarial fixtures in a dedicated migration PR, and rerun portable/Windows
validation. Never silently relax the pin or launch a model to discover compatibility.
