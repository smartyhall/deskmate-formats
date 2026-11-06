# Live Calendar Add and Change Event identity

The held Add and Change Event forms had identical DMCSR allocation words,
selected handles and outer extents. The shared Calendar frame held title
offset `0x0536` in Add and `0x0540` in Change. After Escape both offsets
remained readable while the DMCSR context returned to the selected day
baseline. Find Date also retained the editor's `0x0540` while running
through a different descriptor. The closed database matched E02 byte for
byte. [Prior geometry and title predictions](calendar-dialog-identity.md)

## Replacement clone and pins

On November 6, 2026, Windows had no 86Box process and the historical
port 8876 had no listener. The old machine files stayed in place. The
replacement `rsx-calendar-dialog-identity-01` booted a verified copy
of the archived E02 disk with the repeat's original NVRAM and hardware
configuration. The clone directory, machine UUID, launch credential and
endpoint were new. It ran visibly with seed 1 and `--nohook`. Native
`info` reported a Tandy 1000 RSX, i386SX at 25 MHz, 4 MiB RAM, internal
video and sound, an IDE disk with 1,024 cylinders, four heads and 26
sectors, and no mounted floppy or CD. The RTC sync setting was disabled.
Process 1848 was created at 09:26:21.484 UTC and owned the IPv4 loopback
listener at port 8877. The process path, creation time, executable hash
and listener ownership were rechecked before RAM sampling.

| Input or artifact | Identity |
| --- | --- |
| Repository base | `66edc67179a34456d0f951f063a6acb67a4a9396` |
| 86Box source and build | `855258da966f1594f568350be59e8e1eca082ed1`, 7.0 UCRT64 Release, automation enabled, GDB stub disabled |
| 86Box executable SHA-256 | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Build cache SHA-256 | `bdbc3adcd6f55928050039e008eebb2e0b789f7b52ef39377ee42186252602f5` |
| ROM checkout and RSX BIOS SHA-256 | `908394b690f7da28f47727d9876774fd672c4ed3`, `17984fe7c31ab6b51c96272ba8ee89580eb139aab01399a1b865f6743f3334f2` |
| Backed-up NVRAM SHA-256 | `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2` |
| Replacement prelaunch and effective config SHA-256 | `59f6210957a37ca5f9e3a455980edb2a24373a68422efc5cc0b62d083ef7493f`, `7c9d30ec711055ebc8f763a5287bb18dbc846858a588b3d7ec6ab6bba281c961` |
| Global config and launch receipt SHA-256 | `ed46df650d08c87667b68731a3c8588e6d10a93a9a1393772f3972c01cd128b6`, `5f1c48d48ee4b7cedb5e0af2f8a923d6c5d1489c8c7b18d13a7d43a001a7f24a` |
| E02 source disk and starting copy SHA-256 | `c013712c0cda7628a5a3138047a7d0e9b631098c5c72d41d5b8f717a6f90a281` |
| E02 `PERSONAL.CLN` SHA-256 | `0af0896163c24c992fa515ddca8c45a31496250d6ba84c9f08e28020a07fe0d9` |
| `CALENDAR.PDM` SHA-256 | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| `DMCSR.R89` SHA-256 | `085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75` |
| `DESK.EXE` / `DMDB.R89` SHA-256 | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3`, `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |

The clean 86Box and ROM checkout revisions, build cache, BIOS search
paths and starting disk were verified locally. The module digests came
from the starting disk's installed files. Only Calendar and DMCSR
received held code-anchor verification.

## Mapping and ownership

A register-only rehearsal of the three modal paths reproduced Calendar
`CS:DS=25DA:3472` and DMCSR `CS=0D76`, with DMCSR context `ES=1DB7`.
The real-mode cached bases agreed. The trial sweeps corroborated these
mappings. Checked file positions by adding the MZ header size `0x200`
to IP in the mapped code segment, and confirmed that no relocation
touches any approved code span.

- **Add.** At 21,190 ms in rehearsal, DMCSR file `0x5E35` had
  Calendar `DS=3472`, `SI=22C6` and `AX=0001`, immediately before the
  input path loads the descriptor's component table. The next sampled
  component path at 21,194 ms held `SI=21C6`, the Start Time entry.
  The approved trial reproduced the labelled form, allocation, outer
  geometry and focus 1. Its opening sweep also carried `SI=22C6`
  at DMCSR file `0x0CB3`, a window service thunk.
- **Change.** At 28,027 ms, DMCSR file `0x0F36` held Calendar
  `DS:SI=3472:211C`, the shared frame. The handle lookup at
  `0x2990` held `SI=22C6` at 28,095 ms. At 28,098 ms the record
  copy at `0x24BC` had `ES:DI=1DB7:08E6` with `SI=0028`, 26 bytes
  into a copy starting at record `+4`. That places the child at
  `0x08C8`, above the outer record at `0x088C`. The same child
  address follows from the `0x2529` stop at 28,112 ms.
- **Find Date.** The rehearsal hit DMCSR `0x5E3A` at 23,063 ms
  with `DS:SI=3472:1A9A` at the table lookup, and the opening
  trial held `DS:SI=3472:1A2C` at the service return at 30,372 ms.
  The known Find Date call passes descriptor `DS:1AA0`, whose
  table and frame match those offsets.

The A boundary `0x0850` precedes a `0x3C` marker and the outer
record at `0x088C`. Reading outer geometry required the B boundary
`0x0904` and the independently labelled modal frame. The pinned
editor descriptor points to frame `0x211C` and table `0x22B4`
with nine controls. The Find Date frame and table are separate.
The owner association joins bounded register samples, pinned static
paths and same-trial allocation. The sweeps do not provide an
instruction-synchronous trace at B. [DMCSR layout and record ownership](calendar-dialog-identity.md#geometry-and-record-ownership)

Each of the 12 held checkpoints had a fresh operator-approved MCP
configuration bound to the launch credential, guest clock, frame and
reset identity (one hard, one soft, last at 613 ms). Native control
disconnected before MCP connected. The host socket table showed one
established owner during capture and none at handoff. Each of two read
cycles first compared all four anchors to their pinned file bytes, then
read only the applicable data spans. Every duplicate matched and advanced
**0 guest ms**. All reads used the normal physical view at width one.

| Physical range inclusive | Use |
| --- | --- |
| `0x0F9A4..0x0F9CC`, `0x0F9D7..0x0F9EF` | DMCSR creation and unwind anchors |
| `0x3229E..0x322BA`, `0x32315..0x3232B` | Calendar Add and Change title setter anchors |
| `0x1EB0C..0x1EB11` | Context at A, B and C |
| `0x36844..0x36845` | Editor frame title word at A, B and C, including negative controls |
| `0x1E414..0x1E417` | Allocated outer extents at modal B |
| `0x369E9..0x369EA` | Editor focus byte and mirror at Add and Change B |

## Matched trials

The native launcher used `--port 8877 --seed 1`. The socket stepped
12,000 ms to DOS, then typed `DATE 10-23-2026`, `CD \DESKMATE`
and `DESK CALENDAR` with 300 ms between commands and 6,000 ms after
launch. Calendar restored the selected October 23 day view at
18,772 ms in mode `0x12`, 640 × 480. The register-only rehearsal
labelled the forms before any RAM read. The approved frames matched
those references under clock and row-selection blink masks. At Add B,
the only additional difference was the independently reviewed
2 × 19 Start Time caret blink. Each framebuffer is the latest
render with an unknown render timestamp.

The approved trials each used **1,236 ms** from A to B and **604 ms**
from B to C, including key delivery. Add used F6, 200 ms, Down,
200 ms, Enter, a 220 ms opening sweep and 604 ms of steps. Change
used Enter directly, a 220 ms sweep and 1,012 ms of steps. Find Date
used F5, 200 ms, three Down taps with 60, 60 and 200 ms after them,
then Enter, a 220 ms sweep and 476 ms of steps. The modal returns
used Escape, a 180 ms unwind sweep and 420 ms of steps. Idle used
steps only. Each tap took 4 ms and each register sweep used one-ms
native stops.

All wall clocks below are UTC on November 6, 2026. Entries are
guest ms / frame / wall capture time.

| Trial | A | B | C |
| --- | --- | --- | --- |
| Add | 26,132 / 1,681 / 09:35:49.006 | 27,368 / 1,755 / 09:36:31.534 | 27,972 / 1,791 / 09:37:27.204 |
| Change | 27,972 / 1,791 / 09:37:32.935 | 29,208 / 1,865 / 09:37:41.295 | 29,812 / 1,902 / 09:37:49.144 |
| Find Date | 29,812 / 1,902 / 09:37:54.621 | 31,048 / 1,976 / 09:38:03.729 | 31,652 / 2,012 / 09:38:11.461 |
| Idle | 31,652 / 2,012 / 09:38:17.036 | 32,888 / 2,086 / 09:38:23.221 | 33,492 / 2,122 / 09:38:29.530 |

Every A and C context was `0850/0D9C/0021` (upward boundary,
downward boundary, selected handle). C restored the visible selected
row. All sizes are in DeskMate layout units.

| Trial | B context and record growth | B outer extents | Editor title A → B → C | Editor focus at B | Offline classification |
| --- | --- | --- | --- | --- | --- |
| Add | `0904/0CFC/002D`, +3/+10 | `1194/0B2C` | `0536 → 0536 → 0536` | 1 / 1, Start Time | Active Add Event |
| Change | `0904/0CFC/002D`, +3/+10 | `1194/0B2C` | `0536 → 0540 → 0540` | 5 / 5, Description | Active Change Event |
| Find Date | `0904/0D5C/0027`, +3/+4 | `0AF0/044C` | `0540 → 0540 → 0540` | Outside the approved watch | Active Find Date |
| Idle | `0850/0D9C/0021`, 0/0 | Unallocated | `0540 → 0540 → 0540` | Outside the approved watch | No verified active modal context |

The measured title words and geometry match the static predictions.
The Add A token was already present after rehearsal, so that triplet
shows the token's value while Add is active and its persistence after
Escape. Change demonstrates the change of token at opening. The full
allocation signature, selected handle and geometry collide across the
two editors. All three modals also share the window-record growth of
three. The title watch is an editor slot, so its value during Find Date
describes retained editor state. The observed focus values also agree
with the pinned table and the independently reviewed forms.

## Persistence and evidence

After the last day checkpoint, one Escape and 1,000 ms of steps
returned to the DOS prompt at 34,496 ms, frame 2,191
(09:38:49.327 UTC). No appointment was saved. The final held disk
copy matched the working image at capture. Offline extraction gave the
same 6,144-byte `PERSONAL.CLN` SHA-256 as the source and identical
contents for all 143 installed files. The closed whole-disk SHA-256
was `d6d1ed5843044c4e539dea67fc7a80b05ef5f5aa8135c065c4c50ef188a7fbc3`.
The only changes from E02 were offsets `0x26EA36..0x26EA37` in
the FAT directory entry for `PERSONAL.CLN`. Its DOS modification time
changed from `A999` to `A8A1` (21:12:50 to 21:05:02, guest local
time). The file date, size, starting cluster and contents matched.
The earlier held rehearsal disk, with Calendar still open, matched
the complete source image.

The private evidence index is in
`C:/DeskMateLab/private-evidence/calendar-live-dialog-identity-20261106`,
SHA-256 `20fa8e05caf2e52e51189ec1d740fc0cc45c02de4a46cc166dc577f94f19453a`.
It indexes the native command journal, register sweeps, owner checks,
frame labels and hashes, scoped RAM replies, disk images and manifests,
and the four offline replay bundles. Replay at each archive's C wall
time with a 60,000 ms age limit produced the classifications above.

Draw-only and between-run states, nesting, task switches, other
Calendar forms with equal counts and geometry, and other builds
remain outside the verified identity profile. The editor focus
observations cover indices 1 and 5. Find Date's frame title field
and focus bytes were outside the approved ranges.
