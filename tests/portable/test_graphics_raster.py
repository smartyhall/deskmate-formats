"""Portable checks for the independent RSX Normal-zoom graphics profile."""
from pathlib import Path
import unittest
from unittest.mock import patch

from deskmate_formats import draw, graphics_raster


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/draw'


class NativeRasterTest(unittest.TestCase):
    def render(self, name):
        drawing = draw.parse_file(FIXTURES / (name + '.fig'))
        return graphics_raster.preview_rsx(drawing.form, drawing.palette)

    @staticmethod
    def pixel(frame, x, y):
        start = 3 * (y * frame.width + x)
        return tuple(frame.rgb[start:start + 3])

    def test_native_line_endpoint_and_vga_palette(self):
        frame = self.render('d01')
        self.assertEqual((frame.width, frame.height), (640, 418))
        self.assertEqual(len(frame.rgb), 640 * 418 * 3)
        self.assertEqual(frame.background, (0, 0, 129))
        self.assertEqual([self.pixel(frame, x, 85) for x in range(63, 98)],
                         [frame.background, *([(194, 194, 0)] * 33), frame.background])
        self.assertEqual(self.pixel(frame, 64, 84), frame.background)
        self.assertEqual(frame.omissions, ())

    def test_rectangle_styles_and_screen_locked_phase(self):
        frame = self.render('pattern-grid-native')
        self.assertEqual(frame.rendered_elements, 32)
        self.assertEqual(self.pixel(frame, 47, 50), (129, 0, 0))
        self.assertEqual(self.pixel(frame, 120, 50), (0, 194, 0))
        for y in range(49, 79):
            for x in range(185, 205):
                self.assertEqual(self.pixel(frame, x, y), self.pixel(frame, x, y + 8 * 19))
        self.assertEqual(len(graphics_raster.TILES[15][1]), 19)

    def test_resource_limit_and_explicit_arc_omission(self):
        with patch.object(graphics_raster, 'MAX_WORK', 100):
            frame = self.render('d01')
        self.assertEqual(frame.rendered_elements, 0)
        self.assertEqual(frame.omissions[0].reason, 'raster_work_limit')
        grid = self.render('arc-grid-native')
        self.assertEqual(grid.rendered_elements, 10)
        self.assertEqual(len(grid.omissions), 1)

    def test_axis_dash_phase_and_thick_solid_fallback(self):
        frame = self.render('stroke-grid-native')
        y = int((380 + 4 * 510) * 19 / 220)
        style = ''.join('1' if self.pixel(frame, x, y) == (194, 194, 194) else '0' for x in range(36, 60))
        self.assertEqual(style, '10011100' * 3)
        y = int((380 + 510) * 19 / 220)
        self.assertEqual(self.pixel(frame, 36, y), frame.background)
        self.assertEqual([self.pixel(frame, 340, y + dy) for dy in range(-2, 4)],
                         [frame.background, *([(194, 194, 194)] * 4), frame.background])
