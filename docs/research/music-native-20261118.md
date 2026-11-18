# DeskMate Music score streams

Native Music saves preserve separate event streams for three voices, followed
by a common timing and control stream. This layout also frames all 62 unique
historical scores in the private comparison corpus. The reader keeps every
word with its file offset. A conservative MIDI projection uses the measured
linear notation and timing.
[Sound and RSX laboratory report](sound-native-20261118.md) ·
[Historical archive comparison](audio-historical-corpus-20261118.md)

## Controlled native notation

The first session used the OEM RSX Music module in the disposable 3.05
installation described in the Sound report. From DOS in `C:\DESKMATE`,
`DESK MUSIC` opened an untitled score. The application showed C major,
4/4, a quarter note = 100, and Clarinet, Piano and Bells as the three
default voices. The first voice was active. Its octave indicator enabled
the C key to insert middle C, visible on the ledger below the treble staff.

File → Save As produced each named control. All controls use the same
default title and author. The Save As actions preserved the prior files.
After application exit to DOS and authenticated quit, independent FAT16
directory/cluster reads matched 7-Zip extraction. Exact file lengths, hashes
and ancestry are in the [fixture manifest](../../tests/fixtures/application-generated/manifest.json).

| Specimen | Native actions and resulting words |
| --- | --- |
| M00 | Save the empty default score. All four streams are empty. |
| M01 | Enter `C` at the default quarter duration. Voice 1 is `EA1C` and the conductor is `2018` (24 ticks). |
| M02 | Append `G` at the same duration. Voice 1 appends `EA23` and the conductor becomes `2030` (48 ticks). |
| M03 | Insert a quarter rest with `R`. Voice 1 appends `EA00` and the conductor becomes `2048` (72 ticks). |
| MVALUES | From M03, enter `3 E 5 A 6 F 2 D 1 B` without the intervening spaces. The durations are eighth, half, whole, sixteenth and thirty-second. Voice 1 appends `EE20 E625 E221 F21E F627`. The conductor becomes `20ED` (237 ticks). |
| MTEMPO | Press Home and insert a quarter-note tempo of 140. All eight voice-1 words are unchanged. The conductor adds `118C` before the original `20ED`. |

In the keyboard automation run, F2 followed by O, two Down keys and Enter
selects Save As. Type the new filename in the focused field and confirm.
For MTEMPO, Home moves to the start, F5 → Tempo opens the dialog. Tab
focuses the BPM field. The field displayed 140 before validation and the
score showed the change at the left of the first note after confirmation.

## Container and event representation

| File region | Meaning in the measured profile |
| --- | --- |
| `00h–04h` | `0C 53 4E 47` |
| `04h–16h` | 18 raw header bytes |
| `16h–18h` | Little-endian length. Add 22 to compute the exclusive end of the four streams. |
| `18h` onward | Title and author as consecutive NUL-terminated strings. If the next position is odd, retain one alignment byte. |
| Four consecutive streams | Each begins with little-endian word `7FFE`, carries 16-bit little-endian words, and ends with `7FFF`. Streams 1–3 belong to voices 1–3. Stream 4 carries common timeline and controls. |
| After the declared extent | An optional extra byte occurs in historical specimens and is retained. |

The first-party controls share header bytes `00 01 2B 2D 2D 05 64 2D 2D 00
50 42 42 00 00 00 01 00` before the length. The majority of historical
scores use an all-zero 18-byte header. Other variants differ at individual
positions. Some historical alignment bytes are nonzero. The reader retains
them and checks the actual stream boundaries.

The measured note and rest high bytes are `E2`, `E6`, `EA`, `EE`,
`F2` and `F6`. Their durations are 96, 48, 24, 12, 6 and 3 ticks,
respectively. One quarter note occupies 24 ticks. The low byte is zero for
rests in these cases. Pitch 1 maps to MIDI 33 and the range ends at pitch
63 (MIDI 95). For the measured commands the current voice advances by
the note or rest duration, starting separately at tick 0.

Conductor words `2xxx` advance the common cursor by the lower 12 bits.
This space can express a score duration and delays between control words.
A word `11xx` gives the quarter-note tempo in its low byte at the current
cursor position. The native default of 100 BPM corresponds to 600,000
microseconds per quarter. MTEMPO uses `8C` (140 decimal) without changing
any voice duration.

Historical scores contain further voice encodings and conductor instructions.
The reader retains the original word and location for each. The preview
indicates missing projections and leaves subsequent voice ticks unknown
after an unclassified voice word. Bar markers, repeats, alternate endings,
key and time signatures, dynamics and note modifiers require control
comparisons before a general MIDI exporter can use them.

## Instrument lookup

The later OEM instrument chooser listed the same slot names stored in the
available Sound files. The Cello, Clarinet, Piano and Bells are sampled
instruments; historical slot numbering differs between Personal DeskMate 2
and the later module. The native chooser displayed Marimba for slot 6 when
both `MARIMBA.SND` and the original-container `BANJO.SND` had number 6.
That observation leaves duplicate resolution and original-file discovery
open. An initial keyboard chooser operation stored a `7320` word while
the expected change was slot 6. The native score marker displayed 33.
Treat this as an anomalous selection observation and retain the raw word.
[Baldwin's converter readme archive](http://ftp.oldskool.org/pub/tvdog/tandy1000/sound/dm_music.zip)

## MIDI and Workbench

```sh
deskmate-music score.sng
deskmate-music score.sng --midi score.mid
deskmate-preserve export score.sng --output-dir score-bundle
deskmate-preserve verify score-bundle
```

The JSON includes title, author, raw header and trailer bytes, ordered
events, source offsets and recognized timing. Workbench keeps the original
SNG and includes an offline table for each stream. The preview limits
each stream to 120 rows. The original and JSON retain the full score.

Standard MIDI File type 1 uses 24 PPQ and four tracks, one for tempo and
three for the voice slots. Note On and Note Off preserve the note pitches
and written timing in the measured profile. The end of every track uses
the conductor's total ticks. The projection uses velocity 64 and the
playback device's default MIDI instrument. When a word or timing consistency
check falls outside the supported projection, the Workbench gives a
`midi_omitted` diagnostic and still preserves the original and its score
streams.

Mido 1.3.3 independently read the MTEMPO export as type 1 with four
tracks, 24 ticks per beat, seven notes and a written duration of
approximately 4.23214 seconds. It reported pitches 60, 67, 64, 69, 65,
62 and 71, with the 24-tick rest between 67 and 64.
