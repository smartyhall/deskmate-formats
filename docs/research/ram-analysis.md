# Offline RAM-region analysis

This development helper reads private raw captures, never a live guest or database.
Its output is candidate RAM text, not a claim about the active screen. Screen
identity, selection, focus, coordinates and control-byte meanings remain unknown.
Existing three-positional-argument use remains valid; JSON adds provenance and raw
bytes. Inputs are limited to the investigated conventional RAM range0..0x9FFFF,
with a positive length and physical base whose entire capture fits that range.
Each selected analysis window must be1..256bytes and covered by every input.

## Explicit text extraction

```text
python tools/read_ram_text.py <short-capture> 0x1266e 44 --base-address 0x12640 --physical
```

Without --physical, the positional offset is relative to the file. With it,
subtracting --base-address yields the file offset. JSON includes both offsets,
capture size/base/SHA-256 and the selected raw hex bytes. Text extraction rejects
any non-printable ASCII byte instead of replacing it or guessing an encoding.
No memory address is discovered automatically or treated as universal.

## Compare the same physical region

```text
python tools/read_ram_text.py <full-capture> 0x12640 160 --physical --compare <short-capture> --compare-base-address 0x12640
```

The first base defaults to0. The second defaults to the first unless explicitly
supplied. Comparison preserves every byte of both bounded windows as hex and
lists every changed byte with its physical and capture-relative offsets. Each
side also lists maximal printable ASCII runs of at least4bytes. Binary bytes are
valid comparison input and remain in raw context. Short text runs are omitted
only from candidates, never from raw data or differences. Unchanged candidate
text can be a resource, cached value or stale content; changes do not establish
visibility either. Full capture hashes identify the actual input bytes.

All examples require privately obtained captures. No RAM, screen images or DeskMate
software is distributed. Synthetic portable tests cover offset conversion, shifted
capture origins, all-byte differences, raw context, immutability, unchanged text,
invalid encodings/ranges and CLI JSON/error behavior. The helper does not determine
the emulator's state, resume it, interpret a text-grid structure or write memory.
