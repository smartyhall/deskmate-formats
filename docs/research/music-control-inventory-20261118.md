# Historical Music control inventory

The reader accepted all 62 distinct historical scores structurally. MIDI
projection accepted 15, rejected 43 at the opaque-word gate, and rejected four
more at the repeat-playback gate. This is the reader's first failure in each
score. Multiple families can affect the same score. The receipt counts
distinct files by SHA-256 and reports each family's variants, stream and
relative position by serialized instruction thirds. It excludes score names,
text, full sequences and source paths.
[Aggregate receipt](../evidence/music-control-inventory-20261118.json)

| Priority for historical playback | Scores | Occurrences | Placement and evidence |
| --- | ---: | ---: | --- |
| Repeat execution | 32 | 105 starts and 105 ends | Conductor. Starts use `3002–3004` and ends use `50ff`. Native playback covers a simple repeat. |
| Accidental flag `80` | 28 | 821 | Appears in all three voices and throughout their lengths. Its pitch effect needs a native key-signature and accidental comparison. |
| Alternate ending candidates | 15 | 49 | Conductor `4001–4003`, including 31 occurrences in the final third. Meaning and pass selection need controlled playback. |
| Score marker candidates | 15 | 66 | Conductor `7441–744b`. The operand range is consistent with letter labels. Editing, navigation and playback effects remain unresolved. |
| Other voice controls | 13 | 85 | All have a zero low byte. `8a00` accounts for 60. Voice 3 holds 61 occurrences overall. Compare zero-pitch forms under tie, slur and rest editing. |

The corpus has no observed `EF`, `F3` or `F4` special durations. Keep them
as native control cases after the higher-frequency playback blockers. The
reader already projects 76 key markers in 44 scores and 46 meter markers
in 24 scores. The observed meters are 2/4, 3/4, 4/4, 5/4 and 7/8. Repeated
key or meter records may occur away from the first third. The MIDI
projection emits supported meter events. Its pitch interpretation still
needs the accidental comparison.

Instrument controls appear in 50 scores, with 174 of 221 occurrences in the
first third of their voice. The serialized operands span `00–04`. Dynamics
appear in 37 scores and span all six supported indices. Their 597 occurrences
are spread throughout the voices. Slot labels describe serialized instruments.
Native sample bindings and dynamic amplitudes need separate DAC measurements.
Four header profiles and all four combinations of zero- or one-byte text
alignment and trailer occur in the corpus.

Regenerate with the private extracted corpus and this checkout.

```powershell
$env:PYTHONPATH = 'src'
python tools/experimental/music_control_inventory.py $archiveDirectory
```

The next sequential checks are a natural versus key-signature control with
separated pitches, a two-ending repeat using distinct notes for each pass,
and a native save with a letter marker. Measure the marker's effect on
execution before treating it as an annotation. Reader behavior was unchanged.
[Native Music evidence](music-native-20261118.md)
