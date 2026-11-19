"""Inventory unique historical FIGs without copying artwork or document text."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from deskmate_formats import draw, font_resources, graphics


def count_attributes(stats, name, values):
    for field, value in values.items():
        stats[field][f'{name}:{value}'] += 1


def inspect_element(stats, element):
    raw = element.raw
    kind = element.kind.encode('latin-1').hex()
    stats['physical_kinds'][kind] += 1
    stats['type_modifier_pairs'][raw[:2].hex()] += 1
    stats['lengths'][f'{kind}:{len(raw)}'] += 1
    if any(value < 0 for value in element.coordinates[::2]):
        stats['coordinates']['negative_records'] += 1
    if any(element.coordinates[1::2]):
        stats['coordinates']['fractional_records'] += 1
    if element.kind == 'L':
        count_attributes(stats, kind, {'line_colors': raw[18], 'line_weights': raw[19], 'line_styles': raw[1]})
    elif element.kind in ('R', 'E', 'B') and len(raw) >= 24:
        count_attributes(stats, kind, {
            'line_colors': raw[18], 'line_weights': raw[19], 'line_styles': raw[20],
            'fill_patterns': raw[1], 'fill_backgrounds': raw[21], 'fill_foregrounds': raw[22],
            'attribute_pad': raw[23],
        })
    elif element.kind in ('UA', 'UP') and len(raw) >= 36:
        count_attributes(stats, kind, {
            'line_colors': raw[20], 'line_backgrounds': raw[21], 'line_styles': raw[22],
            'line_weights': raw[23], 'fill_patterns': raw[24], 'fill_backgrounds': raw[25],
            'fill_foregrounds': raw[26], 'attribute_pad': raw[27],
        })
        if element.kind == 'UA':
            if len(raw) >= 44:
                words, = unpack_from('<H', raw, 18)
                ext_x, ext_y, *coords = unpack_from('<8H', raw, 28)
                stats['arc_declared_words'][words] += 1
                if not ext_x or not ext_y:
                    stats['arc_extent_flags']['zero_extent'] += 1
                if any(x > ext_x or y > ext_y for x, y in zip(coords[::2], coords[1::2])):
                    stats['arc_extent_flags']['point_outside_local_extent_unsigned'] += 1
                a, b, c, d, e, f = coords
                if (c - a) * (f - b) == (d - b) * (e - a):
                    stats['arc_extent_flags']['collinear_or_repeated_points'] += 1
        else:
            category = 'filled' if raw[32] and raw[24] != 254 else 'closed' if raw[33] else 'open'
            stats['polyline_flags'][f'{raw[32]:02x}{raw[33]:02x}:{category}'] += 1
            stats['polyline_points'][len(element.points)] += 1
    elif element.kind == 'T':
        count_attributes(stats, kind, {'text_rotations': raw[21], 'text_attributes': raw[18],
                                       'line_colors': raw[19], 'text_font_ids': raw[1]})
        stats['text_lengths'][len(element.text_bytes)] += 1
    elif element.kind == 'Uf':
        stats['external_fonts'][element.font_name or 'unresolved'] += 1
        stats['external_font_metadata_sizes'][len(raw)] += 1
    elif element.kind != 'OO':
        stats['uninterpreted_kinds'][kind] += 1


def inspect(drawing, stats):
    form = drawing.form
    by_offset = {element.offset: element for element in form.elements}
    stack = [(entry.offset, 0) for entry in form.entries]
    deepest = 0
    groups = 0
    while stack:
        offset, depth = stack.pop()
        element = by_offset[offset]
        if element.kind == 'OO':
            groups += 1
            deepest = max(deepest, depth + 1)
            stack.extend((child, depth + 1) for child in element.children)
    stats['group_depth'][deepest] += 1
    stats['groups_per_file'][groups] += 1
    stats['leaves_per_file'][len(tuple(form.draw_order()))] += 1
    stats['palette_sha256'][sha256(bytes(channel for row in drawing.palette for channel in row)).hexdigest()] += 1
    for index, value in enumerate(form.header[6:]):
        if value:
            stats['nonzero_form_header_offsets'][index + 6] += 1
    stats['trailer_values'][drawing.trailer.hex()] += 1
    if form.strokes and form.strokes != b'\0\0':
        try:
            glyphs = graphics.parse_strokes(form.strokes)
        except graphics.GraphicsFormatError:
            stats['stroke_banks']['unsupported'] += 1
        else:
            stats['stroke_banks']['decoded'] += 1
            stats['stroke_banks']['glyph_records'] += len(glyphs)
            for glyph in glyphs:
                stats['stroke_font_ids'][glyph.font] += 1
    else:
        stats['stroke_banks']['empty'] += 1
    for record in form.elements:
        inspect_element(stats, record)
    return form, drawing.palette


def inventory(archive, *, recover_arc_length=False, outline_faces=None):
    inputs = {}
    for path in sorted(archive.rglob('*')):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() != '.fig':
            continue
        if path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError('historical input exceeds inventory read bound')
        data = path.read_bytes()
        identity = sha256(data).hexdigest()
        item = inputs.setdefault(identity, (data, []))
        item[1].append(path.relative_to(archive).parts[0])
    records, stats = [], defaultdict(Counter)
    for identity, (data, archives) in sorted(inputs.items()):
        item = {'sha256': identity, 'size': len(data), 'signature_hex': data[:4].hex(),
                'archive_occurrences': dict(sorted(Counter(archives).items()))}
        stats['signatures'][data[:4].hex()] += 1
        try:
            drawing = draw.parse_bytes(data)
        except graphics.GraphicsFormatError as exc:
            error = str(exc)
            stats['structural_failures'][error] += 1
            item.update(strict_read=False, error=error)
            if recover_arc_length:
                try:
                    drawing = draw.parse_bytes(data, recover_arc_length=True)
                except graphics.GraphicsFormatError:
                    drawing = None
            else:
                drawing = None
        else:
            item['strict_read'] = True
        if drawing is not None:
            form, palette = inspect(drawing, stats)
            item['element_count'] = len(form.elements)
            if drawing.recovered_arcs:
                item['recovered_arc_offsets'] = drawing.recovered_arcs
            try:
                preview = graphics.preview_svg(form, palette, outline_faces=outline_faces)
            except graphics.GraphicsFormatError as exc:
                stats['projection_failures'][str(exc)] += 1
            else:
                stats['projection']['documents'] += 1
                stats['projection']['rendered_elements'] += preview.rendered_elements
                stats['projection']['documents_with_omissions'] += bool(preview.omissions)
                for missed in preview.omissions:
                    stats['projection_omissions'][f'{missed.kind_hex}:{missed.reason}'] += 1
        records.append(item)
    result = {
        'schema_version': 1,
        'distinct_files': len(inputs),
        'occurrences': sum(len(item[1]) for item in inputs.values()),
        'strict_reader_accepted': sum(item['strict_read'] for item in records),
        'counts': {key: dict(sorted(counter.items())) for key, counter in sorted(stats.items())},
        'sources': records,
    }
    if recover_arc_length:
        result['recovered_files'] = sum(bool(item.get('recovered_arc_offsets')) for item in records)
    if outline_faces:
        result['outline_resources'] = {face.name: face.sha256 for _, face in sorted(outline_faces.items())}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--recover-arc-length', action='store_true')
    parser.add_argument('--summary-only', action='store_true')
    parser.add_argument('--ff1', type=Path, action='append', default=[])
    args = parser.parse_args()
    result = inventory(args.archive, recover_arc_length=args.recover_arc_length,
                       outline_faces=font_resources.load_outline_faces(args.ff1))
    if args.summary_only:
        sources = result.pop('sources')
        result['ordered_source_digests_sha256'] = sha256(
            ''.join(item['sha256'] for item in sources).encode('ascii')).hexdigest()
        result['failures_and_recoveries'] = [item for item in sources if not item['strict_read']]
    with args.output.open('x', encoding='utf-8', newline='\n') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
