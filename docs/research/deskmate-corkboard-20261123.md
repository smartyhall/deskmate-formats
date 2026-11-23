# Corkboard, Information Center, and Financial Notebook

The RSX OEM DeskMate 03.04.04 Desktop opens **Corkboard** from its
**F10 Accessories** menu. The private installed `DMNOTEPD.ACC` contains
the Corkboard title and error messages naming `DMCORKBD`. Information
Center 3.61 also names this file in its own open/create errors, and its
dashboard displays the same persistent text in a yellow notepad. Financial
Notebook is a separate application under Home Organizer's Financial column.
Its installed `NOTEBOOK.HLP` identifies it as a place to track stocks,
loans, and investments, and `NOTEBOOK.PDM` names `NOTEBOOK.DB`.
[RSX installation and Information Center controls](deskmate-rsx-oem-recovery-20261122.md)

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

Both 7-Zip extractions had 513 files, matching the clean installation.
The only changed file contents in either transition were
`DESKMATE/DMCORKBD` and `DESKMATE/DESKTOP.CFG`. Both
`INFOCNTR.DB` and `NOTEBOOK.DB` stayed byte-identical. The note file
remained 2,864 bytes. The first save changed offset `0x0000` and bytes
`0x0004–0x002C`, including the single CR delimiter. The edit changed
offset `0x0000` from `29` to `14` (hex) and offset `0x0017` from
`54` to `58`. The unchanged text length with a smaller byte at
offset zero rules out interpreting that byte as the total length.

## Information Center databases

The existing native two-message specimen and the clean RSX template have
the common two-table 1 KiB layout with `DBCOLS` on data/index pages 2/3
and `INFO` on 4/5. Both have `03 02 03` beginning at the directory
marker at `0x044A`. The separate read-only
`database.parse_information_center_bytes()` validates the observed roles,
tail, ordinals, and application schema, then uses the common parser's
chain, index, and row validation. The generic parser still rejects the
nonzero tail. [Two-message native specimen](../../tests/fixtures/application-generated/information-center/rsx-native-two-messages.db)
