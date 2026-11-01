# Database research integration checkpoint

2026-11-01. Review preparation against public main4baf845.
No unreviewed pull request is merged by this work.

## Source inventory

Logical worktree labels identify the existing separate checkouts; host/VM paths
are retained only in private inventory records.

| Investigation / worktree label | Original branch and exact local revision | Original working changes |
|---|---|---|
| Calendar / primary checkout | experiment/e19-space-pressure,73840536a7039acd55e9260fd121c90cb8458191 | Clean; already integrated publicly |
| Address Book Phase II / Address Book checkout | research/addressbook-phase2,b4a83ee84ecef524809cdb4a07ab5e17e1dee8da; earlier0905c6d4f7d574a5e73ecae5e40be1f1834176a8 | Clean; two commits not in inspected main |
| Filer / Filer project checkout | research/filer-f00-f02,b4a83ee84ecef524809cdb4a07ab5e17e1dee8da | Original filer-f00-f02.md and sidecar remain untracked and untouched |
| Cross-application / cross-application project checkout | research/cross-application-db,64f28b6ece0c4c19c0cb690297f0ae864dfc0728 | Clean; incorporates an unchanged copy of the Filer report |
| OCR / OCR checkout | research/screen-observation-ocr,da484fff29b629bf3c443da1f9c8f26582490bb5 | Clean; already integrated publicly; no OCR executed here |

The original Filer report has no independent original commit. Its tracked,
reviewable copy is in64f28b6; the original uncommitted files were not staged,
discarded or rewritten. There is no need to publish a duplicate Filer patch.

The new worktree uses research/database-call-review and includes:

| New history entry | Purpose |
|---|---|
|555b647|Replay0905c6d against inspected public main |
|4a8e5bc|Replayb4a83ee against inspected public main |
|f7b6723|Replay64f28b6, retaining authored Filer/cross-format reports |
|0a1e1e6|MZ coordinate probes, five synthetic tests and five binding regressions |
|2dff165|Native-material privacy exclusions and four synthetic tests |
|Final documentation commit on this branch|Audited call map, evidence classifications, corrected status and this checkpoint |

These replays preserve the source branches and keep review history explicit.
Address Book is independently reviewable in
[PR20](https://github.com/smartyhall/deskmate-formats/pull/20).
The consolidated architecture PR targets main and includes the Phase II
dependency so its documents and tests are self-contained. Review PR20 first;
reconcile the replayed dependency before merging the architecture PR.
No force push, branch deletion, visibility change or automatic merge is needed.

## Validation and publication boundary

Local Windows Python3.13 results: **79 portable tests,107 private regressions
and the original72-test laboratory suite passed**. Ruff checked src, tests and
tools. REUSE and source privacy audits passed. Wheel/source packaging and
distribution audits are recorded with the final publication receipt.

Preservation: **11262 watched files retain size, hash and modification time**,
including prior cross-application evidence/project files. All125 inherited
F00 guards pass. The existing unreadable DeskMateCodex.lock~ exception remains
explicit; that lock was not removed or modified. No native evidence, executable,
media, database or screenshot was written by the investigation tools.

Software/tests retain GPL-3.0-or-later. Research reports and authored evidence
summaries retain GPL-3.0-or-later OR CC-BY-SA-4.0. Formal specification licenses
and standard license texts remain unchanged. No original binaries, substantial
proprietary disassembly, private fixtures, screenshots or host paths are included.

PR20's workflow41356316112 completed successfully on Windows/Ubuntu,
Python3.13/3.14, including licensing, packaging, installed CLI, portable tests,
static checks and content audit. This is verified hosted evidence for PR20,
not a claim about a different architecture head. The architecture head's
workflow is checked separately after publication. Exact branch/head/PR/CI
receipts remain private and are reported at handoff.

## Research status

The [call review](database-call-review.md) confirms named service interfaces
and explicitly limits claims about runtime binding, selector semantics,
record lookup, allocation and deletion. Its
[machine map](database-call-map.json) provides source identities and addresses.

The single next task is an offline trace of one record-lookup request across
the common interface to its index consumer, stopping at unresolved indirect
binding. Native Filer F00–F02 remain prepared but unperformed.
