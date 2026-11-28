"""Read and construct the measured fixed-size DOS DeskMate DMCORKBD note buffer.

The text area is treated as CP437 bytes, not ASCII. The RSX editor drew the
CP437 glyphs for two natively entered bytes (Alt+130 stored 0x82, Alt+225 stored
0xE1) and preserved them across a cold reopen. A seeded note also carried eleven
high bytes; two of them (0x82 and 0xE1) repeated those native entries, so nine
further code points were displayed and re-saved. That is a sample of the high
half, not a sweep. Accepting the whole 0x20-0xFF range except DEL is this
reader's policy, chosen because every observed byte was displayed and preserved.

CR delimits logical lines. The editor wraps a longer line over several drawn
rows, so `rows` reports stored CR-delimited lines rather than the rows on screen.

The normal supported text profile is deliberately narrower than the seeded
evidence. One campaign injected 0x01-0x1F and 0x7F into a note; the editor drew
0x01-0x1F as row breaks, drew 0x7F as a glyph, and kept both classes on save,
dropping only 0x0A when the note loaded. Those bytes were placed by an injector
rather than typed, so the reader and the writer still reject them: a typed note
cannot be shown to contain them, and accepting them would move the normal path
onto evidence that does not establish ordinary entry.

The writer below is a **construction policy**, not a specification. Its rules
come from measured native behaviour and they say so where they are choices:

* the first word is where the accessory drew the caret at the moment the note was
  written, defaulted to the end of the new text; the exact convention at a CR
  boundary was never isolated, so no coordinate convention is invented for a
  caller that did not ask;
* the second word was zero in every measured file and no operation was observed
  to set it, so `create_note` writes zero and `update_note` preserves whatever
  the original file held unless the caller overrides it explicitly;
* bytes after the visible terminator are prior content, not free space: the
  reader never reports them as visible text and `update_note` keeps them unless
  the caller explicitly asks for them to be zeroed;
* 2,794 bytes is the largest composition this project demonstrated in a native
  editor (65 drawn rows of 42 characters plus their CR delimiters). It is the
  default refusal point with an explicit override, not a capacity guarantee: a
  text below it can still demand more drawn rows than the editor draws, and no
  wrapped or mixed shape was driven to its refusal boundary.

`update_note` and `clear_note` act on a caller-supplied 2,864-byte buffer. Size
is the only thing they check: an exact-size buffer is treated as a note, so
supplying one establishes neither file identity nor structural validity, and
provenance remains the caller's responsibility. Sanitisation in this module
concerns the buffer it returns; it is not a secure erase of physical storage.
"""

from dataclasses import dataclass
from pathlib import Path
from struct import pack, unpack_from

SIZE = 2864
TEXT_OFFSET = 4
TEXT_SIZE = 2860
TERMINATOR = b'\x0D'
ENCODING = 'cp437'
# Largest text a native editor was observed to accept in this project's trials:
# 65 drawn rows of 42 characters plus the 64 CR delimiters between them. This is
# a construction policy - the default refusal point - not a capacity guarantee.
# A composition below it can need more drawn rows than the editor draws, and no
# wrapped or mixed shape was driven to its refusal boundary.
DEMONSTRATED_MAXIMUM = 2794
# A text area with no terminator cannot be read back, so text may never fill the
# last byte of the area.
MAXIMUM_WRITABLE_TEXT = TEXT_SIZE - 1


class PolicyError(ValueError):
    """A construction request this module refuses to encode."""


@dataclass(frozen=True)
class Corkboard:
    """Keep the original bytes, including any text left behind by Clear."""

    data: bytes
    header_words: tuple[int, int]
    text: bytes

    @property
    def decoded(self):
        """The visible text as CP437, which is what the native editor draws."""
        return self.text.decode(ENCODING)

    @property
    def rows(self):
        """CR-delimited logical lines as CP437, without a trailing empty line for a final CR.

        These are not the editor's drawn rows: a line wider than the window is
        wrapped on screen into more than one row.
        """
        rows = self.text.split(TERMINATOR)
        if self.text.endswith(TERMINATOR):
            rows.pop()
        return [row.decode(ENCODING) for row in rows]


def _supported(byte):
    # Measured: CR delimiters, printable ASCII, and CP437 high bytes at the
    # sampled code points (0x82 and 0xE1 typed; nine further code points were
    # displayed from a seeded note).
    # Accepted by policy, not measurement: the rest of the high half.
    # Rejected deliberately: 0x00-0x1F other than CR, and 0x7F. A seeded native
    # note displayed and preserved those bytes, but seeding is not typing, so
    # they stay outside the text profile this module reads and writes.
    return byte == 0x0D or 0x20 <= byte <= 0xFF and byte != 0x7F


def parse_bytes(source):
    """Inspect a known DMCORKBD file with CP437 text and CR line breaks."""
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise ValueError('expected byte snapshot')
    size = source.nbytes if isinstance(source, memoryview) else len(source)
    if size != SIZE:
        raise ValueError('expected a 2864-byte DMCORKBD buffer')
    data = bytes(source)
    end = data.find(b'\0', TEXT_OFFSET)
    if end < 0:
        raise ValueError('unterminated DMCORKBD text')
    note = data[TEXT_OFFSET:end]
    if any(not _supported(byte) for byte in note):
        raise ValueError('unsupported DMCORKBD text byte')
    return Corkboard(data, unpack_from('<HH', data), note)


def parse_file(path):
    with Path(path).open('rb') as handle:
        return parse_bytes(handle.read(SIZE + 1))


def text_bytes(text):
    """Encode `text` for the note area, refusing values no native trial covered.

    A string is encoded as CP437 because that is what the editor drew. NUL is
    refused everywhere: it terminates the visible text, so a note containing one
    could not be read back as the caller wrote it. Control bytes other than CR,
    and DEL, are refused as a deliberate policy even though a seeded native note
    displayed and preserved them: the bytes were injected, not typed, so ordinary
    entry was never established. The reader restricts the same profile.
    """
    if isinstance(text, str):
        try:
            data = text.encode(ENCODING)
        except UnicodeEncodeError as exc:
            raise PolicyError(f'text is not representable in CP437: {exc}') from exc
    elif isinstance(text, (bytes, bytearray, memoryview)):
        data = bytes(text)
    else:
        raise PolicyError('expected str or bytes')
    for index, byte in enumerate(data):
        if byte == 0x00:
            raise PolicyError('NUL terminates the visible text and cannot appear inside it')
        if not _supported(byte):
            raise PolicyError(f'byte 0x{byte:02X} at offset {index} is outside the supported '
                              'text profile (printable CP437 or CR)')
    return data


def _check_length(length, allow_above_demonstrated):
    if length > MAXIMUM_WRITABLE_TEXT:
        raise PolicyError(f'{length} text bytes leave no room for the terminator in the '
                          f'{TEXT_SIZE}-byte text area')
    if length > DEMONSTRATED_MAXIMUM and not allow_above_demonstrated:
        raise PolicyError(
            f'{length} text bytes exceed the {DEMONSTRATED_MAXIMUM}-byte composition a native '
            'editor was observed to accept; that ceiling is a construction policy, not a '
            'measured capacity. Pass allow_above_demonstrated=True to write it as an '
            'unmeasured candidate')


def _caret(caret, length):
    if caret is None:
        return length
    if type(caret) is not int or not 0 <= caret <= length:
        raise PolicyError(f'caret must be an int in 0..{length} or None')
    return caret


def _second_word(value):
    if type(value) is not int or not 0 <= value <= 0xFFFF:
        raise PolicyError('second word must be an unsigned 16-bit integer')
    return value


def create_note(text, *, caret=None, second_word=0, allow_above_demonstrated=False):
    """Build a new synthetic note: header words, text, CR line breaks, zero tail.

    `caret` is the text-area byte offset stored at 0x0000; it defaults to the end
    of the text, which is the most common measured state. It is a write-time
    value rather than an insertion boundary the editor normalises, and the exact
    convention for a caret sitting on a CR was never isolated. `second_word`
    defaults to zero because every measured file held zero and no operation was
    observed to set it.

    The 2,794-byte default ceiling is a construction policy, not a promise that a
    native editor accepts every text below it: wrapped visual rows and logical
    line shapes impose constraints this module does not model.
    """
    data = text_bytes(text)
    _check_length(len(data), allow_above_demonstrated)
    body = bytearray(TEXT_SIZE)
    body[:len(data)] = data
    return pack('<HH', _caret(caret, len(data)), _second_word(second_word)) + bytes(body)


def update_note(original, text, *, caret=None, second_word=None, preserve_residual=True,
                allow_above_demonstrated=False):
    """Replace the visible text of an existing note, preserving unrelated bytes.

    `original` must be a full 2,864-byte buffer. Size is the only check: the
    buffer is not re-parsed and not identified, so an exact-size buffer that is
    not a note at all is accepted as one, and supplying a real note is the
    caller's provenance decision. A note whose residual bytes the reader would
    reject can therefore still be updated. The new text is written at 0x0004 and
    terminated immediately after it. Everything else is kept: the second header
    word unless `second_word` is given, and - by default - every byte after the
    new terminator, which is prior content that a shorter note does not overwrite
    and that the reader never reports as visible text. `preserve_residual=False`
    zeroes that tail explicitly; it is the only path in this module that destroys
    bytes the caller did not supply.
    """
    if not isinstance(original, (bytes, bytearray, memoryview)) or len(bytes(original)) != SIZE:
        raise PolicyError(f'expected a {SIZE}-byte DMCORKBD buffer')
    previous = bytes(original)
    data = text_bytes(text)
    _check_length(len(data), allow_above_demonstrated)
    kept_second = unpack_from('<H', previous, 2)[0]
    word1 = kept_second if second_word is None else _second_word(second_word)
    head = pack('<HH', _caret(caret, len(data)), word1)
    if preserve_residual:
        tail = previous[TEXT_OFFSET + len(data) + 1:]
        body = data + b'\x00' + tail
    else:
        body = data + b'\x00' * (TEXT_SIZE - len(data))
    return head + body


def clear_note(original, *, sanitize=False):
    """Clear the visible text the way the measured Clear control did.

    Native Clear changed exactly one byte - the first text byte to NUL - and left
    both header words and every later byte as they were, so the previous content
    stayed recoverable. That is what this function does by default, and it is not
    a secure erase. `sanitize=True` zeroes the whole text area of the buffer this
    function returns and is an explicit, non-native request; it says nothing
    about copies already on physical storage, prior versions, or backups.

    `original` must be a full 2,864-byte buffer, and size is the only check: no
    byte here establishes that the buffer is a note or identifies which note it
    is.
    """
    if not isinstance(original, (bytes, bytearray, memoryview)) or len(bytes(original)) != SIZE:
        raise PolicyError(f'expected a {SIZE}-byte DMCORKBD buffer')
    data = bytearray(original)
    if sanitize:
        data[TEXT_OFFSET:] = bytes(TEXT_SIZE)
    else:
        data[TEXT_OFFSET] = 0x00
    return bytes(data)
