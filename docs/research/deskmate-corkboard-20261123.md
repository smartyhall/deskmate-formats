# Corkboard, Information Center, and Financial Notebook (2026-11-23)

The RSX OEM DeskMate 03.04.04 Desktop opens **Corkboard** from its
**F10 Accessories** menu. The private installed `DMNOTEPD.ACC` contains
the Corkboard title and error messages naming `DMCORKBD`. Information
Center 3.61 also names this file in its own open/create errors, and its
dashboard displays the same persistent text in a yellow notepad. Financial
Notebook is a separate application under Home Organizer's Financial column.
Its installed `NOTEBOOK.HLP` identifies it as a place to track stocks,
loans, and investments, and `NOTEBOOK.PDM` names `NOTEBOOK.DB`.
[RSX installation and Information Center controls](deskmate-rsx-oem-recovery-20261122.md)

The 1991 Radio Shack catalog advertised both Information Center and
Financial Notebook in RL Home Organizer. It describes the former as a
household message board and the latter as a tracker for loans, savings,
and investments. A contemporary 1100 FD review names Corkboard among the
portable's accessories. We confirmed that identification in the recovered
1100 FD media's `DMNOTEPD.ACC`.
[Radio Shack 1991 catalog](https://www.worldradiohistory.com/Archive-Catalogs/Radio-Shack/Radio-Shack-1991.pdf) ·
[Los Angeles Times, February 15, 1990](https://www.latimes.com/archives/la-xpm-1990-02-15-fi-785-story.html)

## Release survey

The survey scanned names and uncompressed case-insensitive byte strings
in extracted FAT disks and installed trees. Exact identities and counts
are in the [structured evidence](../evidence/deskmate-corkboard-20261123.json).
Compressed or ROM-only content and untested menus can escape this check.
The absence of a named module is limited to the inspected tree or media.
Use the [release inventory](../ecosystem/deskmate-evolution-releases.json)
for source-media hashes and the [earlier native survey](deskmate-evolution-native-20261121.md)
for the versions of the early launch controls.

| Edition or control | Corkboard evidence | Associated Home Organizer evidence |
| --- | --- | --- |
| Original Tandy 1000, DeskMate II for 3000 and 1000 SX, Personal DeskMate EX | No Corkboard name or matching accessory filename found in the extracted controls. | No matching modules in the scanned files. |
| Personal DeskMate HX and standalone Personal DeskMate 2 | Identical `DMNOTEPD.ACC` binaries contain **Note Pad**, `dmnotepd`, and a file-create dialog. Personal DeskMate 2 saved the same bytes as later Corkboard for the matched note. | No matching Home Organizer modules in the scanned files. |
| Generic 3.00 and 3.02, 1000 TL 3.02 | Identical `DMNOTEPD.ACC` with both Corkboard and DMCORKBD strings across the three controls. 3.00 is the earliest recovered generic release with this name. | No matching application modules in the scanned files. |
| Generic 3.01, Professional DeskMate | Exact relevant program trees unverified. | Unverified. |
| Generic 3.03.01, 1000 TL/2, 1100 FD, and 1000 SL/2 | All four carry the same Corkboard accessory bytes. Native F10 launch and save measured on the SL/2 with ROM DeskMate and the two program floppies. | No matching application modules in the scanned files. |
| 1000 RL 3.04 distribution | Disk 3 has both `DMNOTEPD.ACC` and `DMCORKBD`. | Disk 3 has Information Center, Disk 4 has Financial Notebook, and Disk 5 has Collections. |
| 1000 RLX 3.04.03 media and RLX B | Bounded scan of available wrapper/support files. The packed application payload was outside this survey. | Unverified in the packed payload. |
| 1000 RSX 03.04.04 | Native F10 launch, save, cold reopen, dashboard edit, and Clear. | Native Information Center 3.61, Financial Notebook, and Collections. |
| Generic 03.05.00 nine-disk, five-ZIP, and five-raw packages | Same `DMNOTEPD.ACC` and stock `DMCORKBD` across these controls. Native F10 launch and file creation measured on five-ZIP. | Desktop binary strings mention `INFOCNTR.PDM`. The inspected generic trees did not contain that module, `NOTEBOOK.PDM`, or `COLLECT.PDM`. |

## RSX write and cold-reopen trial

Launch the [established visible 86Box profile](deskmate-rsx-oem-recovery-20261122.md)
from a new writable copy of the stopped clean OEM installation, preserving its
config and NVRAM. The input disk SHA-256 was
`3085c68955b7fcad648995a40ff30f8f3a799e943710bd43cc0326c69a107fc1`.
The executable SHA-256 is
`e7e1244588ea721aa239564a43fa2636611ae965ea8431672fdc06d8c12c280d`.
Use the authenticated socket in held mode. At DOS change to
`C:\DESKMATE` and run `DESK`. Use the framebuffer to confirm selections.

1. Open F10, press Down five times to highlight Corkboard, and press Enter.
   Type `CORKBOARD ATLAS TEST 20261123`, Enter, and `SECOND LINE`. Escape
   closes the accessory and retains the text. Information Center displayed
   both lines at 84,390 emulated ms. Exit to DOS, then quit through the
   socket (91,310 ms). The first stopped disk SHA-256 was
   `c9914b404a9446d3e943928decd8743c50831e0f1c836d1b4c938b7a5b6d9378`.
2. Relaunch from that disk. The accessory reopened with both lines by
   55,826 ms. In Information Center click inside the notepad, press End,
   Backspace, and type `X`. The final `T` in `TEST` became `X` at
   69,721 ms. Escape from Information Center, exit the Desktop to DOS,
   and quit through the socket (78,791 ms).
3. After the other application tests, cold boot again. The F10 accessory showed
   the edit at 57,376 ms. Click **Clear**, close with Escape, exit to DOS,
   and quit at 70,488 ms. One file byte changed inside `DMCORKBD`, at
   `0x0004`. The first text character became NUL. All later bytes, including
   the remaining synthetic text, stayed present. Clear hides the note from
   the UI and leaves residual text recoverable in the file.

Both 7-Zip extractions had 513 files, matching the clean installation.
The only changed file contents in either transition were
`DESKMATE/DMCORKBD` and `DESKMATE/DESKTOP.CFG`. Both
`INFOCNTR.DB` and `NOTEBOOK.DB` stayed byte-identical. The note file
remained 2,864 bytes. The first save changed offset `0x0000` and bytes
`0x0004–0x002C`, including the single CR delimiter. The edit changed
offset `0x0000` from `29` to `14` (hex) and offset `0x0017` from
`54` to `58`. The unchanged text length with a smaller byte at
offset zero rules out interpreting that byte as the total length.

## Cross-release writes

On the earlier standalone **Personal DeskMate 2 01.00.00**, boot Tandy
DOS 03.20.02 in A: and use the reconstructed startup disk in B: on
the established 1000 SX profile. Set a four-digit date (the two-digit
year was rejected), switch to B:, and run `DESK`. The Desktop has its
own **Note Pad** panel. F1 → Down three times → Enter opens the accessory.
The reconstructed boot pair lacked its data file. Choose **Create**
in the `Cannot Find File` dialog, type the same two lines as on RSX,
and close with Ctrl+Q. The expanded accessory showed the note at
139,208 ms and the Desktop panel displayed it after exit. Select
F2 → Quit DeskMate and quit through the socket after DOS returns
(172,206 ms). A: acquired `DMNOTEPD` and `MENUDATA.TAN`; B: was
byte-identical to its input. The new 2,864-byte `DMNOTEPD` matched the
published RSX `DMCORKBD` byte for byte. The original distribution
disk also holds a blank `DMNOTEPD`. This establishes a storage
continuity across the separate Note Pad and Corkboard names.
[Reconstructed Personal DeskMate 2 controls](deskmate-evolution-native-20261121.md#standalone-personal-deskmate-2-on-the-tandy-1000-sx)

On the clean alternate 03.05.00 installation recovered in
[PR #164](https://github.com/smartyhall/deskmate-formats/pull/164), rename
`DMCORKBD` to `CORKBAK` in DOS on a disposable clone. F10 → Corkboard
opened a blank editor, without a prompt in this hard-disk trial. Type
fourteen lines, `LAB 01 ALPHA BRAVO CHARLIE` through
`LAB 14 ALPHA BRAVO CHARLIE`, with Enter between lines. At 98,760 ms
the scrolled editor showed lines 2–14. Escape and exit to DOS, then
quit at 107,172 ms. The new 2,864-byte `DMCORKBD` contains the full
377-byte text, with first words `0179 0000` in hexadecimal. The backup
matches the stock all-zero source. Desktop settings also changed.

For the SL/2 comparison, use the tested ROM/DESKMATE EEPROM seed and
byte-verified copies of Disk 1 in A: and Disk 2 in B:. The program disks
are catalogued as 03.03.01. F10 offered Corkboard at 17,604 ms. Selecting
it reported a missing `DMCORKBD` on A:. Tab to Cancel and press Enter
to reach **Create File**. Accept, type the original RSX two-line text,
and close with Escape. Exit to DOS and quit at 57,378 ms. Disk 1 gained one
file, with bytes identical to the RSX two-line fixture. Disk 2 was
byte-identical to its input. This extends the prior SL/2 test from shell
startup and editor launches to a persistent accessory write on cloned media.
[Pinned SL/2 ROM, media, and factory EEPROM procedure](deskmate-305-variants-sl2-20261122.md#sl2-rom-startup-on-a-factory-initialized-eeprom)

## Corkboard storage

The observed file contains two little-endian 16-bit words at `0x0000`
and `0x0002`, then a 2,860-byte text area at `0x0004`. The ASCII text
uses CR line delimiters and ends at the first NUL. The word at `0x0000`
matches the insertion point in all three nonempty write states, including
the position-20 Information Center edit and position-377 3.05 write.
The second word remains zero in these specimens, including the scrolled
3.05 view. Its meaning and the maximum editable length remain open.
The RSX binaries independently show two 2-byte transfers and one
`0x0B2C`-byte transfer on the same handle. The read sequences contain
the third transfer size at `DMNOTEPD.ACC:0x063E` and
`INFOCNTR.PDM:0x3EB3`, with corresponding write sequences at
`0x0E1A` and `0x40BD`. The two binaries also reference their own
embedded lowercase `dmcorkbd` names.

`corkboard.parse_bytes()` inspects the ASCII-and-CR profile and reports
both raw words and the visible text. It preserves the entire snapshot,
including the residual bytes after Clear. It requires the caller to
identify the file because the buffer has no signature. Import, export,
CP437, control bytes, exact capacity, and printing remain untested.

## Financial Notebook and Collections

At the RSX Desktop, Right to Home Organizer and Enter. From Collections,
press Right twice and Down four times for Financial Notebook. Its UI
describes stocks, outstanding loans, and savings. Select **No Password**
and use the Loans pane. Item → Add begins or commits a card as you
move to the next card. Enter `ZETA LOAN` and lender `LAB LENDER` for
125.00. The early note entry stored `HETIC LOAN NOTE`; the leftmost
characters of the intended input did not reach the field. Then enter
`ALPHA LOAN` and lender `LAB` for 50.00. The list displayed ALPHA
before ZETA at 93,541 ms. Exit through the Desktop to DOS and quit at
107,957 ms. Only `NOTEBOOK.DB` and `DESKTOP.CFG` changed.

From Home Organizer → Personal → Collections select **New**, enter
`LABCOLL`, choose **No Password**, answer **No** to the categories prompt,
and accept the five default labels. The blank editor was visible at
103,129 ms. Enter `ZETA SPECIMEN` with fields `LAB`, `CONTROL`,
`BOX`, amount 42.00, and note `ORIGINAL SYNTHETIC ENTRY`. Use Item →
Add to accept the first entry, then enter `ALPHA SPECIMEN` with
`LAB TWO`. The two entries were visible at 115,368 ms. After exit to
DOS and socket quit at 130,884 ms, the only content change was the
addition of `DESKMATE/LABCOLL.COL`.

On a new boot, Financial Notebook reopened both loans at 71,014 ms.
With ALPHA selected, Item → Delete removed the card. Append
` CHECKED` to ZETA's Notes field and exit. Collections → Open →
LABCOLL similarly reopened both cards at 102,360 ms. Delete its ALPHA
card with Item → Delete and append ` VERIFIED` to ZETA's note. At the
128,194 ms shutdown, the only changed files were those two databases.

## Shared database framing

The existing native two-message specimen and the clean RSX template have
the common two-table 1 KiB layout with `DBCOLS` on data/index pages 2/3
and `INFO` on 4/5. Both have `03 02 03` beginning at the directory
marker at `0x044A`. The separate read-only
`database.parse_information_center_bytes()` validates the observed roles,
tail, ordinals, and application schema, then uses the common parser's
chain, index, and row validation. The generic parser still rejects the
nonzero tail. [Two-message native specimen](../../tests/fixtures/application-generated/information-center/rsx-native-two-messages.db)

| Native specimen | Bytes, header prefix | Directory marker and roles | Application data |
| --- | --- | --- | --- |
| Information Center `INFOCNTR.DB` | 6,144, `03 00 00 00` | `0x044A`, `03 02 03`. DBCOLS 2/3, INFO 4/5. | Six fields, including Type, Date, Text, Phone, Name, and Time. Two `M` rows and one stock `P` row in the published specimen. |
| Financial Notebook `NOTEBOOK.DB` | 6,144, `03 00 00 00` | `0x044A`, zero-filled after `03`. DBCOLS 2/3, DATA 4/5. | Fourteen named fields include Bookmark, Type, Title, Name, five Amounts, two Dates, Choice, Note, and SmallNote. Observed loans use Type `A`; the no-password entry uses Type `P`. |
| Collections `LABCOLL.COL` | 6,144, `03 00 00 00` | `0x0452`, zero-filled after `03`. DBCOLS 2/3, COLLECTION 4/5. | Nine fields are Bookmark, Type, CategoryID, and Field1–6. Type `D` stores display labels, `B` contains the default category, `P` is the no-password control, and `C` identifies the user cards in this experiment. |
| Filer `qrecord-one.fil` | 8,192, `03 46 49 4C` | `0x046A`, zero-filled after `03`. DBCOLS 2/3, DATA 6/7, LAYOUTS 4/5. | A one-column DATA record (`F7Q9`) and five LAYOUTS rows. [Native Filer controls](filer-native-20261117.md) |

Pairs are zero-based 1 KiB data/index pages. These four specimens share
the six-field DBCOLS self-schema, indexed row addresses, and record framing.
The common reader recovers raw fields in Notebook, Collections, and Filer
directly. The Information Center entry point keeps the same row/index
validation. The measured Filer, Notebook, and Collections continue to
interpret their field semantics independently. The profile accepts raw
application values without assigning meanings to all record types, amount
fields, category attributes, or password representations.

The stock Financial Notebook template starts with zero DATA rows.
After choosing No Password and writing two loans, DATA has three rows
and index IDs `12, 11, 10` (hex), in index order. Physical offsets for
ALPHA, ZETA, and the control are `0x1053`, `0x1013`, and `0x1000`.
Collections lists index IDs `11, 10, 12, 14, 13`; `0x14` is ALPHA
at `0x1099` and `0x13` is ZETA at `0x1054`. Both applications
sort the ALPHA record before ZETA despite inserting it last.

The delete-plus-edit passes changed pages 1, 4, and 5 in both files.
The deleted rows were the highest IDs. The directory live-row count
and next-ID-like token each dropped by one, surviving IDs and starting
offsets persisted, and the strict reader sees no retired rows. The
ZETA notes grew into the prior ALPHA row area. File size, DBCOLS pages,
and packed page links stayed constant. These results cover one last-ID
deletion followed by one edit per app. They do not isolate deletion from
the subsequent edit or establish middle-row reclamation and ID reuse.

## Static DMDB comparison

The RSX Information Center, Financial Notebook, and Collections binaries
contain code-backed DMDB name references. Their MZ relocations identify
the segment loads. In each startup-code context, computing file base
plus the DX immediate resolves to the NUL-terminated `DMDB` name.
The corresponding loader branch sets ES from DS, puts `0x006C` in BX,
and invokes INT E0 through alternative dispatch paths. The far
indirect thunk uses the same `DS:006C` slot.

| Module | DS base / DMDB name | Name setup / far indirect call |
| --- | --- | --- |
| `INFOCNTR.PDM` | `0xC310` / `0x131F6` | `0x872A` / `0x8C62` |
| `NOTEBOOK.PDM` | `0x3830` / `0x5ABC` | `0x2097` / `0x25D0` |
| `COLLECT.PDM` | `0x6850` / `0x911A` | `0x4A31` / `0x4F6A` |

This extends the [earlier Filer/Calendar/Address Book call study](database-call-review.md).
The RSX `TEXT.PDM` control also resolves a DMDB name and uses a far
indirect thunk at `0xF383` through its own slot. The static sequence
supports a common service interface and library, while actual runtime
binding and the route for an individual save remain untraced. Corkboard's
accessory has no NUL-terminated `DMDB` name in the scanned RSX binary.
Its native file and the fixed I/O transfers account for the two-way
note sharing independently of Information Center's database support.

## Reproduction and follow-up

The [structured evidence](../evidence/deskmate-corkboard-20261123.json)
pins the stopped image hashes, file counts, changed spans, and capture
times. At each tested hard-disk checkpoint, wait for DOS after the
normal application and Desktop exits, request socket quit, then copy the
stopped disk, config, and NVRAM into the private archive. Extract each
copy with 7-Zip 26.05 and compare content sizes and SHA-256 values across
the full file tree. For the published RSX specimens, direct traversal
using the [FAT16 procedure](../../tools/experimental/draw_disk.py),
with the name filter adjusted for the note files, independently agreed
with 7-Zip. The alternate 3.05 specimen was checked the same way.
The public [fixture manifest](../../tests/fixtures/application-generated/manifest.json)
records exact bytes and source relationships.
The SL/2 and Personal DeskMate 2 floppy writes were independently
checked using FAT12 traversal and are byte-identical to the same
published two-line fixture.

The first visible RSX launch reported a readiness timeout before the
socket had started serving. The owned process subsequently showed its
normal 86Box window and a held socket at 0 ms, and booted on the first
step request. Later starts used the same visible launcher with a 60-second
readiness window. All input and captures used the socket. The private
archive retains the configuration backups, stopped images, socket
journals, and raw framebuffer captures.

Next, isolate a middle-record deletion before editing another card,
then refill the file through page growth and measure ID reuse. Probe
Information Center message removal and reminders independently of its
notepad. Compare Corkboard's second header word, CP437 behavior, and
capacity with pinned inputs. A live DMDB export trace could establish
which storage routines the individual applications actually call.
