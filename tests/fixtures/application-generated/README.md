# Byte-exact DeskMate native-format research fixtures

Preserve files written by DeskMate during controlled experiments, including
native schemas, indexes, padding and metadata. A separately identified
**tool-generated compatibility candidate** may also be preserved if it is
derived entirely from an approved synthetic source and its independently
verified bytes are necessary for a native acceptance test. Test records must
be synthetic or otherwise authorized for publication. Never normalize or
reconstruct a file and call it an original application-generated fixture.
Tool-generated candidates must explicitly say they are **not** application
output and describe their actual native validation status, including limits.

Record each file under a named subdirectory (e.g. `calendar/E02.cln`).
Update `manifest.json` with its relative path, size, SHA-256, target
application/version, exact source/experiment/actions (`origin`), evidence class,
plus
`"synthetic_data": true`. Give every binary an adjacent REUSE `.license`
sidecar declaring accurate contributor rights in test data under
`GPL-3.0-or-later OR CC-BY-4.0`; native structural facts are not claimed
as proprietary project expression.

Do not include installers, ROMs, executables, full installed trees, disk
images, real user data, screenshots or raw RAM. Archive non-publishable
evidence durably outside Git.

The repository audit verifies exact bytes against the manifest. Historical
fixture hashes do not supply missing fixture bytes. Data files are tracked in
Git but deliberately excluded from the Python distribution archives.

The file `calendar/sdk-14-days-tool-generated.cln` is a **newly recreated
compatibility candidate**, not a DeskMate-produced original: 29 appointments
across October 23–November 5, 2026. Its hash matches the prior privately
archived generated output. The E02 source fixture is unchanged. See
[issue #69](https://github.com/smartyhall/deskmate-formats/issues/69) for the
remaining hash-pinned controlled-save acceptance procedure. The operator reports
all 29 appointments and displayed alarm states appear as expected in DeskMate
3.05; [the dated report](../../../docs/research/calendar-14-days-operator-report.md)
records the successful display milestone and untested persistence/alarm firing.

The complete `calendar/sdk-30-days-allocator-tool-generated.cln` is a
**tool-generated, not application-generated or native-accepted** 8,192-byte
candidate: 61 appointments over October 23–November 21, 2026, with data chain
4→6→7. It independently reproduces the archived allocator candidate byte for
byte. Its [expected listing](calendar/sdk-30-days-allocator-tool-generated.expected.json)
includes every appointment and its record/page/index locations. Use the
[download and native inspection guide](../../../docs/research/calendar-30-day-native-acceptance.md)
for exact identity, all 30 dates, displayed times/alarms and the separate optional
edit/save trial. Directory placement does not change evidence classification.

The exact `native-second-empty-calendar-operator.cln` file is a **user-supplied, native application-produced change to a synthetic source**. The operator reports adding an empty named calendar `Second` to the 61-event Calendar through DeskMate 3.05. The resulting 10,240-byte file contains the original `PERSONAL` events and a new `SECOND` table with its internal configuration row but **zero SECOND appointments**. SHA-256 is `338487558d9992452db15858de1ba9cf790c26abf990ba70b47bbc9dc8d011f5`. The three original appointment data pages are byte-identical, while an existing index page has been physically rebalanced. See [the analysis](../../../docs/research/calendar-multitable-second.md) and [issue #81](https://github.com/smartyhall/deskmate-formats/issues/81). This specimen has only operator-reported guest provenance; it is not a separately instrumented native save/persistence trial.
