# Project status — DeskMate formats

**Revised lab operating policy — 2026-11-11:**
[Experimental laboratory posture](docs/research/experimental-lab-operating-posture.md)
accepts ordinary risk inside the existing recoverable Windows 10 VM for one
separately authorized S0 protocol canary. No new VM, restricted principal,
or comprehensive OS filesystem/network/descendant confinement is required
*solely* to remove hypothetical VM-local risk. Historic DeskMate software is
a normal **local** lab input; public Git publication is a different boundary.
Retain snapshots, a brief actual host/share/credential exposure review,
durable receipts, no uncertain-op replay and a precise model-use grant.

**Experimental profile implemented — 2026-11-12:** the explicit
`experimental-lab` profile permits one exact-plan authorized S0 sentinel turn
with a separate lab-risk acknowledgment. Default live remains blocked and S2
remains synthetic-only. The [current runbook](docs/research/codex-supervisor-s0-live-canary.md)
and [validation report](docs/research/codex-supervisor-experimental-lab-validation.md)
distinguish accepted VM permissions from unverified OS confinement.
No real model invocation has occurred; implementation review and separate
operator authorization remain required. The earlier
`BLOCKED` research record below reflects the **former acceptance gate**;
issue #90's second-VM/restricted-user comparison is no longer the selected
first-canary prerequisite.

**S0 live-readiness completed — 2026-11-11 (America/New_York):**
[PR #89](https://github.com/smartyhall/deskmate-formats/pull/89)
(merged `06b29bd620f0ebe61576083fdc42f1781dccb81e`) completed the
credit-interrupted audit of the S0 operator driver with a real Windows 10
**offline** preflight and stricter synthetic checks. Pinned native Codex
0.166.0 and two 321-file schema inventories match recorded hashes; Codex
reported 387 passed portable tests, and all four final-head GitHub Windows/
Ubuntu CI jobs passed. No actual app-server/model session, guest operation
or auth provisioning was performed.

**Decision: BLOCKED — SPECIFIC REMEDIATION REQUIRED.** The S0 driver now
refuses live execution *before child launch*, irrespective of an operator
plan-digest attestation. Synthetic evidence confirms that environment/cwd
sanitization alone does not contain filesystem or loopback access. Real
OS-enforced file/network/descendant isolation, effective Codex tool/config
restrictions and secure auth provisioning remain unresolved. Do not treat
late event/history checks as containment. [Research report](docs/research/codex-supervisor-s0-readiness.md)
and [structured receipt](docs/evidence/supervisor-readiness-20261111.json).
Next scoped decision [issue #90](https://github.com/smartyhall/deskmate-formats/issues/90)
compares disposable Windows execution environments with low-privilege host
containment and synthetic denial tests; [issue #58](https://github.com/smartyhall/deskmate-formats/issues/58)
retains the real S0 authorization gate and [issue #86](https://github.com/smartyhall/deskmate-formats/issues/86)
retains the subsequent real S2 dispatch gate.

**Earlier merged milestone below — 2026-11-08:** preserved for its dated scope.

**Supervisor merged checkpoint — 2026-11-08 (America/New_York):**
[PR #87](https://github.com/smartyhall/deskmate-formats/pull/87)
(merged `825f9bde92aec087f20fa2a7dcbc82229d532a88`)
added an installable single-use S0 operator driver and **synthetic-only**
S1-accepted-task-to-S2 dispatch bridge. The task's exact Git/queue acceptance
and a separate dispatch grant are checked, with private operation receipts
and read-only Observatory results. The published synthetic demonstration
performed one supervised synthetic thread/turn; no original Codex model,
86Box guest, VM media, paid call, daemon or control listener was used.
Codex reported 375 passing portable tests, including 58 focused supervisor
tests; all four final-head GitHub Windows/Ubuntu CI jobs passed.
[Runbook](docs/research/codex-supervisor-operator-driver.md) and
[evidence receipt](docs/evidence/supervisor-offline-driver-20261108.json).
**Issue #86 remains open:** the first real S0 canary and live S2 task execution
still require separate explicit authorization and effective-isolation review.

**Current merged checkpoint — 2026-11-08 (America/New_York):**
[PR #83](https://github.com/smartyhall/deskmate-formats/pull/83) published
the exact operator-produced, synthetic-data FIRST SECOND appointment fixture
(merged `30e5db48de104c844e935049364174d13ce5050a`).
[PR #84](https://github.com/smartyhall/deskmate-formats/pull/84) implemented
bounded SDK-profile reading of named PERSONAL and SECOND calendars and two
explicitly experimental exact-source writers (merged
`43a6a5734408ef81c010a004c2e4a44ac34f4def`). The reader reports
61 PERSONAL and zero/one SECOND appointments in the two original native
specimens. Both generated whole files reproduce their corresponding original
native file SHA-256 **exactly**, with separately retained native/operator versus
tool-generated provenance. This is released offline-validated source code,
**not** broad writer support, an independently instrumented native save/reopen
or a proven general index balancer. All four GitHub CI jobs passed for #83/#84.
[Campaign and limitations](docs/research/calendar-multicalendar-reader-writer.md).

[PR #80](https://github.com/smartyhall/deskmate-formats/pull/80)
(merged `8b47ab08698ea601308707703e14fe98d342dd8c`) adds the
source-pinned Address Book LastName/FirstName insertion trace and conservative
two-contact byte predictions, **not** a new native two-contact file or writer.
Its four CI jobs passed; issue #70 remains open for actual native verification.

The operator granted standing authority on 2026-11-08 for ChatGPT to merge
ready, passing Codex PRs after independent review. This does not authorize
Codex workers to self-merge or to execute paid Codex turns or native guest actions.
S0 now has an installable operator driver; the S1-to-S0 bridge has a separately
gated synthetic-only demonstration. A real supervisor-owned Codex canary and
real S2 dispatch have not yet been proven or authorized by this work.
[Operator driver and next-canary gates](docs/research/codex-supervisor-operator-driver.md).
[Supervisor design and rollout](docs/research/codex-supervisor-design.md).

**Historical snapshot below — 2026-11-07:** preserved for its dated context,
including now-superseded statements about native Calendar display and current
implementation scope.

**Snapshot:** 2026-11-07 (America/New_York), after publication of the
30-day Calendar in [PR #78](https://github.com/smartyhall/deskmate-formats/pull/78),
merged as `0cba552411d96376cce5db3c6d4907cc8e9b4ace` on `main`.
The allocator implementation remains from merged PR #75, and the synthetic-fixture
publication policy from merged PR #77.

**30-day publication on `codex/publish-calendar-30-days` ([merged #78](https://github.com/smartyhall/deskmate-formats/pull/78)):**
the complete [8,192-byte Calendar](tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.cln)
has been regenerated and matched byte for byte against the preserved allocator
candidate, SHA-256 `d35b10c8e8f0b04e41cd6d16a27b9825531353b00ab503e94b7abd3a11499106`.
The [61-appointment listing](tests/fixtures/application-generated/calendar/sdk-30-days-allocator-tool-generated.expected.json),
[operator download/inspection guide](docs/research/calendar-30-day-native-acceptance.md)
and [publication receipt](docs/evidence/calendar-30-day-publication.json) prepare
native acceptance across all 30 dates and pages 4, 6 and 7. This is **tool-generated,
independently checked offline, not application-produced or native-accepted**.
No emulator/guest operation or native save occurred. Source E02 and the prior
14-day fixture are unchanged. The exact binary and expected listing are now
published on `main`; **native read/display and persistence acceptance remain open**.

This is a concise, public **capability and handoff snapshot**, not a reconstruction
of an older missing `PROJECT_STATUS.md`, a substitute for private experiment
receipts or a live work monitor. Update after verified merges. A result reported
from a draft PR or current experiment is not a released capability.

The immediate objective is **useful Calendar and Address Book files**, validated
independently in DeskMate. Tests in which our reader accepts our writer's output
do not by themselves establish native compatibility.

**Allocator continuation on `codex/dmdb-page-allocator`
([merged #75](https://github.com/smartyhall/deskmate-formats/pull/75)):** campaign base
`8c1e7aa6f6aac04c3167d141f981e10f1d3b860e`.
[Static DMDB investigation](docs/research/dmdb-page-allocator.md) decoded packed
12-bit page chains and reproduced both published E15/E19 header transitions;
original E15/E19 bytes remain unavailable. A separate E02-only, opt-in new-file
builder now produces an independently checked **61-appointment / 30-date /
eight-page candidate**. Existing six-page append profiles stay unchanged.
This is tool-generated and **native open/save acceptance is pending**. No emulator
or Address Book trial was run. The separate experimental builder is now merged,
while the established six-page writer and native-accepted scope are unchanged.
See the successor report/receipt for exact source, candidate and validation identities.

## Evidence vocabulary

- **Implemented:** checked-in source; only the documented test scopes are claimed.
- **Native observed:** tested through an original DeskMate application in a
  controlled emulator experiment.
- **Operator-reported native display:** human inspection in original DeskMate;
  retain the report's scope separately from hash-pinned controlled experiments.
- **Offline tested:** verified by byte comparisons, fixtures or synthetic tests
  without new application interaction.
- **Proposed / unresolved:** an engineering target or hypothesis, not an observed
  storage rule or completed operation.

Dated experiment reports retain what was known *at their respective checkpoints*.
Use [compatibility](docs/compatibility.md) for current supported profiles and
the [README](README.md) for commands.

## Current capabilities

| Area | Implemented or observed | Remaining limits |
| --- | --- | --- |
| Calendar `PERSONAL.CLN` | [Reader and writer](docs/compatibility.md) retain the measured default and SDK profiles; the operator reports **29 appointments / 14 dates** displayed correctly with alarm states in DeskMate. A **separate opt-in E02-only experimental builder** generates an offline-checked **61-appointment / 30-date** candidate ([allocator report](docs/research/dmdb-page-allocator.md)). | Six-page append profiles are unchanged. The 30-day candidate has **not** been opened or saved in DeskMate; native page traversal, persistence and alarm firing remain unverified. Experimental growth is limited to eight pages and rejects unsupported operations. |
| Calendar page behavior | Static 3.05 reader/writer routines identify **packed 12-bit page chains** and reproduce E15/E19 header deltas; a bounded new-file builder now links pages 4→6→7. E16–E18 remain evidence of retained deletions and append behavior. [Source report](docs/research/dmdb-page-allocator.md). | The original E15/E19 files were unavailable in this run; there is no native test of the new 8-page file, no general allocator, and no deletion/reclamation or index-growth writer. |
| Address Book `PERSONAL.ADR` | [Reader](docs/research/addressbook-codec.md) preserves the ten-page/four-table layout, 16 raw contact fields and opaque tables. Empty-to-one writer reproduces **all four** A01–A04 application-produced whole-file SHA-256 hashes using a pinned source template. | 25 fictional contacts were generated in **25 separate one-contact files**, not one populated book. A second insertion, sort/collation rules, additional pages and broad optional field semantics are unverified. |
| Shared DMDB database structures | [Common structural reader](src/deskmate_formats/database.py) and [cross-application evidence](docs/research/cross-application-db.md) cover page framing, schemas, records and indexes. [Call study](docs/research/database-call-review.md) finds code-backed DMDB binding/call thunks in Calendar, Address Book and Filer. | No universal allocation writer or proven runtime DMDB export binding. Shared call interfaces do not establish identical application policies. |
| Interchange | [Version-1 semantic Python/JSON contract](docs/interoperability.md), explicit loss reports, source-snapshot IDs and example files are implemented. | No general native edit/delete, lossless reconstruction, stable external UID mapping or CalDAV/CardDAV network synchronization. |
| Filer | Static schema and sample analysis plus a distinct native CARMAINT open/menu/exit observation; disk contents stayed byte-identical and Print record/report were disabled. [Issue #54](https://github.com/smartyhall/deskmate-formats/issues/54). | No Filer codec. Earlier staged F00–F02 schema/record creation work remains unperformed. |
| 86Box and Observatory | Native authenticated loopback client, held DOS guest evidence, and [Observatory M0/M1](docs/research/observatory-v2-m0-m1.md) read-only publication with [M2](docs/research/observatory-v2-m2.md) opt-in Codex telemetry. Scoped held-canary verification recorded 0 ms guest advance. | No proven unattended service/old-browser acceptance; launcher startup timeout still warrants safe reconciliation [#35](https://github.com/smartyhall/deskmate-formats/issues/35). |
| Supervisor | [S0](docs/research/codex-supervisor-s0.md) owned protocol/receipts and [installable driver](docs/research/codex-supervisor-operator-driver.md); [S1](docs/research/codex-supervisor-s1.md) trusted Git intake; separate synthetic-only S2 grant/dispatch with read-only Observatory outcome. | No validated live S0 canary or real S2 dispatch. A queued task is not execution authority. The next live canary remains separately authorized and unexecuted. |
| Windows lab | Existing Windows 10 Pro research VM and [source-only provisioning work](deployment/windows10/INTEGRATION-STATUS.md). | Fresh full ISO/OOBE and recovery validation incomplete; system modifications need explicit review [#32](https://github.com/smartyhall/deskmate-formats/issues/32). |

Text, Worksheet and Draw remain outside implemented application codecs. See
[format inventory](docs/inventory.md).

## Database campaign checkpoints

The [database implementation report](docs/research/database-campaign.md)
contains details, limitations, private-evidence boundaries and reproducibility
instructions. Milestones were checkpointed on a dedicated Codex branch:

| Milestone | Result | Original checkpoint |
| --- | --- | --- |
| M0 | Windows/Python preflight; offline work avoided the uncertain 86Box startup path. | [Campaign report](docs/research/database-campaign.md) |
| M1 | Bounded common directory/column/index/record reader. | `0158cf8e9086d0292ae43c5aab30470163418a71` |
| M2 | SDK Calendar codec; 29 events over 14 days; page-reader extensions. | `5067da55c5ec3ac97f4d855cddec297e0e022376` |
| M3 | Address Book reader and one-contact writer; four independent native hash matches. | `ca06dd9a5ec5c648940c0981760c6e4bfd5e4fb3` |
| M4–M5 | Independent fixed-profile output checker, strict JSON interchange and loss accounting. | `4f761f9a43163dd90e89f03d910925772a43ecdf` |

The 30-day attempt stopped safely after **39 additions / 40 total events**
with **12 free record bytes**. Its incomplete prefix was archived privately; a
full-month deliverable is not claimed. The 14-day result is 6,144 bytes with
SHA-256 `85ad05d6bf58540e32349bbb559301d36aced164741b03b09b30d63f22d636ac`.
See the [public hashes and provenance](docs/evidence/database-campaign.json).

Phase II from `codex/database-phase-ii`, [merged PR #73](https://github.com/smartyhall/deskmate-formats/pull/73):
[source findings, independent diagnostic and operator runbooks](docs/research/database-phase-ii.md)
are prepared for #70/#71. SDK source documents LastName/FirstName ordering;
native second-contact insertion remains unmeasured. The diagnostic checks E15/E19
published hash/delta predictions without treating synthetic controls as originals.
No multicontact writer or page allocator was enabled; no new Calendar generated.
Current validation: **321 portable tests passed (135.970 s)** and **2 focused
private oracle tests passed (0.059 s)**. Seven diagnostic tests were rerun after
making their synthetic header vectors independent of the diagnostic's constants;
all passed (0.100 s). Ruff, REUSE, repository audit and wheel/sdist build passed.
See the [Phase II receipt](docs/evidence/database-phase-ii.json). This run requested
**0 ms** of emulated execution; actual guest-clock delta was **not measured**.

Reported campaign validation: **313 portable tests passed**, **two private
pinned-baseline hash-oracle tests passed**, plus independent output checks, Ruff,
REUSE, repository audit and isolated wheel smoke tests. The original E15–E19
private specimen archives were not available for that run. No new native
database acceptance test occurred during that earlier campaign; no real
guest-clock delta was measured. The later operator-reported native display
milestone is recorded separately below; it does not establish save persistence.

## Next practical gates

1. **Calendar display milestone achieved; controlled persistence remains open:**
   the operator reviewed all 29 appointments and displayed alarm states in native
   DeskMate. [Issue #69](https://github.com/smartyhall/deskmate-formats/issues/69)
   remains open for hash-pinned installed-file identity, manifests and a separately
   authorized controlled save. No-op OK does not establish an actual rewrite.
2. **Second Address Book contact:** a controlled, freshly cloned A01 scenario
   must establish index ordering/counters/physical append before a multi-contact
   writer is generalized. [Discriminating trial](docs/research/addressbook-codec.md).
3. **Calendar native multipage acceptance:** verify the hash-pinned 61-appointment,
   30-date candidate on a separately authorized disposable DeskMate installation,
   including records on pages 4, 6 and 7. Distinguish display/read traversal from
   an independently approved one-edit/save persistence test. [Download and checklist](docs/research/calendar-30-day-native-acceptance.md).
   A tool-generated full month exists; **native compatibility is not yet established**.
4. **Future sync semantics:** preserve high-precision original CalDAV times when
   the native projected representation is unchanged; interpret confirmed changes
   at the supported quarter-hour granularity, with conflict and tied-start
   handling. This is a **design requirement, not implemented sync**. See
   [operator UI evidence](docs/research/calendar-ui-time-normalization.md)
   and [interop policy](docs/interoperability.md).
5. **Infrastructure only when blocking:** unresolved DMDB binding [#25](https://github.com/smartyhall/deskmate-formats/issues/25),
   launcher safety [#35](https://github.com/smartyhall/deskmate-formats/issues/35),
   Filer enablement [#54](https://github.com/smartyhall/deskmate-formats/issues/54)
   and real supervisor canary [#58](https://github.com/smartyhall/deskmate-formats/issues/58)
   remain separate tracks.

Earlier [readiness research](docs/research/next-codex-campaign-readiness.md)
is a dated pre-campaign audit; [S0 live-canary documentation](docs/research/codex-supervisor-s0-live-canary.md)
is a runbook, not evidence of a paid live test.

## Research and publication safeguards

Follow [AGENTS.md](AGENTS.md) and [LICENSING.md](LICENSING.md). Original
commercial media, ROMs, installed trees, raw memory/screenshots, real user data
and credentials remain outside public Git; controlled synthetic records may
be retained with byte-exact provenance and licensing. Never replay an uncertain
guest-changing operation or mutating Codex request. Identify the owned process,
instance, operation, source/fixture hash and evidence scope; record unknowns
explicitly. The browser is read-only and cannot authorize native operations.

**Maintenance:** Update this dated status only after verifying new source and
experimental receipts. Preserve historical reports as written; amend a current
index or add a dated successor note instead of changing what an earlier
experiment claimed to know.
