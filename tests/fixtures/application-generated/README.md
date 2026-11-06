# Byte-exact DeskMate application-generated research fixtures

Preserve files written by DeskMate during controlled experiments, including
native schemas, indexes, padding and metadata. Test records must be synthetic
or otherwise authorized for publication. Never normalize or reconstruct a
file and call it an original application-generated fixture.

Record each file under a named subdirectory (e.g. `calendar/E02.cln`).
Update `manifest.json` with its relative path, size, SHA-256, originating
application/version and experiment/actions (`origin`), plus
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
