# Historical Draw inventory at PR #120

The [machine-readable inventory](../evidence/draw-corpus-pr120-20261119.json)
rechecks the 206 distinct figures in the
[2026-11-18 archive set](audio-historical-corpus-20261118.md#draw-follow-up).
It records file hashes, sizes, archive identifiers, aggregate record features
and strict-reader outcomes. It contains no artwork, label strings or private
lab paths. Reproduce against the historical extraction with
[draw_corpus_inventory.py](../../tools/experimental/draw_corpus_inventory.py)
and the package imported from the PR #120 worktree
(`5e1b24f8d8d262ac165b125474f7807163afbcc1`).

| Measure | Count |
| --- | ---: |
| Signature `14 46 49 47` | 206 |
| Strictly readable by the PR #120 codec | 204 |
| Documents projected to SVG | 204 |
| SVG projections with one or more omitted records | 178 |
| Rendered leaves | 6,970 |
| Groups | 374 |
| Figures with groups | 132 |
| Maximum group depth | 4 |
| Physical records with nonzero fractional coordinates | 5,503 |
| Physical records with a negative integral coordinate | 4 |

The 204 accepted files contain 3,253 line, 1,071 ellipse and 841
rectangle records. Of 1,797 `UP` records, 262 carry open flags,
63 are closed without fill and 1,472 are closed with fill enabled
under the measured interpretation. The inventory preserves flag byte
distributions. The historical record hierarchy does not, on this evidence
alone, distinguish every native tool mode that generated a `UP`.

The top priority omissions by record count are 1,663 `UA` arcs, 380
external-font references, and 109 `B` records (the SDK calls this a bevel).
All accepted arcs occupy the documented 44-byte extent. Thirty-three
have collinear or repeated defining points under an unsigned reading of
their local coordinates. The codec recognizes six Cobb references and
leaves 374 unresolved. Three documents contain parsable embedded stroke
banks with 50 glyph records altogether. The projection omits 42 of 50
embedded-stroke text records and four records with type byte `aa`.
Patterned fills, line styles and widths can affect thousands of additional
visible elements even when their basic geometry projects successfully.
The statistical inventory counts attributes and reserved bytes separately
from the renderer's interpretation.

The two strict failures reproduce the previous diagnoses. PIPES fails
the display-list group reference checks. BRIDESHW has the one-word arc
length disagreement. Their untouched inputs remain private. See the
[PIPES](draw-pipes-20261118.md) and [BRIDESHW](draw-brideshw-20261118.md)
investigations.

The [follow-up inventory](../evidence/draw-corpus-arcs-20261119.json)
keeps the strict result at 204 of 206. Explicit arc recovery admits
BRIDESHW, bringing the qualified read count to 205. PIPES remains
outside strict and recovery decoding. The updated scalable projection
renders 8,704 leaves across those 205 figures and reports omissions in
122 figures. Twelve arcs retain unsupported extents. The follow-up
inventory binds the same ordered source hashes and records the recovered
list offset independently of the renderer output.
