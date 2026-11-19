"""Measure per-milestone symmetric foreground boundary distances in native pixels."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import fmean

from PIL import Image


def boundary(mask, width, height):
    return [
        p for p, painted in enumerate(mask) if painted and (
            p < width or p >= width * (height - 1) or p % width in (0, width - 1)
            or not (mask[p - width] and mask[p + width] and mask[p - 1] and mask[p + 1])
        )
    ]


def distance_map(points, width, height):
    """City-block distances to the nearest point via two raster sweeps."""
    field = [width + height] * (width * height)
    for position in points:
        field[position] = 0
    for y in range(height):
        top = y * width
        for x in range(width):
            i = top + x
            cost = field[i]
            if y and field[i - width] < cost - 1:
                cost = field[i - width] + 1
            if x and field[i - 1] < cost - 1:
                cost = field[i - 1] + 1
            field[i] = cost
    for y in range(height - 1, -1, -1):
        top = y * width
        for x in range(width - 1, -1, -1):
            i = top + x
            cost = field[i]
            if y < height - 1 and field[i + width] < cost - 1:
                cost = field[i + width] + 1
            if x < width - 1 and field[i + 1] < cost - 1:
                cost = field[i + 1] + 1
            field[i] = cost
    return field


def foreground_boundary(root, artifact, backdrop, size):
    path = root / artifact['path']
    if sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
        raise ValueError(f'comparison artifact hash disagrees: {path.name}')
    with Image.open(path) as source:
        if source.size != size:
            raise ValueError('unexpected comparison dimensions')
        color = tuple(bytes.fromhex(backdrop[1:]))
        args = [pixel != color for pixel in source.convert('RGB').get_flattened_data()]
    return boundary(args, *size)


def compare(root, case):
    size = tuple(case['dimensions'])
    native = foreground_boundary(root, case['artifacts']['native.png'], case['native_background'], size)
    renderer = foreground_boundary(root, case['artifacts']['renderer.png'], case['renderer_background'], size)
    fields = {'native_boundary_pixels': len(native), 'renderer_boundary_pixels': len(renderer)}
    if not native or not renderer:
        return fields | {'mean_l1_pixels': None, 'p95_l1_pixels': None}
    n_map, r_map = distance_map(native, *size), distance_map(renderer, *size)
    samples = sorted([r_map[i] for i in native] + [n_map[i] for i in renderer])
    return fields | {'mean_l1_pixels': round(fmean(samples), 6),
                     'p95_l1_pixels': samples[(95 * len(samples) + 99) // 100 - 1]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = {'schema_version': 1,
              'method': '4-neighborhood foreground boundaries; two-way Manhattan distance in matched pixels.',
              'milestones': {}}
    for path in sorted((args.root / 'examples/draw-comparison/v1').glob('*/manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        result['milestones'][manifest['milestone']] = {
            'renderer_revision': manifest['renderer_revision'],
            'cases': {case['id']: compare(args.root, case) for case in manifest['cases']},
        }
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
