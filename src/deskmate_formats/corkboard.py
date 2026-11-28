"""Read and construct the measured fixed-size DOS DeskMate DMCORKBD note buffer.

The text area is treated as CP437 bytes, not ASCII: the RSX editor drew the
CP437 glyphs for two natively entered bytes (Alt+130 stored 0x82, Alt+225 stored
0xE1) and preserved them across a cold reopen, and it displayed and re-saved a
seeded note of eleven further high bytes. That is a sample of the high half, not
a sweep. Accepting the whole 0x20-0xFF range except DEL is this reader's policy,
chosen because every observed byte was displayed and preserved; the control range
other than CR stays rejected because no native specimen has exercised it.

CR delimits logical lines. The editor wraps a longer line over several drawn
rows, so `rows` reports stored CR-delimited lines rather than the rows on screen.

The writer below is a **construction policy**, not a specification. Its rules
come from measured native behaviour and they say so where they are choices:

* the first word is the caret's text-area byte offset at the moment the note was
  written, so `create_note` and `update_note` default it to the end of the new
  text (the most common measured state) and never invent a coordinate convention
  for a caller that did not ask;
* the second word was zero in every measured file and no operation was observed
  to set it, so `create_note` writes zero and `update_note` preserves whatever
  the original file held unless the caller overrides it explicitly;
* bytes after the visible terminator are prior content, not free space, so
  `update_note` keeps them unless the caller asks for them to be zeroed;
* 2,794 bytes is the largest composition demonstrated in a native editor, not a
  proven universal maximum, so it is the default refusal point with an explicit
  override rather than a hard format limit.
"""

from dataclasses import dataclass
from pathlib import Path
from struct import pack, unpack_from

SIZE = 2864
TEXT_OFFSET = 4
TEXT_SIZE = 2860
TERMINATOR = b'\x0D'
ENCODING = 'cp437'
# Largest text actually accepted by a native editor in this project's trials:
# 65 drawn rows of 42 characters plus the 64 CR delimiters between them. It is a
# demonstrated maximum, not a proven capacity of the format.
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
    # sampled code points (0x82 and 0xE1 typed; eleven more displayed).
    # Accepted by policy, not measurement: the rest of the high half.
    # Rejected as unmeasured: 0x00-0x1F other than CR, and 0x7F.
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
    and DEL, are refused because no native specimen exercised them; the reader
    refuses them for the same reason.
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
            raise PolicyError(f'byte 0x{byte:02X} at offset {index} is outside the measured '
                              'text set (printable CP437 or CR)')
    return data


def _check_length(length, allow_above_demonstrated):
    if length > MAXIMUM_WRITABLE_TEXT:
        raise PolicyError(f'{length} text bytes leave no room for the terminator in the '
                          f'{TEXT_SIZE}-byte text area')
    if length > DEMONSTRATED_MAXIMUM and not allow_above_demonstrated:
        raise PolicyError(
            f'{length} text bytes exceed the {DEMONSTRATED_MAXIMUM}-byte composition a native '
            'editor was observed to accept; pass allow_above_demonstrated=True to write it '
            'as an unmeasured candidate')


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
    of the text. This is the caret convention measured on 03.04.04, and it is a
    write-time value rather than an insertion boundary the editor normalises.
    `second_word` defaults to zero because every measured file held zero and no
    operation was observed to set it.
    """
    data = text_bytes(text)
    _check_length(len(data), allow_above_demonstrated)
    body = bytearray(TEXT_SIZE)
    body[:len(data)] = data
    return pack('<HH', _caret(caret, len(data)), _second_word(second_word)) + bytes(body)


def update_note(original, text, *, caret=None, second_word=None, preserve_residual=True,
                allow_above_demonstrated=False):
    """Replace the visible text of an existing note, preserving unrelated bytes.

    `original` must be a full 2,864-byte buffer; it is not re-parsed, so a note
    whose residual bytes the reader would reject can still be updated. The new
    text is written at 0x0004 and terminated immediately after it. Everything
    else is kept: the second header word unless `second_word` is given, and - by
    default - every byte after the new terminator, which is prior content that a
    shorter note does not overwrite. `preserve_residual=False` zeroes that tail
    explicitly; it is the only path in this module that destroys bytes the caller
    did not supply.
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
    stayed recoverable. That is what this function does by default. It is not a
    secure erase; `sanitize=True` zeroes the whole text area and is an explicit,
    non-native request.
    """
    if not isinstance(original, (bytes, bytearray, memoryview)) or len(bytes(original)) != SIZE:
        raise PolicyError(f'expected a {SIZE}-byte DMCORKBD buffer')
    data = bytearray(original)
    if sanitize:
        data[TEXT_OFFSET:] = bytes(TEXT_SIZE)
    else:
        data[TEXT_OFFSET] = 0x00
    return bytes(data)
