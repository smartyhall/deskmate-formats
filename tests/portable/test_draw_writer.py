"""Validate byte-local drawing edits and browser/Python FIG conformance."""
from base64 import b64encode
import json
from pathlib import Path
from shutil import which
from struct import pack, pack_into
import subprocess
import unittest
from xml.etree import ElementTree

from deskmate_formats import draw, draw_writer, font_resources, graphics


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/application-generated/draw'
CODEC = ROOT / 'examples/draw-workbench/fig.js'


def read(name):
    return (FIXTURES / (name + '.fig')).read_bytes()


class WorkbenchBundleTests(unittest.TestCase):
    def test_standalone_bundle_embeds_current_fig_reader(self):
        workbench = CODEC.parent
        source = CODEC.read_text(encoding='utf-8')
        standalone = (workbench / 'workbench.html').read_text(encoding='utf-8')
        self.assertIn('<script>' + source + '</script>', standalone)


class WriterTest(unittest.TestCase):
    def test_native_style_word_is_retained_without_qualifying_an_edit(self):
        raw = read('cobb-style-flag4-tool-generated')
        original = read('d23')
        self.assertEqual(raw, original[:104] + bytes((4, 0)) + original[106:])
        drawing = draw.parse_bytes(raw)
        item, = drawing.form.draw_order()
        font = graphics.external_font_run(item)
        self.assertEqual((font.name, font.text_bytes, font.style_word), ('Cobb', b'VECTOR 42', 4))
        preview = graphics.preview_svg(drawing.form, drawing.palette)
        self.assertEqual([event.reason for event in preview.omissions], ['unsupported_external_font_style_word'])
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'resolved top-level'):
            draw_writer.permute_outline_label(raw, drawing.form.entries[0].tag, b'42 VECTOR')
        malformed = raw[:104] + bytes((5, 0)) + raw[106:]
        other, = draw.parse_bytes(malformed).form.draw_order()
        self.assertIsNone(graphics.external_font_run(other))

    def test_construct_single_line_from_profile(self):
        expected = read('d01')
        item, = draw.parse_bytes(expected).form.draw_order()
        coords = tuple(int(value * 65536) for value in item.bounds)
        self.assertEqual(draw_writer.new_drawing('L', coords, color=item.raw[18]), expected)

    def test_native_saves_of_browser_created_documents(self):
        for kind in ('line', 'rectangle', 'group'):
            name = f'browser-new-{kind}'
            before = draw.parse_bytes(read(name))
            after = draw.parse_bytes(read(name + ('-native-moved' if kind == 'group' else '-native')))
            source, native = tuple(before.form.draw_order()), tuple(after.form.draw_order())
            self.assertEqual(before.palette, after.palette)
            dx, dy = (300, -11) if kind == 'group' else (0, 0)
            for a, b in zip(source, native, strict=True):
                x0, y0, x1, y1 = a.bounds
                self.assertEqual((b.kind, b.bounds, b.raw[18:]),
                                 (a.kind, (x0 + dx, y0 + dy, x1 + dx, y1 + dy), a.raw[18:]))
            if kind == 'group':
                self.assertEqual(len(before.form.entries), 1)
                self.assertEqual(len(before.form.elements), 5)
                self.assertEqual(len(after.form.entries), 4)

    def test_exact_copy_and_localized_edits(self):
        bad = read('arc-extent-native-resaved')
        self.assertEqual(draw_writer.exact_copy(memoryview(bad), recover_arc_length=True), bad)
        for path in sorted(FIXTURES.glob('*.fig')):
            if path.stem != 'arc-extent-native-resaved':
                with self.subTest(path=path.name):
                    original = path.read_bytes()
                    self.assertEqual(draw_writer.exact_copy(bytearray(original)), original)
        original = read('d01')
        edited = draw_writer.recolor_line(draw_writer.move_line(original, 1, 425 * 65536 + 32768,
                                                               390 * 65536 + 16384), 1, 10)
        element, = draw.parse_bytes(edited).form.draw_order()
        self.assertEqual(element.bounds, (1225.5, 1375.25, 1625.5, 1375.25))
        self.assertEqual(element.raw[18:], b'\x0a\0')
        self.assertEqual(edited[:52], original[:52])
        self.assertEqual(edited[69:], original[69:])

    def test_resize_preserves_header_styles_and_other_records(self):
        original = read('d17')
        drawing = draw.parse_bytes(original)
        element = next(item for item in drawing.form.elements if item.kind == 'R')
        tag, = [entry.tag for entry in drawing.form.entries if entry.offset == element.offset]
        resized = draw_writer.resize_rectangle(original, tag, 1200 * 65536, 900 * 65536)
        current = draw.parse_bytes(resized)
        self.assertEqual(current.form.entries, drawing.form.entries)
        self.assertEqual(current.palette, drawing.palette)
        for before, after in zip(drawing.form.elements, current.form.elements):
            if before.kind != 'R':
                self.assertEqual(before, after)
            else:
                a, b, _, _ = before.bounds
                self.assertEqual(after.bounds, (a, b, a + 1200, b + 900))
                self.assertEqual(before.raw[18:], after.raw[18:])

    def test_edit_guards(self):
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'top-level L'):
            draw_writer.move_line(read('d19'), 1, 0, 0)
        with self.assertRaisesRegex(graphics.GraphicsFormatError, '16.16'):
            draw_writer.move_line(read('d01'), 1, 2 ** 31, 0)
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'positive dimensions'):
            draw_writer.resize_rectangle(read('d04'), 1, 0, 15)
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'no qualified empty-file'):
            draw_writer.delete(read('d04'), 1)
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'packed flat'):
            draw_writer.add_line(read('d19'), (0, 0, 10, 10))

    def test_append_delete_and_reorder_preserve_surviving_records(self):
        source = read('d04')
        before, = draw.parse_bytes(source).form.draw_order()
        ellipse = draw_writer.add_ellipse(source, (100 * 65536, 120 * 65536, 1300 * 65536, 1550 * 65536),
                                          color=10, fill=4)
        form = draw.parse_bytes(ellipse).form
        rectangle, new = form.draw_order()
        self.assertEqual(rectangle.raw, before.raw)
        self.assertEqual((new.kind, new.raw[18:24]), ('E', bytes((10, 0, 0, 0, 4, 0))))
        reordered = draw.parse_bytes(draw_writer.reorder(ellipse, [2, 1])).form
        self.assertEqual(reordered.elements, form.elements)
        self.assertEqual([record.raw for record in reordered.draw_order()], [new.raw, rectangle.raw])
        remaining, = draw.parse_bytes(draw_writer.delete(ellipse, 1)).form.draw_order()
        self.assertEqual(remaining.raw, new.raw)
        line = draw_writer.add_line(source, (0, 0, -65536, 65536), color=3)
        path = draw_writer.add_polyline(line, [(0, 0), (0, 10), (20, 0)], color=7, closed=True, fill=4)
        _rect, line_record, polygon = draw.parse_bytes(path).form.draw_order()
        self.assertEqual(line_record.bounds, (0, 0, -1, 1))
        self.assertEqual(polygon.points, ((0, 0), (0, 10), (20, 0)))
        self.assertEqual(polygon.raw[32:34], b'\xff\xff')

    def test_group_and_ungroup_preserve_leaves(self):
        source = read('writer-add-ellipse-browser-independent')
        grouped = draw_writer.group_all(source)
        self.assertEqual(grouped, read('writer-group-tool-generated'))
        group = draw.parse_bytes(grouped).form
        self.assertEqual([element.kind for element in group.elements], ['OO', 'E', 'R'])
        root = group.elements[0]
        self.assertEqual(root.bounds, (600, 985, 3501, 2721))
        self.assertEqual(root.children, (54, 30))
        ungrouped = draw_writer.ungroup_all(grouped)
        self.assertEqual(ungrouped, read('writer-ungroup-tool-generated'))
        for data in (ungrouped, read('writer-break-object-native'), read('writer-make-object-native')):
            leaves = draw.parse_bytes(data).form.draw_order()
            self.assertEqual([e.raw for e in leaves], [e.raw for e in group.draw_order()])

    def test_palette_and_outline_label_edits_preserve_other_bytes(self):
        source = read('d07c')
        doc = draw.parse_bytes(source)
        result = draw_writer.replace_palette_color(source, 10, (192, 64, 192))
        changed = draw.parse_bytes(result)
        self.assertEqual(changed.form, doc.form)
        self.assertEqual(changed.palette[10], (10, 192, 64, 192))
        source = read('outline-fonts-native')
        amended = draw_writer.permute_outline_label(source, 1, b'DIXON 42')
        self.assertEqual([e.text_bytes for e in draw.parse_bytes(amended).form.draw_order()],
                         [b'DIXON 42', b'MARIN 24'])
        with self.assertRaisesRegex(graphics.GraphicsFormatError, 'permutation'):
            draw_writer.permute_outline_label(source, 1, b'DIXON 99')


@unittest.skipUnless(which('node') and CODEC.is_file(), 'Node.js and the Git-only Workbench source are required')
class BrowserCodecTest(unittest.TestCase):
    def browser(self, script, cases):
        response = subprocess.run(
            ['node', '-e', script, str(CODEC)],
            input=json.dumps({name: b64encode(data).decode() for name, data in cases.items()}),
            capture_output=True, text=True, check=True, timeout=45,
        )
        return json.loads(response.stdout)

    def test_native_style_word_matches_python_read_only_behavior(self):
        result = self.browser(
            '''
            const fs = require('node:fs');
            const codec = require(process.argv[1]);
            const input = JSON.parse(fs.readFileSync(0, 'utf8'));
            const model = codec.read(Buffer.from(input.flag, 'base64'));
            const entry = model.entries[0], part = model.elements.get(entry.offset);
            console.log(JSON.stringify({
              family: part.fontName, style: part.fontStyleWord,
              editable: Boolean(codec.editableOutline(part)),
              permutable: Boolean(codec.canPermute(model, entry.tag)),
              unchanged: Buffer.from(model.copy()).toString('base64') === input.flag,
            }));
            ''',
            {'flag': read('cobb-style-flag4-tool-generated')},
        )
        self.assertEqual(result, {'family': 'Cobb', 'style': 4, 'editable': False,
                                  'permutable': False, 'unchanged': True})

    def test_outline_authoring_parity(self):
        from deskmate_formats.ff1 import serialize_resource
        from deskmate_formats.ff1_geometric import geometric_face
        from deskmate_formats.font_resources import OutlineFace, parse_glyph_index

        data = serialize_resource(geometric_face('Dixon'))
        face = OutlineFace('Dixon', '', parse_glyph_index(data), data)
        fixture = draw_writer.new_outline_drawing(face, 'H Oi', (450, 820), point_size=36)
        fixture = draw_writer.add_outline_text(fixture, face, 'AV 01', (-80, 1600),
                                                point_size=14, width_percent=125)
        tag = draw.parse_bytes(fixture).form.entries[0].tag
        fixture = draw_writer.replace_outline_text(fixture, tag, face, 'I O H E L',
                                                    (475, 840), point_size=48, width_percent=75)
        output = self.browser(
            '''
            const fs = require('node:fs');
            const codec = require(process.argv[1]);
            const source = JSON.parse(fs.readFileSync(0, 'utf8'));
            const face = codec.readOutlineFace(Buffer.from(source.font, 'base64'));
            let model = codec.addOutlineText(codec.blank(), face, 'H Oi', [450, 820], 36, 100);
            model = codec.addOutlineText(model, face, 'AV 01', [-80, 1600], 14, 125);
            model = codec.replaceOutlineText(model, model.entries[0].tag, face, 'I O H E L',
              [475, 840], 48, 75);
            console.log(JSON.stringify(Buffer.from(model.copy()).toString('hex')));
            ''', {'font': data},
        )
        self.assertEqual(bytes.fromhex(output), fixture)

    def test_structural_model_and_raw_copy_parity(self):
        cases = {path.stem: path.read_bytes() for path in sorted(FIXTURES.glob('*.fig'))}
        cases['truncated'] = cases['d04'][:-1]
        bad_directory = bytearray(cases['d01'])
        bad_directory[46:48] = b'\x01\0'
        cases['directory'] = bytes(bad_directory)
        values = self.browser(
            '''
            const fs = require('node:fs');
            const codec = require(process.argv[1]);
            const values = JSON.parse(fs.readFileSync(0, 'utf8'));
            const result = {};
            const hex = bytes => Buffer.from(bytes).toString('hex');
            for (const [name, encoded] of Object.entries(values)) {
                const data = Buffer.from(encoded, 'base64');
                try {
                    const model = codec.read(data);
                    result[name] = {
                        copy: Buffer.from(model.copy()).equals(data),
                        entries: model.entries.map(e => [e.offset, e.tag]),
                        palette: Array.from(model.palette, ([i, rgb]) => [i, ...rgb]),
                        records: Array.from(model.elements, ([offset, e]) =>
                            [offset, e.kind, e.modifier, e.coords, e.children, e.points, hex(e.raw),
                             e.fontName, e.text === null ? null : hex(e.text)]),
                        order: Array.from(codec.leaves(model), e => e.offset),
                        arcs: Array.from(codec.leaves(model)).filter(e => e.kind === 'UA').map(codec.arcQuadratic),
                        strokes: hex(model.strokes),
                    };
                } catch (error) {
                    result[name] = null;
                }
            }
            process.stdout.write(JSON.stringify(result));
            ''',
            cases,
        )
        for name, data in cases.items():
            with self.subTest(name=name):
                try:
                    drawing = draw.parse_bytes(data)
                except graphics.GraphicsFormatError:
                    self.assertIsNone(values[name])
                    continue
                model = drawing.form
                report = {'copy': True, 'entries': [(e.offset, e.tag) for e in model.entries],
                          'palette': drawing.palette,
                          'records': [(e.offset, e.kind, e.modifier, e.coordinates, e.children,
                                       e.points, e.raw.hex(), e.font_name,
                                       e.text_bytes.hex() if e.text_bytes is not None else None) for e in model.elements],
                          'order': [e.offset for e in model.draw_order()],
                          'arcs': [graphics.arc_quadratic(e) for e in model.draw_order() if e.kind == 'UA'],
                          'strokes': model.strokes.hex()}
                self.assertEqual(values[name], json.loads(json.dumps(report)))

    def test_browser_edit_byte_parity(self):
        values = self.browser(
            '''
            const fs = require('node:fs');
            const codec = require(process.argv[1]);
            const values = JSON.parse(fs.readFileSync(0, 'utf8'));
            const read = key => codec.read(Buffer.from(values[key], 'base64'));
            const line = codec.edit(read('line'), 1, {dx: 425.5 * 65536, dy: 390.25 * 65536, color: 10});
            const rect = codec.edit(read('rect'), 1, {width: 1855.5 * 65536, height: 1020.25 * 65536});
            process.stdout.write(JSON.stringify([line, rect].map(m => Buffer.from(m.copy()).toString('hex'))));
            ''',
            {'line': read('d01'), 'rect': read('d04')},
        )
        self.assertEqual(values, [
            draw_writer.recolor_line(draw_writer.move_line(read('d01'), 1, int(425.5*65536), int(390.25*65536)),
                                     1, 10).hex(),
            draw_writer.resize_rectangle(read('d04'), 1, int(1855.5*65536), int(1020.25*65536)).hex(),
        ])

    def test_local_outline_python_browser_conformance(self):
        commands = pack('<BhhBhhB6h', 0, 0, 0, 1, 0, -620, 2, 550, -420, 480, 0, 0, 0)
        glyph = pack('<H4h2H', 1, 0, -620, 550, 0, len(commands), 0) + commands
        first, count, inner = 32, 64, 116
        offsets = 48 + count * 2
        glyphs = offsets + count * 4
        data = bytearray(inner + glyphs)
        data[:5] = b'\xbd\x7a\0\x01\x01'
        pack_into('<H', data, 10, 1)
        pack_into('<HH', data, 14, first, count)
        pack_into('<H', data, 32, 46)
        data[66:70] = b'Cobb'
        pack_into('<HII', data, inner - 2, 48, 0x0101f31e, glyphs + count * len(glyph))
        pack_into('<HHH', data, inner + 12, 1000, first, count)
        pack_into('<H', data, inner + 46, offsets)
        for i in range(count):
            pack_into('<H', data, inner + 48 + 2 * i, 601 + i)
            pack_into('<I', data, inner + offsets + 4 * i, glyphs + i * len(glyph))
        data.extend(glyph * count)
        data = bytes(data)
        fig = read('d23')
        result = self.browser(
            '''
            const fs = require('node:fs'), codec = require(process.argv[1]);
            const values = JSON.parse(fs.readFileSync(0, 'utf8'));
            const font = codec.readOutlineFace(Buffer.from(values.font, 'base64'));
            const model = codec.read(Buffer.from(values.fig, 'base64'));
            const preview = codec.preview(model, {faces: new Map([['cobb', font]])});
            process.stdout.write(JSON.stringify(preview));
            ''',
            {'font': data, 'fig': fig},
        )
        drawing = draw.parse_bytes(fig)
        face = font_resources.OutlineFace('Cobb', '', font_resources.parse_glyph_index(data), data)
        preview = graphics.preview_svg(drawing.form, drawing.palette, outline_faces={'cobb': face})
        self.assertEqual(result['resolved'], 1)
        self.assertEqual(result['omissions'], [])
        self.assertEqual(preview.omissions, ())
        js = ElementTree.fromstring('<svg>' + result['shapes'] + '</svg>')
        py = ElementTree.fromstring(preview.svg)
        for a, b in zip(js.findall('path'), py.findall('{*}path'), strict=True):
            self.assertEqual(a.get('fill'), b.get('fill'))
            tokens = lambda d: [token if token in 'MLCZ' else float(token) for token in d.split()]
            self.assertEqual(tokens(a.get('d')), tokens(b.get('d')))

    def test_browser_structural_edits_match_python_bytes(self):
        actual = self.browser(
            '''
            const fs = require('node:fs'), codec = require(process.argv[1]);
            const values = JSON.parse(fs.readFileSync(0, 'utf8'));
            const u = 65536, raw = m => Buffer.from(m.copy()).toString('hex');
            const first = codec.add(codec.blank(), 'L', [100, 201, 403, 500].map(v => v * u));
            const rectangle = codec.add(codec.blank(), 'R', [503, 660, 1900, 1325].map(v => v * u), {color: 2, fill: 4});
            const second = codec.add(first, 'E', [503, 660, 1900, 1325].map(v => v * u), {color: 2, fill: 4});
            const third = codec.add(second, 'polyline', [[-25, 6], [12, 18], [14, 0]], {color: 7});
            const fourth = codec.add(third, 'polygon', [[25, 100], [200, 20], [100, 900]], {fill: 10});
            const ordered = codec.reorder(fourth, [4, 2, 3, 1]);
            const grouped = codec.group(ordered);
            const broken = codec.ungroup(grouped);
            const removed = codec.remove(broken, broken.entries[1].tag);
            const recolored = codec.paletteColor(removed, 4, [140, 200, 255]);
            const text = codec.read(Buffer.from(values.text, 'base64'));
            const label = codec.permuteLabel(text, text.entries[0].tag, 'DIXON 42');
            process.stdout.write(JSON.stringify([first, rectangle, second, third, fourth, ordered, grouped, broken,
                                                  removed, recolored, label].map(raw)));
            ''',
            {'text': read('outline-fonts-native')},
        )
        first = draw_writer.new_drawing('L', [v * 65536 for v in (100, 201, 403, 500)])
        rectangle = draw_writer.new_drawing('R', [v * 65536 for v in (503, 660, 1900, 1325)], color=2, fill=4)
        second = draw_writer.add_ellipse(first, [v * 65536 for v in (503, 660, 1900, 1325)], color=2, fill=4)
        third = draw_writer.add_polyline(second, [(-25, 6), (12, 18), (14, 0)], color=7)
        fourth = draw_writer.add_polyline(third, [(25, 100), (200, 20), (100, 900)], closed=True, fill=10)
        ordered = draw_writer.reorder(fourth, [4, 2, 3, 1])
        grouped = draw_writer.group_all(ordered)
        broken = draw_writer.ungroup_all(grouped)
        removed = draw_writer.delete(broken, draw.parse_bytes(broken).form.entries[1].tag)
        recolored = draw_writer.replace_palette_color(removed, 4, [140, 200, 255])
        text = read('outline-fonts-native')
        label = draw_writer.permute_outline_label(text, draw.parse_bytes(text).form.entries[0].tag, b'DIXON 42')
        self.assertEqual(actual, [blob.hex() for blob in
                                  (first, rectangle, second, third, fourth, ordered, grouped, broken, removed, recolored, label)])
