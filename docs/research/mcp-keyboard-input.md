# BIOS keyboard input through a separate MCP server

## Result and scope

The upstream `dosbox_send_keys` BIOS-buffer method works with the existing,
unpatched DOSBox-X 2026.10.01 Windows x64 SDL1/software executable. DOS commands
were entered and executed once, repeated, and reproduced after an emulator
restart. Calendar visibly received F5, menu arrows, Enter, Tab and Escape.
**Find Date navigation works:** October 23 EARLY26 and October 31 Halloween
were each verified twice, including after Calendar restart. Clearing the masked
date field before entering replacement digits resolved the apparent input
failure. No appointments or stored files changed. E17 was not performed.

Tests used an isolated local MCP SDK **stdio client calling the actual upstream
server**, not newly registered tools in the current Codex session. The existing
debugger MCP server remained intact and performed independent memory reads and
RUN commands. No companion emulator was built, installed or substituted.

Main was clean and fast-forwarded to
`9e9a369e5a92cceb6b1e92891af0099a39f5bf19`; work uses
`research/mcp-keyboard-injection`. This addresses the investigation in
[issue 8](https://github.com/smartyhall/deskmate-formats/issues/8).

## Pinned upstream and source assessment

Tested upstream: [md0-code/dosbox-x-mcp,
34c106c1292f99a3f1aebd767147c5bdac7a14de](https://github.com/md0-code/dosbox-x-mcp/tree/34c106c1292f99a3f1aebd767147c5bdac7a14de).
Source inspection covered README, packaging, guest discovery, session/key
encoding, Windows process access, MCP tools and companion build/patch files.
The upstream MIT attribution is retained privately; no upstream source is
vendored here. Packaging requires Python 3.11 or later; the isolated test used
Python 3.13. Its core package requires `mcp>=1.9,<2` and `pydantic>=2`;
the isolated install used MCP 1.30.0 and Pydantic 2.14.2 with their transitive
dependencies. No optional image/analysis extras were installed. The complete
environment inventory and install log are private evidence, not project dependencies.

| Question | Source evidence and observed limit |
|---|---|
| Guest memory | `guest.py` scans readable committed host regions for the BIOS keyboard extent pair at physical 0x480, derives candidate guest physical zero, validates head/tail/extents and a non-null INT 21h vector. |
| Ambiguity | Generic attachment rejects zero or multiple plausible guest bases. Explicit `pid` selects the emulator; the caller must also verify executable, creation time and disposable mount. The attachment tool has no explicit RAM-base override. |
| Windows access | `OpenProcess` requests read/query and, for injection, VM write/operation rights (combined 0x438). No SeDebugPrivilege or administrator request is made. Both test client and emulator were non-elevated, medium integrity (RID 8192). |
| Executable compatibility | Generic BIOS discovery does not depend on SDL2 symbols or a patched executable. It succeeded for two fresh SDL1 process identities and different host RAM bases. This proves this build, not every DOSBox version. |
| Ring update | At guest segment 0x40, read head 0x1A and tail 0x1C; write an ASCII/scan-code word at the current tail, then advance/wrap tail in 0x1E..0x3E. It does not write head or generate IRQ/make/break events. |
| Overflow/loss | Sixteen word positions leave fifteen usable slots. A full ring raises before overwriting the next entry. There is no wait-for-space, transaction, rollback, or guest-consumption acknowledgement, and no producer lock around the BIOS path. A failed batch may already have delivered a prefix. |
| Coexistence | Host process-memory access and stdio use no debugger TCP listener. Existing debugger PONG and bounded memory reads/RUN worked during this investigation. Clients must still serialize input and avoid injection while the guest is paused. |

The session caches and revalidates its RAM base. Our private client additionally
verified the target executable hash and process creation identity before each
attachment, compared Windows integrity levels, required an empty validated ring,
prevalidated every key name, limited batches to fourteen keys, used 0.2-second
pacing, and checked head equals tail after delivery. Emptying is evidence of
consumption, **not proof that an application accepted an edit**.

No live buffer-overflow stress test was performed. The full-buffer behavior above
is source inspection; observed short batches drained, including a ring wrap.
The server permits up to 64 keys per call, which exceeds the ring's capacity and
must not be treated as an unconditional safe batch size.

## Controlled observations

| Trial | Observed outcome |
|---|---|
| First DOS process | Eleven character keys produced visible `echo KEYA01`; a separate Enter executed it once. A second `echo KEYA02` command executed once. The ring drained and wrapped without a duplicate. |
| Emulator restart | Normal BIOS `exit` closed the first instance. A fresh explicitly identified process rediscovered a different host RAM base; `echo KEYB01` plus Enter executed once. |
| No-focus control | The first eleven-character trial ran while another host process was foreground, without changing foreground ownership. Later Enter/full-command and Calendar trials recorded the emulator foreground, unchanged before/after; those are not independent unfocused Enter/Calendar proofs. |
| Calendar | BIOS command input launched Calendar. F5 opened Search; three Down keys and Enter opened Find Date. Tab visibly changed button focus, and Escape cancelled the dialog and exited Calendar cleanly. |
| Initial date editing | Home plus `10232026`, a Tab-cycle/Home/digit attempt and a Home/three Right/single `2` probe left the filled date unchanged. All batches drained. These attempts were not accepted. |
| Editing breakthrough | After restart, End/Backspace visibly removed the final year digit. Clearing the remaining digits left the slash mask. Eight replacement digits visibly produced 10/23/2026 before Enter. |
| First round trip | Enter displayed Friday October 23, EARLY26 at 9:00–10:00 AM. A separately verified 10/31/2026 submission returned to Saturday October 31, Holiday/Halloween. |
| Repeat across Calendar restart | Clean Escape to DOS, BIOS `desk calendar`, then the same clear/type/verify/Enter routine reproduced both dates and schedules. Independent screenshots and debugger reads confirm all four schedule states. |

Backspace at the beginning also left the field unchanged, which is not by itself
an informative failure. Screenshots separate the application result from a
successful MCP response. The private action record retains failed foreground
controls, which stopped before input, and screenshots that captured only the
desktop; neither is counted as a successful guest-state verification.

The DOS evidence shows actual character delivery, and Calendar's changing menus
show that it can consume at least these BIOS-delivered keys. The later successful masked-field editing demonstrates character consumption
in this dialog too. Initial insertion into the filled mask was ineffective;
deleting first then inserting worked. This is an observed editing rule for this
dialog, not a general theory of DeskMate's input implementation. No hardware-hook
requirement follows from the earlier failures. No appointments were added,
changed or deleted.

## Independent readback and limits

The original debugger MCP and the alternative server read the BIOS data area
consistently, excluding changing timer bytes. Bounded 160-byte conventional-RAM
captures at physical 0x12640 were retained before decoding. The existing offline
RAM helper is used with the capture's physical origin, not an assumed full dump.
Screenshots remain the independent check of the current dialog/schedule.

Directly reading the host RAM backing at physical 0xB8000 returned zeros despite
visible DOS text. This backing read is not mapped VGA screen evidence; it is
retained as a negative result. No new video-memory interpretation is claimed.

The four later debugger captures contain a 36-byte printable schedule row at
physical 0x12676, ending before 0x1269A. That differs from the prior run's reported
44-byte span at 0x1266E; neither start is a universal screen-buffer address.
The full 160-byte windows and every difference were retained before decoding.
Three immediate alternative-server reads agree on the later verified row. The
first Halloween immediate read contains no expected row, despite a drained BIOS
queue; the later screenshot and debugger read do show Halloween. Timing or buffer
reuse is possible, but its cause is not established. Queue drainage is therefore
not a screen-readiness signal. Adjacent unclassified bytes also vary.
The existing helper reports candidate RAM text, not a logical screen API;
screenshots supply the independent association with the displayed schedule.
No general field-focus schema, coordinate system or performance improvement is
asserted. Cold one-shot stdio clients also rescan memory; a persistent registered
server may avoid that overhead, but its end-to-end performance was not measured.

## Minimal repeatable procedure

1. Work on a complete verified disposable installation. Guard the original
   executable/profile hashes. Start only the intended instance with the unchanged
   working rendering settings; query the existing debugger's actual port if used.
2. Identify the PID from its exact executable, command line/mount and creation
   identity. Require a single intended target and ordinary matching Windows
   integrity. Never silently pick the first similarly named process.
3. Attach with `dosbox_attach(pid=..., profile="none")`. Require keyboard injection
   support and a unique validated guest RAM base. Do not confuse a static host
   capability with the attached process's raw-hook availability.
4. Read 0x40:0 for 256 bytes; validate the observed extents, aligned head/tail and
   empty queue. Confirm the emulator is running, not paused in the debugger.
5. Prevalidate supported names/characters, serialize one producer, and send a
   short batch with `dosbox_send_keys(pid=..., keys=[...], pace_seconds=0.2)`.
   Start with at most eight keys; split longer input after checking the queue.
   Tested names include `enter`, `esc`, `tab`, `home`, arrows and `f5`.
   Ctrl+A and arbitrary modifier combinations are not this tool's interface.
6. Read head/tail, require drainage, and independently verify the visible result
   before the next significant action. On timeout/full/error/unchanged edit, stop;
   inspect recorded delivery and state. Never replay a possibly delivered batch,
   clear the queue, or force a database save to make a test pass.
7. Cancel unsuccessful dialogs, exit Calendar normally, then use BIOS `exit` at
   a verified DOS prompt. Verify complete before/after installation manifests and
   protected hashes. A new process requires a new identity and attachment.

For the verified Calendar day-view menu, F5 followed by three Down keys and
Enter opens Find Date. Inspect that actual dialog before editing. With its date
field active, End plus eight Backspaces clears the editable digits and leaves
the two slashes. Inspect the empty mask, then send eight digits (`10232026` or
`10312026`). Inspect the **complete replacement date before Enter**, then verify
the resulting date heading and schedule row. No Ctrl+A, clipboard paste or
host-window keystroke is required. The repeated trials used a fourteen-key batch
for the known menu path plus clearing, an eight-digit batch, and a separate Enter;
each batch drained and each significant result was inspected. Do not assume this
menu ordinal or masked-field behavior applies to another dialog/application.

The same local workflow is suitable for the demonstrated read-only navigation.
Regular Codex tool registration and a full unfocused Calendar round trip remain
separate untested integration steps; the unfocused character trial is the direct
focus-independence observation. No database experiment is started automatically.

## Future Codex registration

The [configuration example](../../examples/mcp-keyboard.toml.example) is disabled
until its local paths are filled and reviewed. A private, path-complete fragment
was also prepared. Neither was installed into the active Codex configuration.
It uses a separate `doslab_keys` server name, stdio, no application profile, and
an allowlist of attachment, keyboard, memory-read and status tools. It leaves the
existing `doslab_dosbox` debugger server intact. Generic memory writing and the
unavailable companion/raw-input tools are excluded from this suggested allowlist.

Codex documents stdio commands, arguments, environment, startup/tool timeouts and
tool allowlists in its [MCP configuration reference](https://developers.openai.com/codex/mcp/).
The prepared fragment must be reviewed and enabled for a subsequent session;
its presence does not mean this chat acquired those tools.

## Hardware-style alternative: assessed, not tested

The stock process reports `raw_keyboard=false` and `companion_v2=false` on
attachment. The companion build script requires the exact July 2026.07.02 tag
and Release SDL2/x64, whereas this lab uses October 2026.10.01 SDL1. Its Windows
hook routes registered messages to `KEYBOARD_AddKey` on the SDL event thread,
supporting make/break state. The patch contains both SDL event branches, which
does not establish compatibility with this installed binary. V2 adds a separate
authenticated companion protocol and leases; neither is present here.

The hardware-style hook is unnecessary for the Calendar actions verified here.
If a future application fails controlled BIOS-queue tests, a separate compatibility
proposal would review/port the hook against the exact October SDL1 source, with
separate artifacts and make/break/release tests, never replacement of the working
emulator. That is future work requiring its own scope, not a remedy installed by
this task. No build, patch, raw-hook call,
network-facing service, production parser/writer change, CI change or E17 occurred.

## Preservation and checks

Private evidence is under DOSLAB `EXPERIMENTS/RESEARCH/mcp_keyboard`: upstream
commit/source, environment inventory, process identities, original-file guards,
actual MCP replies, BDA/targeted RAM bytes, independent screenshots, action record
and full before/after installation manifests. No third-party code, real database,
memory dump, screenshot or machine-specific path is included in this repository.
The full source, before, run and final installations each contain 126 files and
have identical file sizes and SHA-256 values. All fourteen original profile and
emulator/debugger executable hash-and-modification-time guards pass. Calendar and
both emulator sessions exited normally; the final disposable emulator is closed.

Local checks: 65 portable tests passed once on Windows Python 3.13; REUSE/SPDX
passed for all 62 covered files with zero missing/invalid expressions; the content
audit passed for 130 source files and existing distribution archives. Both TOML
fragments and tool allowlists parse and validate; canonical license text hashes
match the established evidence. Production code, fixtures, CI and dependencies
are unchanged, so no historical private-suite or platform-matrix rerun is claimed.
The new complete installation guards and four targeted RAM/debugger comparisons,
including the documented immediate-read mismatch, are the directly affected
private checks. GitHub Actions is left to run its matrix
after push; no hosted result is asserted here.

## Exact targeted-RAM comparisons
* `cal_accept_1023__cal_accept_1031`: 26 changed bytes in the same 160-byte physical interval.
* `cal_accept_1023__repeat_accept_1023`: 32 changed bytes in the same 160-byte physical interval.
* `cal_accept_1031__repeat_accept_1031`: 0 changed bytes in the same 160-byte physical interval.
* `cal_accept_1023` immediate read versus later debugger: 0 changed bytes in 160; expected 36-byte row agrees: true.
* `cal_accept_1031` immediate read versus later debugger: 135 changed bytes in 160; expected 36-byte row agrees: false.
* `repeat_accept_1023` immediate read versus later debugger: 32 changed bytes in 160; expected 36-byte row agrees: true.
* `repeat_accept_1031` immediate read versus later debugger: 15 changed bytes in 160; expected 36-byte row agrees: true.

These are whole-window counts; they do not assign meanings to adjacent bytes.
Raw bytes, offsets, complete differences and initial unsuccessful actions remain
private. The common row suffix is recorded per capture rather than promoted to a
universal terminator. The most useful next integration check is to register the
prepared stdio entry in a later Codex session and repeat the proven navigation
with a deliberately unfocused guest; E17 remains separately gated.
