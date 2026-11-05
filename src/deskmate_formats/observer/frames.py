"""Prepare explicitly approved pixels before publication."""

from dataclasses import dataclass, field, InitVar
from io import BytesIO
from struct import unpack_from

MAX_PNG_BYTES = 1 << 20
MAX_WIDTH, MAX_HEIGHT = 2048, 1536
GIF_SIZE = (640, 480)
GIF_COLORS = 64
MAX_COUNTER = 2**53 - 1  # Exact in JavaScript, including after JSON decoding.
MAX_TIMESTAMP = 253402300799999  # Last millisecond of UTC year 9999.


def counter(value, maximum=MAX_COUNTER):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("invalid observation counter or timestamp")


@dataclass(frozen=True, slots=True)
class Frame:
    """An approved still, with times supplied by its producer in milliseconds."""

    approved_png: InitVar[bytes]
    generation: int
    captured_at_ms: int
    rendered_at_ms: int | None = None
    rendered_emulated_ms: int | None = None
    width: int = field(init=False)
    height: int = field(init=False)
    png: bytes = field(init=False, repr=False)
    gif: bytes = field(init=False, repr=False)

    def __post_init__(self, approved_png):
        counter(self.generation)
        counter(self.captured_at_ms, MAX_TIMESTAMP)
        if self.rendered_at_ms is not None:
            counter(self.rendered_at_ms, self.captured_at_ms)
        if self.rendered_emulated_ms is not None:
            counter(self.rendered_emulated_ms)
        width, height, png, gif = _prepare(approved_png)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "png", png)
        object.__setattr__(self, "gif", gif)


def _prepare(source):
    if (type(source) is not bytes or not 33 <= len(source) <= MAX_PNG_BYTES
            or not source.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")):
        raise ValueError("expected an approved PNG of at most 1 MiB")
    width, height = unpack_from(">II", source, 16)
    if not (0 < width <= MAX_WIDTH and 0 < height <= MAX_HEIGHT):
        raise ValueError("PNG dimensions exceed the observer limit")

    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("install deskmate-formats[observer] to publish frames") from None

    try:
        with Image.open(BytesIO(source), formats=("PNG",)) as image:
            if image.is_animated:
                raise ValueError("expected a still PNG")
            image.verify()
        with Image.open(BytesIO(source), formats=("PNG",)) as image:
            rgba = image.convert("RGBA")
            # A fresh image carries only visible pixels, including when the
            # input contains ancillary chunks or RGB beneath transparent pixels.
            pixels = Image.new("RGB", rgba.size)
            pixels.paste(rgba, mask=rgba.getchannel("A"))
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ValueError("invalid still PNG") from None

    png, gif = BytesIO(), BytesIO()
    pixels.save(png, "PNG", compress_level=1)
    pixels.thumbnail(GIF_SIZE, resample=Image.Resampling.NEAREST)
    pixels.quantize(colors=GIF_COLORS, dither=Image.Dither.NONE).save(
        gif, "GIF", interlace=False
    )
    return width, height, png.getvalue(), gif.getvalue()
