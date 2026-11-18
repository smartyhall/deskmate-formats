# Historical Draw PIPES.FIG reference failure

The untouched 7,521-byte input has SHA-256
`34b0389df187edbd4618c4561c8843b2928acec39fdaf5eea643a82b3987f5c6`.
The existing native evidence shows a drawing on screen. The portable reader
reports a duplicate or cyclic group reference. The screen does not resolve
which group members Draw actually traversed.
[Corpus and native observation](audio-historical-corpus-20261118.md#draw-follow-up)

## Reference graph and physical records

The 7,408-byte list starts at file byte 44. Offsets below are list-relative.
The directory has one entry, tag 199, pointing to the `OO` at byte 6.
Its 197 word-offset slots occupy bytes 26–419. The first physically adjacent
child starts at byte 420. The 192 other valid-looking references resolve
to distinct leaves, with a single owner and no nested group edges or
reference back to the root. Five consecutive slots account for the failure.

| Zero-based slot | Stored word | Doubled target | Observation |
| ---: | ---: | ---: | --- |
| 90 | `4dbe` | 39,804 | Outside both the list and the file |
| 91–94 | `06b1` in each | 3,426 | Inside the 44-byte `UA` arc beginning at 3,400 |

The next genuine record boundary after 3,400 is 3,444. The false interior
boundary would therefore also truncate that arc. Suppressing duplicates
alone leaves both an out-of-range pointer and an interior pointer.

The physically consecutive region from 5,344 to 5,552 holds exactly five
unreferenced late records. It begins immediately after the valid 44-byte
arc referenced by slot 89. A bounded walk from 5,344 finds three-point
polylines at 5,344 and 5,392, a rectangle at 5,440, and arcs at 5,464
and 5,508. Their measured lengths are 48, 48, 24, 44 and 44 bytes. This
lands on the next referenced record at 5,552 with no gap.

Substituting those five offsets in ascending physical order for slots 90–94
in memory made the existing reader accept 198 records and traverse 197
leaves. This localizes the inconsistency to those slots. Physical adjacency
and a successful parse leave the intended draw order and native behavior
open. The source bytes were preserved and the reader retains its validation.

## Native discrimination

On a disposable disk, Save As the untouched input, reopen it, and compare
the group slots against the original. Repeat after Break Object, if
available, to see which elements become top-level entries. Capture native
screens and compare with a private copy containing the five candidate
references. Use an overlapping synthetic group as a control for display
order. The stored Form Setup Ghidra findings concern graphics escapes,
so they do not establish the Draw group traversal path.
