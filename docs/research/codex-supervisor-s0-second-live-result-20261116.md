# Second real supervisor-owned S0 canary

**S0 LIVE CANARY PASSED.** Exactly one authorized native app-server invocation
created one persistent thread and submitted one `turn/start`. The model returned
exactly `S0_CANARY_OK`; terminal notifications, full persisted history and the
on-disk rollout agreed. The owned direct child exited and the supervisor recorded
`completed`, reason `observed-terminal-and-history`, CLI exit **0**.

This is an actual native observation supporting [issue 58](https://github.com/smartyhall/deskmate-formats/issues/58),
not a synthetic test. The [first experiment](codex-supervisor-s0-live-result-20261115.md)
remains valid historical failure evidence. No retry, alternate model, additional
turn, live restart, S2 dispatch or emulator operation occurred.

## Exact identity and final offline checks

Reviewed implementation: `fe168c86d650f6e8aa4f3187fc4121cf7910783c`
([PR 95](https://github.com/smartyhall/deskmate-formats/pull/95)). The checkout was
clean at that revision. All **54 installed project Python modules** were hashed
against that revision's Git blobs; all matched. The installed schema matched its
Git blob and pinned SHA-256. `tools/check_install.py` passed using Python 3.13.17.
The runtime was Windows 10 build 19045, jsonschema 4.26.0, SQLite 3.50.4.

The exact existing run beneath the protected laboratory archive was
`s0-experimental-lab-20261112/canary-second-20261116T044724Z-41feb502c41e4cecb11402bc34ec019e`.
Canonical plan SHA-256:

`3e2703fee4a9221a97fb98dac7264a6b66d03be5f5ce48b34e7dc2ce8bd48cc6`

The driver's canonical JSON digest is the authorization identity. The original
serialized `plan.json` file SHA-256 is separately
`4e636f69b9461cd363dfa84a3c04f0f3531b21db068ea3c9dedc4729eedc4ba2`.
No replacement plan was generated or original plan changed.

Final offline status/preflight exited 0 and showed no attempt, no operations,
no outcome, and all seven checks true: authentication, configuration, executable,
implementation, never attempted, supported profile and empty scratch. Parameters
matched the grant: `experimental-lab`, Codex **0.166.0**, `gpt-6-luna`, `low`,
10-second per-RPC timeout, 60-second turn-observation bound, null S2 binding and
the fixed no-tools sentinel prompt from the [runbook](codex-supervisor-s0-live-canary.md).

Native executable SHA-256:
`9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`.
Protocol profile SHA-256:
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
Credential bytes and hashes remain private.

The operator separately accepted the documented experimental-lab risk and
authorized this exact directory/digest, one model turn and owned-child cleanup.
The [previous bounded inventory and rollback limitations](codex-supervisor-experimental-lab-validation.md)
were accepted without a new security campaign. Ordinary accessible VM files,
credentials and network resources remained accepted exposure. A host snapshot
identifier was unavailable from the guest; restoration was not tested. Risk
acceptance does not establish isolation.

## Execution and independently inspected result

The authorized PowerShell `live --authorize-live-plan $digest --accept-lab-risk
$digest` command was invoked **once**, using the specified verification Python
and run directory, followed by offline `status`. A private transcript and command
receipt preserve execution output, UTC boundaries, elapsed time and exit code.
Subsequent inspection used local files and process identity checks only; it
opened no further app-server connection.

| Acceptance observation | Actual evidence |
| --- | --- |
| Native initialization | `0002.json` owned-child record follows the checked AppServer constructor; telemetry reports completed protocol handshake. Raw initialize reply is not retained. |
| Persistent thread | Request ID 1, one acknowledged `thread/start`, completed ledger receipt, `ephemeral=false`, initially zero turns, matching scratch cwd. |
| Corrected policy validator | `0004.json`: model `gpt-6-luna`, provider `openai`, effort `low`, approval policy `never`, reviewer `user`, sandbox `{"networkAccess":false,"type":"readOnly"}`. The validator accepted this actual native reply before turn submission. |
| Exactly one turn | `0006.json` records one turn intent; request ID 2 acknowledged in `0007.json`. The ledger contains exactly thread/start and turn/start, both completed. |
| Sentinel | `0012.json` agentMessage completion is exactly `S0_CANARY_OK`; `0013.json` reports the same completed turn with no error. |
| Persisted history | `0014.json` records thread/read and thread/turns/list: same persistent thread, one completed turn, itemsView full, nextCursor null, exactly userMessage and agentMessage with the exact sentinel. thread/read reports idle; its empty turns field accompanies historyMode paginated and is not interpreted as absent history. |
| Independent disk inspection | The retained rollout contains one matching task_started/task_complete pair and matching final agent response. Token usage record and token_count agree. No function-call response item was found; additional_tools is context metadata, not a tool invocation. |
| Owned child | Outcome child_status stopped; later PID/creation-identity check returned not-found. Telemetry reports process.exited. No teardown exception or telemetry publication failure was recorded. |
| Supervisor outcome | Exit 0, completed, observed-terminal-and-history, telemetry_failed false. |

The seven saved notifications were thread/started, turn/started, user item
started/completed, agent item started/completed and turn/completed. No approval
or tool activity was observed in these records or the full turn history. This
does not prove the absence of unobserved activity outside the observation scope.

## Timing and usage

Live command UTC boundaries: **2026-11-16T04:58:39.2102210Z** through
**2026-11-16T04:58:50.1968878Z** (November 15 evening, America/New_York).
Measured live command elapsed time: **10.9801671 host seconds**. The owner's
separate lifecycle measurement was **6.968057699967176 seconds**, excluding
earlier CLI validation. Native terminal/history duration was **2374 ms**;
rollout time to first token was **2208 ms**. These clocks measure different
intervals and are not interchangeable.

Reported usage: **11,374 input tokens, 9 output tokens, 11,383 total tokens**;
cached input, cache-write input and reasoning output were each zero. This is
native reported usage from the retained rollout, not a billing or dollar-cost
measurement. The fixed prompt does not represent the entire model context.
No emulated execution occurred: **0 ms attributable emulated time**, guest
counter delta not measured.

## Evidence preservation and remaining limits

The [sanitized structured observation](../evidence/supervisor-s0-second-live-20261116.json)
publishes selected actual values, receipt states, event ordering and the sizes
and SHA-256 hashes of all 14 original numbered evidence records. It is a
projection for review, not raw wire evidence. Account paths, credentials and
credential hashes, native identifiers, raw model context/history and account
quota metadata are omitted. Original records remain privately inspectable by
an authorized reviewer against those hashes.

The exact protected run retains its permanent attempt fence, unchanged plan,
operations.sqlite3 ledger, 14 evidence records, outcome, Codex home including
the persistent rollout, and telemetry spool. The adjacent private archive
`live-result-second-20261116` retains final offline command receipts, source
verification, authorization scope, execution transcript/timing, post-status,
post-process check, inspection and usage extracts, helper scripts, and SHA-256/
size inventories of the run and archive. Raw evidence was not committed.
A complete private ZIP backup preserves all **242 run files**, independently
checked against the original SHA-256 inventory and ZIP CRCs. ZIP timestamp
metadata was clamped to the format's supported range; file bytes are unchanged.

The driver does not retain native exit code or whether EOF grace required kill
fallback: owned-child disappearance is verified, normal clean exit is unproved.
Raw initialize replies, stderr and invalid frames are not retained by the
driver. OS/network confinement, descendant cleanup, cloud cancellation,
spending caps, power-loss behavior and events after the window remain unverified.
The sentinel is a behavioral test, not an OS control. The accepted exposure and
historical negative findings remain unchanged.

This single-turn real S0 canary satisfies its eight observations. It does not
prove native restart/resume; that broader milestone in issue 58 remains open
for independent review and any separately authorized follow-up. **Issue 86
remains open; real S2 dispatch requires separate authorization.** No producing
worker merge, daemon, infrastructure change or further model invocation is
part of this result.

Publication checks passed: **82 portable supervisor tests** in 273.971 seconds
(synthetic peers only), installed-package/CLI checks, REUSE lint, repository
content audit, Ruff and Git diff whitespace checks. No implementation files
changed in this report PR. These checks do not add native acceptance evidence.
