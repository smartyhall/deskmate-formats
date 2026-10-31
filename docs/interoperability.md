# Future interoperability tools

Current interchange is the parser's JSON listing: raw bytes, IDs/locations, decoded
values, opaque internal records and warnings. It is diagnostic output, not a stable
general interchange schema or a lossless import contract. No converter is claimed.

Future milestones: controlled page-allocation evidence (E15 remains unperformed),
additional date/time/character encodings, index tie rules, explicit schema versions,
then separately reviewed import/export tools with loss accounting for unsupported
values. Address Book/Filer/Text/Worksheet/Draw require their own investigations
before conversion design. Never silently invent timezones, alarms or field meanings.
