"""Decode standalone compression streams with explicit bounds and provenance.

Each decoder returns one opaque payload. Nothing here guesses a member name
from archive-controlled bytes: the caller supplies the derived label and
remains responsible for recursion, persistence and hashing.

Bounds are enforced on *output* bytes, so a small hostile input cannot expand
without limit. Truncated input, trailing garbage and an unrecognised method
are reported rather than repaired.

``Bounds.decoder_bytes`` is deliberately separate from ``output_bytes``. A
decoder's working set does not track the payload it produces: xz allocates a
dictionary that the stream header declares, bzip2 allocates several block-sized
tables (its remembered block size is bounded by the header digit), and the
compress(1) state machine keeps two ``2**maxbits`` tables. Bounding output
alone therefore does not bound memory, so each decoder constrains its own
structure and the number of concatenated streams it will open.

The module is deliberately not named ``compression``. Python 3.14 added a
standard-library ``compression`` package (``compression.bz2``, ``.gzip``,
``.lzma``, ``.zlib``, ``.zstd``); this directory is placed on ``sys.path`` by
the archival tools, so a module called ``compression`` here would shadow the
stdlib package for the whole process and break ``bz2``, ``lzma``, ``zipfile``
and ``tarfile`` users. ``tests/portable/test_archive_module_names.py`` guards
the rule.
"""

from dataclasses import dataclass, field
import bz2
import lzma


UNIX_COMPRESS_MAGIC = b'\x1f\x9d'
BZIP2_MAGIC = b'BZh'
XZ_MAGIC = b'\xfd7zXZ\x00'
CLEAR_CODE = 256
FIRST_FREE = 257
INITIAL_BITS = 9
MAX_BITS = 16
# compress(1) packs codes into groups of eight so a reader can resynchronise.
GROUP_CODES = 8


@dataclass(frozen=True)
class Bounds:
    """Output, structural and decoder-memory limits applied by every decoder."""

    output_bytes: int = 32 * 1024 * 1024
    codes: int = 4 * 1024 * 1024
    decoder_bytes: int = 64 * 1024 * 1024
    streams: int = 8

    def __post_init__(self):
        if min(self.output_bytes, self.codes, self.decoder_bytes, self.streams) <= 0:
            raise ValueError('compression bounds must be positive')


@dataclass(frozen=True)
class Decoded:
    """One decompressed payload and the observations that qualify it."""

    data: bytes | None
    status: str
    detail: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    streams: int = 1


def identify_stream(head: bytes) -> str | None:
    """Return the compression family for a bounded header sample, or None.

    ``head`` must be at least six bytes for every check to be conclusive.
    """
    if head[:2] == UNIX_COMPRESS_MAGIC:
        return 'unix-compress'
    if head[:3] == BZIP2_MAGIC and len(head) > 3 and 0x31 <= head[3] <= 0x39:
        return 'bzip2'
    if head[:6] == XZ_MAGIC:
        return 'xz'
    return None


class _GroupReader:
    """Least-significant-bit-first reader with compress(1) group alignment.

    compress(1) writes codes into a buffer of eight codes at the current width,
    and pads to the end of that group whenever the width changes or a CLEAR is
    emitted. The decoder must make the same jump at the same place, and it is
    measured from the start of the current group, not from the start of the
    stream: after a jump the next group begins at the padded position.
    """

    __slots__ = ('data', 'bit', 'total', 'origin')

    def __init__(self, data):
        self.data = data
        self.bit = 0
        self.total = len(data) * 8
        self.origin = 0

    def get(self, width):
        if self.bit + width > self.total:
            return None
        byte, shift = self.bit >> 3, self.bit & 7
        span = (shift + width + 7) >> 3
        chunk = int.from_bytes(self.data[byte:byte + span].ljust(span, b'\0'), 'little')
        self.bit += width
        return (chunk >> shift) & ((1 << width) - 1)

    def align_group(self, width):
        """Skip to the end of the current eight-code group at ``width``."""
        group = width * GROUP_CODES
        offset = self.bit - self.origin
        aligned = self.origin + -(-offset // group) * group
        self.bit = min(aligned, self.total)
        self.origin = self.bit

    def remaining(self):
        return self.total - self.bit

    def remaining_is_zero_padding(self):
        """True when fewer than eight bits remain and all of them are zero."""
        left = self.remaining()
        if left >= 8:
            return False
        while self.bit < self.total:
            if self.get(1):
                return False
        return True


def _unix_compress_flags(header):
    """Parse the third header byte into (maxbits, block_mode, warnings)."""
    if len(header) < 3:
        raise ValueError('truncated compress header')
    flags = header[2]
    maxbits = flags & 0x1F
    if not INITIAL_BITS <= maxbits <= MAX_BITS:
        raise ValueError('unsupported compress maxbits')
    # Bits 0x20 and 0x40 are reserved by compress(1). Some writers set them
    # without changing the code stream, so they are reported, not rejected.
    warnings = ('reserved-header-flags',) if flags & 0x60 else ()
    return maxbits, bool(flags & 0x80), warnings


def decode_unix_compress(data: bytes, bounds: Bounds = Bounds()) -> Decoded:
    """Decode a compress(1) LZW stream (magic 1F 9D).

    Variable-width LSB-first codes start at nine bits and are written in groups
    of eight. A width change, and a block-mode CLEAR, both pad the current group
    before the new width starts. In block mode code 256 resets the dictionary to
    its literal state; in non-block mode the table simply stops growing when it
    is full. Both are handled here, and a stream that ends inside a code is
    reported as partial rather than silently truncated.

    The transition and CLEAR handling was checked against streams whose eight,
    ten, eleven, twelve, thirteen and sixteen bit configurations all contain
    multiple width changes: gzip 1.15's independent ``unlzw`` decoder produced
    identical bytes for every one. See
    ``docs/research/unix-compress-qualification-20261127.md``.
    """
    if not data.startswith(UNIX_COMPRESS_MAGIC):
        return Decoded(None, 'failed', 'not-a-compress-stream')
    try:
        maxbits, block_mode, warnings = _unix_compress_flags(data)
    except ValueError as exc:
        return Decoded(None, 'failed', str(exc))
    warnings = list(warnings)
    maxmaxcode = 1 << maxbits
    table_prefix = [0] * maxmaxcode
    table_suffix = bytearray(maxmaxcode)
    for literal in range(256):
        table_suffix[literal] = literal
    stack = bytearray(maxmaxcode + 1)
    output = bytearray()
    reader = _GroupReader(data[3:])
    free_ent = FIRST_FREE if block_mode else 256
    n_bits = INITIAL_BITS
    maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1
    oldcode = -1
    finchar = 0
    codes = 0
    clears = 0
    saturated = False
    while True:
        if free_ent > maxcode:
            if n_bits >= maxbits:
                # The table is full. compress(1) neither widens past maxbits
                # nor clears unless the ratio check asks it to, so the stream
                # continues with a frozen table.
                maxcode = maxmaxcode
                saturated = True
            else:
                reader.align_group(n_bits)
                n_bits += 1
                maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1
        code = reader.get(n_bits)
        if code is None:
            break
        codes += 1
        if codes > bounds.codes:
            return Decoded(None, 'limited', 'code-limit', tuple(warnings))
        if block_mode and code == CLEAR_CODE:
            free_ent = CLEAR_CODE
            reader.align_group(n_bits)
            n_bits = INITIAL_BITS
            maxcode = (1 << n_bits) - 1
            clears += 1
            # ``oldcode`` is deliberately kept: compress(1) resumes decoding
            # without treating the next code as a fresh start, so the decoder's
            # table stays one entry behind the encoder's exactly as it did
            # before the CLEAR.
            continue
        if oldcode == -1:
            if code >= 256:
                return Decoded(None, 'failed', 'invalid-initial-code', tuple(warnings))
            output.append(code)
            finchar = oldcode = code
            continue
        incode = code
        depth = 0
        if code >= free_ent:
            if code > free_ent:
                return Decoded(None, 'failed', 'invalid-lzw-code', tuple(warnings))
            # The KwKwK case: the code being defined is used immediately.
            stack[0] = finchar
            depth = 1
            code = oldcode
        while code >= 256:
            if depth >= maxmaxcode:
                return Decoded(None, 'failed', 'lzw-chain-overflow', tuple(warnings))
            stack[depth] = table_suffix[code]
            depth += 1
            code = table_prefix[code]
        finchar = table_suffix[code]
        stack[depth] = finchar
        depth += 1
        if len(output) + depth > bounds.output_bytes:
            return Decoded(None, 'limited', 'output-byte-limit', tuple(warnings))
        while depth:
            depth -= 1
            output.append(stack[depth])
        if free_ent < maxmaxcode:
            table_prefix[free_ent] = oldcode
            table_suffix[free_ent] = finchar
            free_ent += 1
        oldcode = incode
    if clears:
        warnings.append(f'block-clears-{clears}')
    if saturated:
        warnings.append('dictionary-saturated')
    if not output:
        return Decoded(b'', 'empty', 'no-codes', tuple(warnings))
    if reader.remaining_is_zero_padding():
        return Decoded(bytes(output), 'ok', None, tuple(warnings))
    # Whole bytes, or more, are left over without forming the code the next
    # width would need: the stream stops mid-code instead of at a clean group.
    return Decoded(bytes(output), 'partial', 'truncated-final-code', tuple(warnings))


def _drain(decompressor, data, bounds, budget):
    """Drain one stdlib decompressor without allowing unbounded expansion."""
    output = bytearray()
    pending = data
    while True:
        room = budget + 1 - len(output)
        if room <= 0:
            return None, 'output-byte-limit', b''
        output.extend(decompressor.decompress(pending, room))
        if len(output) > budget:
            return None, 'output-byte-limit', b''
        if decompressor.eof:
            return bytes(output), None, decompressor.unused_data
        if decompressor.needs_input:
            if not pending:
                return None, 'truncated-stream', b''
            pending = b''
        else:
            # The decompressor stopped because the output cap was reached;
            # keep draining until it wants more input or finishes.
            pending = b''


def _bounded_streams(factory, data, bounds, magic, malformed_detail):
    """Decode one or more concatenated streams under a shared output budget.

    Concatenated streams are a real-world shape (``cat a.xz b.xz``) and each
    new stream allocates a fresh decoder, so the count is bounded independently
    of the output budget.
    """
    output = bytearray()
    warnings = []
    pending = data
    streams = 0
    while True:
        streams += 1
        if streams > bounds.streams:
            return Decoded(None, 'limited', 'stream-count-limit', tuple(warnings), streams - 1)
        try:
            decompressor = factory(bounds)
            chunk, problem, unused = _drain(
                decompressor, pending, bounds, bounds.output_bytes - len(output))
        except (OSError, ValueError, EOFError, lzma.LZMAError) as exc:
            detail = malformed_detail
            if 'memory usage limit' in str(exc).lower():
                return Decoded(None, 'limited', 'decoder-memory-limit', tuple(warnings), streams)
            return Decoded(None, 'failed', detail, tuple(warnings), streams)
        if problem:
            status = 'limited' if problem == 'output-byte-limit' else 'failed'
            return Decoded(None, status, problem, tuple(warnings), streams)
        output.extend(chunk)
        if unused[:len(magic)] == magic:
            pending = unused
            continue
        if unused:
            warnings.append('trailing-data')
        break
    if streams > 1:
        warnings.append(f'concatenated-streams-{streams}')
    return Decoded(bytes(output), 'ok' if output else 'empty', None, tuple(warnings), streams)


def decode_bzip2(data: bytes, bounds: Bounds = Bounds()) -> Decoded:
    """Decode bzip2 streams using the standard library's independent decoder.

    bzip2 remembers a block size of 100 kB to 900 kB and keeps several
    block-sized tables, so its working set is fixed by the header digit and does
    not follow the output. The digit is therefore checked against
    ``bounds.decoder_bytes``, and concatenated streams are counted.
    """
    if data[:3] != BZIP2_MAGIC or len(data) < 4 or not 0x31 <= data[3] <= 0x39:
        return Decoded(None, 'failed', 'not-a-bzip2-stream')
    block_bytes = (data[3] - 0x30) * 100_000
    # The reference decoder keeps roughly four block-sized arrays live.
    if block_bytes * 4 > bounds.decoder_bytes:
        return Decoded(None, 'limited', 'decoder-memory-limit')
    return _bounded_streams(lambda _bounds: bz2.BZ2Decompressor(), data, bounds,
                            BZIP2_MAGIC, 'bzip2-integrity-or-structure')


def decode_xz(data: bytes, bounds: Bounds = Bounds()) -> Decoded:
    """Decode .xz streams using the standard library's independent decoder.

    ``memlimit`` caps the dictionary the block header declares, which the
    output budget cannot do: a small .xz stream may request a multi-gigabyte
    dictionary and allocate it before emitting anything.
    """
    if data[:6] != XZ_MAGIC:
        return Decoded(None, 'failed', 'not-an-xz-stream')
    return _bounded_streams(
        lambda limits: lzma.LZMADecompressor(format=lzma.FORMAT_XZ,
                                             memlimit=limits.decoder_bytes),
        data, bounds, XZ_MAGIC, 'xz-integrity-or-structure')


DECODERS = {
    'unix-compress': decode_unix_compress,
    'bzip2': decode_bzip2,
    'xz': decode_xz,
}

# Conventional suffixes, used only to derive a readable label for one payload.
SUFFIXES = {
    'unix-compress': '.z',
    'bzip2': '.bz2',
    'xz': '.xz',
}


def decode(data: bytes, kind: str, bounds: Bounds = Bounds()) -> Decoded:
    """Decode one already-identified compression payload."""
    decoder = DECODERS.get(kind)
    if decoder is None:
        return Decoded(None, 'unsupported', 'no-decoder')
    return decoder(data, bounds)
