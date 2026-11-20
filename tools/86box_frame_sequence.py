"""Sample an authenticated held guest and compare decoded framebuffer pixels."""
import argparse
import hashlib
import importlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops

Client = importlib.import_module('86box_client').Client


def compare(previous, current, mask=None):
    if previous is None or previous.size != current.size:
        return None
    difference = ImageChops.difference(previous, current)
    if mask is not None:
        left, top, right, bottom = mask
        if not 0 <= left < right <= difference.width or not 0 <= top < bottom <= difference.height:
            raise ValueError('mask extends outside the sampled framebuffer')
        difference.paste((0, 0, 0), mask)
    with difference:
        r, g, b = difference.split()
        with r, g, b, ImageChops.lighter(r, g) as rg, ImageChops.lighter(rg, b) as any_channel:
            return difference.width * difference.height - any_channel.histogram()[0]


def sample(client, output, intervals, mask, stop):
    output.mkdir(exist_ok=False)
    before = client.status()
    rows = []
    previous = None
    stopped = False
    try:
        for index, interval in enumerate((0, *intervals)):
            result = client.advance(interval, stop)
            stopped = result['stopped']
            if stopped:
                break
            png, meta = client.framebuffer()
            if meta.get('ms') != result['status']['ms'] or meta.get('frames') != result['status']['frames']:
                raise ValueError('frame and held status disagree')
            name = f'frame-{index:03d}.png'
            with (output / name).open('xb') as stream:
                stream.write(png)
            with Image.open(BytesIO(png)) as decoded:
                rgb = decoded.convert('RGB')
            try:
                rows.append({'image': name, 'status': meta, 'interval_ms': interval,
                             'pixel_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
                             'changed_pixels': compare(previous, rgb, mask)})
            except BaseException:
                rgb.close()
                raise
            if previous is not None:
                previous.close()
            previous = rgb
    finally:
        if previous is not None:
            previous.close()
        receipt = {'start_status': before, 'mask_half_open': mask, 'stopped': stopped, 'samples': rows}
        (output / 'observations.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--machine', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--intervals', nargs='+', type=int, default=[271, 503, 827, 1151])
    parser.add_argument('--mask', nargs=4, type=int, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'))
    parser.add_argument('--stop', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if any(not 1 <= interval <= 60000 for interval in args.intervals):
        parser.error('intervals must be 1..60000 ms')
    with Client(args.machine / 'automation.token', args.port) as client:
        receipt = sample(client, args.output, args.intervals, args.mask, args.stop)
    print(json.dumps({'sample_count': len(receipt['samples']), 'stopped': receipt['stopped']}))


if __name__ == '__main__':
    main()
