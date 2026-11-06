# Calendar database findings from the DeskMate SDK

The Development Guide identifies Calendar's configuration row and explains
the extra E01→E02 change at `0x100D` as the saved screen mode. The database
headers identify Calendar's request packets and selector names. The
on-disk page and index implementation still depends on fixture evidence.
[Source identities](sdk-source-identities.md) · [Evidence notation and static method](sdk-calendar-dmcsr.md#evidence-and-method)

## What the application guide resolves

Development Guide Appendix A, Calendar (printed A-5 through A-8, PDF
pp. 478–481), describes the earlier `PERSONAL.CAL`. The 3.05 update
discussion (PDF p. 54) says earlier DeskMate 3 application data formats
carry forward and mentions the Address Book field-size change in 3.03.
The staged retail 3.03 `PERSONAL.CAL` has SHA-256
`c556b7f57102fc5432ce926317c8c0aa95cf8992d7fb64a72e2f270e4c517890`,
the same digest as the archived shipped 3.05 `PERSONAL.CLN` E00. This
is a stronger check for that default database than either filename or
the broad compatibility claim.

| Claim | SDK and independent evidence | Status |
| --- | --- | --- |
| Calendar schema and ordering | A-5 identifies one table per named calendar and seven columns, including the unused Duration slot. The names, widths and C/K types agree with all seven PERSONAL rows in DBCOLS. The documented sort keys are Date, DayOfWeek, StartTime, EndTime and Description, consistent with the parser's observed order. | D+R high for schema. General collation, tie handling and multiple tables still need validation. |
| Internal row ID `0x10` in E01/E02 | A-5 identifies a per-calendar config row with Date `20 20 FF`, Protected `30`, and configuration in Description. Both generated files match the three fields, with other fields empty. Calendar `9EE0..9F5F` builds the defaults and submits a three-column add. | D+S+R high. A record's semantic identity comes from its fields, not a universal row ID or absolute address. |
| Extra E01→E02 byte at `0x100D` | A-6 places saved screen mode at Description byte 1, coded as `0x61 + mode`. Calendar `A9AB..A9BB` stores the biased value in `DS:7CDB` and `A9BC` decodes it. The caller sets default mode 2 at `7266`, can read the saved value at `7288`, and stages the current mode at `72D5` before dispatching the view. The table-close path at `A101..A12F` invokes the three-column config update (`9F6D..9FC3`) with buffer `DS:7CDA` before closing the table. The preserved E01 month exit stores `63` and E02's day exit stores `65`. | D+S+R high. This resolves the observed extra byte as screen state. |
| Other config bytes | A-6 documents initial weekly hour at Description byte 0, followed after mode by unused biased bytes and a fixed marker. E01/E02 store `69` (8) and the same tail. `9EE7..9F20` initializes that payload. A-5 also identifies the active-calendar table index as a `PGSETUP.bText` use. | D+S+R high for defaults. Page-setup serialization and multi-calendar selection remain unverified. |
| Event date and weekday | A-7 specifies three date bytes biased by `0x61` (year relative to 1980, one-based month/day) and one biased weekday (Sunday=1). E01/E02 and historical E03–E07 values agree. The pinned Calendar add path `B06E..B07D` applies the bias to the first three bytes and weekday. | D+S+R high within observed inputs. Year limits, wrap and abnormal input behavior remain open. |
| Event time | A-7 specifies bit 7, hour in bits 6–2 and quarter-hour in bits 1–0. It distinguishes blank-time cases and midnight by field and context. The ordinary observed E01–E07 bytes agree. In particular the documented `80` can mean both times blank or midnight at start, with `E0` for end midnight and `F0` for blank end with a start. | D+R high for ordinary times. The sentinel combinations still need 3.05 data before expanding the parser. |
| Alarm and Protected | A-7 specifies `31` without alarm and `71` with alarm for an ordinary event. In 3.05 `C3DB` initializes the new event's low bits to `31`. The validated-Enter path at `C6A3..C6C3` combines them with `40` when checked. On load, `C396` tests `C0` and `C3B9` retains the low six bits. | D+S+R high for ordinary `31` and `71`. The [controlled Alarm save](calendar-alarm-encoding.md) changed only bit `40` in Protected relative to the no-op save. Bit 7 and other patterns remain open. |
| Reminder and annual occasion | A-7/A-8 describe a weekday code of 8 before biasing, type-specific date/time patterns and shorter text limits (60 and 30 versus 120 for events). The annual leap-day case repurposes time bytes. | D high for the documented formats. These variants need separate 3.05 file evidence. |

The [fixture regression](../../tests/portable/test_calendar_sdk_crosswalk.py)
checks the config signature, screen interpretation, unchanged config tail,
ordinary event formulas and observed terminators on E01/E02. Its oracle
comes from the SDK and recorded user actions. It uses the existing
read-only parser to locate rows and checks their raw bytes. It adds no
proprietary inputs and changes no parser or writer behavior.

## Database request crosswalk

`DMDB.H/.INC`, `DMDECL.H`, and Technical Reference chapter 6 describe
the database manager's selectors, packed call packets and bind modes.
`db_mgr` is declared variadic with a selector first. The OMF public
`_db_mgr_local` records in DM.LIB and DMMED.LIB load two words into
module data. DM.LIB's code at LEDATA `18F0F` reads `BP+4/+6` after
a near call, DMMED.LIB at `18FF5` reads `BP+6/+8` after a far call.
The pinned Calendar local dispatch at `D6CE` agrees with the near form,
including copying selector and argument to `DS:2A52/2A54` and the
selector-zero error `FFCB` (-53). Its internal wrapper `CDF8` takes
a third caller word that can trigger preparation, then forwards two
words to `D6CE`. The far dispatch boundary is distinct from the
public C call. The SDK identifies the requests even where the prior
runtime trace stopped short of the backend. See [binding](calendar-binding-25.md)
and [call review](database-call-review.md).

| Selector | SDK packet | 3.05 static correspondence and limit |
| --- | --- | --- |
| `0x0B` `FIRST_RECORD` | `db_get`, 16 bytes. Word offsets `0/2/4/6/8/A/C/E` hold table, destination, column count/list, query count/list, unsigned record number, and index handle. | `9FCD..A02C` populates this layout at `BP-14h`, destination `DS:7CDA`, one selected column (Description), one equality constraint on the config Date, zero record number and default index. `A035` saves returned packet `+C` into `DS:66D0`. This identifies the [previous lookup trace](lookup-trace-22.md) as config-row retrieval on this branch, with no direct trace of physical index reads. |
| `0x11` `FETCH_RECORD` | Same `db_get` packet, using the specified record number and a disabled query. | Sibling at `A03D..A053` reuses `DS:66D0`, zeroes query count, and issues the fetch. The branch does not initialize the query-array word locally. The chapter's zero-query contract does not establish every unused caller word is zero on this path. |
| `0x07` `ADD_ROW` | `db_add` leading words `0/2/4` are table, count and array. Each `db_value` is a pair of two-byte near offsets (column, value). The documented single-user packet also has previous/next record words `+6/+8`. | `B081..B0BF` passes six named values, and `9F25..9F5F` passes three for configuration. The leading fields match directly. The trailing neighbor words have no proven input values in those preparations. |
| `0x13` `UPDATE_ROW` | `db_update` has table, count, column names, old values, new values and record number at word offsets `0/2/4/6/8/A`. Verify byte `+C` precedes packed neighbor words `+D/+F`. | `B22F..B2C1` builds the six-column change packet and sets verify to 1. `9F6D..9FC3` builds the three-column configuration packet, with a null old-values pointer and verify 0. This identifies the requests statically. It does not show which backend branches actually execute or when the on-disk writes flush. |

The chapter 6 03.05 correction list (Technical Reference PDF p. 4)
broadens earlier version wording to 03.03 and later and clarifies read
binding and page-setup interfaces. The retail 3.05 resource names and
digests differ from the SDK and retail 3.03 database family. Shared public
selectors and packets establish a compatibility surface with those
version-specific backends. They do not establish a byte-identical engine.

## What stays empirical

- **Framing.** The SDK names `0x02` as an end-of-record token and describes
  its use after NUL-terminated fields in read buffers. E01/E02 show
  `01 02` at indexed row ends and `03` after the row list. The SDK
  corroborates the role of `02`. The disk's `01` separators, `03`
  list marker, row prefix and escaping still come from disk evidence.
  The header's minimum application data byte `0x07` makes reserved
  low values plausible. It does not specify on-disk escape handling.
- **Types and limits.** The header identifies C as the older character
  mode, K as character data using the DOS collation table for sorting
  and queries, N as numeric, and D as a date type described in Julian
  terms. Calendar's Date is C and uses the application encoding above.
  The documented 1,020-byte record maximum is compatible with 1,024-byte
  pages and overhead. It neither pins page offsets nor guarantees
  admissibility or allocation behavior at the boundary. The index
  separator macro gives `0x04`, while the C `db_index` member comment
  gives `0x0E`. Leave that API detail unresolved until matched to a
  verified caller or consumer. Neither text specifies disk separators.
- **Index and allocator.** FIRST/PREV/NEXT describe an on-disk index and
  logical record numbers. This supports the index role of observed
  triples without defining their width, target arithmetic or ordering.
  The exposed pack operation, deleted-record and page errors name
  capabilities. They leave the [measured page retention, reuse and
  pressure results](../experiments/e19-space-pressure.md), row-ID
  encoding, free space policy, counters, index chaining, and checksums
  dependent on differential fixtures or a verified engine path.
- **Additional record types.** The appendix is a source of predictions for
  reminder, annual occasion, blank time, and boundary values.
  Expanding the supported parser or writer profile needs generated 3.05
  evidence that distinguishes them, including malformed-input behavior
  and handling of dates beyond the observed range.
