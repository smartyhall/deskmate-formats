# Freebuff native 86Box and DeskMate interaction qualification (2026-11-26)

This campaign tested whether a native Freebuff session can run the project's
existing 86Box research infrastructure directly, without an MCP bridge. It
prepared a disposable clone of the sealed Tandy 1000 RSX DeskMate 03.04.04
installation, drove the guest only through the authenticated loopback socket,
read native screens, wrote genuine Corkboard records, recovered them from the
stopped image by two independent paths, and then fixed two small deficiencies
it found in the reusable automation tooling.

Everything below is either a **native observation** in this campaign's own
emulator sessions or an explicitly labelled inference. The private raw
captures, socket journals and stopped disk images remain in the lab; the public
repository receives only the eligible synthetic fixture, documentary
screenshots and sanitized receipts.

Campaign metadata: owner **Freebuff** (native desktop agent), branch
`freebuff/native-emulator-20261126`, base commit
`9b5d880a8b1626263beeaa9531e46ea8eb5272b6`, emulator **86Box 7.0** automation
build with executable SHA-256
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
Model identity and reasoning effort are not exposed to the agent, so they are
recorded as unknown rather than inferred.

## What was actually exercised

| Facility | Status in this campaign |
| --- | --- |
| `tools/86box_launch.py` visible launch with `--automation-hold` | Exercised five times; each launch reached authenticated `held=true`, `paused=false`, `ms=0` |
| A visible emulator window in the operator's session | Verified by Win32 window enumeration in each launch receipt |
| `tools/86box_client.py` / `deskmate_formats.automation.client` | Exercised: `status`, `info`, `step`, `advance`, `key`, `type_ascii`, `text`, `screenshot`/`observe`, `quit` |
| CP437 text-mode screen reading | Exercised at the BIOS/DOS prompt and after `DESK` exit |
| Native PNG framebuffer capture and agent-side visual interpretation | Exercised on 19 captures; the agent read every frame it used |
| Authenticated socket keyboard input | Exercised for DOS commands and for in-application text and menu keys |
| Mouse input | **Not** used; no pointer device was required for the navigation performed |
| Host keyboard/mouse injection or emulator-display clicks | **Not** used anywhere in the campaign |
| MCP tools | **Not available** to the agent; see the assessment below |
| `tools/86box_checkpoint.py` sealed checkpoint/restore | Discovered and reviewed, not used: the sealed RSX clean install predates a `machine-files.csv` inventory, so the campaign cloned it by verified file copy instead |
| `tools/86box_frame_sequence.py`, `86box_award_setup.py` | Discovered, not needed for this scope |
| `deskmate-86box-mcp` server, Observatory, Supervisor | Discovered and read; not operated, because no MCP client was available and the campaign had no authorization to add one |

## Disposable environment

The sealed source is the clean Tandy 1000 RSX DeskMate 03.04.04 installation
recorded in the [RSX OEM report](deskmate-rsx-oem-recovery-20261122.md): a
54,525,952-byte FAT16 hard disk with SHA-256
`3085c68955b7fcad648995a40ff30f8f3a799e943710bd43cc0326c69a107fc1`,
configuration `ccdfb129802cdee9467c1316ca1cbedeb30a83192d0ffdec7a57fad64d55b8b9`,
and NVRAM `e3ad097bc778d2be320b6f9a01e662eda1ba4ed4bcb9f4e41071d236f84368ac`.
All three were re-hashed before use and matched. The sealed directory was only
read.

Two campaign-owned working directories were created outside the repository, each
a byte-verified copy of that sealed state, and each was relaunched for cold-boot
checks. No other emulator instance ran during the campaign: no `86Box.exe`
process existed at the start, loopback port 8765 was free, and each session was
closed through the socket before the next clone was prepared. The machine,
port and executable are recorded in the private campaign registry.

## Experiment F1: reproducing a published native record

The published [Corkboard study](deskmate-corkboard-20261123.md) records a
two-line native note whose fixture
(`tests/fixtures/application-generated/corkboard/rsx-two-lines/DMCORKBD`) hashes
to `b23d72eeffc9734efdf3e192f424f319f07872e869c8a85dafa6675e2ede7121`. Reproducing
that exact file from the sealed baseline is a direct check that Freebuff-driven
input produces the same native bytes as the earlier Codex-driven session.

Procedure, all guest time advanced in explicit steps on a held machine:

1. Cold boot to the DOS prompt (20,000 emulated ms) and confirm the CP437 text
   screen shows the Phoenix BIOS banner, HIMEM and `SET DMCONFIG=C:\DESKMATE`
   followed by `C:\>`.
2. Type `CD \DESKMATE`, then `DESK`; at 12,000 emulated ms the guest is in BIOS
   video mode 18 (VGA 640 × 480) with the teal DeskMate desktop.
3. Press F10. The Accessories menu opens with **no** item selected and lists
   Setup, Spell Checker, Calculator, Phone List, Corkboard, Month, Alarm, To Do
   List, Clipboard and Task Switch. (F8 is the Applications menu; this run did
   not open it.) Five Downs select **Corkboard**; Enter
   opens the note editor with Clear, Print and Cancel controls.
4. Type `CORKBOARD ATLAS TEST 20261123`, Enter, `SECOND LINE`, then Escape.
   The accessory closes and the desktop returns; the note is retained.
5. Escape again opens the exit confirmation; Enter returns to
   `C:\DESKMATE>` at 57,858 emulated ms. Socket `quit` at 67,862 ms.

The stopped disk hashes to
`52b3dc4d82eeae0b08bced4decf83f503cce64d15764b220ad47879c094f4f0d`. Recovering
`DESKMATE\DMCORKBD` with 7-Zip 26.05 and with the repository's independent FAT16
walker produced the identical 2,864-byte file, SHA-256
`b23d72eeffc9734efdf3e192f424f319f07872e869c8a85dafa6675e2ede7121` — byte-identical
to the published fixture. Its header words are `(41, 0)` and its text is
`CORKBOARD ATLAS TEST 20261123\rSECOND LINE`.

A full-tree comparison of the stopped disk against the sealed install found 513
files in both, with exactly two differing: `DESKMATE/DMCORKBD` and
`DESKMATE/DESKTOP.CFG`. Nothing else in the installation changed.

## Experiment F2 and F3: new synthetic record and a controlled append

F1 shows reproducibility, not new ground. The second experiment used a fresh
clone of the same sealed state and a different note, then edited it after a cold
boot:

1. A new three-line note was typed into F10 Corkboard and closed with Escape;
   the session exited to DOS and quit at 59,192 emulated ms. The stopped disk
   hashes to `74922f8a968f22d1dc0bbe335effa306a923b59e2ac50c393b0f2facb495b3ad`.
2. The recovered file is 2,864 bytes with header words `(55, 0)` and text
   `FREEBUFF NATIVE 20261126\rALPHA LINE TWO\rOMEGA LINE THRE`. The 56th
   character never reached the guest (see the input limitation below); the
   screen and the file agree, so this is an input-delivery result, not a save
   error.
3. A cold boot of the same disk reopened the accessory with the three lines
   intact at 40,616 emulated ms. With the insertion point at the end of the
   stored text, one `E` was typed and the accessory closed with Escape. The
   session quit at 58,836 emulated ms; the stopped disk hashes to
   `b8f57da10c7ee4292d4ed2ea1c5a2d7ed48ae14b8954e653e9a18f3b0891cf17`.

The resulting fixture is published as
`tests/fixtures/application-generated/corkboard/freebuff-rsx-three-lines/DMCORKBD`,
2,864 bytes, SHA-256
`09030f49e5442dc4e7bdb48d1696ef71675f1367ca06c2775057abc9744fd61b`, header words
`(56, 0)`, text
`FREEBUFF NATIVE 20261126\rALPHA LINE TWO\rOMEGA LINE THREE`.

The append is a one-character controlled edit and its byte differential is
exactly two bytes: offset `0x0000` changes `0x37` → `0x38` and offset `0x003B`
changes `0x00` → `0x45`. Nothing else in the 2,864-byte buffer changes. This is
consistent with the published measurement that the first word tracks the text
length and insertion point, and with the earlier Information Center edit
observation that the same word follows the edited position.

## Extension F4: a second application and a read-only cross-check

On the same disk, a cold boot and two Right presses from the default Teach Me
tile followed by Enter opened **Information Center 3.61** at 40,300 emulated ms.
Its dashboard showed a November 2026 month calendar on Wednesday the 4th,
`There are no messages.`, an Important Numbers panel, and the yellow notepad
containing the campaign's own three lines. That reproduces the published claim
that Information Center's dashboard surfaces the same Corkboard text, this time
with content generated entirely by this campaign.

Closing with Escape twice and Enter returned to DOS and the session quit at
55,312 emulated ms. Comparing the stopped disk with the F3 checkpoint found a
single difference, `DESKMATE/DESKTOP.CFG` (recent-item and desktop state only);
`DMCORKBD`, `INFOCNTR.DB` and `NOTEBOOK.DB` were unchanged.

## Tooling deficiencies found and corrected

Both changes are small, provider-neutral and covered by portable tests.

1. **The stopped-disk reader rejected extensionless native files.** The
   independent FAT16 verifier restricted names to `FIG`, `DOC`, `FIL`, `FF1`
   and `PRN`, so the earlier Corkboard work had to adjust the filter by hand.
   `tools/experimental/draw_disk.py` now validates any uppercase DOS 8.3 name,
   including extensionless buffers such as `DMCORKBD`, through a single
   `entry_name()` function; `tests/portable/test_draw_disk_names.py` covers
   padding, an eight-character base without an extension, rejection of
   lowercase, paths, traversal and overlong names, and non-string input.
2. **The socket client rejected a carriage return.** `type_ascii()` mapped
   `\n` to the set-1 Enter scancode but raised on `\r`, which is what a DOS
   command line conceptually contains; the first attempt in this campaign
   failed before sending anything because of it. `\r` now maps to the same
   Enter scancode, and
   `test_carriage_return_and_newline_both_send_dos_enter` checks both
   terminators on the wire.

## Reliability and limitations observed

- **One keystroke was lost** out of 56 characters typed as a single paced burst
  (30 ms per key). The screen and the saved file both stopped one character
  short, so the loss is detectably a delivery/guest-buffer result rather than a
  silent save error. The mitigation used here — read the native screen before
  saving, and verify the file afterwards — succeeded. A paced input helper that
  verifies the rendered text and retries the missing suffix would make this
  deterministic; it is proposed follow-up work, not implemented.
- **No mouse input was needed**, but the campaign did not test pointer-driven
  interaction, drag operations, or any dialog that requires a pointer.
- **Escalating menu selection is not stateless**: the F10 menu starts with no
  selection, so Corkboard needs five Downs from a fresh open. A count taken
  after a previous interaction, or after a slow redraw, can select a different
  entry; the campaign's first attempt opened Phone List for that reason and was
  recognised only by reading the captured frame.
- **The installed package in this environment is stale.** `python -m unittest`
  from the worktree imported a site-packages build that lacks
  `deskmate_formats.corkboard`, so portable tests need `PYTHONPATH=src` (or an
  installed wheel from this revision) to run. This is an environment finding,
  not a repository defect, but it changes what "run the tests" means for a
  native Freebuff session.
- **Total emulated time** for the five sessions was 295,830 ms (67,862 +
  54,628 + 59,192 + 58,836 + 55,312). Only the final stopped disks are retained;
  intermediate states were captured as screenshots and file hashes.

## Assessment for sustained native research

**MCP.** Freebuff's present configuration exposes no MCP client, no server
registration surface and no MCP tools to the agent. The repository's read-only
`deskmate-86box-mcp` server therefore could not be exercised, and the campaign
did not attempt to install one. This did not block any part of the experiment:
the packaged `deskmate_formats.automation.client` covers the same native
operations the read-only server wraps, plus the input and stepping that server
deliberately refuses.

**What worked well.** The launch/observe/step/key/capture loop is a good fit for
an agent that can shell out and read images: every state transition was
confirmed from the native framebuffer or the CP437 text screen rather than
assumed, and the held-step model kept guest time exactly reproducible. Recovery
and verification (7-Zip plus the independent FAT16 walker) is cheap and gave
byte-identical results every time.

**What needed adaptation.** Line terminators, an extensionless-file filter, and
menu-selection state assumptions were the only friction points, and two of the
three are now fixed in the repository rather than in local scripts.

**Implications for Supervisor and Observatory.** This campaign is manual,
operator-visible work; it is not a Supervisor-owned turn and proves nothing
about S0/S2 dispatch, Codex app-server ownership or the Observatory journal.
The observations that transfer are narrower: a provider-neutral session can
drive the same authenticated client, and the evidence contract (screens, hashes,
stopped images, two independent reads) is reproducible across providers. A
future adapter would still need its own approval gates, and nothing here should
be read as MCP coverage.

## Reproduction

The exact procedure requires the private sealed installation and a copy of the
emulator build; neither is published. With those inputs:

```sh
python tools/86box_launch.py --machine <private-clone>
python tools/86box_client.py --machine <private-clone> advance 20000
python tools/86box_client.py --machine <private-clone> type "CD \DESKMATE\nDESK\n"
python tools/86box_client.py --machine <private-clone> advance 12000
# F10 (0x44), five Down (0x150), Enter (0x1c), then the note text and Escape.
python tools/86box_client.py --machine <private-clone> quit
```

Extract with 7-Zip 26.05 and verify independently with the same walker the
published graphics studies use:

```sh
python tools/experimental/draw_disk.py <stopped-image> <7z-extracted-DESKMATE-directory> DMCORKBD
```

## Validation

- `python -m unittest tests.portable.test_draw_disk_names tests.portable.test_86box_client`
  plus the repository's portable suite, Ruff's focused checks, REUSE lint and
  the publication audit were run on this branch; exact outcomes are recorded in
  the pull request.
- Native evidence: five held socket sessions, 19 framebuffer captures, four
  stopped-disk checkpoints, and three recovered notes read identically by
  7-Zip 26.05 and the independent FAT16 walker.

## Visual exemplars

Three native captures accompany this report: the F1 note as typed, the F3 cold
reopen of the three-line record, and the Information Center dashboard showing
the same text. They are ordinary documentary screenshots containing only
synthetic campaign content, published under the operator's 2026-11-21
documentary-image authorization.
