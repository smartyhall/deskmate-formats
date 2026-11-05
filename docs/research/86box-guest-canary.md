# Native 86Box guest canary: source-to-runtime validation

2026-11-04, America/Los_Angeles. **Runtime verified.** The original DOS program
executed on a new writable RSX/DOS 5.00 baseline clone. Its code, data, eight
32-bit registers, real-mode segments, self-loop address and CP437 pattern matched
the independently authored source. Deliberate reconnect preserved the held
checkpoint; a hard reset returned to DOS. No DeskMate, MCP or observer-server
implementation was attempted.

The [sanitized validation summary](../evidence/86box-guest-canary.json) contains
only verified original-canary bytes, selected registers, measurements and hashes.
Full CPU replies, native PNGs, DOS screens, journals, disks, NVRAM and launch
receipts remain private. The emulator was quit and its process exit verified.

## Revisions and preservation

The working tree was initially clean on main. A new local recovery reference was
created before fetching. Remote main was verified at PR 33's merge,
`5236a9529e72842460e42e10bc97fb0b212d75ea`; the dedicated branch
`experiment/86box-guest-canary` starts there. No merged commits were replayed or
historical/recovery branches rewritten.

| Component | Exact identity |
|---|---|
| 86Box source, clean | `855258da966f1594f568350be59e8e1eca082ed1` |
| ROM checkout, clean | `908394b690f7da28f47727d9876774fd672c4ed3` |
| 86Box executable SHA-256 | `e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d` |
| Baseline disk SHA-256 | `6c146364c24000dbf46898eec1abd4940c3f8a3a666670bdda3aa30a01e681ec` |
| Baseline config SHA-256 | `12bb7f7699f85c1eb094bd17da5994f5fc2a0c7bc74de27117b904ce5e5d1773` |
| Baseline NVRAM SHA-256 | `a883930c6a8ed73bfbe238b7cdad519e63acea18b68f9ff1f367d6f02fd4aba2` |
| Baseline manifest SHA-256 | `27847256c686c6c944ba9ea9def8ed7143c76d8a8d8e753d1c14c7f8e8eea11b` |

Hardware remains the [baseline](rsx-dos5-baseline.md): Tandy 1000 RSX, 25 MHz
386SX with interpreter core, 4,096 KiB configured RAM, internal GD5402 video,
PS/2 keyboard/mouse, primary-master 52 MiB IDE image, A: 1.44 MB, B: absent,
host clock synchronization disabled. The normal visible launcher used authenticated
loopback port 8765, held startup, seed 1, and `--nohook`. Process/session metadata
and the backed-up config are private; the process was in interactive session 1.
No host input, Computer Use, display activation/clicking or RDP changes occurred.

All four sealed baseline hashes above matched before cloning and after the
experiment. The clone's hard disk and the experimental floppy also retained their
initial hashes. Only the disposable clone's config and RTC/NVRAM changed as
expected during launch, execution and reset; their hashes are recorded in the
summary. The sealed baseline was never launched or modified.

## Original program and trustworthy construction

[canary.asm](../../experiments/guest-canary/canary.asm) is the reference NASM-style
386 assembly. No assembler was installed for this task. The standard-library
[generator](../../tools/experimental/guest_canary.py) explicitly encodes the same
instruction sequence; this generated binary, not an asserted assembler output,
was executed. Existing host GNU objdump decoded the output as i8086 with origin
0100, independently confirming register immediates, segment instructions and
the `EB FE` jump at 0160. No downloaded DOS program or proprietary utility is used.

The generator emits a **288-byte COM** and a **1,474,560-byte FAT12 data floppy**:

| Output | SHA-256 |
|---|---|
| CANARY.COM | `f4eb898f81815716359bd63bea663d41b2637bc7662e58c3b693680bd3335b7a` |
| canary-data.img | `0334004234965919e2f597ebabf641812e4f6b39c907500ad9e252efd68e4690` |

The floppy contains only our CANARY.COM in cluster 2; it has two identical FATs,
a fixed label/serial/date and no DOS boot files. An independent host FAT reader
listed the expected single 288-byte file. Its original four-byte boot stub halts
if mistakenly booted. **Mount this data floppy only after DOS has booted, and eject
it before reset.** Generated COM/image files are always outside Git; the generator
refuses repository output paths and existing output directories.

Behavior, in order:

1. Establish DS=CS, select BIOS text mode 3 (clear screen), and print the five
   source-defined CP437 lines with DOS function 09h.
2. Disable maskable interrupts with CLI, then explicitly establish DS=ES=SS=CS.
3. Load all eight general-purpose 32-bit registers with known immediate values.
   No DOS/BIOS interrupt or stack operation follows these assignments.
4. Execute NOP padding and the short self-jump `EB FE` at CS:0160 indefinitely.
   The loop performs no memory writes. Recovery uses native hard reset, not a
   guest keyboard shortcut that would need interrupt delivery.

The program fits one cluster and is specific to a 386-or-later CPU. It does not
attempt a graceful DOS exit. Its stable checkpoint is an intentional test fixture,
not a model of how an arbitrary application preserves registers.

## Actual register and address correspondence

At **15,044 emulated ms**, held and unpaused, native registers reported
CS=DS=ES=SS=`0448`, each cached base=`00004480`, and EIP=`00000160`.
CR0.PE was clear and EFLAGS.IF was clear (observed EFLAGS `00007002`).

| Register | Source value | Native observed value |
|---|---|---|
| EAX | 13579BDF | 13579BDF |
| ECX | 0BADF00D | 0BADF00D |
| EDX | 55AA33CC | 55AA33CC |
| EBX | 2468ACE0 | 2468ACE0 |
| ESP | 0000FF00 | 0000FF00 |
| EBP | 10203040 | 10203040 |
| ESI | 11223344 | 11223344 |
| EDI | 55667788 | 55667788 |

COM file offset zero is loaded at segment:0100; ORG changes source labels, not
file placement. From the **observed** real-mode segment and cached bases:

| Original source region | COM file offset | Guest address | Physical address | Read and verified |
|---|---|---|---|---|
| Code through self-jump | 0000–0061 | 0448:0100 | 04580–045E1 | All 98 bytes equal generated code |
| Self-jump | 0060–0061 | 0448:0160 | 045E0–045E1 | `EB FE`; EIP points to 0160 |
| Banner | 0080 | 0448:0180 | 04600 | Source layout plus observed screen; not a separate RAM read |
| Distinctive data | 0100–011F | 0448:0200 | 04680–0469F | All 32 bytes equal source data |

The calculation is `(segment << 4) + offset`, e.g. `0448h * 10h + 0200h = 04680h`.
Both code and data reads explicitly used **normal physical view, width 1**.
Addresses are below A0000 and do not cross the A20/20-bit boundary. No IVT,
device-mapped region, BIOS ROM, DOS memory search or unrestricted scan was read.
The validator rejects wrong registers, mode, segments/bases or checkpoint IP
before approving the two small spans. Do not assume the load segment is always
0448 on another configuration; recalculate it from the new observed state.

The distinctive data, entirely independently authored, were exactly:

```text
44 4d 46 2d 43 41 4e 41 52 59 2d 76 31 00 00 01
02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f a5 5a
```

The native 720 x 400 framebuffer was visually inspected and agreed with the
CP437 extraction, including the box characters:

```text
DMF CANARY v1
SOURCE / REGISTERS / RAM
┌──────────────┐
│ CANARY READY │
└──────────────┘
```

These are actual emulator observations checked against the source. Synthetic
tests alone do not establish them. The frame is the latest rendered display;
held CPU/register/memory consistency does not make the framebuffer an exact
instruction-level image or an execution breakpoint.

## Emulated time, reconnect and reset

| Stage | Emulated ms | Frames | Hard/soft resets | Result |
|---|---:|---:|---|---|
| Authenticated startup | 0 | 0 | 1/0 at initial status/info | Held; no execution advanced during readiness recovery |
| DOS boot check | 12,000 | recorded privately | 1/1 | C:\> before mounting data floppy |
| Canary checkpoint | 15,044 | 1,036 | 1/1 | Registers, code, data, screen match |
| Fresh authenticated connection | 15,044 | 1,036 | 1/1 | Identical validated checkpoint and PNG hash |
| Additional exact 1,000-ms step | 16,044 | 1,106 | 1/1 | Registers, code, data and CP437 pattern still match |
| Hard reset, DOS boot | 28,044 | recorded privately | 2/2 | Floppy ejected; C:\> returned |
| Post-reset VER | 28,560 | recorded privately | 2/2 | DOS 5.00 observed |

The run used 12 x 1,000 ms to boot, then typed `a:\canary` through socket keys
(44 ms), followed by 3 x 1,000 ms. The entry time of the loop was not measured:
15,044 ms is the observation time. No precise host sleep or instruction stepping
was used to catch it.

The client disconnected deliberately only after all outstanding replies arrived,
while the guest was held. A fresh Client authenticated from the default token
file, acquired a new local connection ID, and performed reads only. No key, step
or other possibly applied mutation was replayed. State and native PNG hash were
unchanged at that same emulated time. After another real 1,000-ms emulated step,
the code/data/register checkpoint remained stable; the PNG hash changed while
the validated text/pattern remained the same. Bit-identical video replay is not
claimed.

The hard reset increased both counters from 1 to 2; `last_reset_ms` changed
from 613 to 16,657. The old program mapping was explicitly retired, and only a
fresh DOS boot/version check was performed afterward. The protocol has no native
process UUID or mapping epoch: matching status/info alone cannot establish process
identity across launches. This run used one PID/launch receipt, successful
authentication from the same default token-file path across deliberate reconnect,
and reset counters. The client brackets
each read group; it does not automatically invalidate every caller's cached
application mapping across independent observations. Callers must do that.

### Readiness limitation encountered

The visible launcher's initial short transport request timed out, leaving its
receipt marked startup_failed. No guest mutation had been submitted. A fresh
explicit Client with its normal 15-second timeout verified the same PID and
visible session, held/unpaused at 0 ms. The failed receipt was retained unchanged;
a separate read-only verified receipt was supplied to the experiment runner.
The reason for the transient timeout was not established. No launcher/emulator
patch, automatic retry of mutation, token deletion or second process was used.
If this recurs, inspect the existing process and status; do not blindly relaunch.

The explicit read-only readiness recovery used this procedure (imports refer to
the existing tools directory; output must be a NEW private receipt):

```python
with box.Client(machine / 'automation.token', timeout=15) as client:
    status, info = client.status(), client.info()
assert status['held'] and not status['paused'] and status['ms'] == 0
window = launcher.windows_state(failed_receipt['pid'])
assert window['session_id'] == failed_receipt['caller_session_id']
assert any(w['visible'] and '86Box' in w['title'] for w in window['windows'])
verified = dict(failed_receipt, state='ready', status=status, info=info,
                window_state=window)
# Save verified to a separate file with exclusive mode 'x'; preserve the failure.
```

## Reproduction

1. Verify the sealed baseline manifest and all disk/config/NVRAM hashes. Create
   a **new** machine directory; copy only the manifest's three listed files,
   preserving the relative disk filename, and make only those copies writable.
   Do not copy baseline-manifest.json into the working profile (it denotes a
   sealed capsule to the launcher). Keep independent before/after hash receipts.
2. Generate original experimental media into a new private directory:

   ```powershell
   python tools/experimental/guest_canary.py C:\DeskMateLab\machines\rsx-guest-canary-02\media
   python tools/86box_launch.py --machine C:\DeskMateLab\machines\rsx-guest-canary-02
   ```

3. Use that launch's exact private receipt path and a new external evidence
   directory. The [bounded runner](../../tools/experimental/run_guest_canary.py)
   controls only the socket, checks every stage, deliberately reconnects once,
   hard-resets once, quits, and waits for process exit:

   ```powershell
   python tools/experimental/run_guest_canary.py --machine C:\DeskMateLab\machines\rsx-guest-canary-02 --receipt C:\DeskMateLab\machines\rsx-guest-canary-02\launch-REPLACE\launch.json --evidence C:\DeskMateLab\private-evidence\canary-new-run
   ```

4. On any error preserve the raw diagnostic state; the runner does not reset,
   reconnect or replay a mutation as automatic recovery. Investigate before
   changing anything. Do not reuse its evidence-directory name.
5. After confirmed process exit, rehash the sealed baseline, clone disk and
   experimental floppy. Inspect the native PNG and CP437 readback. Review the
   validator's small allowlisted summary before copying it into public research
   metadata. Never copy the raw evidence directory or launch receipt into Git.

Private locations for this run: machine
`C:\DeskMateLab\machines\rsx-guest-canary-01` and evidence
`C:\DeskMateLab\private-evidence\guest-canary-20261104`. Generated artifacts and
all original guest captures stay there. Exact assembly/generator hashes and
generated-file sizes/hashes are recorded in the public summary. Portable tests
cover instruction/immediate oracles, FAT12 reconstruction, bounded real-mode
mapping, negative register/code/data/text controls, and exclusive external output.
The complete portable suite passed 117 tests on Python 3.13.17 and UCRT64 Python
3.14. The existing deployment suite ran 29 tests with 27 passing and two explicit
Windows symlink-privilege skips. Ruff, REUSE, repository/archive audits and
wheel/source packaging checks accompany publication. No private guest fixtures
or GUI automation are required by these portable checks.

The tested foundation is a stable source-to-live-state correspondence, not a
general debugger. A later experiment can add precise debugger stops or explicit
mapping-generation handling before attempting semantic DeskMate inspection.
