# Future interoperability tools

The implemented Calendar reader currently exports diagnostic text/JSON with raw
bytes, record IDs/locations, decoded values, opaque internal records and warnings.
That output is **not** a stable general interchange schema or a lossless import
contract. Neither a CalDAV/CardDAV client nor an iCalendar/vCard converter
is implemented.

Calendar experiments [E15–E19](experiments/e15-page-boundary.md) have now
**observed** additional page allocation, retained deleted data and later
appends. The shipping reader/writer still reject those multipage layouts.
Address Book [A00–A04](research/addressbook-phase2.md) established bounded
single-contact field behavior; it does not yet have a reader or writer.

Next practical milestones are reliable Calendar date/time and multipage
read/write support, a bounded multi-contact Address Book codec, and independent
native DeskMate acceptance tests. Then define versioned, documented Python/JSON
interchange objects and per-field loss accounting. Keep raw/opaque DeskMate
fields where possible and report unsupported values rather than discarding them.

Future CalDAV/CardDAV mapping must distinguish unstable DeskMate storage record
IDs from stable external identifiers and settle timezones, recurrence, alarms,
text encoding, duplicate handling and conflict policy explicitly. Do not infer
those semantics from today's single-record or scheduled samples.

See [project status](../PROJECT_STATUS.md) for the current implementation
boundary and [compatibility](compatibility.md) for accepted input profiles.
