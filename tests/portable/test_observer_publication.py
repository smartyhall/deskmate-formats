"""Publication contract regressions using independently authored display data."""

from dataclasses import FrozenInstanceError, replace
from importlib.util import find_spec
from io import BytesIO
import unittest
from unittest.mock import patch

from deskmate_formats.observer.frames import Frame, MAX_PNG_BYTES
from deskmate_formats.observer.presentation import ascii_display
from deskmate_formats.observer.publication import (
    Action, Connection, ErrorCode, Machine, Observation, ObservationRegistry, decode_cp437,
)

PILLOW = find_spec("PIL") is not None


def observation(**changes):
    return replace(Observation("fixture", 1, 0, 10_000, 20, True, False), **changes)


def png_fixture(*, metadata=None):
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    output = BytesIO()
    info = PngInfo()
    if metadata is not None:
        info.add_text("Comment", metadata)
    image = Image.new("RGBA", (8, 6), (250, 20, 10, 255))
    image.putpixel((0, 0), (100, 42, 68, 0))
    image.save(output, "PNG", pnginfo=info)
    return output.getvalue()


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.registry = ObservationRegistry((Machine("fixture", "Fixture"),), history_limit=2, stale_after=5)
        self.stream = self.registry.stream("fixture")

    def test_ordering_generation_and_bounded_history(self):
        first = observation(screen="Private to this published snapshot")
        self.stream.publish(first)
        self.stream.publish(observation(sequence=3, emulated_ms=50, dropped_updates=1))
        self.stream.publish(observation(sequence=4, generation=1, emulated_ms=0, dropped_updates=1))
        view = self.stream.view()
        self.assertEqual([event.sequence for event in view.history], [3, 4])
        self.assertEqual(view.observation.generation, 1)
        self.assertEqual(view.observation.emulated_ms, 0)
        self.assertIsNone(view.observation.screen)
        self.assertFalse(hasattr(view.history[0], "screen"))
        self.assertFalse(hasattr(view.history[0], "frame"))
        with self.assertRaises(FrozenInstanceError):
            first.screen = "Modified"
        with self.assertRaises(FrozenInstanceError):
            view.history[0].sequence = 99
        for candidate in (
            observation(sequence=4, generation=1, dropped_updates=1),
            observation(sequence=3, generation=1, dropped_updates=1),
            observation(sequence=5, generation=0, dropped_updates=1),
            observation(sequence=5, generation=1, dropped_updates=0),
            observation(sequence=5, generation=1, dropped_updates=1, instance_id="other"),
        ):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                self.stream.publish(candidate)
        self.assertEqual(self.stream.view(), view)

    def test_no_clock_regression_even_across_an_unknown_sample(self):
        self.stream.publish(observation(emulated_ms=31))
        self.stream.publish(observation(
            sequence=2, emulated_ms=None, held=None, paused=None, connection=Connection.DISCONNECTED,
        ))
        with self.assertRaises(ValueError):
            self.stream.publish(observation(sequence=3, emulated_ms=30))
        self.stream.publish(observation(sequence=3, emulated_ms=31))
        self.assertFalse(self.stream.view().stale)

    def test_freshness_uses_monotonic_time_and_loss_retains_screen(self):
        self.assertTrue(self.stream.view().stale)
        with patch("deskmate_formats.observer.publication.monotonic") as clock:
            clock.return_value = 100
            self.stream.publish(observation(screen="APPROVED"))
            self.assertFalse(self.stream.view().stale)
            clock.return_value = 105
            self.assertTrue(self.stream.view().stale)
            self.assertEqual(self.stream.view().observation.screen, "APPROVED")
            self.stream.mark_unavailable(sequence=2, observed_at_ms=11_000, error=ErrorCode.TIMEOUT)
            view = self.stream.view()
            self.assertTrue(view.stale)
            self.assertIs(view.observation.connection, Connection.ERROR)
            self.assertIs(view.observation.action, Action.CONNECTION)
            self.assertEqual(view.observation.emulated_ms, 20)
            self.assertEqual(view.observation.screen, "APPROVED")
            self.assertIsNone(view.observation.held)

    def test_malformed_observations_and_registry_rejected(self):
        bad_values = (
            {"instance_id": "../fixture"}, {"sequence": True}, {"generation": -1},
            {"dropped_updates": 1 << 53}, {"observed_at_ms": 253402300800000},
            {"emulated_ms": 1.2}, {"held": "true"}, {"paused": 0},
            {"action": "observe"}, {"milestone": "new\nline"},
            {"screen": "\x1b[31m"}, {"screen": "a\u202eb"}, {"screen": "a" * 133},
            {"screen": "\n" * 60}, {"screen": b"screen"}, {"frame": b"pixels"},
            {"connection": Connection.DISCONNECTED}, {"error": ErrorCode.TRANSPORT},
            {"connection": Connection.ERROR, "held": None, "paused": None},
        )
        for values in bad_values:
            with self.subTest(values=values), self.assertRaises(ValueError):
                observation(**values)
        with self.assertRaises(TypeError):
            observation(raw_protocol_reply={"token": "fixture-sentinel"})
        with self.assertRaises(ValueError):
            self.stream.publish({"observation": observation()})
        with self.assertRaises(ValueError):
            self.stream.mark_unavailable(sequence=1, observed_at_ms=0)
        with self.assertRaises(ValueError):
            ObservationRegistry(())
        with self.assertRaises(ValueError):
            ObservationRegistry((self.stream.machine, self.stream.machine))
        with self.assertRaises(ValueError):
            ObservationRegistry(Machine(f"pc-{number}", "PC") for number in range(9))

    def test_cp437_display_and_ascii_fallback(self):
        raw_rows = ("╔═╗ é".encode("cp437"), b"\xba\x01\x7f\x00")
        text = decode_cp437(raw_rows)
        self.assertEqual(text, "╔═╗ é\n║☺⌂ ")
        self.assertEqual(ascii_display(text), "+=+ e\n|?? ")
        for rows in ((b"x" * 133,), [b"x"] * 61, ("not a byte row",)):
            with self.assertRaises(ValueError):
                decode_cp437(rows)

    def test_oversized_and_malformed_frames_rejected_without_decoder(self):
        header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        too_wide = header + (2049).to_bytes(4, "big") + (1).to_bytes(4, "big") + bytes(9)
        for source in (b"not an image", b"x" * (MAX_PNG_BYTES + 1), too_wide, bytearray(too_wide)):
            with self.subTest(length=len(source)), self.assertRaises(ValueError):
                Frame(source, generation=0, captured_at_ms=0)

    @unittest.skipUnless(PILLOW, "requires the observer extra")
    def test_frame_identity_revocation_and_generation_change(self):
        frame = Frame(png_fixture(), generation=1, captured_at_ms=10_000)
        self.stream.publish(observation(frame=frame))
        self.stream.publish(observation(sequence=2, frame=frame))
        self.stream.mark_unavailable(sequence=3, observed_at_ms=9_900)
        self.assertIs(self.stream.view().observation.frame, frame)
        with self.assertRaises(ValueError):
            self.stream.publish(observation(sequence=4, generation=1, frame=frame))
        self.stream.publish(observation(sequence=4))
        self.assertIsNone(self.stream.view().observation.frame)
        with self.assertRaises(ValueError):
            self.stream.publish(observation(sequence=5, frame=frame))
        new_frame = Frame(png_fixture(), generation=0, captured_at_ms=10_000, rendered_emulated_ms=0)
        self.stream.publish(observation(sequence=5, generation=1, emulated_ms=0, frame=new_frame))
        self.assertIs(self.stream.view().observation.frame, new_frame)

    @unittest.skipUnless(PILLOW, "requires the observer extra")
    def test_bad_png_and_inconsistent_frame_times(self):
        data = png_fixture()
        with self.assertRaises(ValueError):
            Frame(data[:40], generation=1, captured_at_ms=10_000)
        with self.assertRaises(ValueError):
            Frame(data, generation=1, captured_at_ms=10_000, rendered_at_ms=10_001)
        frame = Frame(data, generation=1, captured_at_ms=10_000, rendered_emulated_ms=21)
        with self.assertRaises(ValueError):
            observation(frame=frame)
