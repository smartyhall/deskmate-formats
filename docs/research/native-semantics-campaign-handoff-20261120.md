# Extended native-format research handoff, November 20

The campaign started from integrated main at
`263090892484396022ba291c3c641a3f31d9b64e` and the preserved MidiMapper
Win98 installation. Four focused review branches carry the changes.

| Review | Result |
| --- | --- |
| [MidiMapper semantics, PR 143](https://github.com/smartyhall/deskmate-formats/pull/143) | Verified signed pitches, native converter octave shift, note timing, voices, dynamics and control flow. Added lossless historical syntax recognition and exact rational linear PolyDur projection. Includes 12 additional native MIDI files, one native HDS conversion and five original tool-generated HDS inputs. |
| [Help database, PR 140](https://github.com/smartyhall/deskmate-formats/pull/140) | Attributed the 109-file cluster to DeskMate Help. Two exact resources produced native F1 behavior and a filename-held-out negative. Validated 108 structurally, raising the archive candidate total from 17 to 125 of 157. |
| [Sound attribution, PR 141](https://github.com/smartyhall/deskmate-formats/pull/141) | Separated nine VOC and nine menu collisions while preserving the original 69 accepted Sound files. Confirmed a 4,096-byte source truncation in the native application and measured its separate zero-filled resave. |
| [Draw style word, PR 142](https://github.com/smartyhall/deskmate-formats/pull/142) | Isolated a rendering-relevant word at external-font record offset 54. The Python and browser readers now recognize 385 of 385 surveyed physical descriptors, up from 61. The supported renderer and edit profile remains bounded. Includes the native-opened synthetic control and its provenance. |

No campaign PR was merged. The [Faxback OCR review branch](https://github.com/smartyhall/deskmate-formats/pull/136)
was used read-only for the continuation below.

## Data and runtime continuity

The private `semantics-20261120` evidence directory retains socket
receipts, captures, byte-verified media and reproducible private
analysis. The four working snapshots are:

| Guest | Native clock at acknowledged quit |
| --- | --- |
| `restore-tests/win98se-semantics-20261120` | 853,050 ms after the Win98 safe shutdown screen |
| `machines/rsx-help-profile-20261120` | 125,809 ms at DOS |
| `machines/rsx-sound-corpus-20261120` | 73,797 ms at DOS |
| `machines/rsx-draw-font-padding-20261120` | 62,569 ms at DOS |

The stopped Win98 disk SHA-256 is
`094aad9cae5e1a1d837be378b05cc2243d1c157723ec1b597a1a16aeb425a7f6`.
The startup mount prompted a reset and the later volume swap produced a
Win98 disk retry. The previous export batch had already been extracted.
Subsequent B-drive tests used a distinct volume serial and retained the
old A volume so Win98 could open its last-used path.

The offline Faxback pass backed up the prior OCR database using the
SQLite backup API and resumed the exact 2,000-pixel grayscale Windows
OCR profile on the copy. With minimum catalog ID 10000 and a 36-page
budget it added all 36 pages across 30 documents, raising that profile
to 157 pages across 133 distinct document digests. The profile has zero
outstanding failures. A keyword probe found no DeskMate, WinMate,
Windesk, Express Publisher, Discis, or Multicom hits in the additions.
The text, copied database and differential remain private as
`faxback-ocr-continuation.sqlite` and
`faxback-ocr-differential.json`. The deterministic job finished.

## Remaining controlled experiments

1. **MidiMapper scheduling and program selection.** Repeat the same
   100 BPM, 480 PPQ control with zero Note OFF/ON delay across several
   runs, then change one guest timer or audio setting. Compare the onset
   gaps to the 10 ms run's exact eight-tick change. Independently set a
   nonzero program in the player's channel UI and record the same HDS to
   distinguish UI initialization from the proven in-song raw MIDI commands.
   Separate tie, slur, and legato controls before expanding the projection.
2. **DeskMate Setup Help.** Use a matching setup guest with the exact
   DMSETUP.HLP. Its indexed Text row 16 fills page 10 and row 17 starts
   at the next page. Allowing that boundary in a scratch reader reaches
   a finite route anchored at the first index group. No permutation of the
   four Text columns reproduces that route with the existing prefix model.
   Trace the native topic lookup before changing either validation rule.
   Native F1 tests establish the read-only Help behavior. They did not
   qualify a Help writer. Earlier native Filer mutation controls remain
   available for the separate Filer profile.
3. **Draw font style.** Save the same synthetic label through native Draw
   with one style setting changed per file. Record the exact word and pixel
   diff, then compare with the preserved Cobb word-4 control. Verify that
   unsupported record bytes stay exact through any later editor change.
4. **Sound and archive follow-up.** Look for an independent copy of the
   Music Studio 3 disk member before assigning provenance to the missing
   PCM. Continue the Faxback 2,000-pixel pass from the private copy with
   the same scanner profile.

The [MidiMapper report](midimapper-semantics-20261120.md) includes the
native measurements, workflow and fixture references. Startup and
checkpoint records are in the [usage ledger](../evidence/codex-usage/README.md).

## Verification and closeout

The Help branch's installed-wheel run passed 690 portable tests with
two skips, before the documentation-only correction. The final Music
sources passed the focused HDS, repository audit and isolated installed
package checks. A preliminary Music full suite overlapped source edits
and reported a driver implementation fingerprint mismatch. The
unchanged final code passed the 12-test supervisor-editing rerun.
The final complete local suite was still running at the checkpoint
in the private lab. Its output is recorded in
music-portable-final.log.

The safe-stop usage receipt recorded 90% used in the 300-minute
window and 14% used in the weekly window. The run preserved the
publishable checkpoints before consuming the remaining burst allowance.
