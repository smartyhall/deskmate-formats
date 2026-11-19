"""Measure an outline round trip independently of the Draw rasterizer."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from math import dist
from pathlib import Path

from deskmate_formats.ff1 import parse_resource, serialize_resource
from deskmate_formats.ff1_interchange import export_cff, import_outline, _open_font, _source_contours
from deskmate_formats.font_resources import Contour


def path_points(contour):
    start = contour.start
    yield start
    for segment in contour.segments:
        end = segment[-1]
        if len(segment) == 3:
            a, b, _ = segment
            for step in range(1, 16):
                t = step / 16
                s = 1 - t
                yield tuple(s**3*x + 3*s*s*t*y + 3*s*t*t*z + t**3*w
                            for x, y, z, w in zip(start, a, b, end))
        yield end
        start = end


def orientation(points):
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:]))
    return (area > 0) - (area < 0)


def _normalize_lines(contour):
    start = contour.start
    segments = []
    for segment in contour.segments:
        if all(point == start for point in segment):
            continue
        if len(segment) == 1 and segments and len(segments[-1]) == 1:
            previous = segments[-2][-1] if len(segments) > 1 else contour.start
            ux, uy = start[0] - previous[0], start[1] - previous[1]
            vx, vy = segment[0][0] - start[0], segment[0][1] - start[1]
            if ux * vy == uy * vx and ux * vx + uy * vy > 0:
                segments.pop()
        segments.append(segment)
        start = segment[-1]
    return Contour(contour.start, tuple(segments))


def compare(source, output, represented):
    result = dict(max_sample_distance_em1000=0, max_bound_error_em1000=0,
                  max_advance_error_em1000=0, contour_count_differences=0,
                  segment_structure_differences=0, orientation_differences=0)
    from fontTools.pens.boundsPen import BoundsPen

    with _open_font(source) as src, _open_font(output) as out:
        s_set, o_set = src.getGlyphSet(), out.getGlyphSet()
        smap, omap = src.getBestCmap(), out.getBestCmap()
        shared = sorted(smap.keys() & omap.keys() & set(represented))
        s_scale, o_scale = (1000 / font['head'].unitsPerEm for font in (src, out))
        for code in shared:
            left, right = smap[code], omap[code]
            a, b = _source_contours(s_set, left), _source_contours(o_set, right)
            result['contour_count_differences'] += int(len(a) != len(b))
            result['max_advance_error_em1000'] = max(result['max_advance_error_em1000'],
                                                     abs(s_set[left].width*s_scale - o_set[right].width*o_scale))
            sp, op = BoundsPen(None), BoundsPen(None)
            for pen, contours in ((sp, a), (op, b)):
                for contour in contours:
                    pen.moveTo(contour.start)
                    for segment in contour.segments:
                        if len(segment) == 1:
                            pen.lineTo(*segment)
                        else:
                            pen.curveTo(*segment)
                    pen.closePath()
            if sp.bounds is not None and op.bounds is not None:
                result['max_bound_error_em1000'] = max(
                    result['max_bound_error_em1000'],
                    *(abs(x*s_scale-y*o_scale) for x, y in zip(sp.bounds, op.bounds)))
            for s, o in zip(a, b):
                if tuple(map(len, s.segments)) != tuple(map(len, o.segments)):
                    result['segment_structure_differences'] += 1
                    s, o = _normalize_lines(s), _normalize_lines(o)
                spoints, opoints = list(path_points(s)), list(path_points(o))
                result['orientation_differences'] += int(orientation(spoints) != orientation(opoints))
                if tuple(map(len, s.segments)) != tuple(map(len, o.segments)):
                    continue
                result['max_sample_distance_em1000'] = max(
                    result['max_sample_distance_em1000'],
                    *(dist((x*s_scale, y*s_scale), (u*o_scale, v*o_scale))
                      for (x, y), (u, v) in zip(spoints, opoints)))
        result['shared_codepoints'] = len(shared)
        result['reconstructed_metrics_em1000'] = {
            key: getattr(out['hhea'], key)*o_scale for key in ('ascent', 'descent', 'lineGap')}
        result['source_metrics_em1000'] = {
            key: getattr(src['hhea'], key)*s_scale for key in ('ascent', 'descent', 'lineGap')}
    return result, shared


def freetype_overlap(source, output, shared, size):
    from PIL import Image, ImageDraw, ImageFont

    first, second = [ImageFont.truetype(BytesIO(data), size, layout_engine=ImageFont.Layout.BASIC)
                     for data in (source, output)]
    matched = either = 0
    for code in shared:
        char = chr(code)
        a, b = (font.getbbox(char, anchor='ls') for font in (first, second))
        x, y = min(a[0], b[0]), min(a[1], b[1])
        w, h = max(a[2], b[2]) - x, max(a[3], b[3]) - y
        if not w or not h:
            continue
        images = [Image.new('L', (w, h)) for _ in range(2)]
        for image, font in zip(images, (first, second)):
            ImageDraw.Draw(image).text((-x, -y), char, fill=255, font=font, anchor='ls')
        for u, v in zip(images[0].tobytes(), images[1].tobytes()):
            matched += min(u, v)
            either += max(u, v)
    return matched / either if either else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    data = args.source.read_bytes()
    model, receipt = import_outline(data, 'Conversion Control')
    ff1 = serialize_resource(model)
    output = export_cff(parse_resource(ff1))
    metrics, shared = compare(data, output, receipt['represented_codepoints'])
    metrics['coverage_weighted_raster_overlap'] = {
        size: freetype_overlap(data, output, shared, size) for size in (12, 24, 48, 96)
    }
    print(json.dumps({'source_sha256': sha256(data).hexdigest(), 'import': receipt, 'metrics': metrics},
                     indent=2))


if __name__ == '__main__':
    main()
