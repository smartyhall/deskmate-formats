# Read-only structural inspection

Run from a checkout with the project installed, or set PYTHONPATH to src.
The helper imports the existing Calendar block-size and index-header constants;
it does not broaden Calendar parsing or writing.

```text
python tools/inspect_structure.py compare LEFT RIGHT --left-offset 0x800 --right-offset 0x800 --length 0x98
python tools/inspect_structure.py blocks FILE --block-size 1024
python tools/inspect_structure.py triples FILE --offset 0xc28 --count 29
```

Arguments are explicit investigation assumptions. For CARMAINT schema use29
triples (28 entries plus zero candidate); INVNTORY27, ADR28, and the inspected
Calendar14. Count is never inferred from a filename, magic or arbitrary nonzero
bytes. A zero tuple is reported and does not terminate a probe. An out-of-range
target is reported without dereference; a requested input span extending past EOF
is rejected. Prefix comparison is restricted to the existing observed ID range
10–7F hex. No general variable-ID encoding is implied.

Comparison uses exact caller-selected spans, with maximal contiguous unequal
runs and absolute offsets in each input. It does not heuristically align padding.
Block maps retain short final blocks and report hashes, nonzero-byte counts and
whether the existing Calendar index header matches. Divisibility or header match
alone is not a page classification.

Every command emits JSON to stdout with input sizes/hashes. Store output privately:
difference bytes and candidate prefixes can contain proprietary data. There is
no output-file option or native-write operation. Shell redirection remains the
operator's responsibility; never redirect onto an input. Native files are opened
for reading only. Commands do not launch DeskMate or use the emulator.

This complements private lab.py (dumps/strings/numbers/snapshots/heuristic diff)
and the production Calendar codec. It deliberately avoids schema discovery,
automatic record decoding, engine abstraction, export/import or universal parsing.

Five synthetic tests cover independent offsets, exact difference runs, EOF and
negative bounds, explicit block arithmetic, invalid offsets and unknown IDs,
zero tuples, partial blocks, CLI JSON and input content/mtime preservation.
Five opt-in private tests check the shared152-byte region, all14 table indexes,
retired Filer candidates, the counter exception, native ADR variants and Filer
empty/populated DATA. Run:

```text
python -m unittest discover -s tests/portable -p test_structure.py -v
python -m unittest discover -s tests/private -p test_cross_application.py -v
```

The second command requires DOSLAB_ROOT pointing at the existing private lab.
Tests never fabricate native acceptance or use the tool to modify evidence.
