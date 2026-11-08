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
