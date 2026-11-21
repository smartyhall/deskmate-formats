# Draw external-font style word at Uf +54

A byte-verified scan of the expanded TVDog Draw population reached 385
physical `Uf` records. The previous descriptor reader recognized 61.
In all 324 other cases the only rejected field was a word at byte 54
relative to the record start, after the family name's NUL. The measured
word distribution was 4 in 285 records, 12 in 28, 6 in 9 and 128 in 2.
The names were Marin in 220, Dixon in 103 and Cobb in one.

The earlier [descriptor notes](draw-fonts-20261119.md) described the
30-byte region at 26–55 as the name and its padding. A comparison in
native Draw shows that the word at 54 can affect rendering.

## Native controls

The experiment cloned the earlier typography machine with hard disk
SHA-256 `5fa0f78f88989b68eaa0f32e765d1d130f22df5eb63fd71725aa21812386989d`.
It ran DeskMate Draw 03.05.00 on the RSX at 25 MHz with internal VGA,
4 MiB RAM and serial mouse, using the [pinned 86Box and ROM build](rsx-dos5-baseline.md).
The display captures and controls were through the authenticated native
socket. No native font resource was changed.

- The baseline synthetic Cobb label was the exact published `d23.fig`.
  It opened at 23,090 ms. A disposable copy added seven ASCII bytes
  after the first NUL at record offsets 31–37 and left word 54 zero.
  It opened at 32,894 ms. The 265,600 RGB viewport pixels from
  x=0–639 and y=65–479 were byte-identical.
- A historical 345-byte Marin specimen had the word 4. The unmodified
  file opened at 41,890 ms. A private comparison zeroed only that word
  and opened at 51,640 ms. The two viewports differed by 434 pixels,
  all in the label region. Their original source remains in the
  private archive at SHA-256
  `e737348dce98eaf38157b081ca449e02a1ef2fe47524b5aaaab2bab31733f810`.
- The synthetic candidate changed only the same word to 4 at file
  offset 104. It opened at 60,790 ms. Compared with `d23.fig`, 908
  pixels changed in the label region in the same viewport. 7-Zip
  verified the original candidate bytes after ejection. Native quit
  was acknowledged at 62,569 ms.

This demonstrates a rendering difference for the word 4 under two
faces. The exact meaning of its bits and the visual behavior of 6,
12 and 128 remain unmeasured. The ignored-padding differential
is limited to the tested seven-byte position and synthetic label.

## Reader behavior

The Python and offline browser readers expose the family and original
style word for the four measured values. The relevant text and original
record remain available. Exact outline rendering and editing still
require a supported style. Known style words now receive a specific
omission. The projection with explicit generic font substitution
remains available as an approximation.

The `cobb-style-flag4-tool-generated.fig` fixture in the
[application fixture manifest](../../tests/fixtures/application-generated/manifest.json)
is the actual byte-verified input. It is independently authored from
the pinned synthetic d23, with native open and rendering observed.
The private screenshot and disk artifacts remain under
`semantics-20261120`. The four original featured scalable previews
were regenerated with the same inputs. Their SVGs and omission
counts matched byte-for-byte, so their existing comparison baselines
remain the applicable references.

The next controlled experiment is to author the same original string
with one native Text Style switch changed at a time, save each result
and compare the word and viewport. That can identify the flag bits
before changing any glyph interpretation.
