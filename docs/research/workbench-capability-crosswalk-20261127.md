# Preservation Workbench capability crosswalk

Planning checkpoint: 2026-11-27, inspected integrated source
`7dee5fa25eb1b02b2724bdd87759ce53fcb3256b`. Companion to the
[campaign inventory](campaign-inventory.md), not a new normative support matrix.
The maintained [Workbench guide](../preservation-workbench.md),
[compatibility profiles](../compatibility.md), [CLI map](../recovery/cli.md)
and source remain authoritative. Pending PRs are not counted as integrated
capabilities.

## Core offline workflow

| User need | Existing implementation | Remaining product boundary |
| --- | --- | --- |
| Identify a document | `deskmate-preserve inspect` → [native.open_native](../../src/deskmate_formats/preservation/native.py) → bounded profile reader | Not a generic signature service. Unknown signature, unsupported profile, and explicitly selected headerless Text must remain distinct. |
| Preview and export | `deskmate-preserve export` → [bundle.prepare / export](../../src/deskmate_formats/preservation/bundle.py) and application converters | A new bundle directory, not an in-place conversion. Original bytes, JSON and preview/modern projections; report omissions and approximation. |
| Process a folder | Same CLI → [collection.export](../../src/deskmate_formats/preservation/collection.py) | Direct entries only, bounded collection, partial outcomes retained; not recursive archive extraction. |
| Verify | `deskmate-preserve verify` → bundle or collection verifier | Inventory and digests, not authenticity or a native application acceptance test. |
| Explore an archive | [archive intelligence](../../tools/archive/intelligence.md), `archive_intelligence.py` with a private index and content store | Separate offline ingestion and search pipeline, not bundled as a public document-open dialog. Use one writer per index and bounded extraction. |
| Discover compatible historical runtime | [installation-media index](../ecosystem/deskmate-installations.md) and [Evolution Atlas](../ecosystem/deskmate-evolution-atlas.md) | Documentary and observed profile evidence; no automated installer or commercial media distribution. |

The current [project.scripts entry points](../../pyproject.toml) expose the
Workbench and format-specific CLIs. The [preservation CLI](../../src/deskmate_formats/preservation/cli.py)
already shares inspection and export preparation; a UI should reuse this
contract instead of creating a second format classifier. A read-only
inspection may perform conversion planning (not simply a header check).

## Native document dispatch

The eight integrated `native.APPLICATIONS` and `bundle.CONVERTERS` entries
are the first public document workflow boundary. All accept only measured
profiles; all preserve source bytes in the exported bundle.

| Application | Existing output | Important limit | Campaign |
| --- | --- | --- | --- |
| Worksheet | HTML and CSV | Stored values, spans and formula metadata; no formula evaluation | text-worksheet |
| Text | HTML, TXT, picture SVG where supported | CP437/default formatted profile; explicit selection for headerless streams; unsupported graphics/controls reported | text-worksheet |
| Draw | HTML/SVG | Measured 14 FIG geometry and font resources; unsupported objects/styles not inferred | draw-font-graphics |
| Filer | HTML, records CSV, card/report SVG where supported | Bounded DMDB schema/data, opaque values and layouts; not arbitrary household database profiles | filer-utilities |
| Calendar | HTML, ICS, strict interchange where representable | SDK reader; floating times, no general recurrence or allocator; separate bounded writer | calendar-index |
| Address Book | HTML, vCard, strict interchange where representable | Ten-page measured profile; separate one-contact writer; opaque fields retained | addressbook-multicontact |
| Sound | HTML, WAV per sample | Measured original/linked profiles and packed-delta decoding; native playback and fidelity separate | music-sound |
| Music | HTML, MIDI where representable, optional sampled WAV | Supported event timeline, explicit instrument collection, approximate playback | music-sound |

Corkboard and shared household structures have independent read-only
research readers, but are not entries in this Workbench dispatcher.
Print Companion's native survey is not an exporter. Font CLI and bounded
Calendar/Address Book writers remain separate opt-in operations. Do not
enable editing simply because a profile can be read. Other archive
handlers under #194/#195 and DOS analysis under #190/#196/#198 remain
candidate integrations at this snapshot.

## Suggested first interface increment (design only)

A local, offline, read-only interface could present three clear actions:
**Inspect**, **Preserve/export**, and **Verify**. Use exact source identity
and detected profile, display the proposed artifacts and diagnostics before
export, and keep the original in a new verified bundle. An optional
application choice should be explicit, never silently retry incompatible
readers on a rejected input. Permit a batch summary with per-file outcomes
without calling partial completion full success. Do not display a generic
"recovered" state when only raw bytes are preserved or the projection has
omissions.

The next increment should qualify the separate archive-to-document handoff
on small synthetic containers: stable parent/member identity, bounded
extraction, a private derived copy, explicit native profile validation, and
independent bundle verification. Refuse unsafe paths and ambiguous
identification, retain failure/partial status, and do not open executable
members as documents or execute any historical content.

This is an interface design recommendation, not authorization for a service,
upload endpoint, native guest operation, new dependencies or actual archive
migration. Start with the current offline package and existing tests.
