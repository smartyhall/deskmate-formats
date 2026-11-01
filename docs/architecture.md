# Architecture and scope boundaries

The current package is `src/deskmate_formats/calendar`: `personal.py` is the parser,
`writer.py` the experimental append writer, and `cli.py` the read/list/export CLI.
Writer CLI stays with the writer to preserve the verified implementation during
packaging. Only imports and private-test fixture selection were adapted; no format
algorithm was generalized during migration.

Conceptual layers guide later work:

| Layer | Current state / extraction rule |
|---|---|
| Binary reading and encoding utilities | Bounded reads/field rules remain in Calendar; extract a common helper only for a real second use |
| Database containers | Calendar profile plus [cross-application structural evidence](research/cross-application-db.md); no generic engine or cross-application API |
| Application formats | Calendar only; future siblings can be added after evidence establishes their structures |
| Conversion/interchange | Calendar JSON export exists; no general importer, iCalendar conversion or roundtrip guarantee |
| CLIs | Two installed Calendar commands; public Python API remains separate from listing presentation |
| Tests | Independent synthetic portable checks plus explicitly opted-in private archival regressions |
| Specifications/evidence | docs/formats, containers, experiments, evidence; original archive stays external |

There are deliberately no empty Address Book/Filer/Text/Worksheet/Draw modules,
common-engine base classes or conversion frameworks. A shared abstraction must have
experimental support and reduce real duplication, not encode an assumed .FIL family.
