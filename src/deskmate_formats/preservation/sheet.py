"""Worksheet grids and tabular projections of the native WKS cell model."""
from dataclasses import asdict
from itertools import chain

from .model import Conversion, Diagnostic
from .render import csv_bytes, html_page, html_text


SHEET_STYLE = """
.sheet { table-layout: fixed; }
.sheet th, .sheet td { white-space: pre-wrap; overflow-wrap: anywhere; }
.sheet thead th, .sheet tbody th { text-align: center; white-space: nowrap; }
.sheet .number { text-align: right; font-variant-numeric: tabular-nums; }
.formula { background: #edf3fc; }
.input { background: #f6f0dc; }
.text_block { background: #f5f6f0; }
.sheet .small { color: #3a5259; line-height: 1.35; display: inline-block; }
.error { color: #8e2639; font-weight: 600; }
"""


def _value(cell):
    if cell is None:
        return None
    if cell.category in ('formula', 'input'):
        return cell.numeric_value if cell.result_flag and not cell.error_flag else None
    if cell.category == 'number':
        return cell.numeric_value
    return cell.text


def _detail_row(cell):
    return (
        cell.row, cell.column, cell.category,
        cell.text,
        cell.text if cell.category == 'formula' else None,
        cell.numeric_value, f'0x{cell.status:04X}',
        cell.result_flag, cell.error_flag, cell.row_span, cell.column_span,
        cell.offset, cell.raw_string.hex(),
    )


def _spans(cells):
    covered = set()
    for (row, column), cell in cells.items():
        if cell.category != 'text_block':
            continue
        for r in range(row, row + cell.row_span):
            for c in range(column, column + cell.column_span):
                key = r, c
                if key == (row, column):
                    continue
                if key in cells or key in covered:
                    return None
                covered.add(key)
    return covered


def _cell_html(cell, *, merged):
    if cell is None:
        return '<td></td>'
    label = html_text(cell.text)
    stored_number = html_text(cell.numeric_value) if cell.numeric_value is not None else 'Unavailable'
    span = ''
    if cell.category == 'formula':
        if cell.error_flag:
            display = '<span class="error">Stored error</span>'
        elif cell.result_flag and cell.numeric_value is not None:
            display = html_text(cell.numeric_value)
        else:
            display = 'No usable stored result'
        label = (f'<details><summary>{display}</summary><code>{label}</code><br>'
                 f'<span class="small">Stored {stored_number}<br>'
                 f'Result flag {"set" if cell.result_flag else "clear"}<br>'
                 f'Status 0x{cell.status:04X}</span></details>')
    elif cell.category == 'input':
        state = 'Stored value' if cell.result_flag else 'Result flag clear'
        label = (f'<strong>{label}</strong><br><span class="small">{state} · '
                 f'{stored_number}</span>')
    elif cell.category == 'text_block' and merged:
        span = f' rowspan="{cell.row_span}" colspan="{cell.column_span}"'
    return f'<td class="{cell.category}"{span}>{label}</td>'


def _grid(sheet, cells, covered):
    rows, columns = sheet.extreme_row, sheet.extreme_column
    if not cells:
        return '<p>This worksheet is empty.</p>'
    widths = [f'<col style="width:{sheet.column_widths[c] + 2}ch">'
              for c in range(1, columns + 1)]
    headings = ''.join(f'<th scope="col">C{c}</th>' for c in range(1, columns + 1))
    table = []
    for r in range(1, rows + 1):
        columns_html = ''.join(
            _cell_html(cells.get((r, c)), merged=covered is not None)
            for c in range(1, columns + 1) if covered is None or (r, c) not in covered
        )
        table.append(f'<tr><th scope="row">R{r}</th>{columns_html}</tr>')
    width = 6 + sum(sheet.column_widths[1:columns + 1]) + 2 * columns
    return (f'<div class="scroller" tabindex="0" aria-label="Worksheet grid">'
            f'<table class="sheet" style="width:{width}ch"><caption>Used grid · {rows} × {columns}</caption>'
            f'<colgroup><col style="width:6ch">{"".join(widths)}</colgroup>'
            f'<thead><tr><th scope="col">Row</th>{headings}</tr></thead>'
            f'<tbody>{"".join(table)}</tbody></table></div>')


def convert(sheet, filename):
    cells = {(c.row, c.column): c for c in sheet.cells if not c.dummy}
    ordered = [cells[key] for key in sorted(cells)]
    conversion = Conversion(asdict(sheet), [
        Diagnostic('worksheet_format_approximation', 'approximation',
                   'Column widths and text-block spans use browser layout. Native alignment, '
                   'precision settings and print layout are preserved as source data.'),
        Diagnostic('csv_text_safety_prefix', 'notice',
                   'CSV adds an apostrophe to text that could be interpreted as a formula. '
                   'The JSON retains the original strings.'),
    ])
    if any(c.category == 'formula' for c in ordered):
        conversion.diagnostics.append(Diagnostic(
            'worksheet_cache_unverified', 'notice',
            'Formula results come from the saved numeric fields and may be stale. '
            'Open a formula cell to see its expression, stored field and status.'))
    if any(c.error_flag or c.result_flag is False for c in ordered):
        conversion.diagnostics.append(Diagnostic(
            'worksheet_value_csv_result_omitted', 'omission',
            'The value CSV leaves error results and fields with a clear result flag blank. '
            'The cell listing and JSON retain their stored numeric fields.'))
    if any(c.category in ('number', 'formula', 'input') and c.numeric_value is None for c in ordered):
        conversion.diagnostics.append(Diagnostic(
            'worksheet_nonfinite_numeric_field', 'opaque',
            'A non-finite numeric field is blank in CSV and null in JSON. The original cell bytes are retained.'))
    covered = _spans(cells)
    if covered is None:
        conversion.diagnostics.append(Diagnostic(
            'worksheet_overlapping_spans', 'approximation',
            'Overlapping text-block spans are displayed as single cells to keep every anchor visible.'))
    values = ([_value(cells.get((r, c))) for c in range(1, sheet.extreme_column + 1)]
              for r in range(1, sheet.extreme_row + 1))
    headings = ('row', 'column', 'category', 'stored_text', 'formula_source',
                'stored_numeric_value', 'status_hex', 'result_flag', 'error_flag',
                'row_span', 'column_span', 'file_offset', 'raw_string_hex')
    conversion.artifacts.update({
        'values.csv': csv_bytes(values),
        'cells.csv': csv_bytes(chain([headings], map(_detail_row, ordered))),
        'preview.html': html_page(filename, 'DeskMate Worksheet · saved cells',
                                  _grid(sheet, cells, covered),
                                  diagnostics=conversion.diagnostics, style=SHEET_STYLE),
    })
    return conversion
