# Historical DeskMate utility qualification

On November 27, 2026, DBrepair normalized a healthy synthetic Filer file and
recovered the same file with one deliberately damaged DATA index locator. Both
inputs produced the same 8,192-byte output, and original Filer displayed
`F7Q9` after cold reopen. Fil2dbf 0.1 exported that original Filer control to
the same 89-byte dBASE III file in two different DeskMate runtimes. SND2WAV 1.2
preserved all 555 samples of a separate native Sound control and omitted the
expected RIFF alignment byte.

The work starts at [research-origin-001](https://github.com/smartyhall/deskmate-formats/tree/research-origin-001),
commit `a49e72b3b967e6ed0b6097cb040114072a4970e7`, following the
[convergence closeout](https://github.com/smartyhall/deskmate-formats/issues/213).
The [execution runbook](historical-utility-runbook.md) gives the guest
sequences and comparison steps. The
[structured evidence](../evidence/historical-utility-qualification-001.json)
holds exact identities, emulated clocks, byte spans, parser and DBF views,
and file-content inventories.

## DBrepair

The two archived copies of `DBREPAIR.PDM` from `dmrepair.exe` and
`f2d01.zip` are byte-identical. Both are 18,119 bytes with SHA-256
`e1922f36dd470c0f78f8e3872dce055aa3fd088e2ac4d8ccd852b9d2cb2389c4`.
Their differently named documentation members are byte-identical too.
`f2ddos.zip` contains a distinct `FIL2DBF.EXE` launcher for the
03.03.01 runtime. The integrated [static analysis](historical-utility-analysis-20261126.md)
documents shared service-call patterns and leaves the runtime service binding
open.

The input was the native [QRECORD one](../../tests/fixtures/application-generated/filer/qrecord-one.fil)
fixture. It contains one user column, `FTXT_A` (K, 22 bytes), and a single
synthetic record `F7Q9`. DATA starts at page 6, its index starts at page 7,
and the first index tuple is `(6, 0, 16)`. The utility received separate
copies in `C:\UTILTEST`.

| Trial | Before repair | After repair |
| --- | --- | --- |
| Healthy | Original control, SHA-256 `8d9ed82cf8526fb833f4df8689184905905d40cd8b8c3c5925cbf10336ff1476` | Reported 8,192 bytes recovered and zero unrecovered. Created `GOOD.OLD` byte-identical to the input and rewrote `GOOD.FIL`. The repair stop preserved an extraction before Filer reopen. |
| Single defect | [Defect copy](../../tests/fixtures/application-generated/filer/qrecord-index-defect-20261127.fil), SHA-256 `b557d25f3a1cac93b8297b12cc13dfbe24a3f7dddbb957b02714ffefd8f8213c` | Same reported count. Created `DEFECT.OLD` byte-identical to the damaged input. The output after Filer cold reopen matches the healthy repair. |

The pre-run defect plan changed the little-endian DATA in-page offset at
`0x1C2A` from zero to one. The single altered byte makes the locator point
into the live row while leaving the row and its stored value intact. The
independent reader rejected the input at `0x1800` with an unindexed-row,
overlap or gap error. The predictions allowed reconstruction from the
surviving row, rejection or loss on an index-led path, or recovery plus
normalization.

The [shared repair output](../../tests/fixtures/application-generated/filer/qrecord-dbrepair-20261127.fil)
has SHA-256 `eed8ddb2c44dd79d2b4997b7f97d629abead1ed2dc941bb0c3361204be115084`.
Each comparison has 819 changed byte positions spread over 1 KiB pages 1–7.
DBCOLS stays on pages 2/3 but its row ID associations change. DATA moves
from pages 6/7 to 4/5 and retains ID 16 and `F7Q9`. LAYOUTS moves from
4/5 to 6/7. The independent reader found the same column definitions and field
tuples, with multiplicities, in all three tables. Filer displayed the same
single record on both cold reopens. The stopped-disk collection for the
defect followed the read-only Filer reopen, so only the healthy trial has a
pre-reopen extraction. The healthy output remained byte-identical across its
reopen.

The healthy result is **structural normalization**. The defect result
demonstrates **recovery with normalization** for this single invalid
locator. The uniform success dialog did not identify the defect or establish
that the input was healthy. The test establishes preservation of the measured
fields and the Filer view. Record identity preservation outside DATA and
broader database compatibility would require additional controls.

## Fil2dbf

Before execution, the project reader established one ordered DATA field,
`FTXT_A` K/22, and one record, `F7Q9`. The predicted export used the
operator-entered field name `FTXT_A`, type C/22, decimals zero, a 65-byte
header, and one 23-byte record consisting of an active flag and the value
padded to 22 bytes. The predicted descriptor and file terminators were
`0D` and `1A`. Field naming and the character-width mapping are
converter choices. Form geometry, native row IDs, and other tables are
outside this selected-table export.

The separate native 03.05.00 and standalone 03.03.01 runs produced one
byte identity, SHA-256
`5a8e393c7756fdd2dbce07e5226e38fb9e4f6b22593e1e6902f224eccb682b67`.
[Inspect the checked DBF fixture](../../tests/fixtures/application-generated/fil2dbf/qrecord-data-20261127.dbf).
The independent inspector verified version `03`, length and count fields,
character descriptor, active record flag, exact padded value, and both
terminators. The date bytes were `1A 0B 04` in both runs. The raw descriptor
is retained in the evidence. Both inputs remained byte-identical, and neither
successful export created an OLD backup. The standalone runtime additionally
created its local `DMCSR.CFG`.

The separate native negative control supplied a 16-byte ASCII marker under a
FIL extension. The dialog reported that it could not open the requested
input database, and its status line described missing or invalid input. The
marker bytes remained intact. A **zero-byte** `BAD.DBF` was left behind, so
output-file existence alone is insufficient even when the UI rejects the input.

Fil2dbf is a third-party exporter. Its two runs exercised the same converter
PDM through different runtime resources, so their agreement is evidence for
this conversion path rather than confirmation from two independent database
engines. The measured profile covers one Filer DATA character column.
Numeric, deleted, multi-row, and other application profiles remain in the
backlog.

## SND2WAV

In the isolated MS-DOS 5.00 guest, SND2WAV 1.2 converted the pinned native
[odd 5,500 Hz Sound control](../../tests/fixtures/application-generated/sound/odd-5500-native.snd).
The pre-run PCM expectation was 111 repetitions of `80 00 FF 01 FE`
with one 8-bit channel, 5,500 Hz, 555 frames, and a 555-byte data chunk
followed by a pad byte. Python's standard-library WAVE reader recovered
the same format and exact 555 unsigned PCM bytes. The historical file is
599 bytes, with RIFF size 591, data size 555 and no trailing pad. The
project writer pads this odd payload without adding a sample. This
comparison measures one later, uncompressed Sound recording. The WAV
remains in the private lab under the project's audio publication policy.

## Inventory and follow-up

The [utility registry](historical-utility-registry.json) records 31 preserved
accessions and 29 operation/profile entries. This campaign qualified four
entries, and the registry carries forward two prior qualifications for
[DM_Music](dm-music-hds-20261120.md) and
[MidiMapper](midimapper-win98-20261120.md). DBrepair through the DOS
converter's recovery handoff has a working related runtime profile, with the
handoff still open. Twenty-two entries have offline identity evidence and
named prerequisites. The [prioritized backlog](historical-utility-backlog.json)
keeps reports, text, audio, graphics, early Filer, and companion tests scoped
to their original formats and runtimes.

Source packages, historical code and executables, disk images, and full
captures remain in the lab. The fixtures are original synthetic project
content saved by the named utilities or the documented one-byte mutation.
The selected screenshots document actual guest observations. Tandy's
interface and Jeffrey L. Hayes's utility artwork remain the property of
their rights holders, outside the project’s GPL and Creative Commons offers.
