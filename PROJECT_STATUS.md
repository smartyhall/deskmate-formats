# Project status — DeskMate formats

**Snapshot:** 2026-11-07, from `0d8c9e9cb538c65c382cd4f5478048e4397c6bb7` on `main`.
**Purpose:** A concise, public navigation and handoff record—not a substitute for
the original experiment reports, private lab records or a live status service.
Refresh this snapshot after significant merges, preserving dated experimental
conclusions in their original reports. An unmerged PR or an experiment currently
in progress is **not** a shipped capability.

The goal is to document native Tandy DeskMate formats and build independent
readers, writers and eventual interoperability tools. The practical near-term
goal is to generate substantial Calendar and Address Book data which the
original DeskMate applications can actually open and manipulate. Software
self-round-trips are not sufficient evidence of native compatibility.

## Evidence vocabulary

- **Implemented:** present in the repository; tested only to the extent stated.
- **Native observed:** verified in a controlled DeskMate/86Box experiment.
- **Synthetic/offline tested:** exercised without claiming native acceptance.
- **Prepared/proposed:** documented, not executed or validated as a working tool.
- **Unresolved:** an inference or operation not yet supported by decisive evidence.

A document recording what was *planned at its date* remains a historical
record. For current capability, use this file together with
[compatibility](docs/compatibility.md), the [README](README.md) and the
original evidence it links. Do not interpret an issue body or historical
experiment heading as a fresh verification result.

## Current capability matrix

| Area | Supported or directly observed | Limits / next gate |
| --- | --- | --- |
| Calendar `PERSONAL.CLN` | [Reader](src/deskmate_formats/calendar/personal.py) enumerates indexed rows and exposes raw fields plus narrowly decoded appointments. [Append writer](src/deskmate_formats/calendar/writer.py) emits new files with preserved existing rows for the six-page profile. Five generated user appointments were accepted unchanged by DeskMate in Phase III-A. | Four observed dates, six time values, printable ASCII, low IDs, distinct date/start keys, and one data/index page per table. No general page allocator, editing/deletion writer or recurrence conversion. [Exact limits](docs/compatibility.md). |
| Calendar storage research | E15 allocated page 6; E16 retained an unindexed deleted row; E17/E18 appended without reusing its retired slot; E19 allocated page 7 under pressure. [Reports](docs/experiments/e15-page-boundary.md) through [E19](docs/experiments/e19-space-pressure.md) preserve the separate experiments. | These are **native observations**, not multipage reader/writer support or a general allocation/reclamation algorithm. |
| Address Book `PERSONAL.ADR` | [Phase I](docs/research/addressbook-phase1.md) and [Phase II](docs/research/addressbook-phase2.md) establish a no-edit control, single-contact samples, sixteen observed fields, index/counter candidates and variable-length field changes. | No Address Book parser or writer on this baseline. Multiple-contact indexing, page growth, broad field semantics and encoding remain to be established. |
| Shared database structures | [Cross-application study](docs/research/cross-application-db.md) identifies recurring on-disk structures in Calendar, Address Book and shipped Filer samples. [Call review](docs/research/database-call-review.md) confirms code-backed DMDB service binding/call thunks in all three applications. | The actual runtime binding target, record operations, shared allocator and universal page policy are **not** established. A common storage abstraction should reflect measured overlap rather than assumed universal behavior. |
| Filer | Static sample, component and schema/index research exists. A later disposable native run opened the shipped `CARMAINT.FIL` sample, inspected the File menu, and exited with the disk byte-identical; Print record/report were disabled. [Issue #54](https://github.com/smartyhall/deskmate-formats/issues/54). | No Filer parser/writer, new schema or record creation. The earlier [F00–F02 runbook](docs/research/filer-native-runbook.md) is still an **unexecuted staged experiment**; the separate CARMAINT observation did not complete it. |
| 86Box lab and read-only observation | Authenticated native loopback client, held RSX/DOS baseline, synthetic MCP transport tests, native frames and approved RAM snapshots. The [live Observatory comparison](docs/research/86box-observatory-live-report.md) measured 0 ms guest-clock advancement in a scoped held interval. | Does not establish a general debugger, unattended Windows service, a universally passive host display or early-browser compatibility. Startup readiness ambiguity remains [#35](https://github.com/smartyhall/deskmate-formats/issues/35). |
| Observatory v2 | [M0/M1](docs/research/observatory-v2-m0-m1.md) private journal and read-only event feed, and [M2](docs/research/observatory-v2-m2.md) opt-in Codex CLI telemetry, are implemented with offline tests. | Source telemetry, process liveness and guest-clock evidence remain distinct. Read-only browser publication grants no control. Historical-browser acceptance remains open [#31](https://github.com/smartyhall/deskmate-formats/issues/31). |
| Supervisor | [S0](docs/research/codex-supervisor-s0.md) implements a pinned **offline-tested** app-server protocol client, identity-bound operation receipts and reconciliation. [S1](docs/research/codex-supervisor-s1.md) implements trusted Git task intake, private acceptance/rejection queue and sanitized event publication. | No validated real S0 model canary, production approval sender, S2 task dispatcher or autonomous worktree/lease orchestration. Accepting a task is not authorizing its execution. [Issue #58](https://github.com/smartyhall/deskmate-formats/issues/58). |
| Windows 10 deployment | Existing Windows 10 Pro 22H2 laboratory and [source-only provisioning recipe](deployment/windows10/INTEGRATION-STATUS.md); selected install/bootstrap and 86Box build paths were exercised. | Fresh end-to-end ISO/OOBE, reboot/recovery, dependency/cache and cross-hypervisor cases remain incomplete [#32](https://github.com/smartyhall/deskmate-formats/issues/32). |

Other applications—Text, Worksheet and Draw—have no established standalone
format implementations. Filer and shared-engine research must not be confused
with complete application compatibility. See [inventory](docs/inventory.md).

## Current work priority: usable databases

1. **Shared structure, conservatively:** extract verified `.FIL` framing, table,
   schema and index reading for Calendar and Address Book without assuming
   a universal DMDB allocator or deleting opaque fields.
2. **Calendar capacity and fidelity:** expand date/time codecs and parse/write
   multipage data from evidenced transitions. First target: a **14-day
   synthetic schedule with 25–40 events**; preferred target: a **30-day month
   with 60–90 events**. Validate in original DeskMate when separately authorized.
3. **Address Book:** implement a bounded reader and writer, initially 20–30
   contacts, aiming for 50–100, with varied field lengths and native validation.
4. **Interoperability after working files:** document a stable Python/JSON
   interface, loss accounting and stable external-ID semantics. Network
   CalDAV/CardDAV synchronization is deferred; DeskMate record IDs may change.
5. **Infrastructure on demand:** address launcher/protocol or observation defects
   when they block measured database work; do not complete supervisor phases
   simply for their own sake.

These are **targets**, not deliverables already accepted by DeskMate. Keep
portable fixture tests, original-byte comparisons and live application checks
as distinct forms of evidence. See the [interop boundary](docs/interoperability.md).

## Pending review and unresolved gates at this snapshot

- [PR #65](https://github.com/smartyhall/deskmate-formats/pull/65):
  draft *runbook* for the first live S0 canary. It is not an executed test
  or an integrated owner/driver.
- [PR #66](https://github.com/smartyhall/deskmate-formats/pull/66):
  draft readiness audit comparing research, reliability and supervisor work.
  Its findings are advisory, not evidence of a newly completed campaign.
- [#25](https://github.com/smartyhall/deskmate-formats/issues/25):
  Calendar DMDB runtime binding remains unresolved after bounded static work.
- [#35](https://github.com/smartyhall/deskmate-formats/issues/35):
  synthesize and test startup-timeout behavior without relaunching a live child.
- [#54](https://github.com/smartyhall/deskmate-formats/issues/54):
  identify Filer print-command enablement predicates; do not infer printer setup.
- [#58](https://github.com/smartyhall/deskmate-formats/issues/58):
  one explicitly authorized, isolated, real S0 canary remains outstanding.
- [#10](https://github.com/smartyhall/deskmate-formats/issues/10),
  [#31](https://github.com/smartyhall/deskmate-formats/issues/31) and
  [#32](https://github.com/smartyhall/deskmate-formats/issues/32)
  remain separate keyboard, observer-compatibility and deployment tracks.

A new Codex database campaign may be active on a **separate branch**;
this snapshot makes **no claim** about its unmerged code, generated datasets,
private experimental results or resource usage. Reconcile against the actual
pull requests and CI before revising the matrix.

## Operating, publication and preservation rules

Use [AGENTS.md](AGENTS.md) and [LICENSING.md](LICENSING.md) as the standing
constraints. Preserve original commercial software, ROMs, installed trees,
real data, private media, guest RAM/screenshots and credentials outside Git.
Application-generated documents with **controlled synthetic data** can be
included as byte-exact fixtures with SHA-256 and provenance. Record exact
input/build/experiment identities. Never silently repeat a guest-changing
action or mutating Codex request after an ambiguous acknowledgement.

For each milestone, record **source-tested**, **native-observed**, **proposed**,
**blocked** or **not run**, as appropriate; include the exact commit, approved
fixture hashes, test suite and known gaps. Commit and push only in separately
authorized worktrees/branches; keep unreviewed PRs unmerged. A snapshot
document does not authorize new emulator connections, guest mutations,
private-memory capture, real model use or supervisor dispatch.

## Updating this file

Refresh the snapshot/base SHA and only those rows whose supporting evidence
actually changed. Link to the authoritative experiment/PR rather than copying
long logs. If the current status depends on an unmerged campaign, mark its
results pending until reviewed, tested and merged. Historical reports should
retain their dated conclusions; add a short current-status pointer instead
of rewriting what researchers knew at the time.
