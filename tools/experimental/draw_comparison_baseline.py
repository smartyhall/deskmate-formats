"""Build baseline-pr120 from stopped-disk FIGs and private native captures."""
import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image, __version__ as pillow_version

from deskmate_formats import draw, graphics

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/deskmate_formats/supervisor'))
import draw_comparison_audit as audit


FEATURED = dict(zip(audit.FEATURED, (
    ('prim2', 'pstyle', 'Primitive and style chart', 'Lines, weights, dashes, arcs, patterns and 16 palette swatches.'),
    ('plan2', 'wshop', 'Cedar Workshop', 'Floor plan with door arcs, windows, dimensions and six Cobb labels.'),
    ('land2', 'lakeview', 'Cedar Lake', 'Original lake scene with a house, nested window group and patterned roof.'),
    ('type2', 'letter', 'Graphical typography', 'Cobb heading, alphabet and numerals with varied serialized reference bounds.'),
)))
CROP = (0, 62, 640, 480)
SIZE = (640, 418)
VIEW = (0, 0, 8000, 4840)
NATIVE_BACKGROUND = (0, 0, 129)
COBB = '891e9f07ed2d9fd5f5c8e75d0facd3d4094e891096a6e77a6a8b3db1518a265f'
NOTICE = 'SPDX-FileCopyrightText: 2026 Michael A. Hall\nSPDX-License-Identifier: '
METADATA_LICENSE = 'GPL-3.0-or-later OR CC-BY-SA-4.0'


def identity(data):
    return {'sha256': sha256(data).hexdigest(), 'size': len(data)}


def put(path, data, license_id):
    path.write_bytes(data)
    path.with_suffix(path.suffix + '.license').write_text(NOTICE + license_id + '\n', encoding='utf-8')
    return identity(data)


def put_json(path, value):
    put(path, (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode(), METADATA_LICENSE)


def capture(evidence, dos_name):
    frames = []
    receipts = []
    for suffix in ('reopen', 'repaint'):
        path = evidence / f'{dos_name}-{suffix}'
        receipt = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        data = path.with_suffix('.png').read_bytes()
        status = receipt['status']
        if (sha256(data).hexdigest() != receipt['png_sha256'] or
                (status['w'], status['h'], status['bios_mode'], status['held']) != (640, 480, 18, True)):
            raise ValueError(f'wrong framebuffer provenance for {dos_name}')
        with Image.open(path.with_suffix('.png')) as image:
            crop = image.convert('RGB').crop(CROP)
        frames.append(crop)
        receipts.append(receipt)
    first, last = frames
    if first.tobytes() != last.tobytes():
        raise ValueError(f'canvas did not reach stable repaint for {dos_name}')
    final = receipts[-1]
    return last, {
        'source_role': 'fresh-native-reopen',
        'framebuffer_sha256': final['png_sha256'],
        'first_framebuffer_sha256': receipts[0]['png_sha256'],
        'framebuffer_dimensions': [640, 480],
        'bios_mode': final['status']['bios_mode'],
        'emulated_ms': final['status']['ms'],
        'emulated_frame': final['status']['frames'],
        'crop_xyxy': CROP,
        'zoom': 'Normal',
        'dos_name': dos_name.upper() + '.FIG',
        'reopen_actions': receipts[0]['actions'],
        'stable_repaint_actions': final['actions'],
    }


def rasterize(browser, previews, palettes):
    cols = 4
    width, height = SIZE
    rows = (len(previews) + cols - 1) // cols
    cells = []
    view = ' '.join(map(str, VIEW))
    for preview, color in zip(previews, palettes):
        exact = preview.svg.encode()
        audit.check_svg(exact)
        start = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" preserveAspectRatio="none">'
        svg = start + preview.svg.split('>', 1)[1]
        cells.append(f'<section style="background:{color}">{svg}</section>')
    marker = '#52e8a3'
    page = f'''<!doctype html><meta charset="utf-8">
<style>html,body{{margin:0;overflow:hidden;background:{marker}}}
body{{display:grid;grid-template-columns:repeat({cols},{width}px);grid-auto-rows:{height}px}}
section,svg{{display:block;width:{width}px;height:{height}px;overflow:hidden}}</style>
{''.join(cells)}'''
    with TemporaryDirectory(prefix='deskmate-draw-raster-') as temporary:
        folder = Path(temporary)
        src, png = folder / 'sheet.html', folder / 'sheet.png'
        src.write_text(page, encoding='utf-8')
        bounds = (cols * width, rows * height)
        args = ['--headless=new', '--disable-gpu', '--force-device-scale-factor=1',
                '--force-color-profile=srgb', '--hide-scrollbars', '--allow-file-access-from-files',
                '--disable-background-networking', '--disable-component-update', '--no-first-run']
        command = [str(browser.resolve()), *args, f'--user-data-dir={folder / "profile"}',
                   f'--window-size={bounds[0]},{bounds[1]}', f'--screenshot={png}', src.as_uri()]
        subprocess.run(command, check=True, timeout=90, capture_output=True)
        with Image.open(png) as raw:
            sheet = raw.convert('RGB')
        if sheet.size != bounds or (len(previews) % cols and sheet.getpixel((bounds[0]-1, bounds[1]-1)) != (82, 232, 163)):
            raise ValueError('Chromium raster sheet is clipped or scaled')
        result = []
        for index in range(len(previews)):
            col, row = index % cols, index // cols
            result.append(sheet.crop((col*width, row*height, (col+1)*width, (row+1)*height)))
        return result, args


def measure(native, renderer, native_bg, renderer_bg):
    """Compare raw RGB and per-side foreground masks at the same coordinates."""
    colors = Counter()
    counts = Counter()
    diff = []
    union = overlap = exact = exact_all = native_count = renderer_count = 0
    for a, b in zip(native.get_flattened_data(), renderer.get_flattened_data()):
        if a == b:
            exact_all += 1
        n, r = a != native_bg, b != renderer_bg
        native_count += n
        renderer_count += r
        if n:
            colors['#%02x%02x%02x' % a] += 1
        if not n and not r:
            value = (16, 19, 29)
        else:
            union += 1
            overlap += n and r
            exact += a == b and n and r
            if not r:
                value = (55, 204, 234)
            elif not n:
                value = (250, 185, 64)
            elif a == b:
                value = (142, 155, 179)
            else:
                value = (225, 81, 171)
            counts[value] += 1
        diff.append(value)
    image = Image.new('RGB', native.size)
    image.putdata(diff)
    return image, {
        'native_foreground_pixels': native_count,
        'renderer_foreground_pixels': renderer_count,
        'foreground_union_pixels': union,
        'foreground_intersection_pixels': overlap,
        'foreground_iou': round(overlap / union, 6) if union else None,
        'exact_rgb_shared_foreground_pixels': exact,
        'exact_rgb_on_foreground_union': round(exact / union, 6) if union else None,
        'exact_rgb_frame_pixels': exact_all,
        'overlap_with_rgb_difference_pixels': counts[(225, 81, 171)],
        'native_foreground_palette_counts': dict(sorted(colors.items())),
        'native_foreground_bbox_xyxy': native_mask_bounds(native, native_bg),
        'renderer_foreground_bbox_xyxy': native_mask_bounds(renderer, renderer_bg),
    }


def native_mask_bounds(image, background):
    from PIL import ImageChops

    return ImageChops.difference(image, Image.new('RGB', image.size, background)).getbbox()


def save_png(path, image):
    image.save(path, compress_level=9)
    return put(path, path.read_bytes(), audit.LICENSE)


def build(args):
    root, evidence = args.root.resolve(), args.evidence.resolve()
    repo = root / 'examples/draw-comparison'
    baseline = repo / 'v1/baseline-pr120'
    fixtures = root / 'tests/fixtures/application-generated'
    disk = json.loads(args.disk_verification.read_text(encoding='utf-8'))
    plan = json.loads((repo / 'suite-plan-v1.json').read_text(encoding='utf-8'))
    manifest_path = fixtures / 'manifest.json'
    fixture_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    lookup = {item['path']: item for item in fixture_manifest['fixtures']}
    expected_renderer = subprocess.check_output(['git', '-C', str(args.baseline), 'rev-parse', 'HEAD'],
                                               text=True).strip()
    package_src = Path(draw.__file__).resolve().parents[1]
    if expected_renderer != audit.REVISION or package_src != (args.baseline / 'src').resolve():
        raise ValueError('PYTHONPATH must load the renderer from the pinned detached worktree')
    renderer_hashes = {}
    for name in ('draw.py', 'graphics.py'):
        rel = 'src/deskmate_formats/' + name
        committed = subprocess.check_output(['git', '-C', str(args.baseline), 'show',
                                             f'{audit.REVISION}:{rel}'])
        normalized = (args.baseline / rel).read_bytes().replace(b'\r\n', b'\n')
        if normalized != committed:
            raise ValueError(f'baseline checkout changed {rel}')
        renderer_hashes[rel] = sha256(committed).hexdigest()
    suite = {key: plan[key] for key in ('schema_version', 'suite_version', 'baseline_renderer_revision',
                                        'fixture_manifest', 'diagnostic_draw_fixtures', 'cross_application_controls')}
    suite['featured_cases'] = []
    suite['status'] = 'frozen-native-saved'
    suite['native_profile'] = 'DeskMate 03.05.00 on Tandy 1000 RSX, internal VGA BIOS mode 0x12'
    suite['metric_version'] = 'raw-rgb-foreground-v1'
    suite['capture_crop_xyxy'] = CROP
    revisions = json.loads(args.native_profile.read_text(encoding='utf-8'))
    cases, fixture_bytes = [], {}
    previews, palettes, native_images = [], [], []
    all_ids = audit.FEATURED + audit.DIAGNOSTIC
    for case_id in all_ids:
        if case_id in FEATURED:
            candidate, dos_name, title, description = FEATURED[case_id]
            relative = f'draw/suite-v1-{case_id}.fig'
            path = fixtures / relative
            data = (args.extracted / f'{dos_name.upper()}.FIG').read_bytes()
            generated = identity((evidence / 'candidates-final' / f'{candidate.upper()}.FIG').read_bytes())
        else:
            title = case_id.upper()
            dos_name = case_id
            planned = next(item for item in suite['diagnostic_draw_fixtures'] if item['id'] == case_id)
            path = root / planned['path']
            data = path.read_bytes()
            if identity(data) != {key: planned[key] for key in ('size', 'sha256')}:
                raise ValueError(f'diagnostic fixture does not match the plan for {dos_name}')
        ident = identity(data)
        if disk['files'][f'{dos_name.upper()}.FIG'] != ident:
            raise ValueError(f'independent stopped disk bytes do not match {dos_name}')
        drawing = draw.parse_bytes(data)
        preview = graphics.preview_svg(drawing.form, drawing.palette)
        color = next((r, g, b) for i, r, g, b in drawing.palette if i == 0)
        palettes.append('#%02x%02x%02x' % color)
        previews.append(preview)
        native_image, native = capture(evidence, dos_name)
        native_images.append(native_image)
        source_path = path.relative_to(root).as_posix()
        font_pins = {'Cobb': {'filename': 'COBB.FF1', 'sha256': COBB}} if any(
            e.font_name == 'Cobb' for e in drawing.form.elements) else {}
        if case_id in FEATURED:
            fixture_bytes[path] = data
            fixture = {
                'path': relative, **ident, 'application': 'Tandy DeskMate Draw',
                'version': 'DeskMate 03.05.00', 'experiment': '2026-11-19 Draw comparison suite v1',
                'origin': 'Original tool-authored synthetic drawing, opened and saved with native Draw Save As.',
                'expected_content': description,
                'generation_method': 'PYTHONPATH=src python tools/experimental/draw_suite_candidates.py '
                                     'tests/fixtures/application-generated/draw <private-dir>',
                'evidence_class': 'Native Draw Save As and independent stopped-disk extraction',
                'synthetic_data': True, 'native_saved': True, 'native_reopened': True,
                'generator_output': {'dos_name': candidate.upper() + '.FIG', **generated},
                'templates': {f'draw/{name}.fig': lookup[f'draw/{name}.fig']['sha256'] for name in ('d01', 'd23')},
            }
            lookup[relative] = fixture
            suite['featured_cases'].append({
                'id': case_id, 'title': title, 'description': description, 'path': source_path, **ident,
                'status': 'native-saved', 'native_dos_name': native['dos_name'], 'generator_output': fixture['generator_output'],
                'display_directory': [asdict(e) for e in drawing.form.entries],
                'physical_records': [
                    {'offset': e.offset, 'type_bytes': e.raw[:2].hex(), 'coordinate_words': e.coordinates,
                     'record_tail_hex': e.raw[18:].hex(), 'child_offsets': e.children}
                    for e in drawing.form.elements
                ],
                'palette_entries': drawing.palette, 'font_resources': font_pins,
            })
        cases.append({
            'id': case_id, 'title': title, 'source_path': source_path, 'source_sha256': ident['sha256'],
            'dimensions': SIZE, 'native_capture': native, 'font_resources': font_pins,
            'renderer_background': palettes[-1], 'native_background': '#000081',
            'rendered_elements': preview.rendered_elements, 'omissions': [asdict(o) for o in preview.omissions],
        })
    rendered, chrome_args = rasterize(args.browser, previews, palettes)
    for path, data in fixture_bytes.items():
        put(path, data, audit.LICENSE)
    for case, reference, projection, preview in zip(cases, native_images, rendered, previews):
        color = tuple(bytes.fromhex(case['renderer_background'][1:]))
        diff, case['metrics'] = measure(reference, projection, NATIVE_BACKGROUND, color)
        files = {}
        for kind, image in (('native.png', reference), ('renderer.png', projection), ('diff.png', diff)):
            path = baseline / f'{case["id"]}-{kind}'
            files[kind] = dict(path=path.relative_to(root).as_posix(), **save_png(path, image), license=audit.LICENSE)
        kind = 'renderer.svg'
        path = baseline / f'{case["id"]}-{kind}'
        files[kind] = dict(path=path.relative_to(root).as_posix(),
                           **put(path, preview.svg.encode('utf-8'), audit.LICENSE), license=audit.LICENSE)
        case['artifacts'] = files
    if lookup.keys() != {item['path'] for item in fixture_manifest['fixtures']}:
        fixture_manifest['fixtures'] += [item for path, item in lookup.items()
                                         if path not in {f['path'] for f in fixture_manifest['fixtures']}]
    manifest_path.write_text(json.dumps(fixture_manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    put_json(repo / 'suite-v1.json', suite)
    put_json(baseline / 'manifest.json', {
        'schema_version': 1, 'milestone': audit.BASELINE, 'suite_version': 'v1',
        'renderer_revision': audit.REVISION, 'renderer_source_sha256': renderer_hashes,
        'publication': 'original-synthetic-drawing-crops', 'native_profile': revisions,
        'stopped_disk_sha256': disk['disk_sha256'],
        'view_mapping': {'native_frame_origin_xy': [0, 62], 'world_view_box': VIEW,
                         'world_to_crop_pixel_continuous_scale': [SIZE[0] / VIEW[2], SIZE[1] / VIEW[3]],
                         'method': 'World origin fixed from viewport control; independent X/Y scale, no alignment fit per case.'},
        'rasterizer': {'name': 'Chromium headless', 'version': args.browser_version,
                       'executable_sha256': identity(args.browser.read_bytes())['sha256'],
                       'flags': chrome_args, 'preserve_aspect_ratio': 'none', 'device_scale_factor': 1,
                       'png_encoder': f'Pillow {pillow_version}'},
        'metric_version': suite['metric_version'],
        'limits': 'Raw RGB differs even at some matching palette indices. SVG uses antialiasing and approximate fills and strokes.',
        'cases': cases,
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'baseline', 'evidence', 'extracted', 'disk-verification', 'native-profile', 'browser'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--browser-version', required=True)
    build(parser.parse_args())
