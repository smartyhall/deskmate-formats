# Note Pad, Corkboard, and Information Center: one note across editions

Three different DeskMate interfaces can display the same kind of household note. The names and surroundings changed, but controlled native saves demonstrate a narrow and striking continuity: **Personal DeskMate 2's `DMNOTEPD` and RSX DeskMate's `DMCORKBD` were byte-identical for the same two-line note**. On the RSX, the Corkboard accessory and Information Center's yellow dashboard notepad also share `DMCORKBD`. These are measured file relationships, **not** proof that all three applications share a runtime or a database engine. [Native experiments and edition survey](../research/deskmate-corkboard-20261123.md)

## Three ways to leave a note

The following three native screenshots document distinct environments with controlled synthetic text. They are displayed together for comparison; their different layouts should not be mistaken for interchangeable executables.

| Interface | Observed edition | Where the note lives |
| --- | --- | --- |
| **Note Pad** | Standalone Personal DeskMate 2 **01.00.00** on a Tandy 1000 SX profile | `DMNOTEPD` on the writable DOS floppy |
| **Corkboard** | Tandy 1000 RSX OEM DeskMate **03.04.04**, opened from F10 Accessories | `DMCORKBD` in the installed DeskMate directory |
| **Information Center** | **3.61**, launched from the RSX OEM Desktop | Yellow notepad displays and edits that same `DMCORKBD` |

Personal DeskMate 2 offered Note Pad as a Desktop panel and accessory. In the RSX release, Corkboard is reached through F10 Accessories; Information Center makes the saved note visible in a household dashboard alongside **separately stored messages**. The same two synthetic lines were saved on Personal DeskMate 2 and the RSX, and their resulting 2,864-byte files matched exactly. The RSX dashboard displayed the Corkboard text after save and cold reopen; an edit from the dashboard was subsequently visible in Corkboard. [Write and cold-reopen results](../research/deskmate-corkboard-20261123.md#rsx-write-and-cold-reopen-trial) · [Cross-release comparison](../research/deskmate-corkboard-20261123.md#cross-release-writes)

## The note is not the message database

Information Center's pinned messages live in **`INFOCNTR.DB`**, a DMDB-framed indexed database with its own application-specific `INFO` table. The dashboard notepad instead reads and writes **`DMCORKBD`**, a fixed-size text buffer. In the controlled Corkboard edits, `INFOCNTR.DB` remained byte-identical. Removing an Information Center message changed `INFOCNTR.DB`, not `DMCORKBD`. Thus sharing a screen does not mean sharing storage. [Message-removal experiment](../research/deskmate-corkboard-20261123.md#information-center-middle-row-removal) · [Maintained Corkboard format reference](../reference/deskmate-corkboard-format.md)

## How much a note can hold

A Corkboard note has a fixed 2,860-byte text area, but that is not how much of it a person can fill. In controlled native trials on RSX DeskMate 03.04.04, the accessory drew a wrapped row at **42 characters** and accepted **65 drawn rows**; a single line longer than 42 simply wrapped, so 42 is a wrap width rather than a limit on one line. The largest note actually written was **2,794 text bytes**, sixty-five full rows of 42 characters joined by 64 carriage returns, and at that length the editor silently refused Enter, a further character, and a mid-row insertion while the caret and the close still worked. That is the largest composition demonstrated, not a proven universal maximum, and no trial took a composition of wrapped lines to its boundary. Because short rows waste space, a note of 65 short rows runs out earlier than a note of 65 full rows; the limit is structural, not a byte budget. [Capacity trials](../research/corkboard-storage-001-20261128.md#experiment-3-real-editable-capacity)

The text area also holds **CP437** rather than plain ASCII. Alt+130 and Alt+225 on the numeric keypad stored bytes `82` and `E1`, which the accessory drew as `e` with an acute accent and as sharp `s`, and kept across a cold reopen; a note written with shading and box-drawing bytes was displayed correctly and saved unchanged. Those are sampled code points rather than a full sweep, and the reader accepts the wider high half as a deliberate policy. [Encoding trials](../research/corkboard-storage-001-20261128.md#experiment-4-character-set)

## Home Organizer: different jobs, different records

The RSX Home Organizer also includes **Financial Notebook**, for loans, savings, and investments, and **Collections**, for categorized personal records. Their native outputs are not Corkboard files: Financial Notebook stores its data in `NOTEBOOK.DB`, while the tested collection was saved as `LABCOLL.COL`. Both use measured DMDB-style table, schema, index, and row structures, with different application-owned fields. Information Center messages share aspects of this database framing, but the evidence does not establish identical runtime dispatch or editing semantics. [Shared database framing](../research/deskmate-corkboard-20261123.md#shared-database-framing)

## Other native states

The accompanying captures show the RSX Financial Notebook's sorted loan list, a Collections card after a delete-and-edit pass, and Corkboard on the Tandy 1000 SL/2 ROM Desktop with its 03.03.01 program disks. The SL/2 wrote the same matched note bytes as the RSX; this is a specific compatibility observation, not an assertion about all releases.

For a byte-level explanation, consult the [Corkboard format reference](../reference/deskmate-corkboard-format.md). For historical distribution coverage, see the [Evolution Atlas](../ecosystem/deskmate-evolution-atlas.md#corkboard-and-note-pad). The [November 23 experiment report](../research/deskmate-corkboard-20261123.md) and the [November 28 storage campaign](../research/corkboard-storage-001-20261128.md) remain the authoritative records of the individual runs.
