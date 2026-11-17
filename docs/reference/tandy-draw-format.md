# Tandy Appendix A: DeskMate Draw format

**Source:** *DeskMate Development System 03.05.00 Development Guide*, Appendix A Draw (printed A-9; operator-supplied PDF p. 482), plus the common header (p. 476) and a Drawlist tool example (p. 470). **Status: manufacturer-documented, not yet verified with a native Draw corpus.** See [crosswalk](tandy-format-crosswalk.md) and [graphical campaign](../research/graphics-cross-application-plan-20261117.md).

## Outer file layout

The guide describes a Draw file as a Page Setup prefix, a graphics-form header and size information, the actual graphics form, then palette entries.

| Zero-based offset | Size | Documented role |
| --- | --- | --- |
| 0–21 | 22 bytes | Common Page Setup file header; see [common header](tandy-common-headers.md) |
| 22–39 | 18 bytes | `FORM HEADER`: identifies/describes the graphics form |
| 40–43 | 4 bytes | `FORM-SIZE-BUF`: size information for form lists and strokes |
| 44 onward | Variable | Serialized graphics form |
| After graphics form | 64 bytes | Sixteen palette entries |

The source gives an end-of-form expression based on the sum of the `FORM-SIZE-BUF` list and stroke counts plus **44**. Treat the exact **inclusive/exclusive boundary** as a verification question: the scanned prose mixes “end of form” and “start of palette” descriptions. Do not infer a one-byte overlap or skip from OCR punctuation.

Tandy directs implementers to the *DeskMate Technical Reference*, Form Manager section, for the definitions of `FORM HEADER` and the graphics form itself. **Appendix A does not define the internal object commands, stroke format, list encoding, coordinate units, or compression.** Do not pretend it gives a complete Draw parser.

## Palette

The final palette section is described as **16 × 4 bytes**. Each entry has a one-byte palette/color number, followed by three one-byte red, green and blue values (0–255), in that order. This is **not** evidence of an alpha channel; the first byte is a color index.

The guide calls the first through sixteenth entries COLOR1 through COLOR16. Native output should determine whether these indices are constant, change when the user changes the palette, or are stored in a display-hardware-specific numbering.

## Related representations

- **Text:** The manufacturer's [Text format](tandy-text-format.md) says a Draw picture copied into a Text paragraph is stored between length-delimited picture markers. Its payload is passed to `vid-draw-form`. It may correspond to the Draw form **without** the file header or trailing palette. This is a *hypothesis to test*, not a guaranteed identical byte range.
- **Form Setup/Filer:** Its [GRAPHICS representation](tandy-filer-format.md) is reportedly ASCII-compatible encoding of binary graphics. Compare a **decoded logical payload** if the encoding is discovered, not only raw .FIL data against raw Draw files.
- **Drawlist utility:** Elsewhere (PDF p. 470), Tandy describes copying a Draw graphic to the clipboard and using Drawlist to save a generated C array. If the development-tool utility is available, it offers a possible fourth representation of the form/clipboard payload. Do **not** publish proprietary tool binaries; synthetic output may be eligible under the project's evidence policy.

The source documents an additional application identifier `DRAW88` (`0x14`) alongside Draw (`0x10`) but does not explain compatibility or distinct formats. Preserve that as an unresolved version/profile question.

## Native test matrix

Generate, through the real installed Draw application, an empty file, a single short line, the same line moved and resized, a rectangle, a different primitive, a color/style variant, two objects, and a deletion. Capture exact parent hashes, actions, saved bytes, reopen verification and repeat-save control.

For each file:

1. Verify identifier and PGSETUP at offsets 0–21.
2. Inspect the alleged FORM HEADER and FORM-SIZE-BUF at 22–43 without assigning undocumented fields prematurely.
3. Determine the graphics-form boundary and check for exactly 64 trailing palette bytes.
4. Change coordinates or color in one controlled operation and map binary differences to candidate form/palette regions.
5. Copy at least one drawing into Text as soon as the Draw corpus exists; compare its embedded picture span against the **inner** Draw form.
6. Compare one native Form Setup graphical element against the same Draw element, allowing for different outer containers and encoding.

**Implementation scope:** A bounded read-only inspector of header, size, opaque form span and palette is a reasonable first vertical slice. A fully general vector interpreter or image renderer requires additional evidence.
