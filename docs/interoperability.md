# Interoperability contract, version 1

Implemented: Python semantic objects, strict versioned JSON loading/export,
ordinary Calendar append generation and Address Book empty-to-one generation.
No CalDAV/CardDAV transport, server behavior or synchronization engine exists.
The [compatibility profiles](compatibility.md) and [campaign progress](../PROJECT_STATUS.md)
are authoritative about native format limits.

## Working Python interfaces

```python
from deskmate_formats.calendar.personal import parse_file
from deskmate_formats.interchange import export_calendar, load_document

calendar = parse_file('source.cln', profile='sdk')
result = export_calendar(calendar)  # Reject unrepresentable records by default.
document = result.document
items = load_document(document)    # tuple[CalendarItem, ...]
# Each item has .appointment and an optional .storage_record_id.
# For NEW additions, construct CalendarItems without existing storage references.
```

`Appointment(day: datetime.date, start_minutes: int, end_minutes: int,
description: str, duration_raw=b'', protected_raw=b'1')` remains compatible with
the existing Calendar API. Under `profile='sdk'`, `b'1'` is alarm off and `b'q'`
is on; only empty Duration is writable. `CalendarItem` wraps that value with an
optional native snapshot ID. JSON exposes the alarm as a boolean.

```python
from deskmate_formats.addressbook import Contact, create_contact, write_new
from deskmate_formats.interchange import ContactItem, addressbook_document, load_document

contact = Contact('Alex', 'Example', city='Metro', work_phone='555-0100')
document = addressbook_document([ContactItem(contact)])
item, = load_document(document)     # ContactItem(contact, storage_record_id=None)
# result_bytes = create_contact(empty_native_bytes, item.contact)
# write_new('NEW-OUTPUT.adr', result_bytes)
```

`Contact` validates the four populated fields supported by controlled UI evidence.
Other schema names are raw native fields, not additional interchange promises.
Reader diagnostics are a separate, richer output, retaining all raw fields.

## JSON envelope and validation

The envelope contains exactly `format: "deskmate-interchange"`, integer
`version: 1`, `kind: "calendar" | "addressbook"`, `items: [...]`, and optional
`source_sha256` identifying the snapshot from which an export was made. The hash
is provenance, not a unique external synchronization ID. Import validates at most
100 objects, including empty collections; that does not guarantee native capacity.

Calendar items require exactly `date` (YYYY-MM-DD), `start_minutes`, `end_minutes`,
`description`, `alarm_enabled` (boolean), plus optional `storage_record_id`.
Address Book items require exactly `first_name`, `last_name`, `city`, `work_phone`,
plus optional `storage_record_id`. Empty optional strings must be explicit.

Unknown keys, unknown versions, unsupported dates/time sentinels, non-ASCII input,
invalid widths, duplicate snapshot IDs and tied Calendar starts fail.
`InterchangeError` provides stable `code` and JSON-style `path` attributes.
Python serialization of an invalid native value raises `ValueError`; it never
silently drops nonempty Duration or unsupported Protected values.

Examples: [29-appointment 14-day export](../examples/calendar-14-days.v1.json)
and [25 fictional contact values](../examples/contacts-25.v1.json). The contact
example is a semantic collection, **not evidence of a 25-contact native book**.
The writer can create one separate file per contact from an empty source; it
rejects a second insertion. Calendar append still stops when the six-page profile
needs storage growth. Native readers/writers enforce their limits independently
of JSON validation.

## Preservation and explicit loss

Semantic export is not a byte-preserving native round trip. Retain the original
immutable native snapshot, its SHA-256 and all opaque bytes for future edits.
The Calendar configuration row, header, schema, indexes, unknown pages and
Address Book NAMES/CONFIG tables are not serialized into semantic JSON.
Supported append/create operations preserve them directly from the native source.
No native editing, deletion or JSON-to-native reconstruction without a source
template is implemented. Use `write_new` to avoid overwriting source files.

`export_calendar(db)` fails on unrepresentable ordinary records.
`export_calendar(db, lossy=True)` skips them and returns `ConversionIssue` entries
with code `skipped_record`. It does not invent text, timezones or recurrence.
`export_addressbook(book)` fails when opaque contact fields differ from the
observed defaults, or known fields cannot be represented by `Contact`.
With `lossy=True`, nondefault opaque fields are omitted with
`omitted_opaque_fields`; unrepresentable contacts are skipped with
`skipped_record`. Every issue includes its native record path. Callers must retain
and display the issues; explicitly opting in is required. Raw source objects are
never modified. Defaults Birthday/Anniversary/`n` retain their observed bytes;
their absence from JSON does not decode date/boolean semantics.

Storage IDs are **not stable external IDs**: E11/E12 demonstrate reassignment.
An exported ID is meaningful only with its source snapshot and is diagnostic
context, not a requested allocation ID. `load_document` keeps it on the typed
item; callers retain the envelope's source hash. New generation APIs assign IDs
under their bounded native profiles, never from an imported synchronization ID.
No stable UID is invented or derived from names, descriptions, dates or IDs.

## Application evidence and next integration gates

E15 was performed: it observed the seventh page; E16 retained deletion bytes;
E17/E18 appended after retired data; E19 observed the eighth page. These correct
the old roadmap's stale “E15 remains unperformed” statement. The current extended
reader can read bounded indexed pages, but opaque allocation-header changes still
block a general writer. [E15](experiments/e15-page-boundary.md),
[E19](experiments/e19-space-pressure.md).

The newly generated 14-day Calendar has independent offline validation. Four
Address Book reconstructions match published native hashes. No new generated
file was opened or saved in DeskMate in this campaign. Native confirmation of
SDK date/time combinations and multicontact indexing is a separate authorized
experiment. Timezones, recurrence rules, non-ASCII encoding, all-day events,
date-only contacts, collation/ties, native edits/deletions and stable external-ID
mapping need explicit future designs and evidence before bridge implementation.

## Proposed future CalDAV precision and change-detection policy

**Operator decision (not implemented):** For events that have greater timing
precision than DeskMate's supported ordinary quarter-hour model, project the
start **down** to the preceding quarter-hour and the end **up** to the next
quarter-hour. Manual [Add Event UI observations](research/calendar-ui-time-normalization.md)
support this rounding rule for tested examples, but have not independently
established every native encoding or boundary condition. Do not change the
current strict version-1 interchange loader/writer to silently round times.

A future synchronizer must retain both (a) the precise original external
value and stable external event identity and (b) the **last projected value
written to DeskMate**, with a relevant source snapshot and mapping metadata.
Compare each DeskMate readback against that last projection. If unchanged,
**preserve the original external precision**, including seconds or timezone
metadata, rather than treating projection as an external edit. A description-
only edit should not erase unchanged precise start/end values.

If the projected native start/end value **has** changed, treat that confirmed
native time edit as authoritative for the affected time field(s), accepting
quarter-hour precision loss for those edited values. A user opening/saving an
unchanged native event does not establish a distinct time edit; do not infer
intent that cannot be observed. An event modified independently in both systems
must trigger explicit conflict handling, not silent overwriting. Storage record
IDs can change after native edits and must **not** stand in for stable external
UIDs or justify blind deduplication.

Two precise external starts may round to the same native start on the same day.
The existing writer rejects these tied keys; future bridge work must report
and handle collisions explicitly instead of dropping or merging appointments.
Changes that project to the same native time values should not trigger
unnecessary native rewriting. These rules belong to a **future synchronization
layer**, outside the existing native page codec and version-1 interchange API.
