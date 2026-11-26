# Analysing historical DOS executables with Ghidra

Practical procedure for 16-bit DeskMate-era images. It records what was
actually exercised during the [Ghidra qualification
campaign](ghidra-integration-20261126.md) and separates deterministic steps
from interpretation that needs research judgement.

Everything here is read-only with respect to the original files. No step
requires an emulator, a graphical session or a model provider.

## The four coordinate systems

Confusing these is the most common source of error in this corpus. Use the
names exactly.

| Name | Definition | Depends on |
| --- | --- | --- |
| file offset | byte position in the stored `.EXE`, `.PDM`, `.R89` or `.RES` file, including any header | nothing |
| image offset | `file_offset - header_bytes`; equal to the file offset for a COM image | the MZ header size |
| linear address | `16 * segment + offset` | a chosen segment |
| segment:offset | a 16-bit real-mode pair; several pairs label the same linear byte | a chosen segment |

A **synthetic analysis address** is `16 * load_paragraph + image_offset`. This
project uses `load_paragraph = 0x1000` so that image offset 0 is `1000:0000`.
That is an analysis convention. It is not a guest address, and no loaded
image's real paragraph can be read off the file.

A **runtime address** requires an observed loader load segment `L`:

```
linear = 16 * L + file_offset - header_bytes
```

`tools/inspect_dosimage.py map` performs these conversions and always prints
the coordinate kind, so a reported value can be checked against its input.
`--segment` selects which pair labels the result; the pair printed for a
synthetic linear address is one valid labelling, not necessarily the one a
disassembler shows.

## MZ relocation semantics

Two different segment numbers appear in an MZ image and they are not
interchangeable:

* the **site** segment in the relocation-table entry says where a word lives
  (`site_offset:site_segment`);
* the **word at that site** holds the image-relative segment the loader must
  adjust by the load paragraph.

For `DESK.EXE` (`0f2a4024…`), the site segments are `033B`, `0355`, `0405` and
`0456`, while the words at those sites name `0000`, `033B`, `0355`, `03F5`,
`0405`, `0456` and `058A`. Only the second set describes the loader's view of
the image. `tools/inspect_dosimage.py identify` reports
`relocation_site_segments` and `relocated_segments` separately for this reason.

A relocated word pair `offset:segment` becomes a same-image file offset only
when the *segment word* carries a relocation:

```
file_offset = header_bytes + 16 * segment_word + offset_word
```

`tools/inspect_dosimage.py far` reports whether that condition holds and
refuses to dereference an unrelocated pair. MZ has no initial-DS field; any
DS base must come from explicit relocated register loads.

## Reproducing Ghidra's memory blocks

A 16-bit MZ import in Ghidra 12.1.4 does not produce one block. From
`MzLoader.processMemoryBlocks` and `adjustSegmentStarts` in the shipped
`Base-src.zip`:

1. build the loader segment set: every relocated word value, the load
   paragraph and the entry segment, all plus the load paragraph;
2. create one initialized `CODE_<n>` block per segment, starting at
   `segment:0000`, running to the next segment's start, and dropping segments
   whose file offset is past the end of the image;
3. for each block after the first, scan the first 16 bytes **backwards** for a
   far return (`CB`); when found at index *k*, split at *k+1* and join the head
   to the previous block, so the block starts later than `segment:0000`;
4. add uninitialized `CODE_<n>u` and `DATA` blocks for the declared tail and
   minimum allocation.

`MzImage.loader_blocks` in `src/deskmate_formats/dosimage.py` reproduces this
exactly. For `DESK.EXE` the model and the imported program agree on all six
initialized blocks:

| Block | Start | Size |
| --- | --- | ---: |
| CODE_0 | `1000:0000` | `0x33B0` |
| CODE_1 | `133B:0000` | `0x01AF` |
| CODE_2 | `1355:000F` | `0x09F1` |
| CODE_3 | `13F5:0000` | `0x010E` |
| CODE_4 | `1405:000E` | `0x0502` |
| CODE_5 | `1456:0000` | `0x0307` |

The observable consequence matters: **a Ghidra listing's segment prefix is a
loader artifact**, derived from the relocation table plus a far-return scan.
`1355:000F` and `1405:000E` are not boundaries the program chose, and a byte
can be labelled `1000:33B0` or `133B:0000` depending on which block covers it.
Read linear or file coordinates when comparing images, and treat a displayed
segment as display only.

## Importing

Use an explicit processor language. Letting the loader guess is not evidence
of a correct mapping.

Full stored image, standard MZ loader:

```text
python tools/ghidra/ghidra_dos_import.py \
  --project-dir PRIVATE/projects --project cal \
  --input CALENDAR.PDM --language "x86:LE:16:Real Mode" \
  --reopen-check --output PRIVATE/cal-receipt.json
```

Stripped payload at a fixed synthetic base, existing Java script, no analysis:

```text
analyzeHeadless PRIVATE/projects headless \
  -import PRIVATE/specimens/CALENDAR.payload \
  -processor "x86:LE:16:Real Mode" \
  -loader BinaryLoader -loader-baseAddr 0x10000 \
  -noanalysis -scriptPath tools/ghidra \
  -postScript BoundedDecode.java \
  --windows 0xd7e5:0xd802 --file-base 0x200 --address-base 0x10000
```

The payload form keeps published file offsets usable: with
`--file-base 0x200`, a reported `FILE=d7e5` is the absolute offset in
`CALENDAR.PDM`, and `ADDR=1000:d5e5` is its synthetic label.

### Project rules

* One owned project directory per campaign. Never point the tool at a project
  another worker is using; Ghidra locks projects and a second open fails.
* `pyghidra.open_project()` returns a temporary or read-only project that
  cannot persist a program. Use a named project and the loader's
  `LoadResults.save(TaskMonitor)` before release.
* Reopening inside the importing JVM can hit Ghidra's own project cache and
  lock. `--reopen-check` therefore runs import and reopen as separate
  processes, which is also what a later reviewer does.
* An unmodified program cannot be saved: `Program.save()` raises
  `ReadOnlyException`. Persist through `LoadResults.save()`, then close the
  project.
* `--analyze` is opt-in. Byte-level probes do not need autoanalysis, and
  analysis is what turns a 1 KB stub into minutes of work.

## Decoding brackets

Ghidra's x86 language has a display defect for the register form of opcode
`8E`. In `ia.sinc` the constructors read:

```text
:MOV Sreg,m16       is ... byte=0x8e; (mod != 3 & Sreg) ... & m16  { Sreg = m16; }
:MOV Rmr16,Sreg     is ... byte=0x8e; mod=3 & Rmr16 & Sreg          { Sreg = Rmr16; }
```

The semantic assignment is correct, but the display template puts the general
register first. `8E D8` therefore lists as `MOV AX,DS` while its effect is
`DS := AX`. `8C D8` lists as `MOV AX,DS` and really is `AX := DS`. Both forms
print the same text with opposite meanings, which is why `DESK.EXE`'s vector
code must be read from original opcodes.

Cross-check any segment-register instruction with an independent decoder:

```text
python tools/inspect_dosimage.py disasm CALENDAR.PDM \
  --file-offset 0xd7e9 --length 8
```

`disasm` uses Capstone when installed and refuses to pretend otherwise. Ghidra
listing text is never a substitute for the bytes.

## Synthetic specimens

`tests/fixtures/synthetic/dos_images.py` builds deterministic MZ and COM images
with known instruction sequences, relocation entries, a far return at a
segment start and an embedded string. They are used by
`tests/portable/test_dosimage.py` to check parsing, coordinate conversion, the
loader block model and the CLI without any private binary.

Use them when a reachability or mapping rule needs a specimen whose answer is
known; use a preserved original only to check that a rule holds on real bytes.

## Interpreting results

Deterministic extraction ends at the bytes. Keep these separate in any report:

* **observed**: the file, its hash, the decoded instructions and their offsets;
* **derived**: loader block boundaries, coordinate conversions, relocation
  reachability — reproducible arithmetic;
* **inferred**: what a routine does, what a selector means, which module is
  bound at run time;
* **unverified**: anything depending on runtime state that was not observed.

Ghidra's `FUN_*` names, function bodies, decompiler types and references are
the tool's conclusions, not original program metadata. Do not publish them as
symbols, and do not use them to close a question that needs runtime evidence.
