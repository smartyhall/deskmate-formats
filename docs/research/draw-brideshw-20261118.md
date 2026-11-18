# Historical Draw BRIDESHW.FIG arc extent failure

The untouched 6,101-byte OEM figure has SHA-256
`59d76d4a94350adaca1d47423119e23ed6817c2a8e4af658789f01449e4e91bf`.
The retained native screenshot hash matches its transition receipt. Draw
displayed the drawing, but the existing evidence does not isolate the arc
that fails the portable reader.
[Corpus and native observation](audio-historical-corpus-20261118.md#draw-follow-up)

The FIG has a 5,988-byte list starting at file byte 44 and 62 top-level
directory entries. Its two groups contribute 26 further records and have
no shared or nested group references. Top-level entry 34, tag 35, points
to list byte 5,728, file offset `0x168c`. Its type and modifier are
`U/A`. The word at record position +18 is `0017`, which the generic
extended decoder interprets as 46 bytes. Only 44 bytes precede the next
element. The claimed last word would overlap the next element's `UP`
discriminator.

| List byte | Owner and kind | Available bytes | Value at +18 |
| ---: | --- | ---: | ---: |
| 5,684 | Top-level tag 36, `UA` | 44 | 22 |
| 5,728 | Top-level tag 35, `UA` | 44 | 23 |
| 5,772 | Top-level tag 5, `UP` | 192 | 96 |

The DeskMate 3.03 SDK headers `CSRFORM.H` and `CSRBASE.H` identify
`U/A` as an arc. The fixed layout accounts for 44 bytes in total.
The 20-byte extended header is followed by eight attribute bytes, two
16-bit extents and six 16-bit coordinates for the two base points and
apogee. The three words at +20, +22 and +24 of the rejected arc are
`0d0d`, `0100` and `0800` within the inline attributes. There is no
resource pointer in the SDK arc structure. The file's stroke section
contains only the two-byte terminator and its palette is intact.
No separately referenced font, bitmap or stroke resource accounts for
the additional word.

The other 54 arcs in BRIDESHW and all 1,663 arcs in the 204 accepted
historical figures occupy 44 bytes and declare 22 words. Changing only
`0017` to `0016` in a memory copy passed the bounded reader with
88 records and 86 leaves. This isolates the failure to one size word.
The case remains outside strict decoding until the native interpretation
is verified.

For the next native experiment, draw a synthetic standalone arc followed
physically by a distinctly positioned polyline. Verify that their saved
boundaries are 44 bytes apart, change only the arc length from 22 to 23 in
a disposable copy, and compare both shapes on screen and after Save As.
On another disposable disk, Save As the untouched BRIDESHW and compare
this word and its neighboring entries. These controls can distinguish
fixed-layout rendering, skipping the arc and normalizing the size on save.
