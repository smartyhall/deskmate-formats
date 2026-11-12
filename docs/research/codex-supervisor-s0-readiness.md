# S0 live canary readiness — completed 2026-11-11

**Current implementation (2026-11-12):** the explicitly selected
`experimental-lab` profile can pass the launch gate with separate exact-plan
model-use authorization and lab-risk acknowledgment. Default live remains blocked.
Use the [current canary runbook](codex-supervisor-s0-live-canary.md).
The findings, blockers and proposed remedies below describe the historical
November 11 acceptance threshold, not prerequisites for this accepted lab profile.
No live turn was performed by the implementation campaign.

**Subsequent operator policy decision — 2026-11-11:**
This historical audit's observations—including tested outside-scratch
file and loopback access—remain valid. The operator's later
[experimental lab posture](experimental-lab-operating-posture.md)
accepts that **VM-local risk** for a single separately authorized S0
canary, superseding the audit's **recommended additional isolation
prerequisite**, not its recorded evidence. At audit completion the source had a
hard-coded live launch block. This report should not be misread as the
current experiment's unchanged risk-tolerance threshold.

**BLOCKED — SPECIFIC REMEDIATION REQUIRED.** The live-execution block remains
unconditional. Offline compatibility and synthetic regressions do not establish
containment for a real app-server process. No real app-server session, additional
model turn, auth provisioning, emulator interaction, host input, dependency
installation or Windows security change occurred in this completion campaign.

This finishes the interrupted investigation in
[PR 89](https://github.com/smartyhall/deskmate-formats/pull/89), supporting
[issue 58](https://github.com/smartyhall/deskmate-formats/issues/58) and
[issue 86](https://github.com/smartyhall/deskmate-formats/issues/86).
Recovery on `codex/s0-live-readiness` began at
`96864b6cd74f510e6307b15c64eecd9b899fff8f`, based on
`619b2b9bf6a1a951cb61029fdb8460b311925c54`. Existing uncommitted documentation
and tests were backed up privately before editing. The
[structured receipt](../evidence/supervisor-readiness-20261111.json) identifies the
implementation revision, file hashes, environment, commands and results.
The tested probe/test content is committed as
`90291b931615fdea96d15bb38f24e00b05c01c05`; subsequent changes are reports and
runbook notices. The probe's captured HEAD remains 96864b6 because it ran before
that commit; its own source hash and the test hashes identify the tested content.
Raw evidence remains in the protected private archive `s0-readiness-20261108`;
completion evidence is under `resume-20261111`.

## Seven-file checkpoint audit

All seven files changed by `96864b6` were reviewed, including the probe sidecar.
Prelaunch prevention and observations after activity are separate guarantees.

| Code path | Finding and limit |
| --- | --- |
| `driver.py:_validate_plan`, `run` | Every live plan raises before the attempt marker, AppServer construction or any thread/turn RPC, even with matching authorization/isolation digests. Hash/version utility checks can occur. This is prelaunch prevention; there is no bypass flag. |
| `driver.py:implementation_hashes`, `preflight`; `driver_cli.py` | Plans bind all 54 installed project Python modules, executable, schema and config pins. Offline preflight reports requested settings and explicit blockers, not effective configuration. A digest is intent confirmation, not containment or a signature. Privileged concurrent replacement remains outside this guarantee. |
| `driver.py:_effective_policy` | Before turn/start, checks cwd, model/provider, never approvals, user reviewer, effort, read-only policy and persistent empty thread. These are server response checks after thread creation, not proof of OS enforcement or absence of startup activity. |
| `driver.py:_check_items`, `_event`, `_own` | Positive item allowlist admits only user/agent messages and reasoning. Checks response/event/history items, exact thread/turn, one completed full-history turn, no cursor and exactly one persisted/observed sentinel. Detects reported tool activity after it may have occurred. Unknown notifications remain discarded. |
| `protocol.py:AppServer._event` | Duplicate/contradictory terminal events and terminal-then-start fail the session. Existing schema, ID, framing and generation checks remain intact. Events outside the bounded observation window are not ruled out. |
| `synthetic_peer.py`; `test_supervisor_driver.py` | Controlled negative cases cover tools, reviewer/effort/policy drift, hidden/partial history, stale IDs, duplicate terminals, lost acknowledgements, replay, teardown and process identity. The peer is not Codex. |
| `experimental/supervisor_readiness_probe.py` and sidecar | Windows-only offline inventory, corrected and executed as below. Success does not change the live gate. Software sidecar is GPL-3.0-or-later. |

Existing write-ahead SQLite receipts and the permanent attempt fence preserve
uncertainty after lost acknowledgements and reject replay. Synthetic reconciliation
uses read-only RPCs; an unacknowledged turn stays unresolved. Direct-child ownership
uses the retained process handle and creation stamp. Teardown timeout or
unverifiable exit blocks success. Constructor failure/owner crash can leave
incomplete child evidence; the no-replay fence survives. No descendant boundary
is installed by this driver.

Observatory receives fixed summaries and salted correlations, without prompts,
commands, raw results, credentials or transport access. Synthetic secret-marker
tests verify this separation. An observed terminal event is not final driver
success. Private DACLs protect evidence from other ordinary users, but not from
a child running as the same owner.

## Actual offline Windows preflight

Laboratory: Windows 10 build **19045**, Python **3.13.17**. The retained verification
venv contains the checkpoint wheel; all 54 installed project modules match source
byte-for-byte. No system project installation was replaced.
Native identity: **Codex CLI 0.166.0**, SHA-256
`9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`.
The exact private path is retained in `native-probe-final/probe.json`.
This verifies the existing pin, not binary/source reproducibility.

The interrupted run's original `native-probe/probe.json` already recorded two
successful exports and was preserved unchanged. Code review found inherited
environment on the initial version check, unenforced schema equality, unchecked
registry paths and loss of partial output on timeout. Corrections:

* Hash the absolute native executable and reject a reparse-point executable
  before native commands. Version, Git, schema export and profile extraction use
  the minimal home/temp/system-directory environment; extraction uses Python -I.
* Require both exports to equal each other and the full committed inventory,
  including the packaged profile hash. Drift raises without a success record.
* Validate registry type and absolute path; reject nonlocal/redirected policy
  inspection. Inspection errors mean unknown, not absent. This is deliberately
  stricter than the pinned loader on registry errors, not a complete loader emulator.
* Preserve partial streams and failure receipts on timeout/process-start error.
  Stream files use private-file checks and fsync within the protected DACL.
  An archive without a final probe.json is incomplete evidence.

SHGetKnownFolderPath and CoTaskMemFree have declared ctypes signatures, the GUID
uses Windows little-endian layout, and the allocated string is freed. Registry
inspection uses the 64-bit HKLM view. No configuration contents, auth file or
credential store was read. Configuration inspection records path presence only.
The probe changes no registry, policy or sandbox setup.

Reproduce using existing dependencies, a fresh private directory and the pinned
native path, never an npm/PATH shim:

~~~powershell
git fetch origin
git status --short --branch
git rev-parse HEAD
$py = 'C:\PRIVATE-PARENT\verify\Scripts\python.exe'
$exe = 'C:\PINNED-INSTALLATION\bin\codex.exe'
& $py tools/experimental/supervisor_readiness_probe.py --archive C:\PRIVATE-PARENT\probe-NEW --executable $exe --checkout C:\DeskMateLab\sources\deskmate-formats
~~~

Final invocation exited **0**. Both offline exports have **321** JSON files,
matching every committed path/hash. Profile SHA-256:
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
Inventory SHA-256:
`994ccd7691cdb81096b5c83bb2a4ce67c01ba5b935339367aedae7bb77839f24`.
System config/requirements, registry override and inspected scratch ancestor
.codex/config.toml paths were absent at inspection time. This is not a cloud or
effective-config query. Native invocations were --version and app-server
generate-json-schema --out; no initialize/thread/turn RPC occurred.
Pinned CLI source dispatches the generator directly without a server session.

The retained live-plan's offline CLI preflight was inspected: blocked, pins true,
no attempt marker, operations or outcome. Its model/effort are historical
unapproved candidates, not proof of availability. Prepare a fresh plan after
remediation; do not reuse that candidate as authorization.

## Blockers and minimum corrective work

Version-matched findings use OpenAI Codex
[`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`](https://github.com/openai/codex/tree/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856)
(rust-v0.166.0). All 32 retained source files were rehashed against the original
inventory and Git blob IDs in the retained complete upstream tree. Receipt lists
their SHA-256 hashes. Paths below are relative to codex-rs/.

| Blocker | Verified facts/evidence | Unknowns | Minimum correction; prevents first live S0? |
| --- | --- | --- | --- |
| A. OS containment | Driver installs no Job, restricted token, filesystem or network boundary around app-server. Read-only policy permits root reads (`protocol/src/permissions.rs:606–623`). Backend selection is separate (`core/src/windows_sandbox.rs:124–150`, `sandboxing/src/manager.rs:313–329`). A synthetic child with the proposed environment/cwd read and wrote disposable outside-scratch files and contacted only our own ephemeral loopback listener. Win32 inspection: current process not elevated, restrictions flag true, not AppContainer, already in a Job. Required Job/create-process API symbols exist. | Existing Job policy was not inspected. Job presence, token flags and API availability do not prove the intended restrictions. No real backend, descendant cleanup or network allowlist was verified. | Separately authorize a scoped contained launcher/deployment: restricted execution identity, staged runtime, home, scratch and authentication access only, denial of unrelated lab data/control endpoints, required-provider network access, and pre-execution descendant ownership with no breakaway and owner-exit cleanup. Prove denial/cleanup with synthetic children first. A kill-on-close Job alone does not restrict files/network. **Yes.** |
| B. Effective configuration/tools | Precedence: package, system, cloud, user, selected profile, trusted cwd/ancestor/repository, runtime (`config/src/loader/mod.rs:108–137,208–434`); requirements compose separately. ProgramData uses known-folder lookup; HKLM can override requirements. Empty MCP table does not delete lower-layer keys: recursive merge (`config/src/merge.rs:143–153`). Shell/image features can default on (`features/src/lib.rs`, `core/src/tools/spec_plan.rs`); image access does not need PATH/shell. These are source findings plus local presence observations. | Complete merged config, cloud/package additions, tool catalog, provider endpoints, approval behavior and selected sandbox remain unobserved. Thread response covers only part of this. | Audit/freeze relevant local/managed/provider layers and explicit built-in/MCP/plugin/hook policy. Check effective settings before model input in an already-contained initialization experiment. Reject unexpected tools through configuration and OS restrictions; post-event rejection is insufficient. **Yes.** |
| C. Authentication | `login/src/auth/storage.rs:229–298,503–570` supports home-scoped file storage and home-path-derived keyring identity. `core/src/config/mod.rs:4582–4596` selects storage subject to config. No credentials inspected/copied/provisioned. Sanitized environment excludes inherited keys/tokens/proxies. New home changes lookup identity, not OS access rights. | Authorized credential availability, selected auth storage, account/workspace restrictions and runtime acceptance remain unverified. Same-user access to unrelated credentials remains possible. | Operator selects existing authorized auth and securely provisions only required material into the contained identity/home through an approved procedure. Review storage/ACLs without recording secrets. Do not copy a whole Codex home, inherit credential environment or use login/bootstrap fallback. If existing auth cannot be supplied safely, obtain separate bootstrap authorization. **Yes.** |

Current [official configuration guidance](https://learn.chatgpt.com/docs/config-file/config-basic)
and [authentication guidance](https://learn.chatgpt.com/docs/auth) were consulted.
They are moving documentation, not proof of the installed release's behavior.
Version-pinned source and actual offline observations control these findings.

## Validation and observed failures

All **387** portable tests passed in **230.604** unittest seconds
(234.771 host seconds). Deployment: **31** tests in **22.959** unittest seconds
(23.501 host seconds), with two expected Windows symlink-permission skips.
The receipt records focused/full portable, Windows deployment, native Appraiser,
installed-package, Ruff, REUSE and repository-audit results and output hashes.
[CI 42511499540](https://github.com/smartyhall/deskmate-formats/actions/runs/42511499540)
was independently queried: all four Windows/Ubuntu Python 3.13/3.14 jobs passed
at 96864b6. Completion CI is linked in PR 89; checkpoint CI does not validate later edits.

Two preliminary focused runs failed; actual logs remain private:
focused.log raised KeyError: child_status in the hook-item subcase. Insufficient
constructor evidence was retained to establish the cause. Rejection tests had a
two-second startup bound; they now use five seconds, preserving the short turn
deadline. focused-corrected.log raised LockBusy on read-only status immediately
after forced owner exit. That test now waits at most five seconds for lock release,
using read-only status. No dispatch/mutation is retried. Owner-specific follow-up
passed. Production deadlines, gates and no-replay behavior were unchanged.

Windows PowerShell's Appraiser invocation was blocked by its execution policy.
The same script passed using the already-installed pwsh, with no policy override
or security-setting change. Both command outcomes are retained.

An initial repository audit rejected a prose slash-list as a POSIX home path;
the list was rewritten with commas. No private path was published.
Local python -m build --no-isolation failed because setuptools is absent.
No dependencies were installed. Retained wheel/sdist hashes, source/installed
module comparison, archive exclusion and installed CLI checks provide local
packaging evidence; fresh completion packaging is checked by CI. Binary application
fixtures remain excluded from wheel/sdist.

~~~powershell
& $py -m unittest discover -s tests/portable -p test_supervisor_driver.py -v
& $py -m unittest discover -s tests/portable -p test_supervisor_readiness_probe.py -v
& $py -m unittest discover -s tests/portable -p test_supervisor_protocol.py -v
& $py -m unittest discover -s tests/portable -v
& $py -m unittest discover -s deployment/windows10/tests -v
pwsh.exe -NoProfile -File deployment/windows10/tests/test_appraiser_state.ps1
& $py tools/check_install.py
& $py -m ruff check src tests/portable tools
& $py -m reuse lint
& $py tools/audit_repository.py
~~~

## Next experiment and authorization

The minimum next action is separately authorized **synthetic containment
remediation/verification**, addressing A and credential exposure in C before
any native session. Use disposable markers and owned network peers to prove
outside-resource denial, descendant ownership, owner-crash cleanup and identity
handling. Review/pin config/auth inputs, then review a launcher correction before
considering removal of the hard block.

After independently enforceable prelaunch requirements pass, obtain new operator
authorization naming the exact plan digest, selected model/effort, one persistent
disposable thread, one S0 turn, observation bounds and cleanup. Remaining live-only
observations include authorized auth/model availability, effective settings/tools,
real protocol/events, exact sentinel/full history, and descendant exit/cancellation.
Initialization itself requires containment; policy checks after startup cannot
protect startup. Live restart/lost-ack experiments and S2 require separate grants.
Host deadlines are neither a provider spending cap nor proof of cloud cancellation.

**BLOCKED — SPECIFIC REMEDIATION REQUIRED:** A, B and C each prevent safely
authorizing the first live S0 canary. No valid live command is supplied.
Attributable emulated execution: **0 ms**; guest counter delta **not measured**
because no emulator connection occurred. This is a completed blocked research
outcome, not a partially activated supervisor.

