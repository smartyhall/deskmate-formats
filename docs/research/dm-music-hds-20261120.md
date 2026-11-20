# DM_Music 1.04 and HDS conversion controls

## Distribution and playback lineage

The intact TVDog `dm_music.zip` accession is 24,629 bytes with SHA-256
`3f25b8f3367659fc89abd8617a5d4dc9e448e6ee5de51aec5d7f02c0402db902`.
It contains `DM_Music.exe` (77,824 bytes, ZIP timestamp 2006-12-31) and
`DM_Music_Readme.txt` (7,854 bytes, ZIP timestamp 2007-01-14). Their
SHA-256 values are respectively
`b84f1a9a9dab3252c6c85127a7c9d25f68c0cde53a572ede80a4674230a02150` and
`14c9bbd21742d42d736ed8c7befaade0a35e2c694729b53df298b0cd9c8cb0d2`.
The author credits W. Baldwin and J. Hayes. The readme describes VB
runtime service pack 5 and the original release thread identifies Windows
95 or later. The measured lab combination is Windows 98 SE with the
Microsoft VB6 SP6 runtime.

Version 1.01 added source comments. Version 1.02 corrected batch state,
added octave adjustment and emitted meter, key and tempo controls.
Version 1.03 moved tempo changes into the notes section and set the
default header to pace 100 with 4/4 meter. Version 1.04 added instrument,
dynamic and score-marker output. Baldwin reported converter 1.05 and
MidiMapper 6.19 by March 2007, and MidiMapper 6.49 in August 2015.
Those later binary releases were not recovered here.

The companion MidiMapper was an instrument simulator, HDS editor and
MIDI player. Baldwin documented MIDI file export by version 6.9 and
tempo changes from the earlier 5.4 release. The 1.04 readme documents
constraints on consecutive repeat starts and alternate endings in nested
repeats. The author also reported a player default dynamic of `p`,
versus DeskMate's documented `mf`. These are documented player
behaviors pending direct verification. The mirror's converter ZIP
contains no player. The announcement names FortuneCity, Voyager and
later Comli as acquisition leads.

[Original converter accession](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dm_music.zip) ·
[Baldwin's release thread](https://groups.google.com/g/comp.sys.tandy/c/fq1OO44yLtI)

## Executable evidence

The pinned binary is a native x86 Visual Basic 6 build in a 32-bit PE.
`VB5!` at file offset `0x2100`, the
entry point's push of VA `0x402100`, and the `MSVBVM60.DLL` imports
identify the runtime. Native x86 indirect calls to `__vbaFileOpen` and
`__vbaGet3` at `0x405064`/`0x4050c0` and `0x4063e3`/`0x40649c`
identify candidate input code. A third open site at `0x40e3d3` lies
near a `__vbaPut4` call at `0x40e40b`. Those sites are pointers for
further tracing. Their exact roles in SNG parsing and HDS writing
remain unverified. The PE resource tree has three icon entries, one
icon group and one version entry. VB forms need separate inspection
of the VB project structures.

## Native converter run and differential

The authenticated 86Box socket controlled an independent clone of the
VB6 runtime checkpoint with all network links down. The first disposable
FAT12 staging image mounted at A: contained 25 uniquely named SNG inputs
and the pinned program. Each source matched a Git fixture and parsed
independently. The source manifest distinguishes original DeskMate saves
and tool-generated controls. The directory conversion ran at octave +0.

The converter showed a 25-file confirmation at 131,994 emulated ms.
Later frames kept the final input visible and left Convert disabled.
An Alt+F4 closed the app and the following observation showed the
desktop at 216,506 ms. After floppy release, 7-Zip 26.05 extracted all
25 exact CRLF outputs, totaling 5,897 bytes. The first staging script's
8.3 truncation collapsed several intended long names before the run.
The retained DOS-name map identifies every file actually submitted.
The region-hold case did produce output. The unchanged conversion
frame alone had led to a mistaken preliminary stall diagnosis.

The second batch used collision-free 8.3 aliases, copied 35 verified
controls to `C:\HDSLAB`, and converted at octave +0. The 35-file count
was visible at 263,846 emulated ms. The guest shut down normally and
native quit was acknowledged at 300,620 ms. PyFatFS 1.1.0 recovered all
35 outputs from the stopped FAT32 image, totaling 10,298 bytes. This
batch also restored the intended coverage of the chromatic and cadence
controls. The stage maps and all 60 original export instances are private.

The two batches covered 36 distinct input fixtures. The first batch added
24 publishable outputs and the second added eight. One first-batch export
matched the published duration/tempo fixture byte-for-byte. Repeat runs
on already published inputs produced the same ordered event lines. The
32 new outputs are in the [application-generated fixture manifest](../../tests/fixtures/application-generated/manifest.json).
All 60 exports had equal per-voice note/rest duration sequences in the
independent SNG projection and HDS parsing. The observations include independent
durations in a three-voice row, quarter-note triplet members, dots,
double dots, rests, mid-score meter and tempo changes, key signatures,
repeats, score markers, instruments and dynamics. Tie and slur control
rows both use `Sb` and `Se` delimiters. The region-hold control becomes
a whole-note `C3` with no explicit region field in its HDS export.

Paired source events identify `A-3` with MIDI 57, `B-3` with 59, `C3`
with 60, `A3` with 69, and `C+2` with 72 in this converter's output.
The chromatic controls cover all 12 pitch classes from MIDI 60 through 71.
The minus and plus labels are preserved as written. A standard MIDI
octave parser would interpret these spellings incorrectly. The paired
correspondence describes conversion and awaits a MidiMapper playback or
MIDI-export measurement to establish the player's interpretation.

The `deskmate_formats.hds` reader retains the exact source bytes and each
line, including unknown constructs. It projects written note/rest
durations as fractions of a quarter note, typed commands and per-row
slots. It keeps connection modifiers and pitch labels visible. This
reader has no repeat expansion or HDS-to-MIDI pitch mapping. The native
screens, floppy and differential receipts stay under the private
`extended-20261120` evidence root.
