# Cross-application investigation verification

2026-11-01. Local offline checks on isolated research/cross-application-db.
Hosted CI, native Filer acceptance and runtime engine identity are not claimed.

| Check | Result |
|---|---|
| Portable synthetic suite, Python3.13 |70 passed, including5 new structural-helper tests |
| Private archival suite, Python3.13 |102 passed, including5 new cross-application observations |
| Original separate laboratory suite |72 passed, unchanged |
| Focused Ruff checks on new Python files |Passed |
| REUSE licensing and source privacy audit |83/83 files compliant; audit passed |
| Wheel/source build and distribution privacy audit |Passed locally; no artifacts published |
| Production Calendar codec/acceptance, dependencies, CI |Unchanged |
| Preservation watch |11215 files retained content, size and modification time |
| Inherited F00 preservation guards |125 passed |
| Full installations |F00 before/run and AddressBook A00 parent:126 files each, exact manifest match |
| Proprietary material boundary |Raw files, strings, executable probes and Ghidra project remain outside Git |

REUSE, source/distribution audit and final build receipts are retained privately
in lint_results.json and build_results.json. Final lint runs occur after all
authored documents and sidecars are present. Standard license-text hashes and
Markdown links are checked by final_review.py. No installed environment in another
worktree was modified; existing verification tools were reused.

## Preservation limits and failures recorded

The initial broad watch could not read the pre-existing locked
ANALYSIS/GHIDRA/DeskMateCodex.lock~ and aborted before saving a completed baseline.
The corrected watch records that exception and covers11215 other files.
The lock was neither removed nor opened for writing. No claim is made that its
content was verified. Immutable originals, preserved databases and baseline
manifests are covered; no native file was modified.

The default Python lacked REUSE, so the established verification environment was
used without installing dependencies or changing it. A first descriptor-table
probe was two bytes late and failed; the corrected50E0 start resolves all six
names and matches all widths/types. Both are documented as investigation limits,
rather than assigning semantics from an unsuccessful probe.

Scientific negative results are preserved: Address Book has a different magic;
INVNTORY omits a schema value despite the self-schema descriptor; its next-ID-like
token violates a universal max-ID+1 rule; common executable-byte matches also
appear in TEXT.PDM; filenames do not establish PCL database functionality.
See the main report for exact evidence and competing explanations.

## Static code analysis boundary

A new private Ghidra project imported and analyzed DMDBRD successfully as DOS MZ,
x86 LE16 real mode. A first reference query using returned segmented aliases
found no references to the tested metadata names. A second physical-equivalence
enumeration also found no such references; its descriptor-range probe started
two bytes late. The final corrected-range probe also found no references to the
tested names or descriptor region; its successful receipt is retained in
ghidra_refs_corrected.log. Absence of recovered references is not proof of absent
code use: DS-relative addressing, indirect calls and loader fixups remain unresolved.
No substantial disassembly or executable material is published.

## Handoff

The authored report, machine summaries, component findings, read-only helper,
tests and operator runbook are committed only on this isolated research branch.
Other worktrees and the untracked original Filer report remain intact.
Private research/verification scripts and raw logs are retained in
DOSLAB EXPERIMENTS/RESEARCH/cross_application_db with a final evidence index.
PROJECT_STATUS.md receives an appended checkpoint; historical entries are retained.

No Filer F00 after snapshot was fabricated. F01/F02 remain prepared native work.
The next operator session can follow the runbook using fresh disposable copies.
