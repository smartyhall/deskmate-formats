# S3 Windows synthetic validation, 2026-11-16

The bounded editing implementation is `b6cbd6ba935618f8cc7c81299ea95359d45802e3`, based on
reviewed main `9f3e38ee0fa93c6776d2d57d6a51a04c18596e7c`. This report and its
[structured receipt](../evidence/supervisor-s3-20261116.json) are a later evidence
projection; the packages below were built from the implementation snapshot.
No real supervisor-dispatched model, native editing turn or emulator operation
was performed. The [S3 contract and runbook](codex-supervisor-s3.md) distinguish
this synthetic result from a future independently authorized live task.

## Actual checks

| Check | Result |
| --- | --- |
| Full portable suite | **422 passed**, zero skipped, **806.663 host seconds**, including **105 supervisor cases**. |
| Focused S3 suite | **10 passed**, **262.692 host seconds**. |
| Windows deployment suite | **31 run**, **29 passed / 2 skipped**, **4.442 host seconds**. Skips concern unavailable directory-symlink privileges, not S3. |
| Windows PowerShell appraiser mocks | Passed; no Task Scheduler/VM mutation. |
| Ruff, REUSE, repository content audit | Passed. Source audit checked 711 files and all nine declared application-generated fixtures. |
| Wheel/sdist build and installed CLI/import checks | Passed on Python 3.13.17 / Windows 10 build 19045. |
| Installed-source identity | All **59** installed Python modules exactly match the wheel and Git blobs at the implementation commit. |
| Package binary exclusions | Neither wheel nor sdist contains CLN/ADR/FIL/PCL research binaries. |

Exact commands are in the runbook. The private logs are hash-bound in the JSON
receipt; only frozen-code final runs above count toward acceptance. Earlier
development logs remain private and are not substituted for final results.
The native-profile unit test substitutes a synthetic process image and fake
authentication data while exercising exact live-kind grants and policy checks;
it is not evidence of native Codex execution.

Packages, preserved privately with their build/install transcripts:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `deskmate_formats-0.1.0.dev0-py3-none-any.whl` | 231458 | `baa95f8fc5432e698525f6fca50af6a52289ede344077fce9058cb36d359b275` |
| `deskmate_formats-0.1.0.dev0.tar.gz` | 923018 | `4299e4446c4d86ae76d352e864cc9c5d3ea6aa3e372d5d3f150d4e42a661ab21` |

## Installed-package end-to-end result

The installed public task and S3 CLIs performed discovery, explicit acceptance,
offline preparation/validation, bad-grant refusal, synthetic dispatch and local
checkpointing in a standalone disposable clone. Git task commit
`63100c0ca1325d09860ed4f6360581f453dc051f` contains manifest blob `6be91798185467bdf43eefb3c21208983d0476a3`;
its reviewed source parent is `5769479b69fa25ef6ed11619a594994ac20fac51`.
The exact source, manifest, document, plan, queue, attempt, operation ledger,
notifications/history, response, test output, staged-tree/object receipts,
checkpoint outcome, HTTP bodies and command transcripts remain private.

Resulting local commit: **`ac0a5af3596daa339b4d2037249dc924db35213c`**.
Parent: `5769479b69fa25ef6ed11619a594994ac20fac51`. Tree: `69dd56d2afdc3ae8d914399bca048c65a3767896`.
Independent inspection checked the exact parent, file set, both complete Git
blob contents and a clean final working tree. It changes only:

- `src/sample.py`: `answer()` returns **2**, exact 27 bytes,
  SHA-256 `f760ecee8d16c1da2171e50cb1143db3102e4f71e0e307d28c85331dd0a07306`.
- `tests/portable/test_s3_sample.py`: real unittest asserts **2**, exact 144 bytes,
  SHA-256 `31110bdbba3b0f7cc48448405a9e140441fe4b707b0760d7c89999e101337da8`.

The actual unittest, installed publication auditor and REUSE commands each exited
**0**, with argv/interpreter/cwd/status/output hashes retained. These are process
observations, not agent assertions. One persistent synthetic thread/turn and
completed operation receipts were verified against exact full input/history and
scoped fileChange activity. The direct child was verified stopped.

Observatory GET events/agents returned **200**, POST events **405**, and control
routes **404**. No prompt, answer or private root appeared in the event response.
Duplicate dispatch was refused. Queue/ledger/outcome/peer hashes stayed unchanged
across duplicate dispatch and HTTP reads. This is a real local HTTP observation
against the existing read-only viewer, not a new control service.

## Failure and retention scope

The portable S3 tests cover unaccepted/stale tasks, source/workspace changes,
wrong class or grants, duplicate preparation/dispatch/checkpoint, dirty Git
metadata, unauthorized/unexpected files, actual test failure, publication-audit
failure, executable/unsupported tools, unexpected approvals, EOF/lost
acknowledgment, interrupted owner and incomplete checkpoint after object creation
before ref update. Modified workspaces and diagnostics remain available at the
supervisor boundary. Temporary test harnesses clean up only after assertions;
the installed demonstration and four supplemental installed-package failure cases
(unauthorized edit, test failure, publication-audit failure and lost acknowledgment)
retain their full workspaces/receipts. Each refused another dispatch with unchanged
outcome bytes.

A checkpoint intent prevents another attempt even when staging/object/ref status
is incomplete. An interrupted worker leaves its permanent attempt and owner
outcome without inventing a checkpoint. Existing read-only contracts passed their
full regression suite; they were not converted into write-capable tasks.

## Native preparation and limits

Pinned-source inspection established separate shell-tool and apply_patch
registration, and the existing native schema contains workspaceWrite and
fileChange. The live-capable profile freezes the clone cwd and scoped source,
disables shell/JS/code-mode/subagent/Git-commit features, requests network false,
retains never/user approvals and rejects unsupported activity. Its runtime
assumptions and exact source hashes are in the contract/receipt. Actual model
apply_patch availability, effective features and Windows write-policy behavior
remain **unexecuted**, requiring independent review and separate exact-plan
model-use/dispatch/lab-risk/checkpoint grants. No OS isolation, descendant cleanup,
provider cancellation, spending cap or power-loss guarantee is claimed.

Requested emulated time: **0 ms**. No emulator was launched or connected; no guest
clock delta was measured. The synthetic owner's measured host lifecycle is
recorded separately from validation commands and overall demonstration duration.

The proposed first real task is
[Calendar alarm text listing](../../ops/tasks/calendar-listing-alarm.json), with
only calendar/cli.py and test_calendar.py writable. It remains **unaccepted and
undispatched**. The retained first live S2 response was recovered unchanged from
its durable outcome: 5,363 UTF-8 bytes, SHA-256
`ba5167989b8105ded772a3193000c32d7bcb7abd590735e2b2264f75c68e434f`.
Its text is only in the private operator handoff and operator conversation;
it is not committed here.
