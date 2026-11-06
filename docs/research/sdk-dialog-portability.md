# DeskMate 3.05 dialog portability

Address Book's Add List Name used the packed SDK descriptor and the same
DMCSR allocation fields as Calendar. Its held input context grew by two
`0x3C` records and four `0x10` records. The extra child record seen
in Calendar's settled forms was absent at this checkpoint. The approved
application-side spans reproduced the frame, table and settled focus
predictions. Filer's Print Form was verified statically. The permitted
shipped sample had Print record disabled, so that dialog has no live
validation in this experiment.
[SDK crosswalk](sdk-calendar-dmcsr.md) · [Calendar live controls](calendar-live-dialog-identity.md)

## Inputs and controls

November 6, 2026. Repository base
`d984ac6f595131ad15595154b41b733c07e66f3a`. Each machine used a
separately verified copy of the closed E02 image, an independent UUID,
config, NVRAM backup and authenticated IPv4 loopback launch. The
installed module bytes matched the staged retail 3.05 inputs after
independent 7-Zip 26.05 extraction of the source image.
[Source identities](sdk-source-identities.md)

| Input | Revision or SHA-256 |
| --- | --- |
| 86Box | `855258da966f1594f568350be59e8e1eca082ed1`, clean, 7.0 UCRT64 Release, automation enabled, GDB stub disabled |
| 86Box executable | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| CMake cache | `bdbc3adcd6f55928050039e008eebb2e0b789f7b52ef39377ee42186252602f5` |
| ROM checkout and RSX BIOS | `908394b690f7da28f47727d9876774fd672c4ed3`, clean. BIOS SHA-256 `17984fe7c31ab6b51c96272ba8ee89580eb139aab01399a1b865f6743f3334f2` |
| Closed E02 source image, both starting copies | `c013712c0cda7628a5a3138047a7d0e9b631098c5c72d41d5b8f717a6f90a281`, 54,525,952 bytes |
| Backed-up NVRAM | `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2` |
| Original profile | `12bb7f7699f85c1eb094bd17da5994f5fc2a0c7bc74de27117b904ce5e5d1773` |
| Global config | `ed46df650d08c87667b68731a3c8588e6d10a93a9a1393772f3972c01cd128b6` |
| `ADDRESS.PDM` | `ef685b20e259f0932378668d9b120882468dc0da157a015e2df95d4ce61a60fb` |
| `FILER.PDM` | `5c62bfcf9676153003753046b223467136659a23ad0883ba56fb312e55b96005` |
| `DMCSR.R89` | `085edb2f2c67ae323343d9efedd7c731778f5fbb8dc59ed8bd6560006b45da75` |
| `DESK.EXE` / `DMDB.R89` | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` / `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |

Both machines were Tandy 1000 RSX, 25 MHz i386SX, 4 MiB RAM,
internal video and sound, PS/2 input, no dynarec and host RTC sync
disabled. The IDE disk geometry was 1,024 cylinders, four heads and
26 sectors, with no mounted floppy or CD. Both booted MS-DOS 5.00
and had one hard and one soft reset, last reset at 613 guest ms.
Launch visibly with `python tools/86box_launch.py --machine <clone>
--port <port> --seed 1`. The launcher requests hold and `--nohook`.
All guest control used the authenticated native socket. Only one
native owner was established per clone during each capture.
[Ownership and hold procedures](86box-readonly-mcp.md)

| Clone | PID / port | Process creation UTC | Launch identity |
| --- | --- | --- | --- |
| `rsx-sdk-dialog-address-20261106` | 1136 / 8901 | 11:02:47.6061243 | `173c3cfe30e840d1a1e67a5c576b8956` |
| `rsx-sdk-dialog-filer-20261106` | 5736 / 8902 | 11:02:50.1433507 | `20ad7d05ff62419cba1c741fa190c880` |

The Address Book and Filer launch receipts hash to
`cab92692f3cb1fa09f9ec29d6592bb06e1d80c0430ab1c310f9d26b9328057ac`
and `5eae9947ddfe9bd183ca6cfa1ef4fcf87e130b6746a7f9b295e89433cba1a645`.
Their effective configurations hash to
`e37391e53f5666fa7cae7441f8deb17edf327fc0ed79356ceb39c6a402f08bc4`
and `8a9c899d073244185309a43f73a2093cd99d96fa427378cdb706f0fddd3cd0a4`.

## Static verification

Read the MZ headers and relocation directories, decode 16-bit instructions
with Capstone 5.0.7 and cross-check branch targets with GNU objdump
`-D -b binary -m i8086 -M intel`. Both modules have a `0x200`-byte
MZ header. Follow `INT E0`, AX `0206`, with ES:DX naming `DMCSR`
and ES:BX identifying the binding destination. Subtract the name's
near offset from the file-backed string position for the initialized
data file base. Follow each descriptor's near frame and component
pointers in the same file-backed segment. Register-derived runtime
bases are established separately.

| Static relationship | Address Book | Filer |
| --- | --- | --- |
| Bind / slot / far dispatch, file offsets except slot | `9582–958B` / `DS:2814` / `95D0` | `69A5–69AE` / `DS:0E7A` / `69F3` |
| Draw/run calls → wrappers, file offsets | `4F4B/4F69 → 971F/9725` | `40C1/40CE → 6B18/6B1E` |
| Selectors | `20E3/20E4` | `20E3/20E4` |
| File data base | `BDD0` | `8770` |
| Descriptor / frame / table, DS offsets | `1948 / 18D4 / 193E` | `0CD2 / 0CBE / 0CCC` |
| Frame extents in world units / title offset | 3500 × 1540 / `084A` | 3000 × 1430 / `0774` |
| Three component offsets and types | `190E/F805, 18DE/F800, 18F2/F800` | `0C96/F801, 0C64/F800, 0C78/F800` |
| File focus/mirror | `14/00`, with `+3` zeroed at `4F42` before draw | `00/00`, with `+3` zeroed at `40EB` on return |
| Cancel accelerator and command | Escape `001B → F513` bypasses the `F512` submission path | Escape `001B → F534` returns zero, bypassing print in the caller |

DMCSR table words at `12AF7/12AF9` resolve to the draw/run bodies at
file `5B05/5C24`. Run follows descriptor `+5` at `5C8B`, opens
the outer window at `5C91` and iterates the component count. The
group marker consumes one large and one small record. The predicted
`+3/+4` depended on a third, live component-window record. The same
DMCSR code copies the frame extents into an allocated record at
`2505–2517` and handles focus/mirror via `+3/+4`.

## Address Book

The source `PERSONAL.ADR` was the empty 10,240-byte book,
SHA-256 `cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
Step 12,000 ms to DOS, type `VER`, then `DATE 10-23-2026`,
`TIME 08:00:00.00`, `CD \DESKMATE` and `DESK ADDRESS`.
Wait 300 ms after each DOS command except the launch, followed by
6,000 ms. Check the native 640 × 480 mode-`12` frame for Address
Book — All, Total entries: 0. Open List with F4 (`3E`), wait
200 ms, press Down (`150`), wait 200 ms, and press Enter (`1C`)
on New. In the first rehearsal and approved trial, sweep 220
one-ms stops and step 604 ms. The empty edit field, OK and Cancel
appear in Add List Name. Press Escape (`01`), sweep 180 one-ms
stops and step 420 ms. No text was entered into the edit field.
Each tap delivered 4 guest ms. The idle control uses the same
intervals with steps only. The second rehearsal used a 7 ms later
Enter, 280 one-ms stops and a 544 ms settle. The second unwind
used 260 one-ms stops and a 340 ms settle.

| Register-only run | A guest ms / frame | B guest ms / frame | C guest ms / frame |
| --- | --- | --- | --- |
| Add List Name rehearsal | 19,588 / 1,297 | 20,824 / 1,371 | 21,428 / 1,407 |
| Matched idle rehearsal | 21,428 / 1,407 | 22,664 / 1,481 | 23,268 / 1,517 |
| Add List Name mapping repeat | 23,268 / 1,517 | 24,511 / 1,592 | 25,115 / 1,628 |

The application registers gave CS:DS `25DA:31A8` with real-mode
cached bases `0x25DA0/0x31A80`. The first Escape sweep caught
`DI=F513` in the application at 20,957 ms. The second caught
`AX=F513` at DMCSR file `5FB6`, 24,521 ms. At 23,825 ms, DMCSR
CS `0D76`, ES `1DB7` and ADDRESS DS carried `SI=18D4` on
the window-open return at file `2534`. At 23,834 ms DMCSR file
`28D1` carried `DI=088C` after reading and advancing the
large-record boundary. At 23,850 ms the handle lookup at `2996`
carried `SI=1948`. In the approved opening, `SI=1948` occurred
at DMCSR file `25FC` at 25,646 ms, followed by the frame offset
`18D4` in the graphics path and component offset `190E` at
DMCSR file `27CF` at 25,673 ms. These are sampled witnesses
from bounded sweeps. A held framebuffer is the latest render
with an unknown render timestamp.

### Approved capture and current hold

The code and context bases came from the independently observed
DMCSR cached CS `0x0D760` and ES `0x1DB70`. Compute code
addresses as CS base plus file offset minus `0x200`. Compute
descriptor and context addresses by adding the documented offset
to the respective DS or ES base. All reads used normal physical
view at width one under a fresh MCP owner tied to the exact held
clock, frame, reset and launch. Native control closed before each
read owner connected. No alternate address was substituted for
a failed condition.

| Inclusive physical range | Authorized use |
| --- | --- |
| `0x2AB05–0x2AB0B`, `0x0FE2B–0x0FE34` | ADDRESS file `4F65–4F6B` and DMCSR file `28CB–28D4` code anchors, active and idle A/B/C |
| `0x1EB0C–0x1EB11` | ES `0F9C–0FA1` context words, active and idle A/B/C |
| `0x333CB–0x333CE` | DS `194B–194E` focus, mirror and frame pointer, active and idle A/B/C |
| `0x33358–0x3335D` | DS `18D8–18DD` frame extents and title, active and idle A/B/C |
| `0x333D8`, `0x333DB–0x333DC`, `0x333BE–0x333C3` | DS `1958`, `195B–195C`, `193E–1943` control count, table offset and entries, active B |
| `0x1E3D8–0x1E3DB` | Conditional geometry at outer record `0850`. Skipped because A's measured top was `0850`, rather than the required `0814`. |

At A the allocation words were `0850/0CEC/002C`. B held
`08C8/0CAC/0031`. The large boundary rose by `0x78`, two
records, and the small boundary fell by `0x40`, four records.
The B descriptor pointed to frame `18D4` and component table
`193E`. It reported three entries with the pinned offsets
`190E/18DE/18F2`. The held frame gave 3500 × 1540 with title
token `084A`. Focus and mirror were both zero, consistent
with the Address Book initializer and the blank focused edit box.
The result supports the SDK layout and an application-specific
allocation profile. The geometry of the allocated record is a
separate measurement from the extents stored in the frame.

The trial is held at active B, 26,351 guest ms and frame 1,702.
Active A was 25,115 ms and frame 1,628. Both checkpoints matched
the two pinned code anchors and the duplicate observations agreed
with zero guest advancement. The actual A top places the candidate
outer record at `088C`, a different address from the conditional
grant. A separate four-byte authorization is pending. C and the
matched idle RAM comparison will follow the decision at this hold.

## Filer

`DESK FILER` opened a file picker at 19,572 ms, frame 1,296.
Escape returned to DOS at 20,176 ms, frame 1,337. The operator
authorized one read-only open of the shipped `CARMAINT.FIL`
to try reaching Print Form. The sample's pre-open SHA-256 was
`ca5ea9d77dc7545e761457ddc9d40c0b5aca427d7f787a19038d61495f4c67e7`.
The second launch reached the picker at 26,256 ms. Typing the
filename into the picker highlighted `INVNTORY.FIL`, so no
Enter was sent until Up (`148`) and an independent framebuffer
check confirmed `CARMAINT.FIL` both highlighted and in the
filename field. Enter opened the approved sample once.

| Filer checkpoint | Guest ms / frame | Observation |
| --- | --- | --- |
| Highlighted sample | 26,752 / 1,735 | `CARMAINT.FIL` selected |
| Parent A | 28,196 / 1,821 | Automotive Maintenance and Repair Records, empty fields |
| Menu control | 28,400 / 1,834 | F2 opens File. Print record and Print report appear disabled |
| Menu cancellation | 29,004 / 1,870 | Escape restores the identical native parent PNG |
| Normal exit | 30,008 / 1,935 | Escape returns to DOS without a save prompt |

The menu record binds Print record to command `F504`. The
jump table at file `072F` dispatches it to `06AF`, and
`06B2 → 3E6C → 40B7` leads to Print Form. The radio-group
labels describe current and all records. The disabled command
ended the target trial. There is no Print Form B or modal C
and no matched modal idle control. The menu cancellation is
an independent visible control for the parent view.

The sample-opening sweep saw Filer CS:DS `25DA:2E42` and DMCSR
CS `0D76`, context ES `1DB7`. At 26,919 ms the handle lookup
at DMCSR file `2998` held Filer DS with ES `1DB7`. These are
parent-path mappings. The Print Form descriptor, allocation,
focus and cancellation path have no live observation. Filer
received no RAM reads. The held post-exit image was identical
to the source image, covering all disk bytes, including the
sample, all 143 installed files and filesystem metadata.
[Earlier Filer reconnaissance](filer-f00-f02.md)

## Observer boundary

Decode DMCSR allocation boundaries and restoration independently
of application identity. A version-pinned form profile can
combine the measured context with the application call path,
owned frame and table, and an independent framebuffer label.
Retained application objects remain readable outside the modal
scope. The measured two-record Address Book context rules out
a three-record activation requirement shared across these forms.
The reason for the missing third record and the exact relation
between the selected handle and the edit control at settled B
remain open. The Filer data supports a static profile candidate
only. A separate disposable Filer run with an authorized record
would be needed for the modal comparison.

For Observatory v2, publish a reviewed held checkpoint, profile
digest, allocation delta, restoration result and separate
ownership, geometry and focus evidence flags. Treat incomplete
or conflicting evidence as unknown. Browser clients should
consume only the owner-published projection.
[Observatory v2 semantic diagnostics](observatory-v2-spec.md#f9-semantic-deskmate-diagnostics-p2)

The private evidence is archived under
`C:/DeskMateLab/private-evidence/sdk-dialog-portability-20261106`.
It contains setup and native drivers, clone and process identities,
static listings, socket journals, register traces, framebuffer
captures, scoped MCP results and verified disk snapshots.
