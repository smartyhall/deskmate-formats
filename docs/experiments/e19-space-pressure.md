# E19: page-space pressure — in progress

## Status: first input/record-length gate verified; boundary not yet reached

This is an intermediate preservation checkpoint, not a page-reclamation result.
The original E16 seven-page baseline and complete 126-file installation were
verified; SHA-256 818c44af2f351cc764dfd48a82b3d8ae1dd0b5f733c8549dbdd902f67eed05ea.
No E17/E18 output was used. Original executable/profile/debugger guards remain
unchanged. Production Calendar parsing/writing is unchanged and remains bounded.

## Predeclared design

Page 6 starts at0x1800. Its retained24-byte retired row occupies1800..1817 and
03is1818. Reserving a new03 leaves999 contiguous append bytes. Observed60-character
ASCII descriptions require77-byte records (17bytes framing/fields). Twelve use
924bytes, predicting03at1BB4 and75append bytes remaining. A thirteenth77-byte row
would exceed capacity by2bytes. Reclaiming24retired bytes could allow all13live
rows1001bytes plus03 and22zero bytes. The old24-byte hole cannot directly hold
one77-byte row. Neither compaction nor new-page allocation is assumed.

The index has17live6-byte triples and room for163with a full zero sentinel;
30after13additions remains safely within capacity. Planned events use distinct
November2..14,2026 dates,11AM–noon,alarmoff verified visually. Descriptions are
P1901..P1913 followed by A0123456789B0123456789C0123456789D0123456789E0123456789:
exactly60ASCII characters. This grouped suffix replaced a homogeneous55X suffix
in a documented pre-mutation amendment, preserving length while making visual
head/tail verification easier. The upper authorization is14; the plan stops at
13or the first earlier storage transition/error/ambiguity. No unrelated edits.

Full clean checkpoints: originalE16; afterfirstevent length gate; after12ordinary
fits; afterfirstcrossing decision13. Sequential verified disposable copies form
segment01→segment12→segment13; each source comes only from the prior cleanly
closed checkpoint. This is one bounded sequence, not independent variant trials.

## First gate: observed

Exactly one original-application event was saved: November2,2026,11AM–noon,
alarmunchecked, exactP1901plusgroupedsuffix. Independent descriptionhead/tail
screenshots cover all60characters with overlap; complete fields were checked
before one submission. The saved schedule shows the complete wrapped text once.
Calendar and emulator exited normally before the full after snapshot.

OnlyPERSONAL.CLN changes,88byte positions, still7168bytes. Row77bytes at1818,
ID22hex,index1482 `(6,18,22)`; new03at1865. Retired24bytes/ID21remainunchanged and
unindexed; all17originalindexedrowsrawbytes/IDs/addressesstable. Headerpage0and
originalpage4unchanged; count00017→00018,next-IDcandidate00034→00035,opaque001
unchanged. Full126source/before/after and14protectedhash-and-mtimeguards pass.
AfterSHA256:843b6a6b7ac5d317c858454b6047b1c305dff852301dc7640b11afa8d0a32299.

Private plan, actions, every changed byte, block hashes, rawobservations, MCP
replies, BIOS bytes, screenshots and full installations remain under DOSLAB
EXPERIMENTS/PHASE2/E19_space_pressure/segment01. No original database or software
is distributed. Next safe action is the verifiedsegment01after copy for events
02..12, then cleanly exit and measure before crossing. No boundary conclusion,
newheadersemantics,generalallocator or productionmulti-page support is claimed.
