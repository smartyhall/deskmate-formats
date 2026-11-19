"""Verify native and independent Normal-zoom axis-stroke masks on the stroke grid."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image

from deskmate_formats import draw, graphics_raster
from draw_comparison_baseline import CROP


def measure(figure, framebuffer):
    data = figure.read_bytes()
    drawing = draw.parse_bytes(data)
    model = graphics_raster.preview_rsx(drawing.form, drawing.palette)
    independent = Image.frombytes('RGB', (model.width, model.height), model.rgb)
    with Image.open(framebuffer) as image:
        native = image.convert('RGB').crop(CROP)
    checks = Counter()
    for record in drawing.form.draw_order():
        x0, y0, x1, y1 = record.bounds
        if x0 != x1 and y0 != y1:
            continue
        a, b, c, d = map(int, (x0 * 2 / 25, y0 * 19 / 220, x1 * 2 / 25, y1 * 19 / 220))
        box = (min(a, c) - 4, min(b, d) - 4, max(a, c) + 5, max(b, d) + 5)
        color = (194, 194, 0) if x0 == x1 else (194, 194, 194)
        n, r = native.crop(box).get_flattened_data(), independent.crop(box).get_flattened_data()
        checks['axis_color_masks'] += 1
        checks['exact_axis_color_masks'] += all((a == color) == (b == color) for a, b in zip(n, r))
        checks['exact_rgb_neighborhoods'] += n == r
    return {'figure_sha256': sha256(data).hexdigest(), 'framebuffer_sha256': sha256(framebuffer.read_bytes()).hexdigest(),
            'dimensions': (model.width, model.height), 'counts': dict(checks)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('figure', type=Path)
    parser.add_argument('framebuffer', type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.figure, args.framebuffer), indent=2))
