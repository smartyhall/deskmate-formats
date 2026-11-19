"""Validate byte-local drawing edits and browser/Python FIG conformance."""
from base64 import b64encode
import json
from pathlib import Path
from shutil import which
import subprocess
import unittest

from deskmate_formats import draw, draw_writer, graphics


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/application-generated/draw'
CODEC = ROOT / 'examples/draw-workbench/fig.js'


def read(name):
    return (FIXTURES / (name + '.fig')).read_bytes()


class WriterTest(unittest.TestCase):
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
