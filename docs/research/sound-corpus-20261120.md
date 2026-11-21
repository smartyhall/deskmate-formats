# Sound archive attribution and a native truncated-recording test

Reclassifying the 95 byte-distinct Sound candidates from the
[expanded archive inventory](extended-resume-20261120.md) preserves
all 69 previously accepted DeskMate recordings and instruments. Nine
have the Creative VOC signature, one has RIFF/WAVE framing, and nine
are binary `.MNU` members of the same private
[utility archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/utilities/nlogi32.zip).
Those nine share a leading `1A` and compression-like byte with the early
DeskMate profile, but their first descriptor does not address a sample
after a complete descriptor table. Seven remaining `.SND` files still
go to the candidate review queue, including the truncated recording below.
The replay independently rehashed every input, used the archived name for
extension fallback, and left the live index untouched.

The archive classifier now recognizes Creative VOC by its complete magic
and checks the descriptor-table boundary before assigning the early
DeskMate Sound signature. A `.SND` extension can still nominate an
incomplete file for inspection. The Sound parser keeps its strict
bounds and neither zero-fills nor silently drops missing samples.

## PIPEORGN.SND

The [Music Studio 3 disk 2 archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/wares/Music-Studio-3-for-DeskMate/disk2.zip)
contains a 29,740-byte file with SHA-256
`552a1bbec6c479debde2517f6949459648ee6fedbe344a31c6d5da560f782e78`.
The early Sound header and first descriptor specify one 11,000 Hz
recording, with 33,792 unsigned PCM frames starting at offset 44. The
file contains 29,696 PCM bytes, a shortfall of exactly 4,096 bytes.

The starting disk was the stopped follow-up Sound clone with SHA-256
`3570cc700d0d0f1c92c034451d8e427e36b2dfca7389aa98f20e2eb424096010`.
It ran the RSX OEM 3.04 Sound module under DeskMate 3.05, the
[previously pinned RSX emulator and ROM configuration](sound-native-20261118.md#sources-and-laboratory).
The emulated machine used a 25 MHz 386SX, 4 MiB RAM, internal VGA and
internal PSSJ. The native socket ran all controls with emulated time held
between requests.

| Emulated time | Observation |
| --- | --- |
| 24,860 ms | `DESK SOUND A:\PIPEORGN.SND` reached the earlier-recording machine-choice dialog. |
| 32,944 ms | Enter with the displayed 1000 TL default produced an unexpected end-of-file error. The attempted radio change did not visibly move selection. |
| 35,102 ms | After dismissing the error, Sound displayed a partial waveform and the declared 33,792-frame count. |
| 60,894 ms | File → Save As completed to the distinct `A:\REPROBE.SND` on the disposable working floppy. |
| 67,360–71,618 ms | The native 86Box capture around Ctrl+E on the saved copy yielded 203,519 stereo frames at 48 kHz on the main stream, with peak 3,822 of 32,768. Music stream sample values were zero. |
| 73,797 ms | Returned to DOS, ejected the floppy, and acknowledged socket quit. The stopped hard disk remained byte-identical to its input. |

7-Zip 26.05 recovered both files from the ejected image. The original
matched its input SHA-256. The saved copy parses as the later linked Sound
container and is 33,952 bytes with SHA-256
`4dd2f55c85e0a8379d5602f38d7ca7f1dfdd8b2e87ded1219cf97c9c7a06cf7c`.
All 29,696 present source PCM bytes match its prefix exactly. The last
4,096 bytes are `00`. Unsigned PCM centers at `80`, so these bytes are
neither recovered content nor encoded silence. This is the behavior of
one guest and one error-recovery path.

The two original files, saved copy, audio and screenshots remain in the
private `semantics-20261120` evidence directory. The private
`sound-attribution.json`, `sound-attribution-replay.json` and
`sound-differential.json` retain identities, counts and capture values.
No historical audio has been added to Git.
