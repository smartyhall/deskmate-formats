"""Decode standalone compression streams with explicit bounds and provenance.

Each decoder returns one opaque payload. Nothing here guesses a member name
from archive-controlled bytes: the caller supplies the derived label and
remains responsible for recursion, persistence and hashing.

Bounds are enforced on *output* bytes, so a small hostile input cannot expand
without limit. Truncated input, trailing garbage and an unrecognised method
are reported rather than repaired.
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


@dataclass(frozen=True)
class Bounds:
    """Output and structural limits applied by every decoder."""

    output_bytes: int = 32 * 1024 * 1024
    codes: int = 4 * 1024 * 1024

    def __post_init__(self):
        if self.output_bytes <= 0 or self.codes <= 0:
            raise ValueError('compression bounds must be positive')


@dataclass(frozen=True)
class Decoded:
    """One decompressed payload and the observations that qualify it."""

    data: bytes | None
    status: str
    detail: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


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


class _BitReader:
    """Least-significant-bit-first reader used by the compress(1) LZW stream."""

    __slots__ = ('data', 'position', 'buffer', 'count')

    def __init__(self, data):
        self.data = data
        self.position = 0
        self.buffer = 0
        self.count = 0

    def get(self, width):
        while self.count < width:
            if self.position >= len(self.data):
                return -1
            self.buffer |= self.data[self.position] << self.count
            self.position += 1
            self.count += 8
        value = self.buffer & ((1 << width) - 1)
        self.buffer >>= width
        self.count -= width
        return value


def _unix_compress_flags(header):
    """Parse the third header byte into (maxbits, block_mode)."""
    if len(header) < 3:
        raise ValueError('truncated compress header')
    flags = header[2]
    maxbits = flags & 0x1F
    if not 9 <= maxbits <= 16:
        raise ValueError('unsupported compress maxbits')
    # Bit 6 is reserved by compress(1) and is set by some writers; it carries
    # no decoding meaning, so only the block-mode bit changes behaviour.
    return maxbits, bool(flags & 0x80)


def decode_unix_compress(data: bytes, bounds: Bounds = Bounds()) -> Decoded:
    """Decode a compress(1) LZW stream (magic 1F 9D).

    Variable-width LSB-first codes start at nine bits. In block mode code 256
    resets the dictionary to its literal state. The decoder follows the
    published algorithm and never invents output for a truncated stream.
    """
    if not data.startswith(UNIX_COMPRESS_MAGIC):
        return Decoded(None, 'failed', 'not-a-compress-stream')
    try:
        maxbits, block_mode = _unix_compress_flags(data)
    except ValueError as exc:
        return Decoded(None, 'failed', str(exc))
    maxmaxcode = 1 << maxbits
    table_prefix = [0] * maxmaxcode
    table_suffix = bytearray(maxmaxcode)
    for literal in range(256):
        table_suffix[literal] = literal
    stack = bytearray(maxmaxcode)
    output = bytearray()
    reader = _BitReader(data[3:])
    free_ent = FIRST_FREE if block_mode else 256
    n_bits = INITIAL_BITS
    maxcode = (1 << n_bits) - 1
    oldcode = -1
    finchar = 0
    codes = 0
    while True:
        code = reader.get(n_bits)
        if code < 0:
            break
        codes += 1
        if codes > bounds.codes:
            return Decoded(None, 'limited', 'code-limit')
        if block_mode and code == CLEAR_CODE:
            free_ent = FIRST_FREE
            n_bits = INITIAL_BITS
            maxcode = (1 << n_bits) - 1
            oldcode = -1
            continue
        if oldcode == -1:
            if code >= 256:
                return Decoded(None, 'failed', 'invalid-initial-code')
            output.append(code)
            finchar = oldcode = code
            if len(output) > bounds.output_bytes:
                return Decoded(None, 'limited', 'output-byte-limit')
            continue
        incode = code
        depth = 0
        if code >= free_ent:
            if code > free_ent:
                return Decoded(None, 'failed', 'invalid-lzw-code')
            # The KwKwK case: the code being defined is used immediately.
            stack[depth] = finchar
            depth += 1
            code = oldcode
        while code >= 256:
            if depth >= maxmaxcode:
                return Decoded(None, 'failed', 'lzw-chain-overflow')
            stack[depth] = table_suffix[code]
            depth += 1
            code = table_prefix[code]
        finchar = table_suffix[code]
        stack[depth] = finchar
        depth += 1
        while depth:
            depth -= 1
            output.append(stack[depth])
        if len(output) > bounds.output_bytes:
            return Decoded(None, 'limited', 'output-byte-limit')
        if free_ent < maxmaxcode:
            table_prefix[free_ent] = oldcode
            table_suffix[free_ent] = finchar
            free_ent += 1
        oldcode = incode
        if free_ent > maxcode and n_bits < maxbits:
            n_bits += 1
            maxcode = maxmaxcode if n_bits == maxbits else (1 << n_bits) - 1
    if not output:
        return Decoded(b'', 'empty', 'no-codes')
    # A stream that ends mid-code leaves the final code unread; that is a
    # normal termination only when the reader consumed whole bytes.
    warnings = ('trailing-partial-code',) if reader.count else ()
    return Decoded(bytes(output), 'ok', None, warnings)


def _bounded_incremental(decompressor, data, bounds):
    """Drain a stdlib decompressor without allowing unbounded expansion."""
    output = bytearray()
    pending = data
    while True:
        room = bounds.output_bytes + 1 - len(output)
        if room <= 0:
            return None, 'output-byte-limit', b''
        output.extend(decompressor.decompress(pending, room))
        if len(output) > bounds.output_bytes:
            return None, 'output-byte-limit', b''
        if decompressor.eof:
            return bytes(output), None, decompressor.unused_data
        if decompressor.needs_input:
            if not pending:
                return None, 'truncated-stream', b''
            pending = b''
        else:
            pending = b''


def decode_bzip2(data: bytes, bounds: Bounds = Bounds()) -> Decoded:
    """Decode one bzip2 stream using the standard library's independent decoder."""
    try:
        decompressor = bz2.BZ2Decompressor()
        output, problem, unused = _bounded_incremental(decompressor, data, bounds)
    except (OSError, ValueError, EOFError) as exc:
        return Decoded(None, 'failed', type(exc).__name__)
    if problem:
        return Decoded(None, 'limited' if problem == 'output-byte-limit' else 'failed', problem)
    warnings = ('trailing-data',) if unused else ()
    return Decoded(output, 'ok' if output else 'empty', None, warnings)


def decode_xz(data: bytes, bounds: Bounds = Bounds()) -> Decoded:
    """Decode one .xz stream using the standard library's independent decoder."""
    try:
        decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        output, problem, unused = _bounded_incremental(decompressor, data, bounds)
    except (lzma.LZMAError, EOFError) as exc:
        return Decoded(None, 'failed', type(exc).__name__)
    if problem:
        return Decoded(None, 'limited' if problem == 'output-byte-limit' else 'failed', problem)
    warnings = ('trailing-data',) if unused else ()
    return Decoded(output, 'ok' if output else 'empty', None, warnings)


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
