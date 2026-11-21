# MidiMapper 6.38 on Windows 98 SE

## Acquisition

The operator-provided private accession has the original filename
`MidiMapper.zip`, size 440,568 bytes and SHA-256
`323a06e1ae757de09ac25721d94a29ac7bbb1d4038d91cd74cdcdaee2dad798b`.
The modern Windows host downloaded and verified those bytes before
extraction. The original archive, acquisition receipt and extracted
members are retained under the private lab's
`downloads/intake/midimapper-20261120` directory.

The ZIP contains the VB6 setup bootstrap, setup list, PAD XML and a
376,253-byte cabinet. 7-Zip 26.05 extracted 46 cabinet members. They
include the setup engine and uninstaller, VB6 setup toolkit DLL, the
MidiMapper executable, `midifl32.ocx`, the HTML manual, three GIFs,
two BMPs, the `Guitar.frt` and `15-14B.dlc` instrument-definition
files, and 33 HDS files including a guitar tuning control. The full
per-member names, byte counts and SHA-256 values are retained privately
in `private-evidence/midimapper-20261120/distribution-inventory.json`.

The application PE version resource reports 6.38. The setup list
still declares version 6.25.0.0 for that file. The PAD lists 6.12. The MIDI control's
resource reports 1.10.005 and the setup list specifies self-registration
under the Windows system directory. The manual describes the Visual
Basic runtime (SP5 at the time of writing) and the File menu's HDS
to MIDI export.

The source score and the DM_Music control export are documented in
the [DM_Music research notes](dm-music-hds-20261120.md). The
[Windows 98 restoration](win98se-restoration-20261120.md) documents
the offline VB6 SP6 checkpoint.

## Native installation

The lab restored the sealed VB6 SP6 checkpoint using its four-file
SHA-256 inventory and a verified read-only Windows CD. The independent
clone used 86Box 7.0, an ASUS P/I-P55T2P4, Pentium MMX 200 MHz, 128 MiB
RAM, S3 ViRGE PCI and Sound Blaster 16 PnP. All four guest network links
were down. The original 4,294,950,912-byte disk hash was
25dadd27d0bb0cf13ada9e6918d03f785a0d0044d20fbf1e6d05d38823ec9223.
The launcher's initial readiness read timed out. A fresh authenticated
status confirmed the same owned process was held at 0 emulated ms and
the desktop was observed at 42,000 ms.

The original setup EXE, LST and CAB were staged without altering their
contents on a disposable VFAT floppy with the cabinet's long name. The
installer ran from A: with the default installation directory and
program group. It reported success at 104,638 emulated ms without a
restart or a separate runtime prompt. The installed program opened
its MIDI device chooser at 113,771 ms. The selected output was
Creative Music Synth [220] and the input list showed SB16 MIDI In [330].
The cabinet executable imports MSVBVM60.DLL and has fixed file version
6.38.0.0. The native install and launch receipts and screenshots are in
the private campaign evidence directory.

## Major-scale playback and MIDI export

MidiMapper loaded the 383-byte synthetic `major-scale-dm-music-1.04.hds`
from `A:SCALE.HDS` at 118,468 emulated ms. Its source is the 124-byte
`listening-major-scale-v1.sng`. The input hashes are respectively
`64731a55b2a583045eaccddb066b2194e941912445c589dd93b9f826a41e52e1`
and `6844bba6fe94c9de220ff8a05251e14ad666af6150b225b2e2c5e865b8ea436f`.

File > Save as .mid file wrote `A:SCALE.MID`. Recording used Creative
Music Synth [220], 100 beginning BPM, 4/4, 120 ticks per quarter and
blank optional text fields. Tempo changes were written as tempo meta
events and silent mode was unchecked. The app highlighted the active
note on the staff and the positions on the fretboard and keyboard at
124,784 ms. The native music stream captured 584,743 stereo frames at
49,716 Hz from 123,405 through 135,184 emulated ms, with a peak of
−41.15 dBFS and RMS of −50.59 dBFS. The separate main stream was
silent. This verifies playback through the emulated music stream
during recording. The staff and instrument views showed the currently
sounding note within a reference range. A paginated score display was
outside the observation.

7-Zip 26.05 extracted the 374-byte [native MIDI export](../../tests/fixtures/application-generated/midimapper/major-scale-midimapper-6.38.mid)
from the ejected FAT12 image. Its SHA-256 is
`84b3a65d1a59762dfff3d2a452423bdbb774644ed00ae0e25639c7e7b2a049f9`.
The historical application attribution text is ordinary metadata in
the unmodified export. The repository audit allows this exact
manifest-checked path. The wheel and sdist exclude MIDI fixtures.

Mido 1.3.3 independently parsed an SMF type 1 with two tracks. Compared
with the independent SNG projection:

| Field | Source score | MidiMapper export |
| --- | --- | --- |
| Pitch order | 60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60 | Exact match, all on wire channel 0 |
| Note length | Fourteen quarters and one half | Fourteen durations of 121 ticks and one of 241 ticks at 120 PPQ |
| Onsets and rest | One quarter apart, followed by a closing quarter rest after the half note | First onset at 56, later onsets 122 ticks apart, final note off at 2,005 and track end at 2,007 |
| Tempo | 100 quarter-note BPM | 600,000 µs per quarter at ticks 0 and 56 |
| Instrument | SNG instrument slot 9, preserved as HDS instrument number 9 | Program 0 on wire channels 0–2, including the channel with notes |
| Dynamics | mp then mf | Velocity 77 on the fourteen quarter notes, 90 on the final half note |

The export establishes `C3` = MIDI 60 and `C+2` = MIDI 72 for this
player. The 1-tick length increase, recurring 2-tick onset increment
and program selection are observations of this recording mode. This
run does not attribute them to an internal algorithm. The tested
file contains no `A-3`. Its MIDI 57 correspondence in the DM_Music
conversion remains to be tested in the player. The next targeted
control is `batch-listening-minor-scale-v1-dm-music-1.04.hds`,
followed by an instrument-selection differential if needed.

The private campaign directory retains `install.img` with SHA-256
`b8f22aa147c1022c76796267440286fd8d5703208daaf4796733aad4a6960a45`,
`SCALE.MID`, `midi-differential.json`, the native socket journal and
framebuffers. The private `playback/music.wav` SHA-256 is
`f7d607b77ec74147cf47830c0782f6a641fcf591df47500763de16c434b81dc1`.

The guest reached the safe shutdown screen at 159,869 emulated ms.
Windows requested the ejected disk during shutdown, then continued
with a private copy remounted. The original evidence floppy was
preserved. The disposable machine is retained at the private lab's
`restore-tests/win98se-midimapper-20261120` path. The stock and
historical update checkpoints were not opened for writes.

The account meter showed 1% weekly remaining after the first export.
The major-scale control was the only native HDS submitted in this run.

Offline inspection of the stopped FAT32 disk verified installed
MidiMapper 6.38.0.0 and midifl32.ocx 1.1.0.5 byte-for-byte against the
cabinet. MSVBVM60.DLL reports 6.0.97.82. Native quit was acknowledged
at 159,869 ms. Private runtime hashes are in installed-files.json.
