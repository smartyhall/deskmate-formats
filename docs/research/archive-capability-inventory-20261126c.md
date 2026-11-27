# Successor checkpoint 2 — integration corrections and ARC method 8

Campaign `freebuff/archive-qualification-2`, base `cca20c2` on the predecessor
branch. This checkpoint exists because two CI failures and one unresolved
format question were open at the same time; it closes them in that order.

## The Python 3.14 `compression` collision

PR #194 failed all four portable configurations under Python 3.14 with 41
errors. The cause was a module name, not a decoding bug. `tools/archive` is put
on `sys.path` by the archival tools, so `tools/archive/compression.py` took the
name `compression` for the whole process. Python 3.14 added a standard-library
`compression` package (`compression.bz2`, `.gzip`, `.lzma`, `.zlib`, `.zstd`),
and whichever of the two reached `sys.modules` first broke the other.

This was reproduced rather than inferred. A CPython 3.14.0 embeddable runtime
was downloaded to a temporary directory outside the repository, and the
pre-fix commit `36226e3` was checked out into a throwaway worktree. Running the
archive suites under 3.14 gave 35 errors there, with two distinct shapes:

```
AttributeError: module 'compression' has no attribute 'decode_unix_compress'
AttributeError: module 'compression' has no attribute 'DECODERS'
```

The first is the standard-library package answering an import from our test,
the second is our own extractor importing the standard-library package when it
expected the project module. Both directions happen in one suite, which is why
the failure count was larger than the number of affected files.

The module is now `compression_streams`, which is the alias the extractor
already used internally. Nothing about the decoding changed. Three regression
tests were added in `tests/portable/test_archive_module_names.py`:

| Test | What it fixes |
| --- | --- |
| `test_no_archival_module_shadows_a_standard_library_name` | Audits every `tools/archive/*.py` stem against `sys.stdlib_module_names`, so the next such collision fails on 3.13 too. |
| `test_stream_module_imports_after_the_standard_library_package` | Imports the module with a stand-in `compression` package already in `sys.modules`, and checks the stand-in is untouched. |
| `test_extractor_imports_while_the_standard_library_package_is_loaded` | Repeats the first case through `intelligence_extract`, which is where the real failure surfaced. |

The same 49 archive tests were then run under the 3.14.0 runtime and passed.
That is a local check of one interpreter build on Windows, not the CI matrix;
Linux 3.14 remains covered by CI. No other module in `tools/archive` collides
with a standard-library name.

The REUSE failure on PR #195 had a single cause: the successor usage receipt
had no sidecar. It now carries the same terms as the campaign's earlier
receipt.

## ARC method 8: the conventions that were missing

The previous checkpoint recorded a documented negative result — a decoder that
reproduced one member's unpacked length but no member's CRC. The useful part of
that result was the four CRC-bearing genuine members sitting in the corpus, not
the failed hypotheses. Two of them are small (128 and 726 unpacked bytes), which
makes a bit-level search tractable instead of speculative.

The resolution came from reading an independent implementation rather than
trying more combinations. Nomarch 1.4 (Russell Marks, GPL-2.0-or-later) was
fetched from the Debian source archive into a temporary directory and read.
Its `readlzw.c` documents three behaviours that the previous model of the
format did not contain:

1. **Codes are padded into groups of eight.** ARC's encoder completed the
   current group before a code-width change, so a decoder must discard the
   remainder of the group at the *old* width. Nomarch's comment calls this the
   detail that cost the author the most time, and it is the first divergence a
   naive decoder hits.
2. **Code 256 does not clear the string table.** It only returns the code width
   to nine bits and lets new strings overwrite entries above 255, so
   back-references to shorter codes keep resolving. A decoder that clears the
   table on 256 desynchronises from the first shrink onward.
3. **RLE90 is applied after LZW, to the decoded byte stream**, not to the LZW
   input. `0x90 0x00` is a literal `0x90`; `0x90 n` repeats the previous byte
   `n-1` times.

Method 8 also begins with one byte holding the maximum code width, always 12.
Method 9 is the same decoder at 13 bits with no leading byte and no RLE stage;
nomarch's method table confirms the pairing.

## Confirmation on genuine material

The rules were implemented natively and run against both ARC archives in the
TVDog mirror. Every method-8 member now reproduces its stored CRC and consumes
its packed bytes exactly:

| Archive | Member | Method | Packed | Unpacked | Stored CRC | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `t1kbootf.arc` | `BOOTFIX.DOC` | 8 | 3306 | 6195 | `A963` | match |
| `t1kbootf.arc` | `BOOTFIX.SYS` | 8 | 411 | 726 | `F1C8` | match |
| `t1kbootf.arc` | `INT19.COM` | 2 | 2 | 2 | stored | match |
| `tandykey.arc` | `TANDY.ASM` | 8 | 2925 | 5366 | `6ADD` | match |
| `tandykey.arc` | `TANDY.COM` | 8 | 118 | 128 | `79BB` | match |

Both archives now extract with status `ok`, five members of five, with no
external decoder. The CRCs come from the original archiver, so this is
independent of our implementation: a wrong bit convention cannot reproduce
four unrelated CRC-16 values by accident. What it does not establish is
generality beyond method 8 and the two archives, and the CRC covers only the
unpacked member, never the header.

Nomarch itself was not invoked and is not committed. The repository code is a
native implementation whose conventions are documented in the decoder
docstring; the nomarch source informed the reading of the format, and its
licence (GPL-2.0-or-later) would have been compatible with this project's
GPL-3.0-or-later, but no third-party code was copied. Nomarch remains an
optional backend for methods 5 and 6, which use a hashed 12-bit table that has
not been studied here.

## Synthetic coverage

`tests/portable/test_arc_crunch.py` adds an encoder that writes the confirmed
conventions, including group padding, the shrink code and the RLE90 stage. It
proves that encoder and decoder agree; it cannot prove the convention is right,
which is why the genuine CRC table above is the qualification and the encoder
is only the regression harness. The cases are literal and repeated strings,
RLE90 runs and literal escapes, growth through ten and eleven bits, table
saturation with a 256 shrink, method 9 without RLE, an output budget, a
corrupted member, a truncated member, a stored-member size mismatch and the
still-unsupported method 5.

## Resource and process observations

Two measurements are worth passing to the performance campaign. They come from
the failed PR #194 runs, so they compare failure modes rather than successful
work, and the skip counts differed:

| Platform | Interpreter | Tests attempted | Wall time |
| --- | --- | --- | --- |
| Linux | 3.14 | 804 | 78.996 s |
| Windows | 3.14 | 804 | 428.812 s |

The same 41 errors appeared on both, so the difference is platform overhead,
not a different test set. This is not a controlled benchmark and is recorded
only as a durable observation.

A later run of the same branch that passed every configuration gives the
matching successful numbers, recorded here because they compare like with like
and the failure-mode figures above do not:

| Platform | Interpreter | Job wall time |
| --- | --- | --- |
| Linux | 3.13 | 2 m 09 s |
| Linux | 3.14 | 2 m 16 s |
| Windows | 3.13 | 9 m 07 s |
| Windows | 3.14 | 8 m 21 s |

Windows takes roughly four times as long on an identical, passing suite, and
the two Windows figures reverse the interpreter ordering, so neither the
platform ratio nor the interpreter difference should be read as a refined
measurement. What the pair of runs does show is that the platform gap is in the
suite's execution and not in the 41 shared failures.

The full portable suite was again not run locally; the supervisor and observer
subprocess tests exceed the local budget. Focused suites and CI carry the rest.

## Remaining limitations

- ARC methods 3, 4, 5, 6 and 7 remain unsupported. Methods 5 and 6 need the
  hashed 12-bit table; method 4 is the CP/M `SQ`-style Huffman form.
- Method 9 has no genuine specimen, so its code path is covered synthetically
  only.
- A CRC mismatch is reported as a generic read error, not as its own status.
- The three identification axes are still absent from the archive index schema.
- TeleDisk advanced compression, CopyQM against genuine media, Tandy containers
  and the XDF geometry layer are unchanged from the previous checkpoint.

## Revised resumable record

1. **ARC methods 3 to 7**: narrowed to the hashed static 12-bit table (5, 6),
   the Huffman form (4) and the RLE-only form (3). The dynamic decoder is done.
2. **TeleDisk advanced (LZSS/Huffman)**: unchanged; one genuine advanced
   specimen held.
3. **CopyQM against genuine media**: unchanged and still fixture-only.
4. **ZOO, SQZ, HA, UC2, DWC and PAK**: unchanged, still needing header layouts.
5. **FAT32 and VFAT hardening**: the structural reader exists; multi-slot long
   names, cycles, cross-links and FSInfo are not yet covered by tests.
6. **Tandy JV1/JV3/DMK/VDK/JVC and the Tandy filesystems**: unchanged.
7. **Archive index migration**: proposed direction recorded, not implemented.
