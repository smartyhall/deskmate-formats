# DeskMate format inventory

The [Tandy Appendix A format crosswalk](reference/tandy-format-crosswalk.md) contains manufacturer-documented common headers and application-specific technical references for Address Book, Calendar, Draw, Filer, Text and Worksheet. These are **documentation-derived leads**, not new native-verified capabilities; the inventory table below continues to distinguish research already integrated into the repository from open PR work.

| Application/family | Evidence status | Implemented capabilities |
|---|---|---|
| Calendar 3.05 PERSONAL.CLN | E00–E19, Phase III-A and SDK-derived ordinary time/date profile | Measured read/index/append, bounded additional-page reading, 29-event/14-day offline sample; no multipage writer |
| Address Book 3.05 PERSONAL.ADR | [Phase I](research/addressbook-phase1.md) and [Phase II](research/addressbook-phase2.md) native field differentials; [codec report](research/addressbook-codec.md) | Ten-page reader and one-contact writer (four exact native whole-file SHA matches); no multicontact insertion |
| Filer 3.05 | [Native records](research/filer-native-20261117.md) and [controlled forms](research/graphics-native-20261117.md) | Bounded schema, index and DATA inspection. Decodes card and report GRAPHICS chunks. |
| Text 3.05 | [Native text corpus](research/text-native-20261117.md) and [clipboard-pasted pictures](research/graphics-native-20261117.md) | Plain and default-header formatted text extraction. Bounded picture envelope inspection preserves binary payloads. |
| Worksheet 3.05 installation | [Native WKS controls and all five categories](research/worksheet-native-20261117.md) | Bounded read-only TOPLIST, cell, string-pool and cached-value inspection |
| Draw 3.05 installation | [Native FIG files and comparative controls](research/graphics-native-20261117.md) | Bounded `14 FIG` reader and SVG geometry preview for supported primitives. |
| Sound, RSX OEM 3.04 module | [Native synthetic tone and historical SND profiles](research/sound-native-20261118.md) | Original table and later linked readers, bounded music and speech decompression, one WAV per sample. |
| Music, RSX OEM 3.04 module | [Native SNG score controls](research/music-native-20261118.md) | Three voice streams and conductor, ordered event JSON and MIDI for supported linear scores. |
| Supporting DeskMate database structures | DMDB components, common DBCOLS/index framing and code-backed service thunks studied | Bounded read-only [shared parser](../src/deskmate_formats/database.py); no universal allocator or runtime loader binding proved |

The [DeskMate Preservation Workbench](preservation-workbench.md) uses these
readers to produce verifiable bundles and modern previews. Practical exports
include Worksheet and Filer CSV, Text and Draw SVG, Calendar iCalendar,
Address Book vCard, Sound WAV and MIDI for the measured Music subset. The
compatibility profile for each source governs inspection and conversion.

Names are scope categories, not claims about extensions or encodings. File signatures,
application versions and each application's storage model need independent evidence.
Related `.FIL` metadata, records and index structures have been observed in
Calendar, Address Book and Filer samples, but their complete storage semantics
and allocation policies are not interchangeable by assumption. See the
[dated project status](../PROJECT_STATUS.md).
