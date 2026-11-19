"""Draw, Text and Filer projections using the shared native graphics reader."""
from dataclasses import asdict

from .. import filer_graphics, graphics, text
from .model import Conversion, Diagnostic
from .render import csv_bytes, html_page, html_table, html_text


MAX_TEXT_PICTURE_PREVIEWS = 128
MAX_TEXT_SVG_BYTES = 8 * 1024 * 1024
TEXT_STYLE = """
.document { max-width: 53rem; background: white; border: 1px solid #d1dbd8;
  padding: clamp(.8rem, 4vw, 3rem); margin: 0 auto; font: 1.12rem/1.65 Georgia, serif; }
.document p { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; min-height: 1.65em; }
.document .dense-lines { white-space: pre-wrap; overflow-wrap: anywhere; }
.document .center { text-align: center; }
.document figure { margin-block: .8rem; }
.document figcaption { font: .85rem/1.5 system-ui, sans-serif; }
.document .image { width: min(100%, 34rem); max-height: 36vh; }
"""


def _visual_diagnostics(*, native_palette):
    items = [Diagnostic('graphics_visual_approximation', 'approximation',
                        'The geometry preview uses simple strokes, solid fills and approximate '
                        'glyph spacing. Native style, pattern and print data are preserved in the source.')]
    if not native_palette:
        items.append(Diagnostic('graphics_palette_unavailable', 'approximation',
                                'This container has no measured palette. The preview uses neutral colors.'))
    return items


def _svg_data(preview):
    return {'view_box': preview.view_box, 'rendered_bounds': preview.rendered_bounds,
            'rendered_elements': preview.rendered_elements,
            'omissions': [asdict(item) for item in preview.omissions]}


def _omissions(preview, location):
    if not preview.omissions:
        return []
    kinds = ', '.join(sorted({item.kind_hex for item in preview.omissions}))
    return [Diagnostic('graphics_elements_omitted', 'omission',
                       f'{len(preview.omissions)} element(s) omitted from SVG. '
                       f'Type bytes in hex: {kinds}. See content.json for offsets and reasons.', location)]


def _figure(path, label, detail, *, style='', rendered=True):
    image = (f'<img class="image" src="{path}" alt="{html_text(label)}">'
             if rendered else '<p>No supported geometry to display.</p>')
    return (f'<figure{style}>{image}<figcaption>{html_text(detail)} · '
            f'<a href="{path}">SVG</a></figcaption></figure>')


def convert_draw(drawing, filename, *, outline_faces=None):
    preview = graphics.preview_svg(drawing.form, drawing.palette, outline_faces=outline_faces)
    content = asdict(drawing)
    content['preview'] = _svg_data(preview)
    content['profile'] = 'draw-3.05-14-fig'
    diagnostics = _visual_diagnostics(native_palette=True) + _omissions(preview, 'Draw form')
    dimensions = f'{preview.view_box[2]:.3g} × {preview.view_box[3]:.3g} world units (padded preview)'
    body = _figure('drawing.svg', 'Recovered DeskMate Draw geometry', dimensions,
                   rendered=bool(preview.rendered_elements))
    return Conversion(content, diagnostics, {
        'drawing.svg': preview.svg.encode('utf-8'),
        'preview.html': html_page(filename, 'DeskMate Draw · recovered geometry', body, diagnostics=diagnostics),
    })


def _picture_previews(document, conversion, outline_faces):
    figures = []
    budget = MAX_TEXT_SVG_BYTES
    limited = 0
    for number, picture in enumerate(document.pictures, 1):
        metadata = conversion.content['pictures'][number - 1]
        location = f'Picture {number}, file offset {picture.offset}'
        caption = f'Picture {number} · source column {picture.column}'
        if number > MAX_TEXT_PICTURE_PREVIEWS or budget <= 0:
            limited += 1
            metadata['preview_status'] = 'preview_limit'
            figures.append('')
            continue
        try:
            form = graphics.parse_bytes(picture.payload, text_picture=True)
        except graphics.GraphicsFormatError as exc:
            metadata['preview_status'] = 'unsupported_form'
            conversion.diagnostics.append(Diagnostic(
                'text_picture_unsupported', 'omission', f'Picture geometry could not be decoded: {exc}', location))
            figures.append(f'<p>{caption} · geometry unavailable</p>')
            continue
        preview = graphics.preview_svg(form, outline_faces=outline_faces)
        rendered = preview.svg.encode('utf-8')
        if len(rendered) > budget:
            limited += 1
            metadata['preview_status'] = 'preview_limit'
            figures.append(f'<p>{caption} · preview limit reached</p>')
            continue
        budget -= len(rendered)
        path = f'assets/picture-{number:03}.svg'
        conversion.artifacts[path] = rendered
        metadata.update(preview_status='svg', asset=path, preview=_svg_data(preview))
        conversion.diagnostics.extend(_omissions(preview, location))
        indent = f' style="margin-inline-start:min({picture.column}ch,35%)"'
        figures.append(_figure(path, 'Recovered illustration from DeskMate Draw', caption,
                               style=indent, rendered=bool(preview.rendered_elements)))
    if limited:
        conversion.diagnostics.append(Diagnostic(
            'text_picture_preview_limit', 'omission',
            f'{limited} picture(s) exceed the preview budget. All payload bytes are retained in content.json.'))
    return figures


def _document_body(document, figures, *, use_controls, dense_lines):
    controls = document.controls if use_controls else ()
    events = [(item.text_offset, item.offset, item) for item in (*controls, *document.pictures)]
    events.sort()
    body, line, active = [], [], set()
    position = 0
    centered = False
    layout_inside_line = False

    def flush():
        if dense_lines:
            body.append(f'<div class="dense-lines">{"".join(line)}</div>')
        else:
            css = ' class="center"' if centered else ''
            body.append(f'<p{css}>{"".join(line)}</p>')
        line.clear()

    def consume(stop):
        nonlocal position
        if dense_lines:
            line.append(html_text(document.text[position:stop]))
            position = stop
            return
        while position < stop:
            newline = document.text.find('\n', position, stop)
            end = stop if newline < 0 else newline
            if end > position:
                value = html_text(document.text[position:end])
                if 0x13 in active:
                    value = f'<strong>{value}</strong>'
                if 0x11 in active:
                    value = f'<u>{value}</u>'
                line.append(value)
            position = end
            if newline >= 0:
                flush()
                position += 1

    picture_number = 0
    for offset, _, event in events:
        consume(offset)
        if isinstance(event, text.Picture):
            if not figures[picture_number]:
                picture_number += 1
                continue
            if line:
                flush()
            body.append(figures[picture_number])
            picture_number += 1
        elif event.raw in text.LAYOUT_COMMANDS:
            if line:
                layout_inside_line = True
            else:
                centered = event.raw == text.LAYOUT_COMMANDS[0]
        elif event.raw[0] in text.ATTRIBUTE_ON:
            active.add(event.raw[0])
        else:
            active.remove(text.ATTRIBUTE_OFF[event.raw[0]])
    consume(len(document.text))
    if line or (document.text.endswith('\n') and
                not any(item.text_offset == len(document.text) for item in document.pictures)):
        flush()
    if not body:
        body.append('<p>No previewable text or pictures.</p>')
    return '<article class="document">' + ''.join(body) + '</article>', layout_inside_line


def convert_text(document, filename, *, outline_faces=None):
    conversion = Conversion(asdict(document), [
        Diagnostic('text_layout_approximation', 'approximation',
                   'Hard line breaks and measured character attributes are displayed with browser '
                   'fonts and wrapping. Page settings and native pagination remain source data.'),
    ])
    if document.pictures:
        conversion.diagnostics.extend(_visual_diagnostics(native_palette=False))
        conversion.diagnostics.append(Diagnostic(
            'text_picture_placement_approximation', 'approximation',
            'Pictures appear in source order at their decoded text positions. Horizontal indent '
            'uses the stored display column with a width cap for narrow screens.'))
    figures = _picture_previews(document, conversion, outline_faces)
    dense_lines = document.text.count('\n') > 20_000
    use_controls = len(document.controls) == document.control_count and not dense_lines
    if not use_controls:
        conversion.diagnostics.append(Diagnostic(
            'text_formatting_preview_limit', 'omission',
            'The document exceeds the formatting preview budget. Literal text and picture positions '
            'are shown. The original retains every control byte.'))
    body, unmeasured_layout = _document_body(document, figures, use_controls=use_controls,
                                             dense_lines=dense_lines)
    if unmeasured_layout:
        conversion.diagnostics.append(Diagnostic(
            'text_line_layout_omitted', 'omission',
            'A layout control inside a line is retained in JSON. Centering is applied at measured line boundaries.'))
    conversion.artifacts.update({
        'text.txt': document.text.encode('utf-8'),
        'preview.html': html_page(filename, 'DeskMate Text · document preview', body,
                                  diagnostics=conversion.diagnostics, style=TEXT_STYLE),
    })
    return conversion


def _record(row):
    return {
        'storage_record_id': row.record_id,
        'offset': row.offset,
        'index_offset': row.index_offset,
        'values': [value.decode('ascii') if all(32 <= byte <= 126 for byte in value) else None
                   for value in row.fields],
        'fields_hex': [value.hex() for value in row.fields],
        'raw_hex': row.raw.hex(),
    }


def convert_filer(snapshot, filename, *, outline_faces=None):
    data = snapshot.table('DATA')
    headings = [column.name for column in data.columns]
    records = [_record(row) for row in data.rows]
    content = {
        'tables': [{'name': table.name, 'columns': [asdict(col) for col in table.columns],
                    'record_count': table.record_count, 'data_pages': table.data_pages,
                    'index_page': table.index_page, 'descriptor_offset': table.descriptor_offset,
                    'raw_descriptor': table.raw_descriptor} for table in snapshot.tables],
        'data_columns': headings,
        'data_index': [asdict(entry) for entry in data.entries],
        'data_records': records,
        'retired_data_records': [_record(row) for row in data.retired_rows],
        'graphics': [],
    }
    conversion = Conversion(content, [
        Diagnostic('filer_layout_opaque', 'opaque',
                   'LAYOUTS and native form behavior remain in the original file. Geometry previews '
                   'show the decoded GRAPHICS sections.'),
        Diagnostic('filer_fields_untyped', 'notice',
                   'Printable DATA values are copied as text in native field order. Field type codes '
                   'are retained without date, number or other semantic coercion.'),
        Diagnostic('csv_text_safety_prefix', 'notice',
                   'CSV adds an apostrophe to text that could be interpreted as a formula. '
                   'JSON retains the original strings.'),
    ])
    if any(None in row['values'] for row in records):
        conversion.diagnostics.append(Diagnostic(
            'filer_data_field_opaque', 'omission',
            'Non-printable DATA values are blank in CSV and shown as opaque in HTML. JSON includes the exact bytes.'))
    if data.retired_rows:
        conversion.diagnostics.append(Diagnostic(
            'filer_retired_rows_omitted', 'omission', 'Retired DATA rows are included in JSON only.'))
    figures = []
    try:
        sections = filer_graphics.decode(snapshot)
    except graphics.GraphicsFormatError as exc:
        sections = ()
        conversion.diagnostics.append(Diagnostic(
            'filer_graphics_unsupported', 'omission', f'GRAPHICS could not be decoded: {exc}'))
    if sections:
        conversion.diagnostics.extend(_visual_diagnostics(native_palette=False))
    for section in sections:
        kind = {'F': 'card', 'R': 'report'}[section.marker]
        preview = graphics.preview_svg(section.form, outline_faces=outline_faces)
        asset = f'assets/{kind}.svg'
        conversion.artifacts[asset] = preview.svg.encode('utf-8')
        content['graphics'].append({**asdict(section), 'asset': asset, 'preview': _svg_data(preview)})
        conversion.diagnostics.extend(_omissions(preview, f'Filer {kind} form'))
        figures.append(_figure(asset, f'Recovered Filer {kind} geometry', f'{kind.title()} GRAPHICS',
                               rendered=bool(preview.rendered_elements)))
    database_tables = html_table(('Table', 'Rows', 'Data pages', 'Index page'),
                                 ((t.name, t.record_count, ', '.join(map(str, t.data_pages)), t.index_page)
                                  for t in snapshot.tables), 'Database tables')
    fields = html_table(('Field', 'Native type', 'Declared width'),
                        ((col.name, col.kind, col.width) for col in data.columns), 'DATA field definitions')
    data_rows = ([value if value is not None else f'Opaque [{raw}]'
                  for value, raw in zip(row['values'], row['fields_hex'], strict=True)] for row in records)
    body = database_tables + '<h2>Fields and records</h2>' + fields + (
        html_table(headings, data_rows, 'Live DATA records') if records else '<p>No live DATA records.</p>')
    if figures:
        body += '<h2>Recovered form geometry</h2>' + ''.join(figures)
    conversion.artifacts.update({
        'records.csv': csv_bytes([headings, *(row['values'] for row in records)]),
        'preview.html': html_page(filename, 'DeskMate Filer · database overview', body,
                                  diagnostics=conversion.diagnostics),
    })
    return conversion
