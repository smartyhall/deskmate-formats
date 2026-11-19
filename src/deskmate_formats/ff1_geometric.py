"""Independently drawn geometric controls for FF1 reader and renderer trials."""
from .ff1 import CODE_COUNT, FIRST_CODE, Glyph, create_resource, outline_bounds, polygon
from .font_resources import Contour, GlyphOutline


def rectangle(left, top, right, bottom, *, counter=False):
    points = ((left, top), (right, top), (right, bottom), (left, bottom))
    return polygon(*(points[::-1] if counter else points))


def oval(x, y, rx, ry, *, counter=False):
    dx, dy = round(rx * 0.5523), round(ry * 0.5523)
    start = (x + rx, y)
    segments = (
        ((x + rx, y + dy), (x + dx, y + ry), (x, y + ry)),
        ((x - dx, y + ry), (x - rx, y + dy), (x - rx, y)),
        ((x - rx, y - dy), (x - dx, y - ry), (x, y - ry)),
        ((x + dx, y - ry), (x + rx, y - dy), start),
    )
    if counter:
        starts = (start, *(segment[-1] for segment in segments[:-1]))
        segments = tuple((b, a, previous) for (a, b, _), previous in zip(segments, starts))[::-1]
    return Contour(start, segments)


def geometric_face(family='Lab Grid', *, face_id=50, family_id=2, optional_metrics=True):
    """Draw distinctive shared test glyphs; other slots have no ink."""
    shapes = {
        'I': (rectangle(205, -700, 395, 0),),
        'H': (polygon((25, 0), (25, -700), (130, -700), (130, -420), (450, -420),
                      (450, -700), (555, -700), (555, 0), (450, 0), (450, -315),
                      (130, -315), (130, 0)),),
        'E': (polygon((65, 0), (65, -700), (540, -700), (540, -585), (180, -585),
                      (180, -407), (473, -407), (473, -300), (180, -300), (180, -115),
                      (540, -115), (540, 0)),),
        'L': (polygon((65, 0), (65, -700), (180, -700), (180, -135), (540, -135), (540, 0)),),
        'O': (oval(300, -350, 270, 355), oval(300, -350, 143, 215, counter=True)),
        'A': (polygon((5, 0), (225, -700), (370, -700), (595, 0), (460, 0),
                      (408, -180), (190, -180), (138, 0)),
              polygon((230, -299), (369, -299), (300, -546))),
        'V': (polygon((10, -700), (158, -700), (300, -196), (440, -700), (585, -700),
                      (367, 0), (233, 0)),),
        'g': (oval(260, -275, 230, 245), oval(260, -275, 125, 115, counter=True),
              rectangle(510, -520, 580, 175)),
        'i': (rectangle(250, -504, 350, 0), rectangle(250, -695, 350, -590)),
        'b': (oval(350, -215, 210, 220), oval(350, -215, 90, 110, counter=True),
              rectangle(25, -740, 140, 0)),
        '.': (rectangle(245, -110, 355, 0),),
        '!': (rectangle(247, -720, 353, -195), rectangle(247, -108, 353, 0)),
        '0': (rectangle(48, -700, 550, 0), rectangle(165, -580, 433, -120, counter=True)),
        '1': (polygon((133, -510), (133, -655), (300, -740), (420, -740), (420, 0),
                      (292, 0), (292, -610)),),
    }
    shapes['É'] = (*shapes['E'], polygon((220, -745), (305, -860), (450, -860), (300, -745)))
    glyphs = []
    for code in range(FIRST_CODE, FIRST_CODE + CODE_COUNT):
        contours = shapes.get(bytes([code]).decode('cp437'), ())
        advance = 310 if code in (32, 33, 46) else 620
        glyphs.append(Glyph(advance, GlyphOutline(outline_bounds(contours), contours, b'')))
    return create_resource(family, glyphs, face_id=face_id, family_id=family_id,
                           optional_metrics=optional_metrics)
