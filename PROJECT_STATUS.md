# Project status — DeskMate formats

**Snapshot:** 2026-11-07 (America/New_York), Phase II evidence reconciliation
from verified `origin/main` `6c742800f88a63551cb5cd5ba9dc9991bc9a7ead`
([PR #72](https://github.com/smartyhall/deskmate-formats/pull/72)).

This is a concise, public **capability and handoff snapshot**, not a reconstruction
of an older missing `PROJECT_STATUS.md`, a substitute for private experiment
receipts or a live work monitor. Update after verified merges. A result reported
from a draft PR or current experiment is not a released capability.

The immediate objective is **useful Calendar and Address Book files**, validated
independently in DeskMate. Tests in which our reader accepts our writer's output
do not by themselves establish native compatibility.

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
| Calendar `PERSONAL.CLN` | [Reader and writer](docs/compatibility.md) support the measured default profile and an opt-in SDK-derived date/time profile. The operator reports all **29 appointments / 14 dates**, including displayed alarm states, appear as expected in DeskMate 3.05. The committed six-page tool-generated file also has independent offline checks. [Report and limits](docs/research/calendar-14-days-operator-report.md). | Guest-loaded bytes were not independently rehashed; no native edit/rewrite specimen or alarm-firing result was supplied. Writer remains six-page, append-only and rejects tied starts, sentinel times and unsupported opaque values. A complete full-month file is blocked by allocation. |
| Calendar page behavior | E15 allocated page 6; E16 retained an unindexed deleted row; E17/E18 appended rather than reused its slot; E19 allocated page 7 under pressure. [Reports](docs/experiments/e15-page-boundary.md), [E19](docs/experiments/e19-space-pressure.md). | Extended reader handles bounded indexed pages, but these observations do **not** yet specify a safe multipage allocator or deletion/reclamation writer. |
| Address Book `PERSONAL.ADR` | [Reader](docs/research/addressbook-codec.md) preserves the ten-page/four-table layout, 16 raw contact fields and opaque tables. Empty-to-one writer reproduces **all four** A01–A04 application-produced whole-file SHA-256 hashes using a pinned source template. | 25 fictional contacts were generated in **25 separate one-contact files**, not one populated book. A second insertion, sort/collation rules, additional pages and broad optional field semantics are unverified. |
| Shared DMDB database structures | [Common structural reader](src/deskmate_formats/database.py) and [cross-application evidence](docs/research/cross-application-db.md) cover page framing, schemas, records and indexes. [Call study](docs/research/database-call-review.md) finds code-backed DMDB binding/call thunks in Calendar, Address Book and Filer. | No universal allocation writer or proven runtime DMDB export binding. Shared call interfaces do not establish identical application policies. |
| Interchange | [Version-1 semantic Python/JSON contract](docs/interoperability.md), explicit loss reports, source-snapshot IDs and example files are implemented. | No general native edit/delete, lossless reconstruction, stable external UID mapping or CalDAV/CardDAV network synchronization. |
| Filer | Static schema and sample analysis plus a distinct native CARMAINT open/menu/exit observation; disk contents stayed byte-identical and Print record/report were disabled. [Issue #54](https://github.com/smartyhall/deskmate-formats/issues/54). | No Filer codec. Earlier staged F00–F02 schema/record creation work remains unperformed. |
| 86Box and Observatory | Native authenticated loopback client, held DOS guest evidence, and [Observatory M0/M1](docs/research/observatory-v2-m0-m1.md) read-only publication with [M2](docs/research/observatory-v2-m2.md) opt-in Codex telemetry. Scoped held-canary verification recorded 0 ms guest advance. | No proven unattended service/old-browser acceptance; launcher startup timeout still warrants safe reconciliation [#35](https://github.com/smartyhall/deskmate-formats/issues/35). |
| Supervisor | [S0](docs/research/codex-supervisor-s0.md) offline-tested owned app-server protocol and durable receipts; [S1](docs/research/codex-supervisor-s1.md) trusted task Git intake, private operator decisions and sanitized read-only events. | No validated live S0 canary or S2 autonomous dispatch. A queued task is not execution authority. [Canary runbook](docs/research/codex-supervisor-s0-live-canary.md) was prepared, not executed. |
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
3. **Calendar page growth:** compare E15/E19 allocation-associated header bytes
   against original fixtures and new targeted controls before adding a writer
   allocator or claiming a complete 60–90-event month.
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
