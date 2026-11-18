# Historical DeskMate audio and Draw comparators

On 2026-11-18 the Oldskool DeskMate index and the corresponding archive
directory worked over HTTP. HTTPS to the same hosts did not connect during
the initial checks. The private archive preserves the HTTP downloads,
including all 13 named specimen archives, two Music and Sound manuals,
utilities and vendor release media. The archive receipt lists the URLs,
sizes and SHA-256 hashes. [DeskMate index](http://www.oldskool.org/guides/tvdog/deskmate.html) ·
[Tandy 1000 archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/) ·
[Retrieval receipt](../evidence/audio-historical-corpus-20261118.json)

The private lab directory `C:/DeskMateLab/private-evidence/audio-native-20261118`
contains the original ZIPs, indexes and documents. `archive-catalog.json`
records each original archive and normalized internal file path, size, SHA-256
and signature probe. `comparisons.json` groups identical extracted bytes
across releases and collections. The primary extractor verified ZIP member
lengths and CRCs and rejected unsafe paths, symlinks, duplicate paths and
oversized expansions. For an old ZIP compression method unsupported by
Python, 7-Zip supplied selected members and their bytes were checked against
the original directory CRCs. The vendor floppy contents and derived audio
and SVG previews remain in the private directory.

## Audio comparators

| Archive leads | Verified material |
| --- | --- |
| `canon.zip`, `dm2tun.zip`, `oldies.zip`, `tandysng.zip`, `creepy.zip`, `barq2.zip` | Music scores with the `0C SNG` signature. The sets include byte-identical repeats and same-name differences. The index credits Kenneth Udut for CREEPY and attributes the composition of CANON to Johann Pachelbel. |
| `pdm2.zip`, `pdm2musi.zip` | Personal DeskMate 2 Music and historical songs. The four bytes of the main score signature agree with the later files. |
| `banjo.zip`, `beamup.zip`, `thnder.zip` | Earlier Sound table profile, music-compressed. BANJO is assigned to instrument 6. BEAMUP and THNDER are recordings, with BEAMUP identified by the index as a Star Trek effect. |
| `janna.zip` | Earlier uncompressed recording with a 19-byte unassigned tail after its declared audio region. |
| `marimba.zip` | Later linked profile, four music-compressed samples assigned to instrument 6. |
| `rsxdisks.zip`, `1000RLX_HD-B.zip` | OEM application modules, audio resources, demonstration compositions and samples. The two archives supply byte-identical Sound and Music modules. |
| `d1000tl2.zip` | Tandy TL/2 system-disk collection. Disk 4 supplies older Sound and Music executables, earlier copies of Clarinet, Piano, Bells and Cello, and score comparators. Several sample streams differ from the later RSX instrument with the same name. |

There are 21 Sound occurrences and 16 unique files in the catalog. Eight
use the original table (one PCM and seven music-compressed). Eight use the
later linked container (two PCM, five music-compressed and one
speech-compressed). Both profiles pass the bounded Sound reader and PCM
extraction on all 16 files. The 90 Music occurrences reduce to 62 unique
files. All 62 pass the same four-stream structural reader, and 15 pass
the conservative MIDI projection. Header bytes and optional alignment
and trailing bytes distinguish subprofiles. Song
identity cannot be determined from the basename alone. See the audio
research reports for the narrower playback and MIDI claims.
The [Music control inventory](music-control-inventory-20261118.md) ranks
the remaining event families and records their placement by stream.

## Documentation and converters

- Jeffrey L. Hayes describes the original Sound table and, with information
  provided by John Ball, the later linked profile. The tables identify
  stored offsets and lengths, and distinguish unsigned PCM from both
  compression modes. Hayes also describes Conv2snd 2.00 and Snd2wav.
  The original Conv2snd package remains unverified in this collection.
  [Historical Sound format notes](https://nagasm.org/ASL/sound05/index.html)
- Tandy's Music and Sound manuals describe notebook controls, samples,
  pitch/range selection and sustained sections. Their glossary and option
  descriptions explain voice, instrument and title fields observed in the
  native application. The two original PDFs remain in the lab.
  [Music and Sound manual archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/musicsnd.zip) ·
  [1989 manual archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/deskmate/mussnd89.zip)
- `dm_music.zip` contains W. Baldwin's 32-bit Visual Basic converter,
  developed with Hayes, and its readme through version 1.04. The author
  lists support for tempo, key and time signatures, repeats, score markers,
  dynamics and instrument slots. The notes distinguish Personal DeskMate
  2's stock slot meanings from the later sampled instruments. Conversion
  parity and licensing remain open. [Baldwin's 2006 announcement](https://groups.google.com/g/comp.sys.tandy/c/fq1OO44yLtI) ·
  [Preserved converter](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dm_music.zip)
- Hayes's Dmsound 0.7 documentation lists compressed/uncompressed Tandy
  SND and WAV conversion. Its DOS and DeskMate packages, Tandy sound
  programming toolkit materials from `tandysnd.zip`, and the
  `tsampler.zip` utilities were inventoried as possible further oracles.
  No third-party code or binaries are included in the project.
  [Sound tools directory](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/)

## Draw follow-up

The 10 named-archive graphics have the `14 FIG` signature. The current
Workbench exported nine into private, verifiable SVG bundles. Enterprise
`NCC1701.FIG` opens through the Draw reader, with omissions and style
approximations reported in the bundle. `PIPES.FIG` reaches the
display list but fails with a duplicate/cyclic group reference.
Of 206 distinct drawings including vendor examples, 204 pass the structural
reader. The other failure is the OEM `BRIDESHW.FIG`, whose extended
element exceeds the reader's record bounds.

| Private member | Bytes | SHA-256 |
| --- | ---: | --- |
| `ncc1701/NCC1701.FIG` | 9,787 | `eac0be87b4f10b4b4ca39df07f4e5516b896501eb1766141c3b4107449664623` |
| `pipes/PIPES.FIG` | 7,521 | `34b0389df187edbd4618c4561c8843b2928acec39fdaf5eea643a82b3987f5c6` |
| `rsxdisks/DISK4/DOCUMENT/NOTICES/BRIDESHW.FIG` | 6,101 | `59d76d4a94350adaca1d47423119e23ed6817c2a8e4af658789f01449e4e91bf` |

The installed Draw opened and visibly rendered both PIPES and BRIDESHW from
the untouched floppy inputs. These are useful reader-coverage cases. For
PIPES, compare the native tree and group ownership to the rejected reference
path before loosening the cycle check. For BRIDESHW, inspect the record
size and the resource it references. Use NCC1701, ARAZI, CASTLE,
GIFCERT1, GIFCERT2, HHEELLPP and the three `stuff.zip` illustrations as
private picture comparators for fill, embedded strokes and grouping. Their
Workbench manifests and SVGs live in `draw-comparison`. Match any public
regression fixture to a newly drawn synthetic control.
