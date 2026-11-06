# DeskMate 3.05 Calendar editor observations in 86Box

## Live result

The DeskMate 3.05 installer ran from five 720 KiB disks in a new
Tandy 1000 RSX/DOS 5.00 clone. Calendar reproduced the three historical
database hashes. The visual editor experiment, matched idle control and
Start Time focus control completed in graphics mode `0x12` at 640 × 480.
The record and selected row survived cancellation in both focus runs. A
bounded static trace produced a focus-index candidate and register-only
observations located its data segment. The approved RAM comparison below
confirmed the predicted control index for both visible focus states in this
loaded instance. The archive's measured digest is reproducible across both
downloads. The supplied 63-character reference remains unconfirmed.

### Media and disposable installation

The downloaded 7z archive was 1,075,628 bytes and has measured SHA-256
`bb1a74f787cfbdbda813e34a6a912a8533e0f9449ef0edbcb65353bedc9e323c`.
The supplied string contained 63 characters. It differs from the measured
digest by an omitted `b` at position 13. The mismatch was missed on the first
comparison and discovered in the final preservation check, after installation
and capture. A second download returned the same byte length and measured
digest. Archive integrity verification succeeded. It contains five FAT12 floppies
labeled `DESKMATE_1` through `DESKMATE_5`, plus two accompanying text files.
The inspected Disk 1 Calendar, DESK and DMDB binary hashes match the prior
F00 static research, and its shipped `PERSONAL.CLN` matches historical E00.
The original media and working copies were kept separately. [Prior binary identities](calendar-binding-25.md)

| Floppy | Bytes | SHA-256 |
| --- | ---: | --- |
| 1 | 737,280 | `2f6bb36af31d2996d01c9dcf159ae79ff30009d2a9fb9894798989fe2dda1487` |
| 2 | 737,280 | `6aa634f5e7516ef13d57d94c27040732c9aa17ea8d15ba8d816cee80d7610ce5` |
| 3 | 737,280 | `48d8c47807b14853faf14d774259fa8809cb1e189fdeb0852810ee577c9f9a30` |
| 4 | 737,280 | `f79d1344c02c4d8709b7b9bb4b52c197959bb6322b37a6a63717237eae5cafb4` |
| 5 | 737,280 | `9fdb5559ab34914f24b22aa23c0a5c3f7d3c0c668fbb57240a69cd9ecc47627b` |

The live run used the configuration and build pins in the original plan
with fixture policy revision `105b67efe7ae087b6cccf77277ef9bdc5233a05b`.
The installed disk was a verified copy of the already formatted sealed DOS
image. The clone had its own identity, configuration, NVRAM and loopback
endpoint. It launched visibly, held at 0 ms with seed 1, and reached the DOS
prompt at 12,000 ms. The installer rejected `A:\INSTALL` issued from `C:`
and explicitly requested a drive change. From `A:`, `INSTALL` displayed
version `03.05.00`. The installation used the default `C:\DESKMATE`, swapped
working copies only on the numbered prompts, and accepted the default IBM
Graphic printer, 10 CPI, and the full driver set. At 462,928 ms the installer
announced completion and prompted for a reset. The floppy was ejected and the
installer's requested restart completed on this new clone. DOS returned by
482,932 ms, with its soft reset count incremented from one to two. The installed
tree had 143 files, compared with the historical installation's 126. The
installed Calendar, DESK and DMDB files still matched Disk 1 byte-for-byte.

### Native database reproduction

Set the guest date with `DATE 10-23-2026`, changed to the installation
directory and ran `DESK CALENDAR`. For E01, October 23 was selected in month
view. F6, Down and Enter opened Add Event. Entered `0900`, tabbed twice to
End Time, entered `1000`, tabbed twice to Description, and entered `LPHa123`.
Both AM selections and the unchecked Alarm were visually verified before one
Enter saved. Calendar exited from month view. For E02, reopened Calendar,
pressed Enter for the day schedule, then Enter on the selected appointment.
Description was selected on entry. End, Backspace and `4` replaced only its
last character. The complete form was visually verified before saving once.
Calendar exited from day view. [Historical fixture operations and hashes](../formats/calendar/CALENDAR_FORMAT.md)

| Stage | Held guest ms at disk capture | SHA-256 of the 6,144-byte `PERSONAL.CLN` | Historical comparison |
| --- | ---: | --- | --- |
| E00 installed default | 462,928 | `c556b7f57102fc5432ce926317c8c0aa95cf8992d7fb64a72e2f270e4c517890` | Exact match to both historical E00 and the Disk 1 input |
| E01 after closing Calendar | 493,912 | `5a3ff71dbd9654cc98cbda22e5f42e651c7792419c0c856b4bf0cfc5fa3ab508` | Exact match |
| E02 after closing Calendar | 503,096 | `0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9` | Exact match |

An independent offline FAT extractor read the held disk copies. The raw disk
copy hash was checked against the source while the clone stayed held. The
Calendar parser recovered zero user appointments in E00 and the intended
appointment values in E01 and E02. The native UI supplied the Alarm reading.
In the 143-file installation inventories, only `PERSONAL.CLN` changed across
either transition. E00→E01 changed 30 bytes and E01→E02 changed two bytes
at `0x100D` and `0x103C`, agreeing with the historical report. The role of
`0x100D` remains uncertain. E01 and E02 are the original application-written
bytes from this run. E00 remains private because the installer copied a
shipped file byte-for-byte. [Fixture manifest](../../tests/fixtures/application-generated/manifest.json)

### Held editor checkpoints

All groups refer to the same new launch, with held and unpaused execution,
one hard reset, two soft resets and last reset at 463,564 ms. The launch
receipt and native PID, owner identities, frame and register captures, and
PNG hashes are recorded privately. The native control socket was closed
before each MCP owner connected. The standard SDK client observed each
primary checkpoint twice with `include_text` false and an empty RAM allowlist.
Each pair matched the native PNG and registers and measured 0 ms of guest
advancement. The same check passed at the Start Time checkpoint. The
framebuffer is the latest render and its render time is unknown.

| Run | A — day, selected row | B — 1,236 ms after A | C — 604 ms after B |
| --- | --- | --- | --- |
| Description | 508,652 ms, frame 30,981 | 509,888 ms, frame 31,055. Change Event with Description selected | 510,492 ms, frame 31,091. Esc restored the day and row |
| Idle | 510,492 ms, frame 31,091 | 511,728 ms, frame 31,165. Day view | 512,332 ms, frame 31,201. Same day and selected row |
| Start Time | 512,332 ms, frame 31,201 | 513,568 ms, frame 31,276. Change Event with Start Time selected | 514,172 ms, frame 31,312. Esc restored the day and row |
| Register sweep repeat | 514,172 ms, frame 31,312 | 515,408 ms, frame 31,386. Change Event with Description selected | 516,012 ms, frame 31,422. Esc restored the day and row |

Enter opened Change Event directly from the selected row. Both editor variants
showed October 23, 2026, 9:00–10:00 AM, `LPHa124` and Alarm unchecked.
Four Shift+Tabs moved focus from Description to Start Time, with End Time
visually selected after the first two. Each single-key tap consumed 4 ms.
Each modified tap consumed 8 ms. The Description run used 600 ms then 632 ms
of timed steps after Enter. The Start Time run used 600 ms after Enter, a
100 ms step after each modified tap, and a final 200 ms step. Both used a
600 ms step after Esc. Idle replaced all key-delivery time with timed steps.
Visual comparisons allowed the header clock and a one-pixel row-selection
line to vary. The complete held disk images after the primary and Start Time
cancels matched the E02 disk image byte-for-byte. This establishes persistence
at those captures while Calendar was still open.

### Static trace and register-backed candidate mapping

Analyzed verified Disk 1 copies of `CALENDAR.PDM` and `DMCSR.R89` using
Ghidra 12.1.4, with bounded 16-bit pseudo-disassembly and autoanalysis
disabled, and independently checked the opcodes with GNU objdump and MZ
relocations. `DMCSR.R89` SHA-256 is
`085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75`.
Offsets below are original file offsets unless shown as segment-relative.

- Calendar `0xC775` writes `0x0540` to `DS:0x2124`, a pointer to the
  `Change Event` title at file `0xEFB0`, before calling the editor at
  `0xC363`. Calendar `0xC3A8..0xC3B2` passes `DS:0x7B32` as the description
  copy destination. The Description descriptor at `DS:0x2226` also references
  that buffer. Both title and text can persist after closing the dialog.
- Calendar passes `DS:0x22C6` to the `0x20E3` and `0x20E4` service wrappers.
  Its INT E0 binding names `DMCSR`, with the indirect far call through
  `DS:0x2936`. The named module's relocated descriptor and original selector
  table give a conditional `0x20E4` handler at file `0x5C24`. In its dialog
  path, `0x5E7C..0x5E8E` uses descriptor byte `+3` to index the control table
  at descriptor `+0x13`, and `0x6004` writes the index after the Tab or
  Shift+Tab path. `0x5E5A..0x5E66` copies the current index into `+4` when
  different, before drawing the selected control. Calendar also initializes
  `+3` on dialog setup. The original nine-entry control table identifies
  index 5 with `DS:0x2226` (Description) and index 1 with `DS:0x21C6`
  (Start Time). Whether the named service is the actual live target remains
  a separate comparison. Use `+3` as the primary focus prediction and treat
  `+4` as a previous or rendered-control index candidate.
- The Calendar loop recognizes `0x001B` at `0xC539`, and the cancel path
  marks the stack-local flag at `0xC678`. At `0xC682`, the record-copy path
  is gated on `0x000D`. This static distinction agrees with the visual and
  on-disk observations. It supplies no persistent active-modal flag.

The repeat sampled registers after each of 220 one-ms steps during opening
and 180 one-ms steps during cancel. It used no `memr` requests. At 514,195 ms
the native stop was `25DA:E0BE`, with `DS=ES=SS=3472`, `AX=7B32` and
`DI=7B3A` (low words). With the code segment base `0x25DA0`, IP `0xE0BE`
maps to file `0xE2BE`, immediately after the string-copy word loop. The
destination start and advanced destination index agree with a seven-character
description plus NUL. During cancel the same code segment appeared at three
further stops with DS still `0x3472`. The observed Calendar data base is
`0x34720`. The contiguous-image formula using `0x25DA + 0x0E87` would be
17 paragraphs short of that observed segment. Code and data bases must be
verified independently. The primary B happened to stop in a different
execution context, so its live DS is unsuitable as an application address.

The approved normal-view width-one reads below applied to this one launch
and still-loaded Calendar instance. The protocol first required both code
comparisons against the original image. If either fails, stop before the data reads. Rebind the
approved region list to each held sample in the MCP owner. The four data spans
sum to 16 bytes. The primary prediction is `05` at `0x369E9` for Description
and `01` for Start Time. Compare A→B, B→C and A→C, as well as the matched
idle samples. The title pointer and description can show stale content, and
the focus index is meaningful only when the corresponding editor is active.

| Gate | Physical range | Length | Basis |
| --- | --- | ---: | --- |
| Code verification | `0x32315..0x3232B` | 23 | Calendar `0xC775..0xC78B`, title setter and editor call |
| Code verification | `0x33E54..0x33E66` | 19 | Calendar `0xE2B4..0xE2C6`, string-copy instructions surrounding the register stop |
| Data | `0x36844..0x36845` | 2 | Calendar `DS:0x2124`, title pointer |
| Data | `0x369E9..0x369EA` | 2 | Calendar `DS:0x22C9..0x22CA`, control-index candidates |
| Data | `0x37056..0x37059` | 4 | Calendar `DS:0x2936`, DMCSR dispatch pointer. Compare its words without dereferencing it |
| Data | `0x3C252..0x3C259` | 8 | Calendar `DS:0x7B32`, seven description characters and potential NUL |

### Approved RAM comparison

The initial code-only check at 516,012 ms, frame 31,422, matched both
reference windows in the independently hashed `CALENDAR.PDM`. At every
subsequent checkpoint the owner matched both windows again before reading
the four data spans. A native PNG matched the corresponding previously
labelled frame after masking the clock digits and selection blink line.
The owner reproduced the native registers and read the data twice at each
held checkpoint. Both read groups agreed with a guest-time delta of **0 ms**.
The SDK owner used one authenticated connection per checkpoint. The host
socket table confirmed the prior owner was closed at every handoff. The
launch, reset counters and Calendar code anchors stayed consistent.

Each table cell shows guest ms, frame count and the two decoded control
indices at the held checkpoint. The first index is descriptor `+3` and the
second is `+4`.

| Run | A | B | C |
| --- | --- | --- | --- |
| Description | 516,012 ms / 31,422 / (8, 8) | 517,248 ms / 31,496 / (5, 5) | 517,852 ms / 31,532 / (8, 8) |
| Idle | 517,852 ms / 31,532 / (8, 8) | 519,088 ms / 31,607 / (8, 8) | 519,692 ms / 31,643 / (8, 8) |
| Start Time | 519,692 ms / 31,643 / (8, 8) | 520,928 ms / 31,717 / (1, 1) | 521,532 ms / 31,753 / (8, 8) |

In each editor run both index bytes changed on A→B and B→C, and all 16
approved data bytes agreed on A→C. The idle triplet was constant. At B only
the two index bytes differed between the editor runs, while the visible
values stayed the same. The first index therefore tracks the selected
control in this editor under these conditions, in agreement with the
code that updates it and indexes the control table. The second index
coincided in these settled samples. Its behavior between updates remains
unmeasured.

Index 8 is the Cancel entry in the editor's table. Day-view A and C both
held this value, and the first A followed an earlier cancelled editor in
the same application lifetime. The result is consistent with retained
editor state. It leaves open what the slot contains before the first
editor open and how an observer independently determines that the modal
editor is active. The title pointer and the description buffer matched the
known title and appointment text in all nine samples, including the day
views. The dispatch pointer was also invariant and matched the relocated
named DMCSR descriptor entry. The pointer comparison used the stored value
alone and left the target unread.

The last held disk copy was byte-identical to the archived E02 disk. The
clone remains visibly running and held on the restored day view at 521,532
ms. The browser listener stayed disabled throughout. Private evidence
contains the original media, clone backups, held disk copies, raw bounded
RAM and register replies, checkpoint PNGs, owner and timing records, byte
diffs, and the offline Ghidra projects and traces. The completed canary was
outside the run.

## Original experiment plan

The question is whether bounded, independently located guest
structures track the **Change Event** dialog and its keyboard focus. The
primary sequence is Calendar day view → Change Event with **Description**
focused → the original day view. Each run has three checkpoints. Separate
repeat runs control for elapsed time and distinguish focus from modal state.

## Guest and input fixture

Use a new writable 86Box RSX/DOS 5.00 clone restored from the sealed pristine
baseline, provisioned with a verified complete DeskMate 3.05 installation from
the private **E02** checkpoint. E02 is preferable because it has one synthetic
user appointment and an observed path from a selected day-view row into Change
Event. The fixture is October 23, 2026, 09:00–10:00 AM, `LPHa124`, alarm off.
`PERSONAL.CLN` has SHA-256
`0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9`.
Verify the full 126-file manifest before transfer and again against the
provisioned image offline. Use the private fixture archive as the source of
record. An already sealed DeskMate-enabled RSX image is acceptable if its boot
configuration, installed files and fixture provenance pass the same checks.
The existing DeskMate-named local configuration has no attached disk, and the
inspected local inventory did not establish an installed DeskMate 3.05 image or
locate the E02 archive. Acquisition or access to the approved private source
and image provisioning are prerequisites. [E02 and E03 observations](../formats/calendar/CALENDAR_FORMAT.md)

Start with the canary's Tandy 1000 RSX hardware profile, including an
interpreted 386SX at 25 MHz, 4 MiB configured RAM, internal Cirrus video, PS/2
keyboard, network links off, saved NVRAM and host time synchronization disabled.
Pin DOS startup files, working directory, launch seed (proposed `1`), initial RTC,
rendering mode and disk geometry. Record the actual graphics mode and frame
dimensions at A. DOSBox-X previously showed graphics mode `0x12`, but the RSX
result is a compatibility check. If DeskMate fails to start or render the same
workflow, retain the failure and stop. A different machine or boot profile
requires its own baseline. [RSX baseline](rsx-dos5-baseline.md) · [Historical screen mode](screen-state.md)

Use the automation-enabled executable SHA-256
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`,
86Box source `855258da966f1594f568350be59e8e1eca082ed1`, ROM revision
`908394b690f7da28f47727d9876774fd672c4ed3`, and the repository base at
`b47c940816510fb548586c49372e9ff2781604d0` or the approved descendant
containing this protocol. Verify all pins before launch, including the actual
ROM files and build options. The matching local Release build cache has
`AUTOMATION=ON` and `GDBSTUB=OFF`. Record the Python and MCP SDK versions and
SHA-256 for the parent manifest, clone config, NVRAM, disk, boot files,
installed tree and experiment scripts. Give the new machine and private
evidence directory unique names and reserve a distinct loopback endpoint.
Back up its config and NVRAM before changing them.
The sealed RSX/DOS baseline is a provisioning parent. The completed canary
clone, media, launch and raw evidence are excluded from this experiment.
[Validated canary custody and pins](86box-observatory-live-report.md)

## Checkpoints and independent labels

First run an authorized compatibility and input rehearsal on a separate
disposable copy, using native PNGs and status/registers only. Confirm the
historical `desk calendar` launch from the installed directory and the actual
RSX path to the E02 day and selected row. If Find Date is needed, validate each
visible result before accepting the date. The DOSBox-X MCP work demonstrated
unfocused input and whole-date overtyping in Find Date. It also showed that a
drained BIOS queue can precede a usable display. Carry over short serialized
input and visual checkpoints. Use the native 86Box set-1 keyboard path for this
guest. [Keyboard integration](mcp-keyboard-integration.md) · [Historical input path](mcp-keyboard-input.md)

| ID | Action and expected visual label |
| --- | --- |
| `A-day` | Start with the October 23 day schedule visible, the E02 appointment selected and no menu or editor open. Record the date, selected row, row text and displayed time interval. |
| `B-description` | Tap Enter (`0x1c`) once on the verified selected row. Inspect Change Event and all original field values. If required by the rehearsed route, use an exact approved series of Tab (`0x0f`) or Shift+Tab actions to reach Description. Require a visible insertion caret or selection highlight in Description and unchanged date, start/end, description and alarm. Record the opening and focus actions separately. |
| `C-cancel` | With B verified, tap Esc (`0x01`) once if the rehearsal confirms it cancels this editor. Otherwise agree on an observed keyboard-only Cancel route in advance. Require the editor to disappear and A's Calendar day, appointment contents and row selection to return. A selection mismatch is a failed restoration criterion. Capture C before any application exit. |

There is no field entry between A and C. Record the exact set-1 make/break
sequence, including release of Shift if used, and freeze the rehearsed path
before capture. A fixed proposed starting settle schedule is 100 emulated ms
after each logical action, followed by a no-key 100 ms confirmation. Use the
same schedule in matched runs, or document and freeze revised timings after
the rehearsal. The visual label must agree at both times apart from cursor
blink or other identified redraw effects. Capture the checkpoint at the second
sample. During the measurement run, an ambiguous caret, stale view, unexpected
dialog, partial keyboard delivery, or unexpected elapsed delta stops the run.
Record actual guest ms and frames before and after each tap, timed step and
capture. Scheduled native key delivery advances the clock. Use measured key
deltas and the observed `quantum_ms` to design matched step schedules. If
elapsed times cannot be matched at that quantum, report the mismatch and
withhold conclusions that depend on that control. Record wall time separately.
[Native client timing and failure semantics](86box-client.md)

A reviewer labels the native PNGs independently of the RAM results, using
the visible title, fields, focus marker and restored row selection. Record
unreadable focus as unknown. Use the offline Calendar parser on the private
fixture as a second oracle for appointment values and the post-run file
comparison for persistence. BIOS
text extraction is a text-mode facility. For DeskMate graphics pass
`include_text: false` and use `include_framebuffer: true` for the independent
visual record. The PNG is the latest rendered frame at capture, with unknown
render time. Matching native brackets establishes a coherent held read group
within the available sampling, with millisecond execution granularity.
[86Box capability review](86box-automation-preflight-23.md)

## RAM allowlist and mapping gate

Only exact, preapproved physical spans in demonstrated conventional ordinary
RAM are eligible. Document the binary hash, disassembly reference, owning
segment, translation, requested view and length for each. Use `normal` view,
width 1, and stay within `0x00500..0x9FFFF` and the verified guest RAM map. The
MCP adapter allows four spans per observation. Keep mapping checks in their
own approved group when necessary. Start the rehearsal with an empty RAM
allowlist. [MCP read policy](86box-readonly-mcp.md)

| Candidate | Justification and proposed read |
| --- | --- |
| Calendar module identity | After an independently established Calendar load paragraph, approve two small code anchors, file `0xD7E5..0xD802` (30 bytes) and `0xDE9F..0xDEAF` (17 bytes). Compare them with the exact CALENDAR.PDM and account for any relocations in those ranges. The prior disassembly verifies the binding sequence and far-call thunk here. These checks corroborate module mapping, not UI state. |
| Database service slot, comparison control | Four bytes at verified Calendar `DS:0x2A62`, file `0x114D2..0x114D5` in the original. The thunk consumes this slot. Test whether it stays stable across A/B/C. Record raw little-endian offset and segment and any change. The runtime target and the slot's relationship to a particular operation remain unresolved. |
| Active dialog and focus | No validated offsets yet. Before approving any such read, trace the Change Event resource or caller offline through open/cancel and focus-navigation instructions. Require code-backed reads/writes, owner segment and exact operand sizes for the active modal object and current-control identifier or pointer. Propose only the resulting fields, each at most 8 bytes. Stop at an unresolved indirection. Pointer-target reads require their own evidence and approval. |
| Editor values | Optional, at most 64 bytes of a verified bounded field or descriptor identified by a static copy, render or control-access path. Prefer Description as a cross-check against E02, and record the raw extent and encoding evidence. If the object exists only at B, read it only at B. Compare its verified owner slot across all three states. |

The historical physical window `0x12640..0x126DF` is a **DOSBox-X lead**.
It held a schedule row and changed in Find Date, with unrelated tail churn
even on repeated views. Static or cached strings elsewhere survived Calendar
exit. A bounded offline trace can try to recover the owning object from the
private captures and the original module. Reconsider this window only after
independent 86Box mapping and exact span approval. A Change Event layout, focus
flag and universal buffer terminator have yet to be established. The INT E0
vector, BIOS data area, BIOS queue, device apertures, arbitrary stack, and
DMDB pointer targets are outside this read plan. The vector observation in the
binding research requires a different, instruction-synchronized experiment.
[DOSBox-X window and controls](screen-state-phase3.md) · [Calendar binding boundary](calendar-binding-25.md)

For static preparation, obtain the original `CALENDAR.PDM` and `DESK.EXE`
with the binding report's hashes. Use `tools/inspect_structure.py mz` and
bounded 16-bit disassembly on private copies. Find the actual dialog resource
or construction call, then follow only the activation, cancellation and focus
paths to the first proven state accesses. Use original opcodes and relocations
to verify segment loads. A string hit, Ghidra's synthetic base, or a database
selector cannot establish a runtime address. The relevant state might live in
DESK or a loaded resource. In that case establish that module's own mapping.
Produce a sanitized field/offset and evidence table before freezing the read
manifest. Proprietary listings stay private. [MZ inspection](structural-inspection.md) · [Static call review](database-call-review.md)

For the proven Calendar image layout, a file offset `f` maps to
`16*L + f - 0x0200` using an independently established load paragraph `L`.
The conditional Calendar data segment is `L + 0x0E87`. Establish the load
paragraph and segment ownership with trusted loader evidence or an unambiguous
in-module register stop and approved corroborating code anchors. Verify
real-mode CPU state, effective segment bases/limits, address translation and
absence of wrap for the proposed spans. Live DS at a timed hold may belong to
DOS, DESK or another module. Treat a load or object address that changes as a
new mapping. If identity or mapping cannot be established with the available
primitives, stop the RAM arm. Any later debugger or instrumentation proposal
requires separate review. A UI-only rehearsal and a module-control comparison
are distinct outcomes, neither of which identifies a focus field.

## Single owner and capture procedure

Use the validated [native-to-MCP handoff](86box-observatory-canary.md) on the
new guest. The visible launcher makes its readiness connection and closes it.
For each checkpoint, exactly one native control client advances the held guest
over authenticated IPv4 loopback, verifies the visual checkpoint, and records
the approved mapping evidence. Once held, close that client and verify its
socket is closed before starting one MCP stdio owner. Use the exact token
fingerprint, guest ms, frame count and reset counters to configure a fresh
`ram_checkpoint` with the signed-off spans. The current adapter binds RAM
approval to a held sample, so the A approval cannot follow the guest to B or C.
The launcher, control client and MCP owner run in sequence. Browser polling, if
separately enabled, reads only the MCP owner's published projection.

1. Record a private checkpoint ID `run-id/A-day`, `run-id/B-description`, or
   `run-id/C-cancel`. Include launch receipt identity (PID, start time, session,
   executable, configuration and media hashes, endpoint and private token
   fingerprint), native machine/version, counters, mode, guest time/frames,
   held and paused flags, and approved address manifest. Require `held=true`,
   `paused=false` and unchanged post-boot reset counters throughout A/B/C.
2. Call `get_instance_status`, then `observe_machine` with that owner's
   `expected_session` and `expected_generation`, `include_text: false`,
   `include_framebuffer: true`, and exact named RAM ranges. Require consistent
   status/info brackets and matching frame metadata. Repeat the grouped read at
   the same hold to test for a zero-emulated-ms delta and equality of sampled
   registers, spans and frame. Save replies and PNGs privately before assertions.
3. Close and verify the MCP socket has closed before the next native action.
   At each planned handoff, match the process and last held sample before
   permitting input. Record each owner session and connection generation.
   A planned handoff gets a new session and approval. Unexpected reconnect,
   reset, stale map, mode change, transport ambiguity or wrong visible state
   invalidates the comparison. Preserve the partial record and stop without
   replaying input, including a potentially delivered make or break.

Keep the observer listener disabled for the primary experiment. Private PNGs
already supply the visual oracle. If a browser view is approved later, use a
loopback listener and the reviewed PNG digest bound to that held checkpoint.
Browser publication includes approved display and status only. Capture RAM and
registers through the private owner interface. The protocol exposes no exact
instruction breakpoints, atomic RAM-and-frame snapshots, or semantic DeskMate
focus API. [Owner and publication limits](86box-observatory-live-report.md)

## Comparison and evidence criteria

- Preserve each raw span with its manifest, origin, length, view, width and
  SHA-256. For a same-mapping triplet compare **A→B**, **B→C**, and **A→C**
  by byte at the same offset and group contiguous changes. Use the existing
  offline helper with an explicit capture base for each file. Across fresh
  launches align only independently revalidated module/object-relative fields
  and retain both original physical addresses. Compare little-endian words or
  far pointers only where instruction operands justify that interpretation.

  ```text
  python tools/read_ram_text.py A.bin <physical-start> <length> --physical --base-address <physical-start> --compare B.bin --compare-base-address <physical-start>
  ```

- Run a matched day-view idle control, with three observations at the same
  measured elapsed intervals as the input run, using timed steps in place of
  key-delivery time. Repeat the primary A/B/C from a fresh clone of the sealed
  provisioned image. Under separate approval, run an otherwise equivalent
  A/B/C with StartTime visibly focused at `B-start-time`. Freeze both input
  routes and match checkpoint times by padding with bounded no-key steps. The
  fixture and editor values stay the same. Use the idle RAM triplet to flag
  time-related changes and the two settle PNGs to check visual stability.
  Retain all raw deltas, including those classified as churn.
- A modal-state candidate should show the same B state in both focus variants,
  differ from day view, return to the A value at C, and survive replication
  and the idle control. A focus candidate must distinguish Description from
  StartTime while the modal candidate and field values agree, and match the
  independently labeled focus and code path in repeated runs. A single
  `A == C != B` pattern supports an editor-associated candidate only. Record
  non-reverting values and any residual editor text as possible history or
  caching. Visible restoration allows unrelated RAM to differ. An unchanged
  database pointer or matching Description string alone supplies no UI schema.
- After approved cleanup and only once the working image is closed, compare
  whole-image hashes and offline guest file inventories, with a byte-level
  comparison of `PERSONAL.CLN`. Separate timestamp, disk, NVRAM and preference
  changes from appointment data changes. An unexpected database difference
  must be retained and explained before claiming a no-edit result. Verify the
  protected source, baseline and media hashes again. If the operator elects to
  leave C held, mark post-exit persistence verification pending.

Use an access-restricted directory under the laboratory's private evidence
root. Preserve private launch/owner receipts, configuration and NVRAM backups,
before/after manifests, action journals, original PNGs, raw grouped replies,
raw RAM and comparison output. Keep token contents solely in the owner's
protected token file and exclude them from logs. Record observer socket
ownership and optional HTTP captures privately. Publish only independently
authored, sanitized conclusions, exact measured emulated time and observation
limits. [Evidence policy](../evidence/README.md)

## Operator approvals before execution

1. Identify and authorize the source DeskMate 3.05 installation and E02
   manifest, plus the exact new image and clone directories for provisioning.
   Approve the transfer method and every writable medium. If new media need
   formatting or partitioning, name the new emulated disk explicitly.
2. Approve visible held launch on the new endpoint and the bounded rehearsal
   actions. Then approve the frozen boot, navigation, Enter/focus and Cancel
   key sequences and emulated-time budgets, including which repeat and idle
   control runs may execute. Approve private PNG and register capture at the
   named checkpoints. Include any additional mount or configuration action
   explicitly.
3. Approve mapping verification and each concrete RAM span after reviewing
   address, length, ownership and justification, with separate fresh held
   checkpoint bindings for A, B and C. Any unresolved UI span stays excluded.
   Approve any later loopback display publication separately for each PNG digest.
4. Choose whether the new guest stays held at C or may exit Calendar and shut
   down normally through the native socket for offline disk verification.
   Reset, forced shutdown or recovery after an uncertain mutation requires a
   separate decision. Keep all approvals specific to the new guest.

## Preparation checks

The local 86Box executable hash and source revision match the live canary
report. The sealed RSX baseline manifest, disk, config and NVRAM hashes match
the archived baseline. The private DeskMate inputs were unavailable in the
inspected locations, so the proposed dialog and focus offsets remain open.

All 171 portable tests passed on Windows Python 3.13.17 with the MCP and
observer extras. A separate authenticated synthetic graphics peer verified
serial owner handoffs, refusal of A's stale approval at B before a memory
request, equal duplicate held samples, and the three exact byte comparisons.
The synthetic clock and bytes were assigned by the fixture. This checks the
capture policy and comparator, independently of DeskMate behavior.
