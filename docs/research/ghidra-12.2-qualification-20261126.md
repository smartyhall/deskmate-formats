# Ghidra 12.2 qualification (2026-11-26)

Ghidra 12.2 is installed beside 12.1.4 and is now the preferred release for
new research. It corrects the reversed `MOV Sreg, r/m` display introduced in
12.1.3, and — which the earlier reproduction could not test — the operand
indexing and assembler consequences of the same pattern change. Everything
else the campaign depends on is unchanged: p-code, decoder lengths, the 16-bit
MZ loader's block model, analysis counts and fingerprints, the decompiler,
persistent annotations, and both Java scripts.

Nothing was upgraded in place. The 12.1.4 installation and every 12.1.4
project are untouched; 12.2 uses its own project directories, and no 12.1.4
project was opened by 12.2.

Two categories are kept apart, as in the other Ghidra notes:

* **observed** — a property of the bytes or of a run: encodings, listed text,
  p-code, block boundaries, counts, digests, exit status;
* **Ghidra-derived** — function boundaries, `FUN_*` names and decompiled
  source: the tool's model of the bytes, not original structure.

## Release identity and layout

| Item | Value |
| --- | --- |
| Package | `ghidra_12.2_PUBLIC_20261016.zip`, 569,712,708 bytes |
| SHA-256 | `2c2cd776db3c1f6a097ba418922378ac3649cadd5e844a6f5f088ae628a7be67` (matches the published asset digest) |
| Build | 2026-Oct-16 1220 UTC, revision `8ca9077040cc43cd790babcfccf19475622a3e9a` |
| Install | `C:\tools\ghidra_12.2_PUBLIC`, extracted beside `C:\tools\ghidra_12.1.4_PUBLIC` |
| Java | `application.java.min=25`; Temurin `25.0.5.1+2-LTS` at `C:\tools\jdk-25.0.5.1+2` |
| Runtime | PyGhidra 3.2.0 (bundled), Python 3.13.17, `x86:LE:16:Real Mode` |

Temurin 25 was installed beside the lab's Temurin 21.0.13.9 and is selected
per invocation through `JAVA_HOME`; the machine-wide `JAVA_HOME` still points
at Java 21, so 12.1.4 remains runnable without changes.

The JDK archive (`jdk25.zip`, SHA-256
`849d380ab0a64d9098e7d3a2de28beb73841c3b255c8284f019ccd8748c5eb5b`) matched
the Adoptium release metadata before extraction. Both downloads and all
projects live in the private lab, not in Git.

The relevant upstream record: the change history for 12.2 lists
"_Processors_: Fixed regression in x86 mov segment instruction operand
ordering. (GP-7279, Issue #9635, #9637)", and PR #9637 was merged as
`dc1e375` for the 12.2 milestone. The independent correction at
[`eb4x@6c59662`](https://github.com/eb4x/ghidra/commit/6c596622770a6f0a5ec7fab45b61c40fc9228d36)
describes the same three-call-site rename and adds assembler regression
cases. This note is the verification that the shipped release does what those
records say; it is not a new defect report, and none was filed.

## Instruction display

Fourteen forms from the campaign specimen
([`segment_forms.py`](../../tests/fixtures/synthetic/segment_forms.py)) were
decoded in a fresh project by each build. Left of the arrow is 12.1.4, right
is 12.2.

| File offset | Bytes | 12.1.4 | 12.2 | Correct |
| ---: | --- | --- | --- | --- |
| 0 | `8E D8` | `MOV AX,DS` | `MOV DS,AX` | yes |
| 2 | `8E C0` | `MOV AX,ES` | `MOV ES,AX` | yes |
| 4 | `8E D0` | `MOV AX,SS` | `MOV SS,AX` | yes |
| 6 | `8E E0` | `MOV AX,FS` | `MOV FS,AX` | yes |
| 8 | `8E E8` | `MOV AX,GS` | `MOV GS,AX` | yes |
| 10 | `8C D8` | `MOV AX,DS` | `MOV AX,DS` | unchanged |
| 12 | `8C C0` | `MOV AX,ES` | `MOV AX,ES` | unchanged |
| 14 | `8C DB` | `MOV BX,DS` | `MOV BX,DS` | unchanged |
| 16 | `8E 1E 34 12` | `MOV DS,word ptr [0x1234]` | same | unchanged |
| 20 | `8C 1E 34 12` | `MOV word ptr [0x1234],DS` | same | unchanged |
| 24 | `66 8E D8` | `MOV EAX,DS` | `MOV DS,EAX` | yes |
| 27 | `66 8C D8` | `MOV EAX,DS` | `MOV EAX,DS` | unchanged |
| 30 | `8E C8` | `MOV AX,CS` | `MOV CS,AX` | yes (reserved encoding, still decodes) |
| 32 | `8C C8` | `MOV AX,CS` | `MOV AX,CS` | unchanged |

Long mode, from the 64-bit specimen with `x86:LE:64:default`:

| File offset | Bytes | 12.1.4 | 12.2 |
| ---: | --- | --- | --- |
| 0 | `48 8E D8` | `MOV RAX,DS` | `MOV DS,RAX` |
| 3 | `48 8C D8` | `MOV RAX,DS` | `MOV RAX,DS` |
| 6 | `8E D8` | `MOV EAX,DS` | `MOV DS,EAX` |
| 8 | `4D 8E C0` | `MOV R8,ES` | `MOV ES,R8` |
| 11 | `49 8C D8` | `MOV R8,DS` | `MOV R8,DS` |

This matches the trial-correction table in
[`ghidra-segment-register-display-20261126.md`](ghidra-segment-register-display-20261126.md)
exactly, now from the stock release rather than a patched copy. Instruction
lengths and offsets are unchanged in every case: the correction moved text,
not decoding.

## Operand indexing

`Instruction.getOpObjects` is what generated listings, the decompiler and
emulation-style tooling read. In 12.1.4 the `8E` register forms expose their
operands general-register first:

| Bytes | 12.1.4 operands | 12.2 operands |
| --- | --- | --- |
| `8E D8` | `['AX', 'DS']` | `['DS', 'AX']` |
| `66 8E D8` | `['EAX', 'DS']` | `['DS', 'EAX']` |
| `8E C8` | `['AX', 'CS']` | `['CS', 'AX']` |
| `8C D8` | `['AX', 'DS']` | `['AX', 'DS']` |
| `8E 1E 34 12` | `['DS', 'word ptr [0x1234]']` | unchanged |

The consequence is easy to miss. In 12.1.4, `8E D8` and `8C D8` produce the
*same* two operand objects in the *same* order, so any script that classified
an instruction by operand 0 could not tell "load DS" from "store DS" without
re-reading the opcode byte. In 12.2 the operand order agrees with the
architectural direction for every form.

## P-code

P-code is identical everywhere. Across the 8 compared forms, the 14 specimen
forms and the 5 long-mode forms, every output varnode, size and input list
matched between builds, including the segment-register write for each `8E`
form and the AX/EAX/RAX write for each `8C` form. The defect was never
semantic, which is why earlier campaign work that read p-code or original
bytes was unaffected.

## Assembler

The assembler is where the defect had the largest practical effect, and it is
the part the earlier reproduction could not measure. Assembling at the
program's first mapped address with `Assembler.assembleLine`:

| Statement | 12.1.4 | 12.2 |
| --- | --- | --- |
| `MOV DS,AX` | rejected (`AssemblySyntaxException`) | `8E D8` |
| `MOV ES,AX` | rejected | `8E C0` |
| `MOV AX,DS` | `8C D8` | `8C D8` |
| `MOV DI,ES` | `8C C7` | `8C C7` |
| `MOV ES,DI` | rejected | `8E C7` |
| `MOV DS,EAX` | rejected | `66 8E D8` |

Round-tripping each 12.1.4 listing back through the assembler makes the
defect tangible: in 12.1.4 the text `MOV AX,DS` assembled from `8E D8`
re-encodes as `8C D8`, i.e. the listing converted a segment load into the
opposite instruction. In 12.2 every one of the fourteen listed forms
round-trips to its own bytes.

Two API facts found while building the probe, both relevant to analysis
procedures:

* `Assemblers.getAssembler(Language)` returns an assembler with no program
  binding; assembling then fails with a null program context. Only the
  `Program`-taking overload binds it, in both builds.
* `Assembler.assemble(Address, String…)` changed shape between the builds:
  12.1.4 returns an `InstructionBlock` (`getBytes`, `getInstruction`), 12.2
  returns an `InstructionRecordIterator` and writes into the program, which
  needs an open transaction. `assembleLine(Address, String)` returns `byte[]`
  in both and is the portable read-only call. This is a caller-visible API
  change, not a decoding change.

## Loader mappings and analysis

Both images were imported with `--analyze` and reopened in a second process,
under their own project directory.

| Image | Build | Instructions | Functions | Blocks | Content SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| `DESK.EXE` (`0f2a4024…`) | 12.1.4 | 4,660 | 170 | 9 | `1ad71b7a57780048d2d35f3d61ceff4caa3f287c28620471291abddca75284aa` |
| `DESK.EXE` | 12.2 | 4,660 | 170 | 9 | `1ad71b7a…` (identical) |
| `CALENDAR.PDM` (`819df565…`) | 12.1.4 | 24,154 | 508 | 6 | `f880c8131c55ba55…` |
| `CALENDAR.PDM` | 12.2 | 24,154 | 508 | 6 | `f880c813…` (identical) |

The block sets match block for block — `CODE_0` 13,232, `CODE_1` 431,
`CODE_2` 2,545, `CODE_3` 270, `CODE_4` 1,282, `CODE_5` 775, `CODE_5u` 4,153,
`DATA` 69,280, `HEADER` 512 for `DESK.EXE`; `CODE_0` 58,576, `CODE_1` 144,
`CODE_2` 784, `CODE_3` 12,577, `DATA` 23,664, `HEADER` 512 for
`CALENDAR.PDM` — as do `image_base`, minimum and maximum addresses
(`1000:0000` … `HEADER::000001ff`). The `CODE_<n>u` / `DATA` split, the far-
return adjustment and the segment origins the campaign documented from source
are therefore still what the shipped loader produces.

The report surface is equally stable for `DESK.EXE`: 4,660 instructions, 170
functions, 1 thunk, 195 symbols, 9 data types, 9 blocks, the same
function-size histogram (56 / 70 / 38 / 6 over the 1–16, 17–64, 65–256 and
257–1,024 buckets), and the same two references into `1000:0000`
(`133b:0004`, `1355:0149`).

Decompilation of `FUN_1000_0009` produces byte-identical text in both builds
(`sha256 f1f7117f5b75251282181fae52c4044316a8590cbce00a562ac689bed5f2eb54`,
21 lines, 380 characters, `void __cdecl16far FUN_1000_0009(void);`). Since
the decompiler renders the same operands, this is the expected result, and it
is a check on the correction being display-only.

Analysis wall clock is reported for completeness, not as a benchmark: the
`CALENDAR.PDM` autoanalysis stage took 17.7 s under 12.2 against 45.6 s under
12.1.4 on the same host, with the import stage at 2.1 s against 3.5 s. That is
a single pair of runs with no controlled warm-up or repetition, so it is not a
measured speedup and should not be quoted as one.

## Existing scripts and annotations

`CalendarBinding25.java` (DESK payload) and `BoundedDecode.java` (Calendar
payload) ran unmodified as `analyzeHeadless` post-scripts under 12.2 and
reproduced the documented windows, now with the corrected text:

```text
FILE=37b5 BYTES=8e1e1000 MOV DS,word ptr [0x10]
FILE=37c1 BYTES=8cc0 MOV AX,ES
FILE=dea4 BYTES=8cd3 MOV BX,SS
FILE=dea6 BYTES=8ec3 MOV ES,BX
FILE=dead BYTES=ff1e622a CALLF [0x2a62]
```

The `DE9F–DEAF` thunk is the case that earlier notes described from bytes as
"`ES` from `DS`" while the 12.1.4 listing read `MOV BX,ES`; 12.2 prints
`MOV ES,BX`, which is the same claim from the listing.

Annotation handling is unchanged: a plate comment, a `Note` bookmark in
category `campaign-probe` and a label were written in one process, and a
second process reopened the stored program and found all three
(`persisted: true`).

## Did any earlier conclusion rely on the wrong display?

No. The campaign's rule since the reproduction has been to read segment-MOV
instructions from original bytes and to state their effect from p-code, and
the audit against that rule found four places where reversed text appears:

* [`database-call-review.md`](database-call-review.md) quotes the listing form
  and states the effect separately;
* [`ghidra-dos-binary-analysis.md`](ghidra-dos-binary-analysis.md) contrasts
  `8E D8` and `8C D8`, both of which print `MOV AX,DS` in 12.1.4, and explains
  why the pair is dangerous;
* [`ghidra-integration-20261126.md`](ghidra-integration-20261126.md) tabulates
  the observed reversal with Capstone as the independent decoder;
* [`ghidra-segment-register-display-20261126.md`](ghidra-segment-register-display-20261126.md)
  is the reproduction itself.

Every one of them labels the text as the tool's output rather than the
architecture, and none builds a conclusion on it. The two narrative claims
that read "sets `ES` from `DS`"
([`database-call-review.md`](database-call-review.md),
[`deskmate-corkboard-20261123.md`](deskmate-corkboard-20261123.md)) rest on
bytes and p-code, and the 12.2 re-decode of the same windows now prints the
same reading directly.

One methodological point survives: the defect was also an *operand-order*
defect, so a script that keyed on operand 0 could silently swap a load for a
store. No campaign script does that — the probes classify by opcode byte or
by p-code output — but the older listings should be re-read rather than
diffed textually if they are ever compared with 12.2 output.

## Procedure changes

* `deployment/windows10/Provision-Lab.ps1` installs Temurin 25 and Ghidra
  12.2, verifying the published SHA-256 before extraction.
* `Configure-LabGhidraFirewall.ps1` defaults to the 12.2 directory and picks
  the newest Adoptium JDK so a lab image holding both 21 and 25 still selects
  the runtime 12.2 needs.
* `Verify-Lab.ps1` and `Audit-LabDisk.py` check for the 12.2 headless tool.
* `ops/tasks/ghidra-dos-import.json` and `ops/tasks/ghidra-program-report.json`
  pin 12.2, revision `8ca90770…`, `java_major` 25.
* [`ghidra-static-qualification-20261126.md`](ghidra-static-qualification-20261126.md)
  and [`ghidra-dos-import-receipts.md`](ghidra-dos-import-receipts.md) keep
  their 12.1.4 measurements as history; new receipts state the build they came
  from.

New work should use 12.2. 12.1.4 stays installed for reproducing the earlier
receipts and for the historical record in
[`ghidra-segment-register-display-20261126.md`](ghidra-segment-register-display-20261126.md).

## Toolchain selection

A follow-up review asked that provisioning verify the selected JDK major and
the actual Ghidra version instead of inferring an installation from an
executable, and that the loose `jdk-2*` fallback not select a mismatched
runtime. Three mechanisms now do that:

* `tools/ghidra/ghidra_toolchain.py` — provider-neutral discovery and selection.
* `deployment/windows10/GhidraToolchain.ps1` — the same rules for the lab
  scripts (`Verify-Lab.ps1`, `Configure-LabGhidraFirewall.ps1`,
  `Provision-Lab.ps1`).
* `ops/toolchains/*.json` — portable profiles that pin a release without
  naming an absolute path.

Selection reads `Ghidra/application.properties` for the release identity and
`<java-home>/release` for `JAVA_VERSION`; a directory name is never evidence.
Precedence, highest first: explicit argument, profile, environment
(`GHIDRA_INSTALL_DIR`, `GHIDRA_JAVA_HOME`, `JAVA_HOME`), Ghidra's
`launch.properties` override, discovery. Declared candidates keep their order;
discovered ones rank by the version they prove, so `12.2` outranks `12.1.4`
instead of whichever name sorts first.

The Java strategy decides among compatible discovered runtimes. `minimum` — the
default — takes the oldest major that satisfies the release's own
`application.java.min`, which keeps a historical release in its own era;
`newest` opts into the newest compatible one.

Measured on the lab host on 2026-11-27:

| Profile | Release selected | Java selected | Rejected |
| --- | --- | --- | --- |
| `ghidra-12.2.json` | 12.2, build `2026-Oct-16 1220 UTC`, revision `8ca9077…`, java.min 25 | `C:\Tools\jdk-25.0.5.1+2`, major 25 | `…\jdk-21.0.13.9-hotspot`: "major 21 is below the 25 required" |
| `ghidra-12.1.4-historical.json` | 12.1.4, build `2026-Sep-21 1613 UTC` | `…\jdk-21.0.13.9-hotspot`, major 21 | none |

The same rules were exercised through PowerShell: `Verify-Lab.ps1` now reports
both installations with their recorded versions and builds, the selected JDK
with its major, and `compatible`, instead of a boolean for the presence of a
launcher. `Configure-LabGhidraFirewall.ps1` refuses to guess a runtime and
names every rejected candidate with its reason.

**Remaining discrepancy, recorded rather than papered over.** The machine-level
`GHIDRA_INSTALL_DIR` on this host is still `C:\Tools\ghidra_12.1.4_PUBLIC`, so a
default selection (no profile, no requirement) resolves to 12.1.4 — correctly,
because the environment layer outranks discovery and 12.1.4 is compatible with
the Java 21 that `JAVA_HOME` names. New work therefore selects through a
profile or `--require-ghidra-version 12.2`. The variable was deliberately left
alone: it is shared machine configuration, and changing it belongs to
provisioning rather than to this campaign.

## Read-only procedures added for the campaign

`--symbols`, `--disassemble` and `--pcode` were added to
`ghidra_program_report.py` and exercised against `/DESK.EXE` on 12.2. Measured
output, the correction to the first p-code rendering, and the full contract
table with per-procedure status are in
[the procedure contracts note](ghidra-procedure-contracts.md).

## Limitations

* Two images were re-imported under 12.2 (`DESK.EXE`, `CALENDAR.PDM`).
  `FIL2DBF.EXE` and `DBREPAIR.PDM` were not re-imported in this pass; their
  12.1.4 receipts stand unchanged, and nothing here claims their 12.2 counts.
* The assembler comparison covers the six statements listed above and the
  fourteen round-trips; it is not exhaustive over x86 syntax.
* Timing figures come from single runs on a shared workstation.
* Ghidra-derived material — function boundaries, `FUN_*` names, decompiled
  text — stays in the private lab; only digests and counts appear here.

## Receipts

Private, under the campaign evidence root
`C:\DeskMateLab\private-evidence\ghidra-integration-20261126`:

| Evidence | Path |
| --- | --- |
| Display, operands, p-code, assembler, 16-bit | `exports/segcmp-12.1.4.json`, `exports/segcmp-12.2.json` |
| Display, 14 forms | `exports/segforms-12.1.4.json`, `exports/segforms-12.2.json` |
| Display, long mode | `exports/segforms64-shared.json`, `exports/segforms64-12.2.json` |
| Imports under 12.2 | `receipts-122/desk.json`, `receipts-122/cal.json` |
| Report, functions, xrefs | `exports/report-desk-122.json` |
| Decompiled text comparison | `exports/dec-1214-fn9.txt`, `exports/dec-122-fn9.txt` |
| Annotation persistence | `exports/annot-122.json`, `exports/annot-verify-122.json` |
| Java scripts | `logs/122-bounded.txt`, `logs/122-calendarbinding.txt` |
| Symbol, disassembly and p-code procedures | `exports/proc-122.json`, `exports/proc-pcode-122.json` |
| Toolchain selection, preferred release | `exports/toolchain-12.2.json` |
| Toolchain selection, historical release | `exports/toolchain-12.1.4.json` |

The probe itself is [`ghidra_x86_segment_compare.py`](../../tools/ghidra/ghidra_x86_segment_compare.py).
