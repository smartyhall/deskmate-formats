# Address Book codec checkpoint

New offline implementation, 2026-11-07. Sources: [A00–A02](addressbook-phase1.md),
[A03–A04](addressbook-phase2.md), [common storage](database-campaign.md), and the
preserved empty ADR with SHA-256
`cb890e6d7ba96fafb5a5d3991e208f4de862bee485f6ce32696e989c97d3394c`.
The full original A01–A04 archives were not recovered in this checkout.

## Reader and field confidence

`deskmate_formats.addressbook.parse_bytes/parse_file` validates the ten-page
profile, four tables and exact DBCOLS definitions. Live DATA rows are enumerated
in stored index order, without assuming that order's collation policy. All sixteen
raw values, raw row bytes, index/row locations, full source bytes and opaque
unrelated tables are retained through `AddressBook.storage`.

| Python field | DATA schema name / zero-based slot | Width | Evidence |
| --- | --- | ---: | --- |
| first_name | FirstName / 1 | 18 | A01/A02 controlled First Name length |
| last_name | LastName / 2 | 20 | A01 visible Last Name and saved/reopened value |
| city | City / 4 | 20 | A04 independent City population |
| work_phone | WorkPhone / 8 | 20 | A03 independent phone shortening |

Widths and the other twelve schema names are original-byte observations from
DBCOLS, not an assertion that all UI behaviors are known. Address, CompanyName,
HomePhone, Title, State, Zip, Notes and the date/default fields remain raw.
In particular `Christmas='n'` is not interpreted as a boolean. Birthday and
Anniversary are retained application-written defaults, not entered dates.
Non-ASCII verified fields return null in `known_fields` while retaining bytes;
there is no automatic CP437 or Unicode conversion.

Reader bounds: 10,240 bytes; data/index page pairs 2/3, 4/5, 6/7, 8/9;
low-ID page-local rows; no extra pages, retired rows or missing trailing fields.
Multiple independently framed synthetic contacts are readable, with an explicit
warning that native ordering is unverified. This is not native multicontact evidence.

## Experimental writer and independent oracle

`Contact(first_name, last_name, city='', work_phone='')` validates printable ASCII,
declared widths and nonempty first/last names. `create_contact(source, contact)`
accepts only an empty DATA table with the observed next-ID 16, opaque token 000
and trailing directory tokens 3/2. It inserts ID 0x10, the sixteen-field default
profile, one index triple and counters 1/17. It checks every changed byte against
the insertion/counter/index spans and preserves all unrelated bytes. `write_new`
uses flushed hard-link publication and fails if the target already exists.

All four generated reconstructions match the independently published **whole-file
native SHA-256** values exactly:

| Case | Varied field | Generated SHA-256 |
| --- | --- | --- |
| A01 | TEST / USER A / 202-555-0142 | `19215ea147c65b259eb963fd240e9931d96e77f92d1001f0f7edf89024076ac8` |
| A02 | First TESTLONG | `ae216968bce070f7a5d9619b844e20295428dac628984a05d22f203e032d76a6` |
| A03 | Phone 555-0142 | `81b48761fce08c57cbe43a3bb0a23fc4f7d2faee0cdb800375c9175220787d5d` |
| A04 | City METRO | `2584874c957d74b0c1240ebc0d02a50ac4c886a53b977749cb912e1628cce46f` |

These are newly tool-generated reconstructions, preserved privately, not recovered
application-generated originals. No new DeskMate open/save was performed. Native
evidence is the historical A01–A04 observations; the new check establishes exact
byte agreement. Other field combinations and lengths are offline-verified only.

Eight portable tests cover independent complete-byte synthetic oracles, width
boundaries (including opaque Address/CompanyName), non-ASCII retention, malformed
schema/framing, immutable source, no-overwrite publication, cleanup and CLI use.
Two focused private tests passed against the hash-pinned locally preserved empty
baseline, checking all four native hashes and unrelated table/header preservation.
Run these with explicit `DESKMATE_ADR_BASELINE` or the original `DOSLAB_ROOT`:

```sh
python -m unittest discover -s tests/portable -p test_addressbook.py -v
python -m unittest discover -s tests/private -p test_addressbook_writer.py -v
```

## Generated contact dataset and unsupported boundary

`addressbook.samples.contacts()` returns 25 deterministic fictional contacts.
`tools/generate_addressbook_samples.py EMPTY.adr NEW-DIRECTORY` writes **25 separate
one-contact files**, reusing only the unchanged empty source. A manifest pins
every output and synthetic value. Actual outputs/manifest are privately archived;
[public hashes](../evidence/database-campaign.json) preserve reproducibility.
This is **not** a single 25-contact book; the minimum multicontact target is unmet.

The writer rejects insertion into a nonempty book. A single observed index cannot
establish multiplerow sort keys, tie/collation rules, counters or physical append
policy. The descriptor's trailing 3/2 tokens are suggestive, not sufficient proof.

Smallest discriminating native trial, **not authorized/executed**: clone verified
A01; add exactly First ZULU, Last ALPHA, City blank, Work Phone 555-0100, then
save/exit once. Compare count/next-ID, both index triples, physical spans, original
row preservation and all other installed files. Last-name sorting predicts the
new index entry before USER A, TEST, unlike physical append or first-name sorting.
A later same-last-name contact would distinguish secondary ordering. Stop on
ambiguous acknowledgement; no replay. No multipage or mixed-case claim follows.
