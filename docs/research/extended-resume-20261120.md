# Extended campaign continuation, November 20

## Checkpoints and review branches

The checkout started on `codex/historical-os-20261120` at `401b2b0`.
Fetch and GitHub inspection showed PRs 129–135 open. PR 134 targets
the roadmap branch of PR 132, and PR 135 targets the archive branch of
PR 131. The only working-copy edit on the historical OS checkout was
the unfinished update and driver narrative. It is now preserved in
commit `38a1a26` on [PR 133](https://github.com/smartyhall/deskmate-formats/pull/133).
The resumed campaign did not merge review branches.

- [Windows 98 restoration](win98se-restoration-20261120.md) records the
  recovered update completion, cumulative per-file observations,
  stopped checkpoint, Creative Sound Recorder result and catalog seed.
- [DM_Music analysis](dm-music-hds-20261120.md) records both offline
  batches, 32 newly published HDS fixtures, executable findings and the
  lossless HDS reader. The branch `codex/dm-music-hds-20261120` targets
  the Windows research branch, which carries its four original fixtures.
- `130e7d5` on [PR 136](https://github.com/smartyhall/deskmate-formats/pull/136)
  adds OCR and reviewed product relationships. `880cf41` on
  [PR 137](https://github.com/smartyhall/deskmate-formats/pull/137)
  adds the ARC decoder adapter and measured reingest. Both target the
  archive branch of PR 135.

## Corpus triage and native evidence

A digest-verified replay of the existing candidate inventory reproduced
the structural totals. The private receipt keeps nested member paths
and all occurrences per identity. It records application/version
attribution when established. No population received native opening,
display or Save As acceptance from this replay.

| Population | Investigation after replay |
| --- | --- |
| DMDB | 17 accepted of 157. All 109 rejected at `0x0464` had the expected `03` marker and a compact nonzero tail immediately after it. The three observed spans were 6 bytes (76 files), 8 bytes (25) and 12 bytes (8). All 109 contained `DBCOLS` and lacked the other measured table names in the first directory page. The tail could encode a related database profile. Its meaning and application attribution are open. |
| Worksheet | Seven accepted of 39. Among rejects, 20 began with BOF record prefixes consistent with a non-DeskMate worksheet family. Ten carried the DeskMate signature. Seven of those had a short declared length. Truncating to that boundary left an unterminated string in each. Correcting the length in a private in-memory probe exposed unresolved string or text-block errors in all seven. |
| Sound | 69 accepted of 95. Nine rejects carried the Creative VOC signature and one carried RIFF/WAVE. Nine had the early DeskMate marker byte but out-of-profile sample counts and rates, which require attribution. One plausible original-layout recording reached an invalid sample bound. |
| Draw | 228 of 231 rendered to SVG. Of those, 143 had reported omissions. The largest groups by omitted element were invalid external font descriptors (322), unsupported glyphs or rotation (176), unsupported elements (116), unresolved external font references (61) and unsupported arc extent (17). The three parser failures concerned group references, an extended record boundary and file size. These results measure independent previews. |

Seven additional Windows and converter frames were visually reviewed
and measured privately. Six are 640×480, and the updated System
Properties exemplar is 800×600. The records cover menus, focused
confirmation, the disabled/enabled Convert transition, a file dialog
and the shutdown controls. Decoded RGB distinct-color counts range
from 112 to 325. These are framebuffer colors. The measured frames supplement
the existing visual evidence inventory.

## Private continuation material

Under `C:/DeskMateLab/private-evidence/extended-20261120` the incoming
and resumed evidence includes `win98-security-disk-comparison.json`,
`win98-update-guest-logs`, `dm-music-first-differential.json`,
`dm-music-retry-differential.json`, both DOS-name maps, exact HDS exports,
`native-population-resume.json`, `native-rejection-triage.json`,
`draw-corpus-preview.json`, `faxback-ocr-resume.sqlite`, `arc-eval.sqlite`
and `visual-resume-exemplars.json`. The baseline and the updated Windows
checkpoint are under `C:/DeskMateLab/checkpoints/win98se`. The runtime
working clone remains in `restore-tests/win98se-dm-music-resume-20261120`
with the second batch's FAT32 files. Both owned emulator runs reached
normal shutdown before native quit. The bounded OCR and ARC runs finished.

## Verification at handoff

Targeted checks passed for 86Box checkpoint/control, HDS, OCR and ARC.
REUSE, repository audits and isolated wheel/sdist builds passed. The
32 staged HDS blobs matched the original output SHA-256 and size. All
three final distribution pairs excluded the research formats and the
HDS distribution included the reader.

The local 636-test run used the source checkout and produced one failure
and two skips. Its failing supervisor test launches an isolated Python
subprocess, which could not import from the source-only `PYTHONPATH`.
That test passed when rerun using the prior installed-wheel test
environment. In hosted CI for `38a1a26`, one Windows Python 3.14 job
timed out in the existing Appraiser PowerShell deployment test. The
separate test result and failing job log are retained. Review hosted
checks on each branch before integration.

## Open experiments

- Restore and smoke-test the new 04 checkpoint. Acquire verified late
  Windows Update packages for the separate end-of-support environment.
  IE6-only and earlier maintenance configurations remain separate targets.
- Compare the same WAV in Sound Recorder and Media Player on a cold boot
  of the existing Creative trial and the stock and VB6 controls. Add
  MIDI/FM after establishing repeatable wave device behavior.
- Recover MidiMapper and compare its MIDI export with the measured HDS
  labels. The native player and a full VB6 IDE distribution are still
  missing from the qualified environment. Absolute playback pitch,
  boundary notes, empty inputs and octave-offset behavior remain open.
- Stage representative DMDB tail spans, one DeskMate Worksheet with a
  suspect string pool, and the Sound sample-bounds case in disposable
  guest directories. Record native opening and Save As before changing
  parsers. Draw's external font descriptor cluster and PIPES repaint
  remain separate core investigations. No new sampled-renderer or Draw
  fidelity milestone was produced.
- Continue OCR using the existing private database and preserve the
  two measured rendering profiles. Eight ZIP and six MZ/SFX analyses
  remain partial after the ARC reingest. WinMate and VIS still have
  preserved optical and resource evidence from PR 135 plus the new
  WinMate product links. Period-correct native execution, application
  lineage and VIS runtime attribution remain open. No new site or
  documentation migration was started.
