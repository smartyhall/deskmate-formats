# Tandy Appendix A: DeskMate Calendar data format

**Source:** *DeskMate Development System 03.05.00 Development Guide*, Appendix A Calendar (printed A-5 onward, PDF pp. 478–481) and common header (p. 476). **Status: manufacturer-documented; selected features independently native-verified elsewhere.** See [crosswalk](tandy-format-crosswalk.md), [Calendar index research](../research/calendar-index-trigger-20261117.md) and [native writer acceptance](../research/calendar-writer-maintenance-20261117.md).

**Version warning:** The guide calls its illustrative file `PERSONAL.CAL`; the actual researched 3.05 application writes `PERSONAL.CLN`. Preserve exact observed extensions and do not silently rename native files to match the printed guide.

## Logical tables and selection

Tandy describes one logical table per calendar, maximum **20** calendars, with default table `PERSONAL`; the shared `DBCOLS` metadata table is separate. New calendar table names are user-defined. The guide says PGSETUP's last member `bText` is repurposed as a **last-selected calendar index**: `DBCOLS` is table-name index 0, user calendars start at index 1. This is **documented application behavior**, not evidence that all PGSETUP `bText` fields have this meaning.

Each Calendar table has seven columns:

| Name | Maximum length | Database kind | Documented role |
| --- | ---: | --- | --- |
| `Date` | 3 | C | Encoded date or record classification |
| `DayOfWeek` | 1 | C | Encoded weekday/type |
| `Duration` | 1 | C | Described as unused |
| `StartTime` | 1 | C | Packed time/special marker |
| `EndTime` | 1 | C | Packed time/special marker |
| `Protected` | 1 | C | Alarm/record flag |
| `Description` | 120 | K | International-character string or configuration |

The guide specifies sort fields: `Date`, `DayOfWeek`, `StartTime`, `EndTime`, `Description`. It does not specify every tied-key collation, index subdivision or retirement rule. Use native evidence for those.

## Per-table configuration record

The guide describes a special record whose Date field is exactly `20 20 FF`, Protected is `30`, and Description stores application configuration data rather than appointment prose. It documents:

| Description subfield | Documented encoding |
| --- | --- |
| First displayed weekly hour | `0x61 + hour` (default hour 8 → `0x69`) |
| Last screen | `0x61 + screen ID`, where IDs 1 yearly, 2 monthly, 3 weekly, 4 daily |
| Number-of-changes placeholder | `0x61`; described unused |
| Three date placeholder bytes | `0x61` each; described unused |
| Eight changed-by placeholder bytes | `0x61` each; described unused |
| Eleven-byte code placeholder | Fixed printable token; described unused by Tandy |
| Calendar password region | No stored data, according to the guide |

Avoid publishing or depending on the source's legacy password placeholder as an authentication mechanism. The precise configuration-record body length and unused fields are **version-sensitive**, and our implementation must preserve opaque bytes.

## Event records

The guide describes a maximum of **20 events per day** per calendar. The ordinary event data encodings are:

- Date: three bytes `0x61 + (year − 1980)`, `0x61 + month`, `0x61 + day`; the guide's example is in the 1980s. Year wrap/valid range outside that period is unspecified.
- DayOfWeek: `0x61 + weekday`, with Sunday 1 through Saturday 7.
- StartTime and EndTime: one-byte packed quarter-hour time. Bit 7 set; bits 2–6 encode hour (0–24); bits 0–1 encode quarter hour 0, 15, 30, or 45 minutes.
- Illustrations: `0x81` corresponds to 00:15, `0x84` to 01:00 and `0xDF` to 23:45.
- Midnight start may be `0x80); midnight end is `0xE0`. If **both** time entries are left blank the guide describes `0x80` in each. If **only end** is blank it specifies `0xF0` for EndTime.
- Protected flag: `0x31` for no alarm, `0x71` for an event with an alarm.
- Maximum appointment description is **120 characters**.

These values are concrete test vectors. They should be checked against actual alarm on/off native files and against the modern codec rather than using them to overwrite unfamiliar stored bytes.

## Reminder and annual-occasion records

The guide describes a **combined limit of 70** reminder/annual-occasion items per calendar, with special weekday code `0x69` (corresponding to type code 8).

| Field | Reminder | Annual occasion |
| --- | --- | --- |
| Date | `61 61 61` (hex) | `0x61` year component, then `0x61 + month`, `0x61 + day` |
| DayOfWeek | `0x69` | `0x69` |
| StartTime | `0x80` | Usually `0x80`; special leap-day encoding below |
| EndTime | `0x80` | Usually `0xBC`; special leap-day encoding below |
| Protected | `0x31` | `0x31` |
| Maximum description | 60 characters | 30 characters |

For February 29 of a leap year, the guide describes a year-dependent marker of **`0x80 + (year − 1980)`** in both time fields, contrasting with the ordinary occasion markers. The scan has compressed/ambiguous wording around that exceptional rule; validate it with application-created 1984/1988 specimens if this feature becomes a priority. Do not treat the note as tested native behavior.

## Recommended native verification

1. Confirm ordinary date/time/flag table entries from known app-generated samples without relying on the guide's `.CAL` filename.
2. Compare otherwise-identical alarm-on and alarm-off events; verify `Protected` changes and any alarm-related side effects.
3. Generate one reminder and annual occasion, and isolate their special-type markers.
4. Generate a February 29 occasion in two leap years to resolve the ambiguous exception.
5. Switch between two calendars and test the reported `bText` last-selection index.
6. Keep row allocation, index balancing and deletion policy separate from *logical* record values; those are only partially documented by manufacturer material.
