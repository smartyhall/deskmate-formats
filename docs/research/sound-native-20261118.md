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
[86Box device source](https://github.com/86Box/86Box/blob/master/src/sound/snd_pssj.c)

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
positions follow Hayes's description. The later positions are nonzero in all
three shipped Clarinet samples with plausible in-sample start/end pairs.
The reader exposes the numbers and retains the rest of the descriptor.
WAV loop semantics need an independent endpoint and playback experiment.
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
| `0–D` | Add the indexed delta, clip to 0–255 and emit the resulting predictor. |
| `E h l` | Set and emit the literal byte `16*h+l`. |
| `F 0–D` | Repeat the current predictor 1–14 times. |
| `F F h l` | Repeat the current predictor `14 + 16*h + l` times. |
| `F E h l` | Set the predictor to 128 and emit it `base + 1 + 16*h + l` times. |

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
