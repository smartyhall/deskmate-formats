# First real S3 Git-delivered dispatch: blocked before editing

On 2026-11-17, exactly one manually authorized real S3 dispatch of
`calendar-listing-alarm`, revision 1, S1 acceptance sequence 2, returned **exit 5**.
The native app-server initialized and acknowledged one persistent thread, but
reported `readOnly` rather than the frozen `workspaceWrite` sandbox. The supervisor
refused the effective policy before submitting `turn/start`. No editing turn,
source change, validation command or local task checkpoint occurred. The intended
success criterion was not achieved. No retry, steering or infrastructure repair
was attempted.

## Frozen provenance and offline checks

- Reviewed implementation/task commit: `31158e1833406cdcd00a575a3a82b2f90f8f3212` (PR #99).
- Claim: `883aa0e5db4fbc586a788caff894273fae0deb24ce144163ed8de290bc8bade5`.
- Canonical plan SHA-256: `a6efdbe7e569014cc2c486723eb9aadc7b239b31e017fc7925352a139c9f9fd6`.
- Serialized original plan SHA-256: `ac7a4c6f95bd73d389f61b370169d2cff3737a5e65ac5af607a84c3e748880fd`.
- Accepted manifest blob: `68d591fd28817276caa525d2e4721482b4fad1ce`;
  SHA-256 `a38bb0ce2c85c733ea1b610cc67e3e2ce4713b3785eeb52e5a0cca733df4a78b`.
- Exact source parent: `9f3e38ee0fa93c6776d2d57d6a51a04c18596e7c`.
- Native Codex: `0.166.0`; executable SHA-256
  `9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`.
- Protocol profile SHA-256: `c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
- Model `gpt-6-luna`, effort `low`, profile `experimental-lab`;
  RPC timeout 10 seconds, turn observation bound 300 seconds.

The complete operator handoff and merged S3 runbook were read. Existing offline
inspect and validate both exited 0. All eight preflight checks were true, with no
live blockers. Independent checks confirmed all 59 installed module hashes against
reviewed source, the original plan bytes/digest, model and bounds, staged/source
authentication equality without printing credentials, accepted identities, frozen
scope, pristine files and Git metadata, and absent prior attempt/operations/outcome/
checkpoint. Both trusted local main and directly queried remote main remained at
the reviewed commit immediately before dispatch. No plan or manifest was changed.

## Native observations

The retained dispatch completed at `2026-11-17T06:06:58.7012336Z`; worker owner
elapsed time was `2.1249795999610797` host seconds. This is not emulated time or a
provider usage measurement. Exactly one dispatch command was invoked.

The durable operation ledger contains one acknowledged, completed `thread/start`
(request 1), thread `01a1e81d-9e24-7001-910d-0ee906a17b0f`. Returned CLI version,
model/provider, low reasoning, exact workspace cwd, persistent thread, never
approval policy and user reviewer matched the selected values. The returned
thread was idle with no turns. Its sandbox was exactly:

```json
{"networkAccess": false, "type": "readOnly"}
```

The frozen staged config requested `workspace-write`, network false and both
temporary-root exclusions true. The actual response lacked those exclusion fields
and had the wrong sandbox type. `_effective_policy` raised the original error:
`editing sandbox policy differs from reviewed plan` (`DriverError`). This is an
observed configuration incompatibility; its native root cause is **unresolved**.
The experiment does not establish why native Codex selected read-only policy.

There was **one thread and zero turn/start operations**. There was no model final
response, terminal editing event, fileChange event, or supervisor history-read
receipt. Terminal/history agreement therefore cannot be assessed. Native
apply_patch availability, cloud authentication acceptance, model editing ability
and effective feature enforcement remain untested. No approval or unauthorized
tool activity appears in the retained supervisor operation/evidence records;
absence of a submitted turn is not proof of OS confinement.

Owned direct child PID 9044 was recorded with its process identity. Supervisor
cleanup reported `stopped`; independent post-run identity verification reported
`not-found`. This verifies direct-child cleanup, not descendant containment.
No emulator was used; requested emulated time was 0 ms, guest clock unmeasured.

## Independent source, validation and Git inspection

Full filesystem and Git metadata inventories still exactly match the frozen
initial inventories. The independently retained binary Git diff is empty. Both
authorized source paths are unchanged; no files were created or deleted.

| Planned supervisor validation | Fixed deadline | Actual outcome | Exit status |
| --- | ---: | --- | --- |
| Python `-m unittest discover -s tests/portable -v` | 1800 s | not-run: validation-not-reached | none |
| Installed publication audit under Python `-I` | 600 s | not-run: validation-not-reached | none |
| Python `-m reuse lint` | 600 s | not-run: validation-not-reached | none |

Actual task portable tests executed: **0**. No validation timed out; no command
result or output hash exists for an unexecuted step. The checkpoint outcome is
`blocked`, reason `worker incomplete; changes retained`. The checkpoint intent
exists, but there is no staged/object receipt, new commit or ref advance.

The local task branch remains `s3/ec9532d7fa15461082152cfbfd7462b3`, clean,
with HEAD/source parent `9f3e38ee0fa93c6776d2d57d6a51a04c18596e7c` and tree
`41c8e96ea225419c457dae4818cbfe98de5797b3`. No task branch was published.

| Unchanged file | Git blob | SHA-256 |
| --- | --- | --- |
| `src/deskmate_formats/calendar/cli.py` | `aa8104cbecd19145dc95b97b0b8f3c2cc53de3d4` | `4ed90a8dd64165219ed4c68172ea2504181fc0146e0c5ce2c04210be1f9c83f1` |
| `tests/portable/test_calendar.py` | `5f3ac900f6a2d8d1897aa61bf047586fd230ed5c` | `a5d0b96cca225f09348297bbd7889153cfcbb7567c56b3a955b692cfbf1f1d33` |

## Evidence custody and next independent action

The original private preparation and S3 state remain in custody. A private ZIP
retains the complete preparation, original plan, disposable workspace, queue,
operation/evidence/outcome records, dispatch transcript and exit code, empty diff
and independent verification scripts/receipts. It has 1703 entries, 7,829,861 bytes,
and SHA-256 `13655b5f568cd28fb85f36b27a48029dadbc9cc272b699caf84f7653b217ee21`.
An adjacent inventory records individual entry sizes/hashes. Raw authentication,
model context, private paths and native state are deliberately excluded from this
public report. The archive is private and includes sensitive authentication data.

This reporting branch contains documentation only, independently of the local
task workspace. Reporting checks do not substitute for the unrun task validation.
PR #100 and trusted main were not advanced or merged during execution.

The next action is independent review of the original frozen config, native
thread-result receipt, operation ledger, blocked outcomes and pristine workspace,
then review of this sanitized report. Any native-policy diagnosis, code fix,
replacement preparation or later dispatch requires a separate assignment and
applicable review/authorization. This permanently attempted claim is not replayed.

Reporting validation: repository publication audit, REUSE lint and Git whitespace
check each exited 0 on the documentation branch. No task tests were rerun.
