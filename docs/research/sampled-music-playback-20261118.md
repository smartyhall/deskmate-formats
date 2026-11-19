# DeskMate sampled Music playback

## Fresh RSX DAC baseline

The retained instrumented 86Box executable and source patch matched their
prior SHA-256 hashes. A disposable clone used the stopped follow-up disk,
its RSX configuration and NVRAM, and seed 1. DOS booted before the new
FAT12 data floppy was mounted. Files were copied into the guest DeskMate
directory. In the guest, Sound played the control with Ctrl+E and Music played
each score with Alt+P. Every guest action used the authenticated loopback
socket. The run ended at 81,720 emulated milliseconds and 5,132 video frames.
The stopped 48 kHz mono signed 16-bit DAC stream spans exactly 81.720 seconds.
It contains the pre-mix PSSJ DAC contribution. [Setup and tap instructions](pssj-dac-capture-20261118.md) · [Hashes and windows](../evidence/sampled-music-baseline-20261118.json)

```powershell
$env:PYTHONPATH = 'src'
python tools/experimental/sampled_music_probe.py tests/fixtures/application-generated/music/m11.sng tests/fixtures/application-generated/sound/labinst-native.snd <new-directory>
```

The generated Sound files preserve LABINST's 11,000 Hz rate, root code 28,
range codes 25–63 and 5,500-frame PCM extent. Regions at frames 0–1,099,
1,100–2,199 and 2,200–5,499 contain 500, 900 and 1,400 Hz tones respectively.
Slot 9 avoids substituting the existing slot 7 file. The paired copies use
slots 10 and 11 to isolate a changed end word and cleared loop words. The
generator reproduced the exact eight privately archived probe files. The
published MARK9 and MARKLONG bytes are tool-generated and were accepted for
playback together. Sound resave and edit behavior remain untested.

| Control | Observed activity and periodic signal |
| --- | --- |
| Retained Sound tone replay | 0.50 s, about 448.6 Hz |
| M11, C4 then C5 | 0.43 s and 0.38 s, about 444.4 and 888.9 Hz by crossing estimate, 0.57 s onset interval |
| MARKLONG, whole C4 | 1.82 s, about 505 Hz then 914 Hz, with no sustained 1,400 Hz tail signature |
| MARKHI, whole C5 | 1.77 s, about 1,000 Hz then 1,828 Hz, with the intro shortened to about half its original duration |
| SHIFT, end word 1,980 | 1.79 s, with the 900 Hz source region still dominant after the intro |
| NOLOOP, both words zero | 0.50 s, with all three regions audible in sequence |
| MARKFAST, sixteenth, eighth and quarter C4 | Three intro entries. The first ends before the sustain region. The first two activity spans join at 10 ms activity resolution. |

The retained 10 ms interval analyzer reports windowed activity and
mean-crossing frequency. The zero-padded spectral method in the private
archive independently resolves the region sequence. It estimated about
504 and 908 Hz in MARKLONG, roughly 1% above the physical source
frequencies. Exact source frame endpoints and the native gate, envelope
and gain still require separate identification. The held notes gave no
evidence of a release jump into the tail. The no-loop control played the
entire tail during the held gate. Its end was independent of score length.

The private directory `music-sampled-playback/baseline` retains the input
floppy, stopped DAC stream, transition and framebuffer receipts, and
measurement outputs. The pre-existing source disk and captures remain intact.
