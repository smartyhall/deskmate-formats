# Experimental S0 lab profile — November 12 validation

Implementation checkpoint **`e3b5f37d79c5db67076b503a9491ff807b4e815e`** on
`codex/s0-experimental-lab`, based on fetched `origin/main`
`f119e8ac99626958b71100c17087416192f5afd9`. [PR 93](https://github.com/smartyhall/deskmate-formats/pull/93)
is for independent review; the producing worker does not merge it.
The [current runbook](codex-supervisor-s0-live-canary.md) supplies preparation,
exact separate approval statements and the command that consumes model usage.

**No additional real model invocation occurred.** Native execution was limited
to pinned `--version` checks and one offline schema export. No initialize,
thread/start or turn/start RPC was sent to real Codex. No emulator, guest disk,
Ghidra, host security setting, credits purchase or persistent service was used.
Attributable emulated execution: **0 ms**; guest-counter delta **not measured**.

## Changed launch behavior

Explicit `prepare --profile experimental-lab` and an existing `--auth-file` freeze
the model, effort, native/schema/config/module/authentication hashes, prompt,
run ID, paths and bounds. `live` requires both `--authorize-live-plan DIGEST`
and `--accept-lab-risk DIGEST` for that exact plan. Old isolation attestations
do not grant launch authority. Default/unsupported live profiles remain blocked;
S2 remains synthetic-only even if a caller supplies an accepted-task binding.

The successful gate uses the existing one-shot owner: permanent attempt receipt
before process creation, write-ahead operation receipts, one new persistent empty
thread, one fixed sentinel turn, notifications, terminal/exact-answer/full-history
checks and direct-child teardown. Missing acknowledgments remain uncertain;
there is no live retry, alternate model, restart, approval response or force-clear.
Ordinary VM permissions are accepted; OS confinement and descendant ownership
are **not** supplied or proved by this profile.

## Actual bounded Windows readiness findings

| Check | Observation | Limit/consequence |
| --- | --- | --- |
| Machine | Windows 10 Pro x64 build 19045; VMware7,1; VMware Tools running | Existing accepted lab, no new environment |
| Python/package | Python 3.13.17, SQLite 3.50.4, jsonschema 4.26.0; dedicated verification venv; 54 installed Python modules equal source | Base system package was older; it was not replaced. Isolated install required force-reinstall of the same version |
| Native | Codex 0.166.0; SHA-256 `9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42` | Native npm binary selected, no PATH shim/upgrade |
| Protocol | One fresh offline export: 321 files match the full committed inventory; profile SHA-256 `c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`; inventory SHA-256 `994ccd7691cdb81096b5c83bb2a4ce67c01ba5b935339367aedae7bb77839f24` | Export is not a real session or runtime compatibility result |
| Model/config | `gpt-6-luna`, Low; pinned bundled catalog lists Low; current local cache also lists it | Cache belongs to 0.167.0; real 0.166.0 account/model acceptance is untested |
| Authentication | Existing ChatGPT token structure present, no API-key field in that auth source; explicitly copied only auth.json into the protected new home | No credential values or credential hashes published; no login/refresh/provider validation performed |
| Directory | Fresh protected fixed-drive run outside Git, scratch empty, ledger empty, preflight checks true | Same-user child can still access other permitted VM resources |
| Host shares | Only local C: disk and D: optical drive in logical-disk query; no mapped connections; VMware shared-folder namespace absent on the check | Read-only guest inventory; no share write probe or host configuration query |
| Hypervisor control | No vmrun, VBoxManage, vmware-vdiskmanager or virsh found on PATH | Not a disk-wide search; host was not operated |
| Other credentials | GitHub CLI configuration location present; common SSH, AWS credential file, Azure, gcloud and Git plaintext-credential locations absent; no token/key/secret/password environment variable names observed | GitHub capability is an external-effect exposure to acknowledge; contents/scopes were not inventoried. Sanitized child env does not prevent same-user access |
| Rollback | Known procedure: retain evidence, power off the VM and restore the selected pre-experiment snapshot with VMware host snapshot manager | Actual snapshot identifiers are not observable from this guest. Operator confirmation was requested; do not invent a snapshot or claim restore was tested |

The brief inventory used bounded read-only CIM/PowerShell queries (20 seconds
per child), path presence and authentication/model **metadata only**. It did not
repeat the November 11 isolation audit or reopen issue 90. No concrete writable
host share or hypervisor control endpoint was demonstrated. Existing GitHub
configuration and host snapshot visibility limits are recorded for the exact
operator decision; they do not create a separate infrastructure campaign.

Pinned model-catalog source: OpenAI Codex
`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`, models-manager/models.json SHA-256
`1384625c0b6b3e67d3c60da29becea2b017f2c283fc1e2d05b8edafb4698eb10`.
Its description identifies Luna as fast/affordable and lists Low reasoning.
[Official model selection](https://learn.chatgpt.com/docs/model-selection) was
consulted as current guidance; pinned source/local observations control this
candidate. No current catalog or documentation proves account acceptance.

## Prepared real plan — not executed

Private run: `s0-experimental-lab-20261112/canary-reviewed` beneath the existing
protected lab evidence parent. Plan SHA-256:

`8226d264f380810230dd6443787dd8d46b17f252322c1a5559588a68dc809085`

Profile `experimental-lab`, model `gpt-6-luna`, effort `low`, fixed sentinel,
10-second RPC bound, 60-second turn-observation bound, null task binding.
Offline status records **no attempt, no operations, no outcome**. The private
preflight state is `experimental-lab-awaiting-authorization`, not live success.
Both operator approval statements in the runbook must name this digest and
run directory. Implementation review/merge alone does not authorize it.

Concrete approval text for this candidate, **not granted by this report**:

> I acknowledge experimental-lab risk for plan
> 8226d264f380810230dd6443787dd8d46b17f252322c1a5559588a68dc809085
> in C:\DeskMateLab\private-evidence\s0-experimental-lab-20261112\canary-reviewed.
> I accept the documented ordinary VM permissions, unverified confinement and
> descendant cleanup, credential-exposure inventory and rollback visibility
> limits. This does not authorize host or external actions.

> After independent implementation review and merge, I separately authorize
> exactly one supervisor-owned Codex 0.166.0 invocation for that exact plan and
> directory: gpt-6-luna, Low reasoning, one new persistent thread, exactly the
> fixed S0 sentinel prompt once, model usage and owned direct-child teardown
> including failure cleanup. Use 10-second RPC and 60-second turn-observation
> limits; these do not cap provider usage or prove cancellation. No retry,
> alternate model, live restart, S2 or emulator operation is authorized.
If module/config/auth/native bytes change, prepare a fresh plan and obtain new
exact-plan grants; never edit/reuse an attempted plan as recovery.

To examine this already prepared candidate and, only after separate authorization,
execute it, use the runbook's `$py` and set:

```powershell
$run = 'C:\DeskMateLab\private-evidence\s0-experimental-lab-20261112\canary-reviewed'
$digest = '8226d264f380810230dd6443787dd8d46b17f252322c1a5559588a68dc809085'
& $py -m deskmate_formats.supervisor.driver_cli --run $run status
& $py -m deskmate_formats.supervisor.driver_cli --run $run preflight
# Separate exact operator model-use grant required before this command:
& $py -m deskmate_formats.supervisor.driver_cli --run $run live --authorize-live-plan $digest --accept-lab-risk $digest
```

## Durable synthetic experiment

The protected archive `s0-experimental-lab-20261112` retains source and command
inventories, all command logs/exit codes/hashes, schema export, real preparation
receipts, and two complete synthetic production-live-path runs. In these runs
only native identity verification and the subprocess image were substituted;
the real profile gate, config, AppServer handshake, Operations, ledger,
telemetry, evidence and owner executed. The peer has no model/network client
and does not read credentials. Do not mislabel these as native observations.

Success observed exactly initialize, initialized, **one thread/start**, **one
turn/start**, thread/read, thread/turns/list; completed receipts and stopped child.
Owner elapsed **0.9500774000189267 host seconds**. Lost-ack observed one thread
and one turn send, an unacknowledged `needs-reconciliation` turn, blocked outcome
and stopped child in **0.9581780000007711 host seconds**. These are separate
synthetic cases, not two real turns. The complete private directories remain
available for independent review, with a redacted summary in the public receipt.

## Validation results

The implementation checkpoint passed all four Windows/Ubuntu Python 3.13/3.14
[CI jobs](https://github.com/smartyhall/deskmate-formats/actions/runs/43163794718),
including portable tests, native Windows deployment tests, Ruff, REUSE, builds,
installed entry points, archive/repository audit and synthetic MCP stdio checks.
The final local portable suite passed **397 tests in 338.360 unittest seconds**
(**343.62602830003016 host seconds**), including all 80 focused supervisor cases.
Checkpoint CI does not cover subsequent documentation/evidence edits. Final
artifact hashes and the standalone driver run are recorded in the structured
receipt accompanying this report.

The local deployment suite was executed twice: 31 cases each, two expected
Windows symlink-permission skips, and one 30-second timeout starting legacy
Windows PowerShell for the mocked Appraiser test. No deployment source was
changed. The same Appraiser script passed with installed pwsh in 2.762189400033094
host seconds; Windows CI passed the original PowerShell deployment test. This
is a measured local test-host limitation, not a new canary prerequisite.

Preliminary failures are retained privately. A same-version pip installation
initially selected the old global package; force-reinstall into the dedicated
venv corrected that. A development driver run hit the old 0.8-second read-only
restart bound. The delayed-ack fixture now waits six seconds and its test RPC
bound is five seconds, keeping handshake margin while still losing the reply.
The first broad focused run (80 cases) found a new success fixture's 0.3-second
observation timeout and an existing HTTP projection timeout; the HTTP case passed
in isolation and on the following broad run. That following run found the
original success fixture's 0.25-second observation timeout. Both success helpers
now use five-second test bounds; the production 10/60-second defaults did not
change. CI tested the committed corrections. No failed synthetic mutation was
replayed to obtain a pass.


The standalone driver suite passed **31 tests in 99.946 unittest seconds**
(**100.60519620002015 host seconds**). Ruff, REUSE, installed CLI checks and
repository audit passed. A clean detached worktree at the exact implementation
commit built wheel and sdist successfully; its archive/repository audit passed,
all 54 module bytes match the canonical installed wheel, committed driver tests
match the sdist, and binary fixtures/commercial inputs are excluded.
The [structured receipt](../evidence/supervisor-experimental-lab-20261112.json)
records commands, sizes, SHA-256 values, elapsed times and source/runtime pins.

Artifact comparison found one pre-existing checkout byte difference: the
one-line supervisor/__init__.py had CRLF while the Git blob/clean worktree had LF.
Its Python content was identical. The verification venv was reinstalled from
the clean committed wheel, and installed checks plus full-path synthetic success
and lost-ack demonstrations passed again. A fresh real plan (`canary-reviewed`)
was prepared against all 54 canonical module bytes. The earlier unattempted
`canary-prepared` plan is retained as superseded; do not execute it.
This alignment changed no runtime code; the full suites and canonical CI validate
the same implementation. No attempt fence was cleared and no real turn occurred.

The canonical-wheel synthetic owner elapsed **3.7033220999874175 host seconds**
for success and **0.7984126000083052 host seconds** for lost acknowledgment.
Both direct children stopped. Event/ledger/history evidence remains private;
exact methods and safe receipt summaries are published separately.

Reproduce the accepted checks with the reviewed verification interpreter and
clean implementation checkout (the deployment host limitation above is retained):

```powershell
& $py -m unittest discover -s tests/portable -p test_supervisor_driver.py -v
& $py -m unittest discover -s tests/portable -v
& $py -m unittest discover -s deployment/windows10/tests -v
pwsh.exe -NoProfile -File deployment/windows10/tests/test_appraiser_state.ps1
python -m build
& $py tools/check_install.py
python -m ruff check src tests/portable tools
python -m reuse lint
python tools/audit_repository.py
git diff --check
```

Remaining live observations are account/model acceptance, actual effective
thread policy, notifications, exact sentinel/history and direct-child exit.
OS confinement, descendant cleanup, provider cancellation/spending caps, startup
activity outside the allowed event subset and power-loss behavior remain
unverified. They are accurately documented limits of the accepted lab experiment,
not new isolation prerequisites. S2 dispatch remains disabled.
