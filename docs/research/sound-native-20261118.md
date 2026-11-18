# DeskMate Sound containers and PCM

DeskMate Sound stores unsigned, single-channel 8-bit samples. In the two
measured containers, sample descriptors delimit the stored and decoded
regions independently. The earlier 16-byte header uses a fixed descriptor
table. The later 114-byte header links descriptors by absolute file offsets.
Both music and speech compression use the same packed-delta decoder with a
sample-specific table. The independent reader returns the decoded samples
and preserves every original byte in Workbench bundles.

## Sources and laboratory

The installed generic 03.05.00 distribution and the 242-file research-disk
lineage were inventoried before the first experiment. The generic installation
has neither audio application. The Tandy 1000 RSX OEM DeskMate 3.04 Disk 2
and the RLX-HD-B 03.04.03 backup both contain byte-identical `SOUND.PDM`
(`ea5c305a76ae52143f907ed040c05c2c5ea47f6bca45dda3271e410a23af67a2`)
and `MUSIC.PDM`
(`f54651f6597c89efb5810352d69afdd2887a21217c8d519f3c39d83bf0966993`).
The initial trial copied application and audio resource files into a disposable
3.05 installation and made the OEM `MEMORY.RES` available on the sample floppy.
Sound and Music launched through the 3.05 `DESK` command in that configuration.
This identifies the application binaries separately from the runtime version.
[Private archive provenance](audio-historical-corpus-20261118.md)

The RSX clone used a 25 MHz 386SX, 4 MiB RAM, internal VGA and internal sound.
86Box source revision `855258da966f1594f568350be59e8e1eca082ed1` maps the
RSX's PSSJ PSG to ports `1E0h–1E3h` and its digital controls to
`1E4h–1E7h`. The source models timer-driven ADC/DAC data and DMA channel 1.
Its DAC conversion centers `80h` at zero. Pinning and inspecting the source
establishes the modeled hardware. UI launch and waveform display establish
native interpretation of the opened file. Windows WinMM enumerated zero
host audio input and output endpoints in this session. Audio output
fidelity and live microphone capture need their own observations.
[86Box device source](https://github.com/86Box/86Box/blob/855258da966f1594f568350be59e8e1eca082ed1/src/sound/snd_pssj.c)

## Container grammar

Offsets are zero-based. Multi-byte container fields are little-endian.
Ranges below use inclusive starts and exclusive ends. The raw descriptor and
raw header are included in JSON. Gaps and bytes after the last owned region
remain available from the original.

| Field | Original | Later |
| --- | --- | --- |
| Fixed header extent | 16 bytes | 114 bytes |
| Identifier | `00h = 1A` | `2Ch–2Eh = 1A 80` |
| Compression | `01h`, byte | `42h`, word |
| Descriptor count | `02h`, byte | `2Eh`, word |
| Instrument number | `03h`, byte | `30h`, word |
| 10-byte name | `04h` | `00h` |
| Rate in samples per second | `0Eh`, word | `58h`, word |
| Descriptor allocation | 28-byte table at `10h` | 46-byte records, first at `72h`, linked absolute offsets |

Zero in the instrument field denotes a recording, with a single descriptor in
the measured corpus. Instrument slots are 1–32. The value 255 denotes an
instrument without a slot. The application and comparators cover rates
5,500, 11,000 and 22,000 samples per second. The exporter writes the stored
positive rate into WAVE verbatim so that other stored rates retain their
meaning as data. Other rates have no native playback qualification.

| Descriptor field | Original relative offset | Later relative offset |
| --- | --- | --- |
| Next descriptor, dword with zero at end | No link | `00h` |
| Pitch, following flag, low and high range | `00h–04h` | `06h–0Ah` |
| Absolute payload offset, dword | `04h` | `0Ah` |
| Stored length, dword | `08h`, zero for PCM | `0Eh`, explicit for PCM |
| Decoded sample count, dword | `10h` | `12h` |
| Sustain endpoints, two dwords | `14h`, `18h` | `16h`, `1Ah` |

The sustain fields store positions relative to the sample. The original
positions follow Hayes's description. In the later LABINST control, a
native 1,100 to 2,200 sample selection produces those exact two values.
The three shipped Clarinet samples also contain in-sample start/end pairs.
The reader exposes the numbers and retains the rest of the descriptor.
WAV loop playback and endpoint inclusion need an independent experiment.
Pitch codes 1–63 run from A1 to B6, with 1 mapping to MIDI 33. The application
labels octaves from A, so its C3 is standard C4. Unset triplets can use
`FF` and the following flag varies between specimens. MARIMBA's note ranges
overlap. Sample selection from overlapping ranges remains an open playback
question.
[Hayes and Ball historical notes](https://nagasm.org/ASL/sound05/index.html)

The old, uncompressed `JANNA.SND` ends with 19 bytes outside the stated PCM
region. Its exported audio uses the descriptor's 47,259 samples. The later
multi-sample specimens put descriptors first and use links `114 → 160 → 206`
or `114 → 160 → 206 → 252`. The reader follows the chain and rejects
cycles, count disagreement, out-of-bounds offsets and overlapping regions.
The earlier one-byte signature can coincide with the later marker when
original PCM begins `1A 80`. Sound validates both layouts in that case.

## Music and speech compression

Compression codes 1 and 2 refer to encoder modes. A 30-byte sample-local
prefix contains fourteen signed **big-endian** 16-bit deltas and a final
unsigned big-endian run base. The rest of the sample is a high-nibble-first
stream. Start a sample with the predictor at 128.

| Nibbles | Output |
| --- | --- |
| `0–D` | Add the indexed delta with signed 16-bit arithmetic, clip to 0–255 and emit the resulting predictor. |
| `E h l` | Set and emit the literal byte `16*h+l`. |
| `F 0–D` | Repeat the current predictor 1–14 times. |
| `F F h l` | Repeat the current predictor `14 + 16*h + l` times. |
| `F E h l` | Set the predictor to 128 and emit it `base + 1 + 16*h + l` times, with a 16-bit run count. |

This grammar was recovered by examining the 16-bit OEM `COMPRESS.RES`
(`3c07b618046092080f3eb2dd3e186fb325b81dd5ad562f14d24a55ad7daf549a`).
At module image offset `0B78h` (file offset `0D78h`), the decompression
routine initializes the table and predictor and dispatches eight nibble
states through the table at image offset `0E90h`. The routine also accepts
subsequent input chunks using saved state. The independent implementation
reads the serialized stream in one pass and stops at the bounded descriptor
count. Historical payloads sometimes have extra nibbles or bytes after that
count. The TL/2 OEM Cello's second sample has a 28-frame silence run that
begins at sample index 12,455, crosses the 12,478-frame endpoint and has
two more encoded nibbles after the run. WAV uses the declared endpoint.
A stream that ends early is rejected for WAV conversion while its container
remains inspectable.

To reproduce the static comparison, load the resource after its 512-byte
MZ header in a 16-bit real-mode CPU emulator without DOS services. Set up
separate code, data, stack and output segments. Call `0B78h` with a far
pointer to a structure holding the destination capacity dword and a far
pointer to the destination paragraph, then near pointers to a 59-byte
persistent work area and the input buffer, followed by the input byte
count. Continuation calls use a null initial structure pointer and the same
work area. Compare only the declared output sample count. Use input chunks
of at most 10,000 bytes in this experiment. An initial one-call comparison
for the 36,580-byte BEAMUP region produced only a prefix because the
routine doubles the chunk count in a 16-bit register. The chunked oracle
matched the full 40,831-sample result.

Across 32 historical sample regions, the independent reader matched
the exact declared number of output bytes produced by the original routine.
Music mode matched on both container
generations, including all four MARIMBA samples and the 155,904-sample
THNDER recording. Speech mode matched on the later 11,318-sample LEARNING
recording. These are decoded PCM identities. Lossy encoding can alter the
waveform relative to the original signal. The historical audio and oracle
outputs stay in the private archive.

## Reader and export

```sh
deskmate-sound trial.snd
deskmate-sound trial.snd --sample 1 --wav trial.wav
deskmate-sound trial.snd --sample 1 --pcm trial.raw
deskmate-preserve export trial.snd --output-dir sound-bundle
deskmate-preserve verify sound-bundle
```

The Sound API exposes `stored_sample(index)` and `pcm(index)`. For PCM input
the bytes are identical. For compressed input they are the encoded region and
its decoded projection. The Workbench writes one RIFF WAVE per decodable
sample and records both hashes. WAVE output uses mono 8-bit PCM and pads odd
data chunks to RIFF word alignment without adding a frame. Each offline
preview includes native pitch, range and sustain numbers and local audio
controls.

## Synthetic PCM round trip

The tool-generated later-profile input `TONE.SND` contains a 440 Hz sine
at 11,000 samples per second. The period has 25 samples. The generator
calculates `128 + round(63 * sin(tau * i / 25))` for indices 0–24 and
repeats this period 220 times. Its 5,500 bytes follow a zero-filled
160-byte prefix populated with the later identifier, name `LAB TONE`,
one recording descriptor, and lengths 5,500. Set the four pitch and
range bytes to `FF 00 FF FF`. The payload offset is 160.

Sound opened the file from a disposable floppy and displayed 0.500 seconds,
5,500 samples and 11,000 Hz. Native Save As wrote `TONERAWO.SND`.
The stopped-disk extractions match the input byte-for-byte at SHA-256
`9f62938169ecf09c1134bf3aa3feb805c64acf43d57355e63d908b23713cc71a`.
The Git fixture is the native Save As result.
[Native tone](../../tests/fixtures/application-generated/sound/tone-native-pcm.snd)

An independent libsndfile 1.2.2 read confirms the exported WAVE subtype
`PCM_U8`, one channel, 11,000 Hz, 5,500 frames, and unchanged PCM at SHA-256
`e5788ae0618e3167842ee0de426973800c06ad85f48b01228a6cd3e7b868b795`.
The same library verified the frames, rates and full payload bytes of all
35 WAVs from the 16 distinct historical Sound files. Those bundles are
available in the private lab under `historical-sound-bundles`.

## Native recording and instrument differentials

The second disposable boot cloned the stopped first trial, changed the
mouse device from PS/2 to serial, and copied OEM `MEMORY.RES` into the guest
DeskMate directory. All key and relative mouse events used the authenticated
86Box socket. The graphics-mode controls were verified from held frames.
The stopped images, rollback identities, exact emulated times
and verified extractions are in the [native receipt](../evidence/audio-native-20261118.json).

| Control | Saved result |
| --- | --- |
| S00 | Native Sound saved the empty recording as 160 bytes. It has one descriptor with data offset 160, zero stored and decoded length, and 11,000 Hz. |
| S01 and S02 | The earlier tool-generated TONEOLD opened with a recording-machine prompt. It offered TL, SL, TL/2-family or Other. Choosing Other (No adjustment) and choosing the default 1000 TL in a separate load both yielded the same later-format 5,500-frame resave. It differs from the later tool input only at header offset 92, which is 3 instead of 0. PCM matches exactly in both cases. |
| S03 | The 5,500 Hz input was 111 copies of the unsigned byte pattern `80 00 FF 01 FE`. The native save preserved all 555 frames. WAVE's data chunk stays odd and its padding byte sits outside the frame count. |
| S04 | At 22,000 Hz the source was 255 center frames, then `00 FF 01 FE`, then 252 center frames. Native Sound showed the four-frame pulse region in a 511-frame recording. |
| S05 | Ctrl+R opened Record. A 0.100-second request at 11,000 Hz produced 1,104 frames and a horizontal centerline. Every saved byte is `80`. This exercises the emulated recording path under the no-input condition. Its exact frame duration is 1,104 / 11,000 seconds. |
| TONEMUS and TONESPK | Two independent opens of the same PCM input, with File → Data compression set to Music or Speech before Save As. Both stored 3,001 bytes for 5,500 decoded frames. |
| S06 and S07 | Reopen each compressed file, select No compression and save separately. These two PCM resaves are byte-identical. The independent decoder recovers their exact 5,500 data bytes from both compressed sources. |
| LABINST | Copy all of S01, create a new instrument file and paste. Name it LABTON, set number 7, choose C3 and set the range to A3–B6. From Home, Right and Shift+Right with a 0.1-second unit select samples 1,100–2,200. Options → Define sustain stores both positions. |
| S10 | Copy the selected 1,100-frame region, add a note, paste, and assign pitch C4 and instrument number 8. The first 5,500-frame sample retains C3, range A3–B6 and its loop. The next link points to a second descriptor at 160. It has C4, 1,100 frames and unset range and loop fields. |

The earlier synthetic input can be regenerated independently. This command
writes the exact 44-byte original prefix and the 5,500 PCM bytes. The Git
file is marked **tool-generated** with native import and later-profile save
evidence.
[Original-format tone fixture](../../tests/fixtures/application-generated/sound/tone-original-tool-generated.snd)

```sh
python -c "from math import sin,tau; from struct import pack; p=bytes(128+round(63*sin(tau*i/25)) for i in range(25))*220; open('TONEOLD.SND','xb').write(pack('<4B10sH4B6I',26,0,1,0,b'LAB TONE',11000,255,0,255,255,44,0,0,len(p),0,0)+p)"
```

The two compressed tone files differ in exactly three bytes. Header byte
66 is 1 or 2, and the big-endian run base at offsets 188–189 is 25 or 3,060.
The remaining compressed data is identical for this tone. Stored regions
are 54.56% of the PCM length. Both contain `-256` in unused delta entries,
so a decoder that rejects values outside `[-255, 255]` rejects genuine native
output. The recovered bytes differ from the starting tone at 3,078 of
5,500 sample positions, by at most one amplitude unit. RMS error is
0.74809 units. Other waveforms can produce different tables and stream lengths.

LABINST's descriptor stores pitch 28 for native C3, range codes 25–63,
and the two sustain words. The copied waveform still has a physical
frequency of 440 Hz. Setting the nominal note changed metadata and kept
those PCM bytes identical.
[Cross-application slot control](music-native-20261118.md)

## Emulated playback

An instrumented build from the same pinned 86Box revision records the RSX
PSSJ DAC contribution in `pssj_get_buffer` before host mixing. It appends
signed 16-bit mono values at `SOUND_FREQ` (48,000 Hz), with a 96-second cap.
The capture excludes the PSG path, speakers and room acoustics. The VM still
had zero WinMM endpoints. Use the source patch and commands under the private
campaign archive to rebuild the probe. The executable, source diff, input
floppy, DAC stream, and selected screenshots are identified in the native
evidence. The [DAC reproduction guide](pssj-dac-capture-20261118.md) records
the build commands and an independent offline reanalysis.
The first probe attached the nonbootable floppy before boot and did
not reach DOS. The successful clone booted to DOS before floppy insertion.
[Native receipt](../evidence/audio-native-20261118.json)

| Control | DAC observation |
| --- | --- |
| Sound plays TONERAWO | About 448 Hz and 0.50 seconds of signal. The stored PCM is 440 Hz at its declared rate. |
| Music plays M11 with slot 7 | About 445 Hz for C4 and 891 Hz for C5. The active windows span 0.42 and 0.37 seconds. The second onset follows the first by about 0.57 seconds. |
| SLOT8 changes only the instrument to 8 | The same frequencies and active durations. For these two notes the second sample with unspecified range did not displace the first sample, whose range covers both pitches. |
| HELD7 gives slot 7 a whole C4 note | About 445 Hz for 1.82 seconds, exceeding the source sample's 0.50-second length. The fixture has a defined sustain loop. |
| REP7 repeats C4 and G4, count 2 | Four active intervals at about 445, 665, 445 and 665 Hz, with onsets approximately 0.57 seconds apart. |
| MID7 and EIGHTH change tempo at the second quarter | The second active window spans about 0.16 seconds at 75 half notes per minute, and 0.58 seconds at 151 eighth notes per minute. The first active window spans about 0.42 seconds in both. |

Active intervals use 10-ms bins and frequencies use short-window spectral
estimates. The playback clock and native envelopes differ from the written
MIDI timeline and direct PCM export. The DAC evidence verifies sample use,
octave transposition and sustained output on this configuration.

## Next sampled-playback controls

1. Keep LABINST's slot and loop words, and replace its uniform sine with
   different signals in frames 0–1099, 1100–2199 and 2200 onward. First
   reopen and save it in Sound and record the bytes. Then use HELD7 to
   measure the actual loop boundaries, cycling order and release tail.
2. Start with S10 and give its two samples distinguishable frequencies.
   Compare explicit disjoint ranges with overlapping ranges, then reverse
   descriptor order. Keep pitch, note duration and volume fixed initially.
   The captured SLOT8 result supplies the unset-range control.
3. Repeat M11 at two dynamics and with a second active voice. Capture DAC
   rate, mixing and gate changes before building an independent sampled-song
   renderer. Use a one- or two-voice synthetic score for the first parity
   check. A separate encoder control can save the same pulse train and long
   silence in both compression modes to characterize their encoder choices.
