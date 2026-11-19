"""Outline interchange between static OpenType fonts and measured FF1 resources."""
from fractions import Fraction
from io import BytesIO
import math
import re

from .ff1 import CODE_COUNT, FIRST_CODE, UNITS_PER_EM, Glyph, create_resource, outline_bounds
from .font_resources import Contour, FontResourceError, GlyphOutline, draw_outline_slot


def _repertoire(first, count, native_text_map):
    if native_text_map:
        if (first, count) != (FIRST_CODE, CODE_COUNT):
            raise FontResourceError('Draw text mapping requires a 32–255 glyph index')
        return {draw_outline_slot(code): bytes([code]).decode('cp437')
                for code in range(32, 224) if code != 127}
    return {code: bytes([code]).decode('cp437')
            for code in range(first, first + count) if code >= 32 and code != 127}


def _source_contours(glyph_set, name):
    from fontTools.pens.basePen import BasePen

    class OutlinePen(BasePen):
        def __init__(self):
            super().__init__(glyph_set)
            self.contours = []
            self.start = None
            self.segments = []

        def _moveTo(self, point):
            self.start, self.segments = point, []

        def _lineTo(self, point):
            self.segments.append((point,))

        def _curveToOne(self, a, b, point):
            self.segments.append((a, b, point))

        def _qCurveToOne(self, control, point):
            start = self._getCurrentPoint()
            # Exactly degree-elevate the quadratic before quantization.
            a = tuple(x + Fraction(2, 3) * (y - x) for x, y in zip(start, control))
            b = tuple(x + Fraction(2, 3) * (y - x) for x, y in zip(point, control))
            self._curveToOne(a, b, point)

        def _closePath(self):
            if self.segments:
                if self.segments[-1][-1] != self.start:
                    self._lineTo(self.start)
                self.contours.append(Contour(self.start, tuple(self.segments)))
            self.start, self.segments = None, []

        def _endPath(self):
            if self.segments:
                raise FontResourceError(f'open source contour in {name}')

    pen = OutlinePen()
    glyph_set[name].draw(pen)
    return tuple(pen.contours)


def _open_font(source):
    from fontTools.ttLib import TTFont, TTLibError

    try:
        font = TTFont(BytesIO(source), recalcTimestamp=False)
    except TTLibError as error:
        raise FontResourceError(f'invalid modern font: {error}') from error
    if ('glyf' not in font and 'CFF ' not in font) or 'fvar' in font or 'CFF2' in font:
        font.close()
        raise FontResourceError('expected static TrueType or OpenType CFF outlines')
    return font


def import_outline(source, family, *, face_id=2, native_text_map=False):
    """Build an FF1 candidate and report coverage and pre-serialization quantization."""
    glyphs = []
    missing = []
    represented = []
    coordinate_error = advance_error = 0
    with _open_font(source) as font:
        cmap = font.getBestCmap() or {}
        glyph_set = font.getGlyphSet()
        scale = Fraction(UNITS_PER_EM, font['head'].unitsPerEm)
        repertoire = _repertoire(FIRST_CODE, CODE_COUNT, native_text_map)
        for code in range(FIRST_CODE, FIRST_CODE + CODE_COUNT):
            char = repertoire.get(code)
            name = cmap.get(ord(char)) if char else None
            if name is None or name == '.notdef':
                if char is not None:
                    missing.append(ord(char))
                glyphs.append(Glyph(0, GlyphOutline((0, 0, 0, 0), (), b'')))
                continue
            represented.append(ord(char))

            def quantize(point):
                nonlocal coordinate_error
                scaled = point[0] * scale, -point[1] * scale
                rounded = tuple(round(value) for value in scaled)
                if any(not -32768 <= value <= 32767 for value in rounded):
                    raise FontResourceError(f'converted coordinate outside signed FF1 word for byte {code}')
                coordinate_error = max(coordinate_error, *(abs(a - b) for a, b in zip(rounded, scaled)))
                return rounded

            contours = tuple(Contour(quantize(c.start),
                                     tuple(tuple(quantize(p) for p in s) for s in c.segments))
                             for c in _source_contours(glyph_set, name))
            nominal = glyph_set[name].width * scale
            advance = round(nominal)
            if not 0 <= advance <= 65535:
                raise FontResourceError(f'converted advance outside unsigned FF1 word for byte {code}')
            advance_error = max(advance_error, abs(nominal - advance))
            glyphs.append(Glyph(advance, GlyphOutline(outline_bounds(contours), contours, b'')))
        report = {
            'source_format': 'TrueType' if 'glyf' in font else 'CFF',
            'source_units_per_em': font['head'].unitsPerEm,
            'source_metrics': {'ascent': font['hhea'].ascent, 'descent': font['hhea'].descent,
                               'line_gap': font['hhea'].lineGap},
            'source_unicode_mappings': len(cmap),
            'considered_codepoints': [ord(char) for char in repertoire.values()],
            'represented_codepoints': represented,
            'missing_codepoints': missing,
            'unrepresented_source_codepoints': len(cmap.keys() - set(represented)),
            'substitutions': [],
            'map': ('Draw base-outline slots for CP437 bytes 32–223, excluding DEL'
                    if native_text_map else 'direct slot CP437, bytes 32–255, excluding DEL'),
            'max_coordinate_error_em1000': float(coordinate_error),
            'max_advance_error_em1000': float(advance_error),
            'source_feature_tables_outside_interchange': sorted(set(font.keys()) & {
                'BASE', 'CBDT', 'CBLC', 'COLR', 'CPAL', 'EBDT', 'EBLC', 'GDEF', 'GPOS', 'GSUB',
                'JSTF', 'MATH', 'SVG ', 'cvt ', 'fpgm', 'kern', 'morx', 'prep', 'sbix',
            }),
            'limits': ['outline and nominal advances only', 'no hinting or layout conversion',
                       'source font-wide metrics and names are outside the FF1 interchange',
                       'missing slots have zero advance and no outline'],
            'native_acceptance': 'unverified',
        }
    return create_resource(family, glyphs, face_id=face_id), report


def export_cff(resource, *, native_text_map=False):
    """Export the base outlines to CFF, with bounds-derived vertical metrics."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.t2CharStringPen import T2CharStringPen

    units = resource.units_per_em
    if not 16 <= units <= 16384:
        raise FontResourceError('units per em cannot be represented in OpenType')
    family = resource.family
    postscript = (re.sub(r'[^A-Za-z0-9-]', '', family) or 'DeskMateOutline') + '-Regular'
    cmap = {ord(char): f'c{code:02X}' for code, char in
            _repertoire(resource.first_code, len(resource.glyphs), native_text_map).items()}
    charstrings = {'.notdef': T2CharStringPen(0, None).getCharString()}
    metrics = {'.notdef': (0, 0)}
    ascent = descent = 0
    for code, glyph in enumerate(resource.glyphs, resource.first_code):
        name = f'c{code:02X}'
        pen = T2CharStringPen(glyph.advance, None)
        bounds_pen = BoundsPen(None)
        for target in (pen, bounds_pen):
            for contour in glyph.outline.contours:
                if not contour.segments:
                    continue
                x, y = contour.start
                target.moveTo((x, -y))
                for segment in contour.segments:
                    points = tuple((x, -y) for x, y in segment)
                    if len(points) == 1:
                        target.lineTo(points[0])
                    else:
                        target.curveTo(*points)
                target.closePath()
        bounds = bounds_pen.bounds
        start = math.floor(bounds[0]) if bounds else 0
        if bounds:
            ascent = max(ascent, math.ceil(bounds[3]))
            descent = min(descent, math.floor(bounds[1]))
        if not -32768 <= start <= 32767 or not -32768 <= descent <= ascent <= 32767:
            raise FontResourceError('FF1 coordinates exceed OpenType horizontal metric range')
        metrics[name] = (glyph.advance, start)
        charstrings[name] = pen.getCharString()
    builder = FontBuilder(units, isTTF=False)
    builder.setupGlyphOrder(list(charstrings))
    builder.setupCharacterMap(cmap)
    builder.setupCFF(postscript, {'FullName': family + ' Regular', 'FamilyName': family,
                                  'Weight': 'Regular'}, charstrings, {})
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=ascent, descent=descent)
    builder.setupNameTable({'familyName': family, 'styleName': 'Regular', 'uniqueFontIdentifier': postscript,
                            'fullName': family + ' Regular', 'psName': postscript, 'version': 'Version 1.0'})
    builder.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0,
                     usWinAscent=ascent, usWinDescent=-descent)
    builder.setupPost()
    builder.font.recalcTimestamp = False
    builder.font['head'].created = builder.font['head'].modified = 2082844800
    output = BytesIO()
    builder.save(output)
    return output.getvalue()
