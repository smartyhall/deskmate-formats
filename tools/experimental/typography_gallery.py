"""Build the typography v1 crops from the pinned private oracle captures."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageChops

from deskmate_formats import draw, graphics_raster
from deskmate_formats.font_resources import load_outline_faces


CASES = {
    'lab-grid': ('BRTYPE.FIG', 'TEN.FF1', 'browser-native-repaint'),
    'bonum': ('TYPECFF.FIG', 'MAPCFF.FF1', 'mapcff-repaint'),
    'liberation-mono': ('TYPETTF.FIG', 'MAPTTF.FF1', 'mapttf-repaint'),
}


def identity(source):
    data = source.read_bytes()
    return {'sha256': sha256(data).hexdigest(), 'size': len(data)}


def foreground(image):
    return ImageChops.difference(image, Image.new('RGB', image.size, image.getpixel((639, 417)))).convert(
        'L').point(lambda n: 255 if n else 0)


def generate(private, dest):
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': 1, 'profile': 'Draw 03.05.00 RSX VGA Normal', 'cases': {}, 'images': {}}
    for case, (figure, font, capture) in CASES.items():
        source, fontfile = private / figure, private / font
        drawing = draw.parse_bytes(source.read_bytes())
        preview = graphics_raster.preview_rsx(drawing.form, drawing.palette, outline_faces=load_outline_faces([fontfile]))
        dimension = (preview.width, preview.height)
        if preview.omissions or dimension != (640, 418):
            raise ValueError('specimen has omissions or unexpected raster size')
        receipt = json.loads((private / f'{capture}.json').read_text(encoding='utf-8-sig'))
        frame = private / f'{capture}.png'
        if identity(frame)['sha256'] != receipt['png_sha256']:
            raise ValueError('framebuffer differs from socket receipt')
        with Image.open(frame) as opened:
            native = opened.convert('RGB').crop((0, 62, 640, 480))
        independent = Image.frombytes('RGB', dimension, preview.rgb)
        a, b = foreground(native), foreground(independent)
        overlap = ImageChops.multiply(a, b).histogram()[255]
        union = ImageChops.lighter(a, b).histogram()[255]
        manifest['cases'][case] = {
            'figure': identity(source), 'font': identity(fontfile), 'full_frame_sha256': receipt['png_sha256'],
            'emulated_ms': receipt['status']['ms'], 'frames': receipt['status']['frames'],
            'native_foreground': a.histogram()[255], 'independent_foreground': b.histogram()[255],
            'intersection': overlap, 'union': union, 'foreground_iou': overlap / union,
        }
        for kind, image in [('native', native), ('independent', independent)]:
            target = dest / f'{case}-{kind}.png'
            image.save(target, compress_level=9)
            manifest['images'][target.name] = {**identity(target), 'dimensions': list(dimension)}
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    generate(args.private, args.output)
