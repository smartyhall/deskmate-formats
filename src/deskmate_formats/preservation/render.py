"""Standard-library rendering helpers for offline preservation artifacts."""
import csv
from html import escape
from io import StringIO
import json
import unicodedata


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2, default=bytes.hex,
                       sort_keys=True) + '\n').encode('utf-8')


def csv_text(value):
    """Protect text cells from spreadsheet formula interpretation.

    Numeric values from measured binary fields are passed through separately.
    The apostrophe is an export convention; JSON retains the exact text.
    """
    if not isinstance(value, str):
        return value
    for character in value:
        if character in '\t\r\n=+-@＝＋－＠':
            return "'" + value
        if not (character.isspace() or unicodedata.category(character) in ('Cc', 'Cf')):
            break
    return value


def csv_bytes(rows):
    stream = StringIO(newline='')
    csv.writer(stream).writerows([csv_text(value) for value in row] for row in rows)
    return stream.getvalue().encode('utf-8')


HTML_CONTROLS = dict.fromkeys((*range(9), 11, 12, *range(14, 32), 127), 0xFFFD)


def html_text(value):
    return escape(str(value).translate(HTML_CONTROLS))


STYLE = """
:root { color-scheme: light; font: 16px/1.55 system-ui, sans-serif;
  color: #202c30; background: #f1f4f3; }
body { max-width: 78rem; margin: 0 auto; padding: clamp(.8rem, 3vw, 2.5rem); }
header { border-bottom: 1px solid #b5c8c2; margin-bottom: 1.5rem; padding-bottom: .8rem; }
h1 { overflow-wrap: anywhere; font-size: clamp(1.4rem, 4vw, 2.15rem); margin: 0; }
h2 { font-size: 1.2rem; margin-top: 1.6rem; }
header p, figure, figcaption { margin: .45rem 0; }
figure { min-width: 0; }
a { color: #185c51; }
.scroller { overflow: auto; border: 1px solid #b5c8c2; }
table { border-collapse: collapse; background: white; }
th, td { border: 1px solid #d1dbd8; padding: .35rem .6rem; text-align: left; vertical-align: top; }
th { background: #e4ede9; }
caption { background: #e4ede9; text-align: left; padding: .4rem .6rem; font-weight: 600; }
summary { cursor: pointer; }
code, .small { font-size: .87rem; }
code { overflow-wrap: anywhere; }
.image { display: block; width: min(100%, 54rem); max-height: 70vh; object-fit: contain;
  object-position: left center; background: white; border: 1px solid #d1dbd8; }
.notes { margin-top: 1.6rem; padding: .1rem 1rem .4rem; background: #e4ede9; }
.notes li { margin: .3rem 0; }
"""


def html_page(title, subtitle, body, *, diagnostics=(), style=''):
    notes = ''
    if diagnostics:
        items = ''.join(
            f'<li>{html_text(item.message)}'
            + (f' <span class="small">({html_text(item.location)})</span>' if item.location else '')
            + '</li>'
            for item in diagnostics
        )
        notes = f'<section class="notes"><h2>Conversion notes</h2><ul>{items}</ul></section>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self' file:; base-uri 'none'; form-action 'none'">
<title>{html_text(title)}</title>
<style>{STYLE}{style}</style>
</head>
<body>
<header><h1>{html_text(title)}</h1><p>{html_text(subtitle)}</p></header>
<main>{body}{notes}</main>
</body>
</html>
""".encode('utf-8')
