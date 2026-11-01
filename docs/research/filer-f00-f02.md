# Filer reconnaissance: F00 prepared, native experiments blocked

2026-11-01. This is a static inventory and an explicit experimental stop point.
Filer was not launched. F00's no-edit control, F01's schema creation and F02's
single insertion remain unperformed. No Filer parser or writer was implemented.

## Provenance and reliability boundary

The lab's PROJECT_STATUS.md, AGENTS.md, Calendar specification, experiment
methodology, baseline manifests and Address Book A00-A04 reports were inspected.
The existing E19, Address Book Phase II and OCR worktrees were clean at inspection
(7384053, b4a83ee, da484ff respectively). A separate research/filer-f00-f02 worktree
was created from b4a83ee to retain the latest locally available Address Book findings.
No branch was merged, published or pushed; existing worktrees were not changed.

The parent is the complete known-good A00_recon/before/files installation, itself
retained from the clean Calendar keyboard-research baseline. All 126 files were
verified against its existing manifest before copying. This is a known-good
research installation, **not a freshly installed empty Calendar baseline**:
PERSONAL.CLN is e48066b2b78fb73ec414271ae4404468529628c840dfac3f7c374621544bc243.
PERSONAL.ADR is the empty A00 book. Original media and the pristine installation
were never mounted or overwritten.

Private evidence is retained at DOSLAB/EXPERIMENTS/FILER/F00_baseline:

* before/files and run/files: independent complete 126-file copies with manifest.json;
* source_verification.json, directory_inventory.json and copy_comparison.json;
* static_candidates.json: complete printable ASCII runs with offsets and raw headers;
* static_shared_spans.json: unclassified schema/index-region byte spans;
* prepare.py, ACTIONS.md, stage_status.json, preservation_guard.json and verification logs.

Copies preserve file modification times; inventories retain working metadata.
The copying comparison reports zero created/modified/deleted files relative to
the parent. **It is not an application no-edit control.** No after snapshot was
fabricated and no incidental launch/exit changes have been measured.

Computer Use initialized but list_apps timed out twice. Its documented recovery
reset, reinitialization and final list_apps retry also timed out. The registered
DOSBox session inventory returned attached=[] and windows=[] before preparation.
No guest input was sent. A separate keyboard MCP exists, but observation and
save verification were not established in this investigation. Input-only progress
would not meet this experiment's controls. This failure does not show that Filer
itself or the BIOS keyboard transport is incompatible. AUTOTYPE and OCR were not
used, changed or investigated.

## Installed candidates and static observations

The installed directory has no nested subdirectories: AUTOEXEC.BAT at the copied
root and 125 files under DESKMATE. Full sizes and SHA-256 hashes for every file,
including zero-length USERDICT.SPL, are in the manifests.

| Installed file | Bytes | Observed role / confidence |
|---|---:|---|
| FILER.PDM | 40081 | application-module candidate; name-based, UI association unverified here |
| FILER.HLP | 22528 | help-resource candidate; name-based |
| FILER.TUT | 22110 | tutorial-resource candidate; name-based |
| CARMAINT.FIL | 14336 | sample/template database candidate; internal structured text confirmed, native role unverified |
| INVNTORY.FIL | 12288 | sample/template database candidate; internal structured text confirmed, native role unverified |
| FORMSET.PDM / .HLP / .TUT | 60163 / 30720 / 10156 | related form-design candidates; relationship untested |
| DMDB.R89, DMDBBLD.RES, DMDBRD.RES, DMDBUPD.RES | 1109 / 11858 / 21955 / 13740 | database-component candidates by name only; no runtime tracing |
| DB01.PCL through DB09.PCL | individual sizes in inventory | auxiliary candidates, function unknown |

Neither an external index nor a separate schema file has been attributed to Filer.
This inventory cannot rule out auxiliary files created during native use.

CARMAINT.FIL SHA-256:
ca5ea9d77dc7545e761457ddc9d40c0b5aca427d7f787a19038d61495f4c67e7.
INVNTORY.FIL SHA-256:
62316203c555e42cddc47b118f4a34ef1c60362e684d2b90a978fb3675d9c6fe.
Both begin 03 46 49 4C and have sizes divisible by 1024 (14 and 12 units).
Size divisibility alone does not establish a page architecture.

In both candidates, DBCOLS begins at 0x0402, LAYOUTS at 0x0427, GRAPHICS at
0x044D and DATA at 0x0470. cname occurs at 0x0802, owner at 0x081D,
type at 0x0868 and uniq at 0x0881, matching those literals' locations in
the inspected Calendar and Address Book files. These are confirmed byte/text
correspondences. The adjacent five-digit ASCII strings have not been established
as Filer counts, identifiers or allocation values by a controlled mutation.
The captured 0x0800-0x0897 and 0x0C28-0x0C4B spans are not jointly byte-identical
to Calendar in either candidate; no general schema or index identity is claimed.
Printable ASCII literals establish those bytes' encoding only, not a general
text codec, numeric endianness or delimiter-escaping rule.

## Comparison matrix

Confidence describes the stated observation, not a universal implementation rule.
C refers to the [Calendar specification](../formats/calendar/CALENDAR_FORMAT.md);
A1 and A2 to [Address Book Phase I](addressbook-phase1.md) and
[Phase II](addressbook-phase2.md); F refers to the private static evidence above.

| Characteristic | Filer candidates | Calendar | Address Book | Confidence / evidence |
|---|---|---|---|---|
| First four bytes | 03 46 49 4C in both .FIL files | 03 46 49 4C | 03 00 00 00 | high, raw bytes F/C/A1 |
| File sizes / grouping | 14336, 12288; multiples of 1024 | initial six pages; native growth measured | 10240 in A00-A04 | sizes high F/C/A2; Filer page semantics untested |
| DBCOLS at 0x0402 | present in both | present | present | high literal correspondence F/C/A1 |
| Metadata labels | LAYOUTS, GRAPHICS, DATA | PERSONAL | DATA, NAMES, CONFIG | high literal observations F/C/A1; roles tentative for Filer |
| Schema-like literals at matching offsets | cname, owner, type, uniq | measured six-field DBCOLS rows | corresponding metadata present | high literal correspondence; shared machinery unproven F/C/A1 |
| Native user record | not created | 01-separated variable fields; 01 02 ending | sixteen fields; native length controls | Filer unknown; measured C/A2 |
| Index / record IDs | not decoded or mutation-tested | six-byte LE triples resolve measured rows | (4,0,0x10) for one contact | Filer unknown; measured C/A1/A2 |
| Count / next ID | adjacent ASCII numbers, roles untested | measured transitions, bounded semantics | insertion candidates 00000→00001 / 00016→00017 | Filer unknown F; C/A2 observations high |
| Auxiliary storage / no-edit effects | native control not performed | control unchanged all126 contents | all126 unchanged; ADR mtime changed | Filer unknown; C/A1 controls high |

The evidence supports shared **structural conventions** in the shipped candidates.
It does not distinguish hypothesis 1 (same storage machinery) from hypothesis 2
(shared conventions with distinct representation). A completely unrelated layout
is less consistent with the repeated, positioned metadata literals, but hypothesis
3 is not excluded for a newly created native Filer database. Code sharing, schema
semantics, record boundaries, counts, allocation, byte order and IDs remain untested.

## Resume procedure and next experiment

The single next experiment is **complete F00's native no-edit launch/exit control**.
Restore reliable screenshot observation first; minimum manual intervention is to
open the isolated run copy in the established DOSBox build, inspect Filer's initial
screen and available operations, then exit cleanly without data edits. Record all
actions and screenshots. Confirm the mounted path is F00_baseline/run/files, with
no writable original or prior experiment mount. A launch command is deliberately
not asserted here because the Filer entry point was not verified in its native UI.
Capture a complete after tree and working timestamps only after visible clean exit;
compare every path, size, hash and changed byte against before.

Only after that control, retain a verified parent copy for F01. Proposed identifiers
are database FREC01 and one text field FTXT_A, length 24 if the native UI permits
it. Record the actual native type label, length, required defaults and actions;
do not claim these proposed values were accepted. Save an empty schema with zero
records, exit and snapshot. F02 must start from the exact successful F01 result,
insert only F02_VALUE_7Q9 once, visually verify it before and after saving, exit,
and compare the complete tree plus all byte deltas. If the native UI requires
additional fields, document the actual minimal schema before the single save.
No binary edits may substitute for either stage.

## Regression and preservation verification

Python 3.13: all 65 portable tests, all 97 private fixture tests and the separate
original 72-test laboratory suite passed. REUSE checked 74/74 files successfully;
the repository content audit passed. No production code, existing tests, license
policy or license texts changed. Source/before/run full-file verification and
preservation guards are recorded privately in final_verification.json. These
checks protect prior work; they do not validate any unperformed Filer operation.
