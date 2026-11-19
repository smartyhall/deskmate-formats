"""Publish matched scalable and native-resolution projections of the frozen Draw suite."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from PIL import Image, __version__ as pillow_version

from deskmate_formats import draw, font_resources, graphics, graphics_raster

from draw_comparison_baseline import NATIVE_BACKGROUND, audit, capture, measure, put, put_json, rasterize, save_png


ROOT = Path(__file__).resolve().parents[2]


FONT_MILESTONES = ('vga-ff1-03', 'vga-pen-04')
MILESTONES = ('arc-vector-01', 'vga-raster-01', 'vga-strokes-02', *FONT_MILESTONES)


def pinned_code(*, use_fonts=False):
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    pins = {}
    modules = (draw, graphics, graphics_raster)
    for module in (*modules, font_resources) if use_fonts else modules:
        path = Path(module.__file__).resolve()
        name = path.relative_to(ROOT).as_posix()
        expected = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{revision}:{name}'])
        if expected != path.read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError(f'commit the renderer before generating the milestone: {name}')
        pins[name] = sha256(expected).hexdigest()
    return revision, pins


def build(args):
    using_fonts = any(name in FONT_MILESTONES for name in args.milestone)
    if using_fonts and len(args.milestone) != 1:
        raise ValueError('build font milestones separately')
    faces = font_resources.load_outline_faces(args.ff1)
    if bool(faces) != using_fonts:
        raise ValueError('the FF1 milestone requires local pinned FF1 resources')
    revision, pins = pinned_code(use_fonts=using_fonts)
    library = ROOT / audit.TREE
    baseline = json.loads((library / audit.BASELINE / 'manifest.json').read_text(encoding='utf-8'))
    verified = json.loads(args.disk_verification.read_text(encoding='utf-8'))
    source_receipts = []
    for case in baseline['cases']:
        source = ROOT / case['source_path']
        source_data = source.read_bytes()
        source_hash = sha256(source_data).hexdigest()
        if source_hash != case['source_sha256']:
            raise ValueError(f'frozen source changed: {source.name}')
        dos_name = case['native_capture']['dos_name']
        if verified['files'][dos_name] != {'sha256': source_hash, 'size': len(source_data)}:
            raise ValueError(f'wrong source bytes on recapture disk: {dos_name}')
        native, receipt = capture(args.evidence, dos_name[:-4].lower())
        with Image.open(ROOT / case['artifacts']['native.png']['path']) as previous:
            if previous.convert('RGB').tobytes() != native.tobytes():
                raise ValueError(f'recapture differs from the frozen Normal profile: {dos_name}')
        receipt['source_role'] = 'verified-identical-native-recapture'
        receipt['baseline_framebuffer_sha256'] = case['native_capture']['framebuffer_sha256']
        drawing = draw.parse_bytes(source_data)
        for family, spec in case['font_resources'].items():
            if using_fonts and (family.casefold() not in faces or faces[family.casefold()].sha256 != spec['sha256']):
                raise ValueError(f'{dos_name} requires the pinned {family} FF1')
        preview = graphics.preview_svg(drawing.form, drawing.palette, outline_faces=faces)
        source_receipts.append((case, native, receipt, drawing, preview))
    vector, flags = [None] * len(source_receipts), []
    if 'arc-vector-01' in args.milestone:
        if not args.browser or not args.browser_version:
            raise ValueError('the vector milestone requires the browser and its version')
        vector, flags = rasterize(args.browser, [item[4] for item in source_receipts],
                                  [item[0]['renderer_background'] for item in source_receipts])
    profiles = {
        'arc-vector-01': {
            'mode': 'scalable SVG at Normal-zoom viewport',
            'rasterizer': baseline['rasterizer'] | {'version': args.browser_version, 'flags': flags},
            'limits': 'Shared quadratic arcs. Solid one-pixel SVG strokes and solid fill approximations. '
                      'Cobb remains omitted. VGA colors and browser antialiasing differ.',
        },
        'vga-raster-01': {
            'mode': 'experimental independent RSX Normal-zoom raster',
            'rasterizer': {'name': 'Independent RSX raster', 'version': '1', 'png_encoder': f'Pillow {pillow_version}'},
            'limits': 'Framebuffer-phase pattern fills and VGA palette conversion. Approximate ellipse, '
                      'arc and polygon stepping. Strokes are one-pixel solid approximations. Text is omitted. '
                      'The companion SVG is the separate shared scalable projection.',
        },
        'vga-strokes-02': {
            'mode': 'experimental RSX raster with measured axis-aligned strokes',
            'rasterizer': {'name': 'Independent RSX raster', 'version': '2', 'png_encoder': f'Pillow {pillow_version}'},
            'limits': 'Adds measured horizontal and vertical line styles and widths. Diagonal and shape '
                      'outlines remain approximate. Text is omitted. The SVG is a separate scalable preview.',
        },
        'vga-ff1-03': {
            'mode': 'experimental RSX raster with local FF1 cubic outlines',
            'rasterizer': {'name': 'Independent RSX raster', 'version': '3', 'png_encoder': f'Pillow {pillow_version}'},
            'limits': 'Unhinted base-face fill using decoded contours and nominal advance words. '
                      'Font raster quantization, sizing, colors, pair adjustments and embedded stroke text '
                      'remain incompletely understood. Diagonal and shape outlines remain approximate.',
        },
        'vga-pen-04': {
            'mode': 'experimental RSX raster with the square line pen and slanted brush',
            'rasterizer': {'name': 'Independent RSX raster', 'version': '4', 'png_encoder': f'Pillow {pillow_version}'},
            'limits': 'Keeps local unhinted FF1 outlines. Adds directed oblique line stepping, '
                      'pen stamps and dash timing. Slanted brush spans and other shape outlines '
                      'remain approximate.',
        },
    }
    for name in args.milestone:
        profile = profiles[name]
        if name == 'arc-vector-01':
            profile['rasterizer']['executable_sha256'] = sha256(args.browser.read_bytes()).hexdigest()
        directory = library / name
        if (directory / 'manifest.json').exists():
            previous = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
            if previous['renderer_revision'] != revision:
                raise ValueError(f'committed milestone belongs to a different renderer revision: {name}')
        directory.mkdir(exist_ok=True)
        cases = []
        for (original, native, receipt, drawing, preview), svg_image in zip(source_receipts, vector):
            case = {key: original[key] for key in ('id', 'source_path', 'source_sha256', 'title', 'dimensions',
                                                   'font_resources', 'native_background')}
            case['native_capture'] = receipt
            if name.startswith('vga-'):
                raster = graphics_raster.preview_rsx(drawing.form, drawing.palette, outline_faces=faces)
                projection = Image.frombytes('RGB', (raster.width, raster.height), raster.rgb)
                background = raster.background
                current = raster
            else:
                projection = svg_image
                background = tuple(bytes.fromhex(original['renderer_background'][1:]))
                current = preview
            case['renderer_background'] = '#%02x%02x%02x' % background
            if using_fonts:
                case['renderer_font_resources'] = {
                    family: {'sha256': faces[family.casefold()].sha256, 'mode': 'local-unhinted-base-face'}
                    for family in case['font_resources']
                }
            case['rendered_elements'] = current.rendered_elements
            case['omissions'] = [vars(item) for item in current.omissions]
            diff, case['metrics'] = measure(native, projection, NATIVE_BACKGROUND, background)
            paths = {}
            for kind, image in [('native.png', native), ('renderer.png', projection), ('diff.png', diff)]:
                path = directory / f'{case["id"]}-{kind}'
                paths[kind] = dict(path=path.relative_to(ROOT).as_posix(),
                                   **save_png(path, image), license=audit.LICENSE)
            path = directory / f'{case["id"]}-renderer.svg'
            paths['renderer.svg'] = dict(path=path.relative_to(ROOT).as_posix(),
                                         **put(path, preview.svg.encode(), audit.LICENSE), license=audit.LICENSE)
            case['artifacts'] = paths
            cases.append(case)
        native_profile = baseline['native_profile'] | {
            'starting_disk_sha256': baseline['stopped_disk_sha256'],
            'emulator_terminal_ms': verified['terminal_ms'],
            'emulator_terminal_frames': verified['terminal_frames'],
        }
        manifest = {key: baseline[key] for key in ('schema_version', 'suite_version', 'publication',
                                                  'view_mapping', 'metric_version')}
        put_json(directory / 'manifest.json', manifest | {
            'milestone': name, 'renderer_revision': revision, 'renderer_source_sha256': pins,
            'native_profile': native_profile, 'stopped_disk_sha256': verified['disk_sha256'],
            **profile, 'cases': cases,
        })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence', 'disk-verification'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--browser', type=Path)
    parser.add_argument('--browser-version')
    parser.add_argument('--ff1', type=Path, action='append', default=[])
    parser.add_argument('--milestone', choices=MILESTONES, action='append', required=True)
    build(parser.parse_args())
