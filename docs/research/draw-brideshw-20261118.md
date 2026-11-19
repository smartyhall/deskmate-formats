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

## Native reopen and size-word control

On 2026-11-19, Draw 03.05.00 opened the untouched historical FIG and saved
`BRDSAVE.FIG` on a disposable clone. The resave is 6,101 bytes, SHA-256
`97b2da2ea6d7627d499a4324e0a11eed67aabe01607e982b06a9774b05335b87`.
Only six bytes changed, at file offsets 32, 36–39 and 292. The arc still
declares 23 words and still occupies 44 bytes. The untouched source,
native resave and private one-word-corrected copy reopened natively with
byte-identical 640 × 418 drawing crops in the Normal viewport.

The independent synthetic candidate contained a 44-byte `UA` record at
list byte 10 followed by a visibly distinct 20-byte line at byte 54.
Native Save As preserved both records. The stopped-disk extraction
confirmed a 22-word declaration at file offset 72. The next test staged
that result and a second copy with only file byte 72 changed to 23. Draw
showed both the arc and line in both files. They and the native resave of
the 23-word variant had identical native drawing pixels. The native resave
preserved all 187 candidate bytes. 7-Zip and the direct FAT16 reader
agreed on the extracted figures in both trials. The source controls are
in the [fixture manifest](../../tests/fixtures/application-generated/manifest.json).

For these controls, the visible operation uses fixed arc geometry across
the 44-byte boundary. Native Save As preserves the declared size word.
Strict decoding still rejects the disagreement. Draw's opt-in
`recover_arc_length=True` or `--recover-arc-length` qualifies one
23-word declaration in a 44-byte `UA` followed by a valid line or
polyline record. The directory, child ownership and remaining lengths
receive the usual validation. The reported recovered offset identifies the
affected original record, and the original size word remains available.
