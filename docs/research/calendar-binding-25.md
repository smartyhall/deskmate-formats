# Calendar INT E0 binding: recovery and static boundary

2026-11-02; [issue 25](https://github.com/smartyhall/deskmate-formats/issues/25).
Continues [the selected request](lookup-trace-22.md) and
[the database call review](database-call-review.md). No native execution.

## Recovery checkpoint

The interrupted investigation created `research/calendar-binding-25` from
main `391c0ca` in one separate worktree. Recovery reused it. The worktree was
clean; earlier research worktree heads matched the recorded baseline. Private
scripts, vector scan, source hashes and the 11,392-file preservation baseline
survived under DOSLAB `EXPERIMENTS/RESEARCH/calendar_binding_25`.

The baseline exception is one temporary Ghidra database page already absent
when the baseline was taken. This is not evidence of a change by this task.
Historical manifests remain unchanged. Both new Ghidra imports stopped before
the probe script ran: the normal launcher exceeded its bound and its owned
Java process was terminated; the direct-Java attempt terminated at its
300-second bound during import. Neither produced a verified instruction
listing. Their incomplete projects and logs are retained privately. Recovery
found no surviving process from either attempt. Existing MCP services were
left alone. No GUI, emulator, VM, configuration or original database was used.

## Evidence standard and current conclusion

**H** means original bytes and explicit MZ/address arithmetic; **M** means a
functional interpretation; **U** means unresolved. File offsets are absolute
hexadecimal. A byte scan identifies candidates, not instruction boundaries.

Calendar's slot remains unresolved. The raw binding sequence supplies
`ES=DS`, `BX=2A62`, `DX=2944` and selects `AX=0206` or `020C` before the
interrupt at file `D800`. The old trace's call at `DEAD` still reads the
four-byte slot at file `114D2`; its segment word has no MZ relocation.
No callback/export selection or forwarding into DMDBRD has been established.

DESK.EXE contains vector get/set candidates and a possible AH=02 dispatch
table. These are **provisional** at this checkpoint: failed Ghidra imports
must not be counted as validation. In particular, an on-disk installation
path does not identify the actual runtime interrupt vector. That distinction
is required even if the candidate path is subsequently validated.

| Original image | SHA-256 |
|---|---|
| CALENDAR.PDM | `819df5658b663aa69b15584abf805062679e97f587f3404738f6e82876e4bd23` |
| DESK.EXE | `0f2a40243c997276904d2555a117c60eedf0016dde073285e8d63c8345a2eba3` |
| DMDB.R89 | `799444bb8c04632d261f61498ba269f9352e5528718f2e0a89512bf6ef7b808f` |

The originals are the preserved F00 before installation. Recovery rehashed
them; no binary or proprietary listing is included here. Public observations
will be extended only after bounded instruction and relocation checks.
