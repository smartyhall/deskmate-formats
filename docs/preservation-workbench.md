# DeskMate Preservation Workbench

The Workbench exports measured DeskMate document profiles. Each bundle keeps
the original bytes, source-derived details and a preview or import format.
The original is the preservation copy. Modern files are projections with
documented limits. The workbench runs offline with Python 3.13 or later.

## Use

```sh
python -m pip install .
deskmate-preserve inspect old-files/RESULTS.WKS
deskmate-preserve export old-files/RESULTS.WKS --output-dir results-bundle
deskmate-preserve verify results-bundle
```

Open `results-bundle/preview.html` in a modern browser. The output parent must
exist, and the named output directory must be new. Reads are bounded to 1 MiB,
with stricter limits in individual readers. Input files are opened read-only.

The program recognizes Worksheet, Draw, formatted Text, Address Book, Sound
and Music signatures and validates their structures. Calendar and Filer share the `03 FIL`
signature. Their table and column profiles distinguish them. A filename
extension alone is insufficient evidence. Some native Text files are DOS
streams with no distinctive header. Confirm their origin and select Text
explicitly.

```sh
deskmate-preserve inspect old-files/LETTER.DOC --application text
deskmate-preserve export old-files/LETTER.DOC --application text --output-dir letter-bundle
```

Inspection reports the profile, diagnostics and planned artifacts as JSON.
It runs the same projections as export and writes nothing.

## Collections

```sh
deskmate-preserve export old-files --output-dir desk-archive
deskmate-preserve verify desk-archive
```

A directory export processes up to 1,024 direct entries in filename order,
skipping subdirectories. Open `desk-archive/index.html` for previews, manifests
and failure messages. The JSON response and `collection.json` record each
file's outcome. One rejected file leaves earlier and later successes intact.
An explicit application selection applies to every input in that invocation.
Export a headerless Text file separately when working with a mixed collection.

Exit status `0` indicates success, `1` indicates a collection export with
one or more input failures, and `2` indicates an invalid command, source or
bundle, or an I/O error. Collection verification reports how many bundles
passed and how many input files failed at export time.

## Bundle and verification

```text
results-bundle/
  original.wks
  manifest.json
  content.json
  preview.html
  values.csv
  cells.csv
```

`manifest.json` records the exact source filename, original byte length and
SHA-256, native profile, parser entry point and package version. The stored
original uses a fixed name with the detected application's extension. The
artifact list records relative paths, lengths and SHA-256 digests. Graphic
assets may be under `assets/`. `content.json` is application-specific and
retains raw fields, offsets or payloads where the readers expose them.

The `measured_profile` inspection state means the native reader accepted the
bounded structure. Consult each diagnostic's `code`, `effect`, `message`
and optional `location` for limits. Effects distinguish approximations,
omissions, opaque source values and informational notices. Evidence for
individual interpretations is in the application research and compatibility
profiles linked below.

The verifier checks the [version 1 manifest shape](preservation-manifest-v1.schema.json),
relative paths, inventory, sizes and SHA-256 hashes. It rejects unexpected
files, links within the archive and duplicate JSON properties. It also
checks the collection index and each child manifest against their recorded
digests. A child directory can be verified independently. Verification works
without running a native reader. Authenticity requires a separately trusted
digest or copy of the manifest. File permissions and filesystem timestamps are
outside this byte-preservation format.

## Exports and evidence limits

| Application | Practical files | Scope |
| --- | --- | --- |
| Worksheet | `preview.html`, `values.csv`, `cells.csv` | One-based grid, documented column widths, labels, numbers, formulas, inputs and multiline blocks. Browser alignment, widths and spans approximate the native display. |
| Text | `preview.html`, `text.txt`, picture SVGs | CP437 literal text, normalized LF hard breaks and measured EOF padding behavior. HTML displays measured bold, underline and the observed center/reset controls at line boundaries. Picture positions and order come from the stream. |
| Draw | `preview.html`, `drawing.svg` | Measured FIG geometry and stored RGB palette. The SVG view box frames rendered objects in world coordinates. |
| Filer / Form Setup | `preview.html`, `records.csv`, card/report SVGs when present | Native DATA field names, schema order, index order and printable values. Recovered GRAPHICS geometry and raw LAYOUTS have different evidence and coverage. |
| Calendar | `preview.html`, one `.ics` per nonempty supported calendar, strict `interchange-v1.json` when representable | SDK-derived ordinary date and quarter-hour time codecs. All parsed rows, raw fields and control records are available in the archival JSON. |
| Address Book | `preview.html`, `contacts.vcf`, strict `interchange-v1.json` when representable | The measured ten-page profile exposes first name, last name, city and work phone. The archival JSON includes the opaque contact bytes. |
| Sound | `preview.html`, `assets/sample-01.wav` and additional sample WAVs | Independently decoded mono PCM at the stored rate. Preserves original sample offsets, compressed regions and pitch/range/sustain metadata. |
| Music | `preview.html`, `composition.mid` when representable | Three voice streams and a conductor, with measured notes, rests and quarter-note tempo. Original and event JSON are also preserved for scores with opaque words. |

**Worksheet.** A formula's expression, binary64 cache, raw status word and
measured result/error flags remain together in `content.json` and the detailed
CSV. Expand a formula cell in HTML to inspect its expression and cache. The
rectangular CSV uses the stored numbers where the result flag allows it and
leaves error or uncalculated results blank. Cached values may be stale.
The exporter performs zero formula evaluation. The rectangular CSV puts
multiline text at its anchor; the detailed CSV includes spans. Import CSV
as UTF-8. Text values that could be interpreted as formulas gain a leading
apostrophe in CSV, including values with suspicious prefixes after whitespace.
Use JSON for exact decoded strings. Measured numbers remain numeric CSV cells.
[Worksheet native study](research/worksheet-native-20261117.md)

**Text, Draw and Filer.** SVG reconstructs supported lines, rectangles,
ellipses, polylines and the subset of old text objects with usable embedded
stroke glyphs. Styles and patterned fills use solid approximations. External
font references and unsupported objects are omitted with machine-readable
diagnostics, including type and list offsets in `content.json`. Text and
Filer use neutral colors because their measured containers lack the FIG palette.
All Text picture envelopes and payloads remain in the archival JSON, including
pictures that exceed the preview budget. Filer places opaque DATA values in
hex in JSON and leaves them blank in CSV. LAYOUTS remains in the original.
The HTML and SVG work from local files with no scripts or external assets.
[Text native study](research/text-native-20261117.md) ·
[shared graphics evidence](research/graphics-native-20261117.md) ·
[Filer native study](research/filer-native-20261117.md)

**Calendar.** Each supported named calendar has its own iCalendar file.
Native appointment times are floating local times. An enabled or disabled
alarm is recorded as `X-DESKMATE-ALARM-ENABLED`. Alarm triggers and recurrence
rules remain outside this projection. Events use a snapshot-scoped UID
derived from the original SHA-256, calendar ordinal and row ID. Editing the
original can change every generated UID. `DTSTAMP` is the fixed UTC placeholder
`19800101T000000Z`, required for the file syntax and explicitly identified as
export metadata. Internal/control records, retired rows and undecoded records
stay in archival JSON. The strict version-1 interchange limits still apply,
including the rejection of multicalendar collections.
[Interoperability contract](interoperability.md)

**Address Book.** vCard 4.0 uses structured names, the locality component of
the address and a work telephone text value. The file is UTF-8 with CRLF
endings and byte-aware folding. Opaque name-adjacent fields, other phone fields,
dates and miscellaneous flags stay in archival JSON. Unsupported contacts or
opaque values produce diagnostics. Strict interchange is emitted only when its
existing validator accepts the book.
[Address Book codec](research/addressbook-codec.md)

**Sound and Music.** Sound's local audio controls play the independent WAV
projection. The Workbench records the hashes of the stored and decoded
sample regions, and both compression modes are lossy. Music MIDI uses
neutral velocity and default MIDI playback instruments. Unsupported
sequencing controls produce a MIDI omission diagnostic. The original score,
raw words and known events remain available.
[Sound report](research/sound-native-20261118.md) ·
[Music report](research/music-native-20261118.md)

## Reproduce the native demo

Use an installed build and a fresh output path. This example shows the three
shapes Draw saved in D17, copied into Text and preserved natively as TP06.
Open `text-demo/preview.html` to view the resulting document and illustration.

```sh
deskmate-preserve export tests/fixtures/application-generated/text/tp06.doc --output-dir text-demo
deskmate-preserve verify text-demo
```

For an eight-family collection, copy the following committed native synthetic
specimens into a new directory. Run the collection example above with that
directory as the input.

| Input | What to inspect |
| --- | --- |
| [Worksheet WMIX](../tests/fixtures/application-generated/worksheet/wmix.wks) | All five cell categories in one grid |
| [Text TP06](../tests/fixtures/application-generated/text/tp06.doc) | Text and the pasted Draw line, rectangle and ellipse |
| [Draw D17](../tests/fixtures/application-generated/draw/d17.fig) | The three shapes in the Draw container with palette |
| [Filer G18](../tests/fixtures/application-generated/filer/g18.fil) | A card form with 36 lines from a multi-chunk GRAPHICS stream |
| [Calendar alarm trial](../tests/fixtures/application-generated/calendar/alarm-on-86box-trial-c.cln) | One appointment with the measured alarm enabled |
| [Address Book two-contact save](../tests/fixtures/application-generated/addressbook/native-two-contact-20261117.adr) | Two native contacts and their core vCard fields |
| [Sound 440 Hz tone](../tests/fixtures/application-generated/sound/tone-native-pcm.snd) | One uncompressed native Save As control and its exact PCM waveform |
| [Music tempo control](../tests/fixtures/application-generated/music/mtempo.sng) | Seven notes, a rest, six base durations and an explicit 140 BPM tempo |

The [portable end-to-end test](../tests/portable/test_preservation.py) builds
and verifies this collection. [The Worksheet regression](../tests/portable/test_preservation_worksheet.py)
verifies all 44 native Worksheet specimens byte-for-byte. The
[fixture manifest](../tests/fixtures/application-generated/manifest.json)
records provenance, lengths and source hashes.
