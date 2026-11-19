"""Generate narrow grouping and native Text picture-writing controls."""
import argparse
from pathlib import Path
from struct import pack

from deskmate_formats import draw, draw_writer, graphics, text
from draw_suite_candidates import arc, encode, group, shape


def picture_candidate(template, fig_template):
    """Replace one known picture envelope in the original synthetic DOC."""
    source = text.parse_bytes(template)
    picture, = source.pictures
    arcs = [
        arc((100, 110, 1200, 740), (0, 630, 1100, 630, 550, 0), 10),
        shape('R', (1250, 190, 1950, 740), 2, 1, 7),
    ]
    contents = encode(fig_template, [group(*arcs)])
    parsed = draw.parse_bytes(contents)
    form_end = parsed.palette_offset - 2
    payload = contents[22:form_end] + picture.payload[-1:]
    graphics.parse_bytes(payload, text_picture=True)
    count = pack('<H', len(payload))
    envelope = b'\x01' + count + pack('<H', 3) + payload + count + b'\x02'
    end = picture.offset + 8 + len(picture.payload)
    output = template[:picture.offset] + envelope + template[end:]
    rebuilt, = text.parse_bytes(output).pictures
    if rebuilt.column != 3 or rebuilt.payload != payload:
        raise ValueError('native picture envelope did not round-trip')
    return output


def generate(fixtures):
    drawing = fixtures / 'draw'
    base = (drawing / 'writer-add-ellipse-browser-independent.fig').read_bytes()
    grouped = draw_writer.group_all(base)
    word_source = (drawing / 'outline-fonts-native.fig').read_bytes()
    form = draw.parse_bytes(word_source).form
    by_offset = {element.offset: element for element in form.elements}
    text_tag, = (entry.tag for entry in form.entries if by_offset[entry.offset].text_bytes == b'DIXON 24')
    return {
        'GROUPNEW.FIG': grouped,
        'UNGROUP.FIG': draw_writer.ungroup_all(grouped),
        'TXNEW.DOC': picture_candidate((fixtures / 'text/arc-transfer-native.doc').read_bytes(),
                                       draw.parse_file(drawing / 'd01.fig')),
        'PALNEW.FIG': draw_writer.replace_palette_color((drawing / 'd07c.fig').read_bytes(), 10, (192, 64, 192)),
        'TEXTNEW.FIG': draw_writer.permute_outline_label(word_source, text_tag, b'DIXON 42'),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    for name, data in generate(args.fixtures).items():
        with (args.destination / name).open('xb') as output:
            output.write(data)
