# DeskMate 3.05 Calendar dialog identity

The outer DMCSR window record held the predicted geometry for both Change
Event and Find Date. The same physical bytes were also readable in day
view, where the verified window boundary placed them outside the allocated
records. Add Event uses the same layout and control table as Change Event.
Their static title-pointer assignments differ. A visual and register-only
Add trial on the repeat clone cancelled without changing the E02 disk.
[Activation experiment and runtime pins](calendar-dialog-activation.md)

## Geometry and record ownership

The repeat used the already-held E02 clone and the pinned runtime from the
activation experiment. The process creation identity, executable, authenticated
loopback owner and reset identity matched the preserved launch. The same
DMCSR code and data bases were corroborated by opening and unwind register
samples. The file offsets below refer to the verified original `DMCSR.R89`
and `CALENDAR.PDM`, whose two MZ headers are `0x200` bytes. The code anchors
have no relocations in either range.

| Approved range, inclusive | Purpose |
| --- | --- |
| `0x0F9A4..0x0F9CC` | DMCSR context creation and selection anchor, file `0x2444..0x246C` |
| `0x0F9D7..0x0F9EF` | DMCSR context restoration anchor, file `0x2477..0x248F` |
| `0x1EB0C..0x1EB11` | Three existing context words at `ES:0x0F9C..0x0FA1` |
| `0x1E414..0x1E417` | New geometry candidate, verified below |

1. At day-view A, the upward allocation boundary was `0x0850`. The marker
   inserted by `0x2A2E`, whose boundary write is `0x2A7F`, takes `0x3C`
   bytes. The outer modal starts at `0x088C`. The input dispatcher calls
   `0x2496` with the descriptor's layout at `0x5C8A..0x5C94`.
2. `0x2499` allocates a `0x3C`-byte record through `0x28A2`. The copy at
   `0x24BC` starts at record `+4`, advances `DI` by `0x38`, and leaves
   `DI` at record `+4` again after the subtraction at `0x24C8`. The writes
   at `0x2508` and `0x2513` use `ES:[DI+0x14]` and `ES:[DI+0x16]`.
   Thus the first width and height words occupy record `+0x18..+0x1B`.
   The second copies at `0x250C` and `0x2517` fall outside this read.
3. During the Change Event opening, native stops at 29,862 and 29,981 ms
   landed on `0x24BC` with `ES` base `0x1DB70`. `SI=0x0028` was `0x1A`
   bytes into the copy from `CS:0x000E`, and `DI=0x08AA` was `0x1A` bytes
   past `0x088C+4`. The register arithmetic independently locates that
   allocation at `0x088C`. The earlier same-clone Find Date capture at
   file `0x2529` had `DI=0x08DC` after the `+8` start and twelve-byte copy,
   identifying the child record at `0x08C8` on that path. The settled Find
   Date boundary, allocation order and independently verified dialog label
   place its containing dialog in the preceding record at `0x088C`.
4. At modal B, the upward boundary was `0x0904`. The marker, outer record
   and one child record were allocated. `0x6B5B..0x6B71` saves the outer
   selection and creates and selects the child. `0x6BC9..0x6BD1` removes
   the child and restores the saved selection. The active-window handle
   may refer to that child, so the geometry probe uses the verified outer
   record relative to A. It never follows a selected handle.

With the verified context base `0x1DB70`, the first size words at context
offset `0x08A4..0x08A7` give physical `0x1E414..0x1E417`. That range is
above the allocation boundary when A or C is in day view, including the
idle control. Its bytes in those states are preserved privately without a
geometry interpretation. The source layouts are `DS:0x211C` for Change
Event and `DS:0x1A2C` for Find Date, using layout offsets `+4` and `+6`.
Their dimensions are in DeskMate layout units.

## Approved measurements

Each transition used the original native set-1 navigation and one owner at
a time. The private recorder rechecked both code anchors immediately before
each of the two data reads at each checkpoint. It verified identical held
registers, reset counters and data replies, with **0 ms** of guest advancement
between duplicates. The native frames matched independently labelled
references with clock and row-selection blink masks. A→B took 1,236 guest
ms and B→C took 604 guest ms in each triplet. Find Date used the Search menu
and a timed pad to match the interval. The idle run used steps alone.

| Run | A guest ms / frame | B guest ms / frame | C guest ms / frame | Geometry at B |
| --- | --- | --- | --- | --- |
| Change Event | 29,856 / 1,904 | 31,092 / 1,978 | 31,696 / 2,015 | `0x1194`, `0x0B2C` |
| Matched idle | 31,696 / 2,015 | 32,932 / 2,089 | 33,536 / 2,125 | Unallocated |
| Find Date | 33,536 / 2,125 | 34,772 / 2,199 | 35,376 / 2,235 | `0x0AF0`, `0x044C` |

The window counts reproduced `+3/+10` for Change Event and `+3/+4` for
Find Date. For both dialogs all four geometry bytes differed from A at B,
and the raw six-byte context and four-byte probe both matched A at C.
The idle bytes were invariant. The geometry words corroborate the two
tested styles only when the outer record is allocated at the expected
address. A nested dialog would change the required parent reference. Equal
dimensions across different forms remain possible.

## Add Event and Change Event

Bounded Ghidra 12.1.4 decompilation on a copy of the Calendar project was
cross-checked against i8086 instruction bytes and branch targets. The table
keeps static continuation paths separate from the cancellation observations.

| Calendar file offsets | Static finding |
| --- | --- |
| `0xC6ED..0xC718` | Add clears byte `+1` of its temporary event, writes title pointer `0x0536` at `DS:0x2124`, passes the selected-date argument and initial time arguments, and calls the editor at `0xC363`. |
| `0xC75C..0xC789` | Change copies `0x85` bytes from the selected existing record to its temporary event, writes title pointer `0x0540`, and calls `0xC363` with that copy. |
| `0xC375..0xC3DB` | The editor tests temporary record byte `+1`. The existing-record path copies its date, times, description and alarm-related flags into editor fields. The new-record path uses the supplied date and initializes the alarm and description to zero. |
| `0xC3DF..0xC4E7` | Both paths format the fields, use the same form descriptor `DS:0x22C6` and nine-entry control table, and call DMCSR selectors `0x20E3` and `0x20E4`. Initial focus depends on the time values in `0xC3F0..0xC443`. Both modes can later select the same control. |
| `0xC678..0xC6EC`, `0xC720`, `0xC793` | Escape goes through editor cleanup and bypasses copying the form back to the temporary record. Each caller returns before the persistence branch on `0x001B`. A validated Enter path packs the edited record before returning. |
| `0xC72F`, `0xB0BF` | The Add continuation calls `0xAFA0`, which builds a six-field packet and submits selector `0x07` via `0xCDF8`. |
| `0xC7A8`, `0xB118`, `0xB2C1` | The Change continuation calls `0xB0E4` with the edited copy and original-event arguments. One branch goes through `0xB1FA` and submits selector `0x13` via the same dispatcher. These are static request paths. The current experiment exercised only cancellation. |

The Add visual control used Event → Add without entering fields. At
36,388 ms, frame 2,296, it showed Add Event with the selected October 23
date, blank time and description fields, and the alarm unchecked. The
surrounding frame matched the Change Event form layout.
Escape returned to the same selected day row at **36,992 ms, frame 2,332**.
No approved data spans were read during Add. The final complete held disk
matched the archived E02 disk SHA-256
`c013712c0cda7628a5a3138047a7d0e9b631098c5c72d41d5b8f717a6f90a281`.

An exact next test can distinguish the mode words after independent modal
activation. On this clone, registers at Change Event opening (29,879 ms)
showed Calendar `CS=0x25DA`, `IP=0x1528` at file `0x1728` and
`DS=0x3472`. The Add opening and return sweeps corroborated those bases.
The proposed title-pointer read is two bytes at `0x36844..0x36845`, after
matching the relocation-free Calendar anchors `0x3229E..0x322BA` (29 bytes
at file `0xC6FE..0xC71A`) and `0x32315..0x3232B` (23 bytes at file
`0xC775..0xC78B`). With separately approved reads, the expected title
offset is `0x0536` in Add and `0x0540` in Change. The earlier Change run
showed retention after Cancel, so the prediction concerns B and does not
depend on either offset clearing in day view.

### Bounded comparison with other applications

Address Book file `0x971F` and `0x9725` load the same two selector values
and jump to `0x95B3`, whose far dispatch at `0x95D0` uses `DS:0x2814`.
Filer file `0x6B18` and `0x6B1E` load them and jump to `0x69D6`, whose
dispatch at `0x69F3` uses `DS:0x0E7A`. The binding operands at Address Book
`0x9582` and Filer `0x69A5` pass their respective slots and adjacent
`DMCSR` names to `INT 0xE0` with `AX=0x0206`. These are static references
to shared window services. Per-application descriptor layouts, live binding
and allocation counts would need independent evidence.

## Deterministic offline replay

`tools/experimental/calendar_dialog_state.py` consumes an archived A/B/C
bundle. The `mapping` object supplies `module_sha256`, `code_base` and
`context_base`. Each of three ordered `samples` supplies `label`,
`capture_id`, `source_id`, `launch_id`, `guest_ms`, `frame`, `observed_at_ms`,
`held`, `paused`, `reset` (hard, soft, last-reset ms), two `anchors`, and
the six-byte `window`. Anchors specify `address`, `length`, `view`, `width`
and `sha256`. Data spans carry `hex` in place of `sha256`. Optional `geometry`
at B must match the allocated outer record and the proposed form size.
The decoder verifies the pinned DMCSR identity and the mapped anchor digests.
An archive's labels and provenance still require a trusted capture process.

The replay classifies B as no tested modal context, Change Event-style,
Find Date-style, or unknown. It checks A/C restoration and observation age
against caller-supplied `--as-of-ms` and `--max-age-ms`. The age calculation
is deterministic for the same archived timestamps. Change Event-style
retains the possibility of Add Event. Optional focus evidence must refer to
the same held capture, have a separate reviewed Change Event label, match
the pinned Calendar source and anchors, and supply the mapped, agreeing
indices. Only the live-corroborated Description and Start Time indices are
reported. `decode_focus` can also be used with a standalone archived held
sample. The three geometry triplets and both previous focus samples replayed
successfully from private evidence. The new portable tests use synthetic
inputs, including stale samples, changed identities, failed restoration and
conflicting geometry. The decoder does not access a guest or publish data.

```text
python tools/experimental/calendar_dialog_state.py archive.json --as-of-ms <archive-time> --max-age-ms <limit>
```
