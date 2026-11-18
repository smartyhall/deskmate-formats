"""Exercise the complete native Worksheet corpus through preservation export."""
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.preservation import bundle
from deskmate_formats.preservation.model import PreservationError
from deskmate_formats.preservation.render import csv_text


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/application-generated/worksheet'


def csv_rows(data, *, detail=False):
    stream = StringIO(data.decode('utf-8'), newline='')
    return list(csv.DictReader(stream) if detail else csv.reader(stream))


class WorksheetPreservationTest(unittest.TestCase):
    def prepared(self, name):
        return bundle.prepare(FIXTURES / f'{name}.wks')

    def test_all_44_native_files_preserve_bytes_and_verify(self):
        paths = sorted(FIXTURES.glob('*.wks'))
        self.assertEqual(len(paths), 44)
        with TemporaryDirectory() as directory:
            for source in paths:
                with self.subTest(source=source.name):
                    original = source.read_bytes()
                    output = Path(directory) / source.stem
                    result = bundle.export(source, output)
                    self.assertEqual(bundle.verify(output), result)
                    self.assertEqual(result['source']['sha256'], sha256(original).hexdigest())
                    self.assertEqual(result['source']['filename'], source.name)
                    self.assertEqual((output / 'original.wks').read_bytes(), original)
                    self.assertEqual(source.read_bytes(), original)

    def test_stale_cache_and_formula_errors(self):
        stale = self.prepared('w06')
        self.assertEqual(csv_rows(stale.files['values.csv'])[0], ['2.0', '9.0', '5.0'])
        cells = csv_rows(stale.files['cells.csv'], detail=True)
        self.assertEqual((cells[-1]['formula_source'], cells[-1]['stored_numeric_value']),
                         ('R1C1+R1C2', '5.0'))
        self.assertIn(b'R1C1+R1C2', stale.files['preview.html'])
        self.assertIn(b'may be stale', stale.files['preview.html'])
        for name, last_column, cache, status in (('werr', 3, '0.0', '0x0192'),
                                                ('wref', 2, '11.0', '0x00B2')):
            with self.subTest(name=name):
                result = self.prepared(name)
                self.assertEqual(csv_rows(result.files['values.csv'])[0][last_column - 1], '')
                detail = next(row for row in csv_rows(result.files['cells.csv'], detail=True)
                              if row['category'] == 'formula')
                self.assertEqual(detail['stored_numeric_value'], cache)
                self.assertEqual(detail['error_flag'], 'True')
                self.assertEqual(detail['status_hex'], status)
                self.assertIn(b'Stored error', result.files['preview.html'])
        pending = self.prepared('w05')
        self.assertEqual(csv_rows(pending.files['values.csv'])[0][-1], '')
        self.assertIn(b'No usable stored result', pending.files['preview.html'])

    def test_sparse_grid_multiline_and_saved_input(self):
        sparse = self.prepared('wsparse')
        values = csv_rows(sparse.files['values.csv'])
        self.assertEqual(len(values), 99)
        self.assertTrue(all(len(row) == 99 for row in values))
        self.assertEqual(values[98][98], 'FAR99')
        self.assertIn(b'<th scope="row">R99</th>', sparse.files['preview.html'])
        multi = self.prepared('w08m')
        self.assertIn(b'rowspan="2" colspan="2">FIRST\nSECOND', multi.files['preview.html'])
        self.assertEqual(csv_rows(multi.files['values.csv'])[0][0], 'FIRST\nSECOND')
        self.assertIn(b'<col style="width:18ch">', self.prepared('w11').files['preview.html'])
        mixed = self.prepared('wmix')
        self.assertEqual(csv_rows(mixed.files['values.csv'])[1][0], '4.5')
        self.assertIn(b'RATE7', mixed.files['preview.html'])
        self.assertEqual(csv_rows(self.prepared('w04').files['values.csv']), [['-7.0']])

    def test_text_safety_and_escaping_leave_source_text_in_json(self):
        for value in ('=1', ' +1', '-CMD', '@SUM(A1)', '\twords', '\n=1', '\u200b=1', '＝1'):
            self.assertEqual(csv_text(value), "'" + value)
        self.assertEqual(csv_text(-7.0), -7.0)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'renamed.bin'
            path.write_bytes((FIXTURES / 'w01.wks').read_bytes().replace(b'ALPHA7', b'=1<&",'))
            result = bundle.prepare(path)
            self.assertEqual(result.manifest['application'], 'worksheet')
            self.assertEqual(csv_rows(result.files['values.csv']), [['\'=1<&",']])
            self.assertIn(b'=1&lt;&amp;&quot;,', result.files['preview.html'])
            self.assertEqual(json.loads(result.files['content.json'])['cells'][0]['text'], '=1<&",')

    def test_bundle_determinism_collision_and_tamper_detection(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'one'
            another = Path(directory) / 'two'
            source = FIXTURES / 'wmix.wks'
            bundle.export(source, output)
            bundle.export(source, another)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()},
                             {p.name: p.read_bytes() for p in another.iterdir()})
            with self.assertRaises(FileExistsError):
                bundle.export(source, output)
            artifact = output / 'values.csv'
            artifact.write_bytes(b'?' * artifact.stat().st_size)
            with self.assertRaises(PreservationError) as raised:
                bundle.verify(output)
            self.assertEqual(raised.exception.code, 'hash_mismatch')
            manifest = another / 'manifest.json'
            value = json.loads(manifest.read_text(encoding='utf-8'))
            value['artifacts'][0]['path'] = '../elsewhere.csv'
            manifest.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(PreservationError) as raised:
                bundle.verify(another)
            self.assertEqual(raised.exception.code, 'invalid_manifest')
