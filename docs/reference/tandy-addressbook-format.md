# Tandy Appendix A: Address Book / Phone List

**Source:** *DeskMate Development System 03.05.00 Development Guide*, Appendix A Address Book/Phone List (printed A-3; PDF p. 477), plus common header (p. 476). **Status: manufacturer-documented; native reader and writer work exists separately.** See [crosswalk](tandy-format-crosswalk.md), [Address Book codec](../research/addressbook-codec.md) and [native second-contact evidence](../research/addressbook-two-contact-native-20261117.md).

The guide describes `PERSONAL.ADR` shared by Address Book and Phone List, with three **application-level tables**: CONFIG, NAMES and DATA. In actual DMDB files the physical **`DBCOLS`** schema table is also present, producing four total physical tables in the measured Address Book profile.

## CONFIG

| Column | Documented maximum size | Purpose |
| --- | ---: | --- |
| `UserId` | 10 | User or shared/network identifier |
| `LastList` | 20 | Last-accessed list name |
| `ConfigInfo` | 200 | Application configuration |

The manual is not a license to infer actual personal or network identity from an opaque record. Test structural representation using synthetic data.

## NAMES

| Column | Documented maximum size | Purpose |
| --- | ---: | --- |
| `Internal` | 20 | Internal name of a static DATA column |
| `Users` | 20 | User-facing name of that column for form letters |

This links Address Book schema metadata to Text's manufacturer-documented form-letter field syntax. The exact internal name spellings should be read from native files, not guessed from descriptive labels.

## DATA

The manufacturer describes **15 fixed data fields**, with user-defined list membership extending columns **16–40**. Sort order is **LastName / FirstName**. Its database-manager column-name operation can discover how many dynamic lists exist, but the documented explanation does not prove a runtime function selector in our environment.

| Number | Field | Maximum characters |
| ---: | --- | ---: |
| 1 | `Title` | 5 |
| 2 | `FirstName` | 18 |
| 3 | `LastName` | 20 |
| 4 | `Address` | 38 |
| 5 | `City` | 20 |
| 6 | `State` | 8 |
| 7 | `Zip` | 10 |
| 8 | `CompanyName` | 29 |
| 9 | `WorkPhone` | 20 |
| 10 | `HomePhone` | 20 |
| 11 | `DateOne` | 8 |
| 12 | `NoteOne` | 12 |
| 13 | `DateTwo` | 8 |
| 14 | `NoteTwo` | 12 |
| 15 | `Notes` | 40 |

Tandy calls `DateOne`/`DateTwo` eight-character **stored Julian date** fields, but does not specify their complete encoding on this page. List-membership columns beyond 15 are described as **one-character Y/N** values indicating whether a contact belongs to each user-defined list. Maximum potential list columns from the 16–40 range: 25.

**Explicit version note:** the guide labels `Title` as **10** and `Address` as **43** for DeskMate **3.3**, in contrast to widths **5** and **38** in this baseline. This is a documented change: do not silently treat data files from 3.3 as interchangeable with the 3.05 measured profile.

## Text interoperation

The Text appendix describes inline field spans using `0x05` (start) and `0x06` (end), with asterisks around an Address Book field name inside. For form letters, the application substitutes contact field values at **print** time, not necessarily into the saved document. See [Text reference](tandy-text-format.md). A minimal native test is one Text document containing an actual Address Book field token, opened/saved without printing, followed by a synthetic print/preview control if supported.

## Verification boundaries

- The listed field *sizes and logical labels* are manufacturer statements; raw DMDB `DBCOLS` rows and native writer tests determine exact machine encodings.
- Tandy's three application tables coexist with a physically present DBCOLS table; preserve both levels of counting.
- Native two-contact work demonstrates a bounded insertion/sort case, not every dynamic list, field, multi-page profile or tie-break rule.
- Prioritize first user-defined list creation, special date fields, and distinct LastName/FirstName order controls if expanding the codec.
