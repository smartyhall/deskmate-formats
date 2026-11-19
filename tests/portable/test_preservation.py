"""Export native specimens through the Workbench without DeskMate or an emulator."""
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree

from deskmate_formats import interchange, text
from deskmate_formats.calendar import personal as calendar
from deskmate_formats.preservation import bundle, cli, collection, native, pim
from deskmate_formats.preservation.model import PreservationError


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/application-generated'
DEMO = ('worksheet/wmix.wks', 'text/tp06.doc', 'draw/d17.fig', 'filer/g18.fil',
        'calendar/alarm-on-86box-trial-c.cln', 'addressbook/native-two-contact-20261117.adr',
        'sound/tone-native-pcm.snd', 'music/mtempo.sng')
SVG = '{http://www.w3.org/2000/svg}'


def codes(result):
    return {item['code'] for item in result.manifest['diagnostics']}


def run_cli(*args):
    with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()) as stderr:
        result = cli.main([str(arg) for arg in args])
    return result, json.loads(stdout.getvalue() or stderr.getvalue())


def unfold(data):
    assert data.endswith(b'\r\n')
    for line in data.split(b'\r\n'):
        assert len(line) <= 75 and b'\n' not in line and b'\r' not in line
        line.decode('utf-8')
    return data.replace(b'\r\n ', b'').decode('utf-8').splitlines()


class DetectionTest(unittest.TestCase):
    def test_plain_text_requires_explicit_selection(self):
        path = FIXTURES / 'text/t12.doc'
        code, result = run_cli('inspect', path)
        self.assertEqual(code, 2)
        self.assertEqual(result['error'], 'unsupported_signature')
        self.assertIn('--application text', result['message'])
        code, result = run_cli('inspect', path, '--application', 'text')
        self.assertEqual(code, 0)
        self.assertEqual(result['profile'], 'text-3.05-headerless-dos-stream')
        self.assertIn('planned_artifacts', result)
        self.assertEqual(bundle.prepare(path, application='text').files['text.txt'], 'KéZ W'.encode())

    def test_invalid_files_are_diagnosed_and_create_no_output(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'candidate.wks'
            output = Path(directory) / 'archive'
            for data, expected in ((b'ELSE', 'unsupported_signature'),
                                   (b'\x14FIG', 'invalid_native_profile'),
                                   (b'\x10FIG', 'unsupported_draw_profile'),
                                   (b'\x03FIL', 'unsupported_dmdb_profile'),
                                   (b'x' * (native.MAX_SOURCE_BYTES + 1), 'input_too_large')):
                with self.subTest(error=expected):
                    source.write_bytes(data)
                    status, result = run_cli('export', source, '--output-dir', output)
                    self.assertEqual((status, result['error']), (2, expected))
                    self.assertFalse(output.exists())
            source.write_bytes(b'A\x13B\x1a')
            status, result = run_cli('inspect', source, '--application', 'text')
            self.assertEqual((status, result['error']), (2, 'invalid_native_profile'))

    def test_shared_fil_signature_uses_structure(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'renamed.bin'
            for family, name in (('filer', 'qrecord-one.fil'), ('calendar', 'alarm-on-86box-trial-c.cln')):
                data = (FIXTURES / family / name).read_bytes()
                self.assertEqual(data[:4], b'\x03FIL')
                path.write_bytes(data)
                self.assertEqual(bundle.prepare(path).manifest['application'], family)


class GraphicsPreservationTest(unittest.TestCase):
    def test_native_text_corpus_formats_and_positions(self):
        paths = sorted((FIXTURES / 'text').glob('*'))
        for path in (path for path in paths if path.suffix in ('.doc', '.txt')):
            with self.subTest(path=path.name):
                result = bundle.prepare(path, application='text')
                document = text.parse_file(path)
                content = json.loads(result.files['content.json'])
                self.assertEqual(result.files['text.txt'].decode(), document.text)
                self.assertEqual([row['payload'] for row in content['pictures']],
                                 [picture.payload.hex() for picture in document.pictures])
                self.assertEqual([row['text_offset'] for row in content['pictures']],
                                 [picture.text_offset for picture in document.pictures])
        for name, markup in [('t07', b'<strong>R8</strong>'),
                             ('t08', b'<p class="center"><strong>R8</strong> </p>'),
                             ('t11', b'AB<u>C</u>')]:
            result = bundle.prepare(FIXTURES / 'text' / (name + '.doc'))
            self.assertIn(markup, result.files['preview.html'])
        result = bundle.prepare(FIXTURES / 'text/tp04.doc')
        page = result.files['preview.html']
        order = [page.index(value) for value in
                 (b'BEFORE LINE', b'picture-001.svg', b'picture-002.svg', b'AFTER LINE')]
        self.assertEqual(order, sorted(order))
        shifted = bundle.prepare(FIXTURES / 'text/tp02.doc')
        self.assertIn(b'margin-inline-start:min(3ch,35%)', shifted.files['preview.html'])
        self.assertIn(b'source column 3', shifted.files['preview.html'])
        picture_first = bundle.prepare(FIXTURES / 'text/tp03.doc')
        self.assertIn(b'<article class="document"><figure', picture_first.files['preview.html'])
        three_shapes = bundle.prepare(FIXTURES / 'text/tp06.doc')
        svg = ElementTree.fromstring(three_shapes.files['assets/picture-001.svg'])
        self.assertEqual({child.tag for child in svg}, {SVG + tag for tag in ('desc', 'line', 'rect', 'ellipse')})

    def test_invalid_or_unsupported_picture_does_not_discard_text_or_payload(self):
        reference = FIXTURES / 'text/tp01.doc'
        picture, = text.parse_file(reference).pictures
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'picture.doc'
            data = bytearray(reference.read_bytes())
            data[picture.payload_offset] = 0
            source.write_bytes(data)
            result = bundle.prepare(source)
            self.assertIn('text_picture_unsupported', codes(result))
            self.assertIn(b'BEFORE LINE\nAFTER LINE', result.files['text.txt'])
            item, = json.loads(result.files['content.json'])['pictures']
            self.assertEqual(item['payload'], bytes(data[picture.payload_offset:picture.end_offset - 3]).hex())
        unsupported = bundle.prepare(FIXTURES / 'text/tp09.doc')
        self.assertIn('graphics_elements_omitted', codes(unsupported))
        item, = json.loads(unsupported.files['content.json'])['pictures']
        self.assertEqual(item['preview']['omissions'][0]['kind_hex'], '5566')

    def test_text_caps_formatting_while_still_rejecting_unbalanced_controls(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'large.doc'
            prefix = text.FORMATTED_HEADER + b'\x13\x12' * (native.MAX_TEXT_CONTROLS // 2 + 1)
            source.write_bytes(prefix + b'<A>&\x1a')
            result = bundle.prepare(source)
            self.assertIn('text_formatting_preview_limit', codes(result))
            self.assertIn(b'&lt;A&gt;&amp;', result.files['preview.html'])
            content = json.loads(result.files['content.json'])
            self.assertEqual(content['control_count'], native.MAX_TEXT_CONTROLS + 2)
            source.write_bytes(prefix + b'\x13A\x1a')
            with self.assertRaises(PreservationError):
                bundle.prepare(source)

    def test_draw_native_palette_and_opaque_elements(self):
        for path in sorted((FIXTURES / 'draw').glob('*.fig')):
            with self.subTest(path=path.name):
                if path.name == 'arc-extent-native-resaved.fig':
                    # The Workbench uses strict intake. The exact native
                    # malformed-length control requires explicit Draw recovery.
                    with self.assertRaisesRegex(PreservationError, 'extended element exceeds its record'):
                        bundle.prepare(path)
                    continue
                result = bundle.prepare(path)
                self.assertIsNotNone(ElementTree.fromstring(result.files['drawing.svg']).get('viewBox'))
        rectangle = bundle.prepare(FIXTURES / 'draw/d07c.fig')
        source = json.loads(rectangle.files['content.json'])
        red, green, blue = next(color[1:] for color in source['palette'] if color[0] == 10)
        self.assertIn(f'stroke="#{red:02x}{green:02x}{blue:02x}"'.encode(), rectangle.files['drawing.svg'])
        self.assertGreater(source['preview']['view_box'][2], 0)
        opaque = bundle.prepare(FIXTURES / 'draw/d23.fig')
        self.assertIn('graphics_elements_omitted', codes(opaque))
        self.assertNotIn(b'<text', opaque.files['drawing.svg'])
        self.assertIn(b'No supported geometry', opaque.files['preview.html'])

    def test_native_arc_in_draw_text_and_both_filer_graphics(self):
        cases = (
            ('draw/arc-transfer-native.fig', ('drawing.svg',)),
            ('text/arc-transfer-native.doc', ('assets/picture-001.svg',)),
            ('filer/arc-transfer-native.fil', ('assets/card.svg', 'assets/report.svg')),
        )
        for name, assets in cases:
            item = bundle.prepare(FIXTURES / name)
            for asset in assets:
                with self.subTest(name=name, asset=asset):
                    shape = ElementTree.fromstring(item.files[asset]).find(SVG + 'path')
                    self.assertIn(' Q ', shape.get('d'))

    def test_filer_native_records_and_card_graphics(self):
        for path in sorted((FIXTURES / 'filer').glob('*.fil')):
            with self.subTest(path=path.name):
                result = bundle.prepare(path)
                self.assertIn(b'FTXT_A', result.files['records.csv'])
                for name, data in result.files.items():
                    if name.endswith('.svg'):
                        self.assertEqual(ElementTree.fromstring(data).tag, SVG + 'svg')
        result = bundle.prepare(FIXTURES / 'filer/qrecord-one.fil')
        self.assertEqual(result.files['records.csv'], b'FTXT_A\r\nF7Q9\r\n')
        content = json.loads(result.files['content.json'])
        self.assertEqual(content['data_columns'], ['FTXT_A'])
        self.assertEqual(content['data_records'][0]['values'], ['F7Q9'])
        g18 = bundle.prepare(FIXTURES / 'filer/g18.fil')
        card = ElementTree.fromstring(g18.files['assets/card.svg'])
        self.assertEqual(len(card.findall(SVG + 'line')), 36)
        self.assertIn(b'Card GRAPHICS', g18.files['preview.html'])

    def test_filer_synthetic_report_and_opaque_data(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.fil'
            g18 = bundle.prepare(FIXTURES / 'filer/g18.fil')
            graphics, = json.loads(g18.files['content.json'])['graphics']
            data = bytearray(g18.files['original.fil'])
            marker = graphics['row_offsets'][0] + 2
            self.assertEqual(data[marker], ord('F'))
            data[marker] = ord('R')
            source.write_bytes(data)
            self.assertIn('assets/report.svg', bundle.prepare(source).files)
            data[marker] = ord('?')
            source.write_bytes(data)
            self.assertIn('filer_graphics_unsupported', codes(bundle.prepare(source)))
            one = (FIXTURES / 'filer/qrecord-one.fil').read_bytes()
            source.write_bytes(one.replace(b'F7Q9', b'F\x82Q9'))
            opaque = bundle.prepare(source)
            self.assertIn('filer_data_field_opaque', codes(opaque))
            self.assertEqual(json.loads(opaque.files['content.json'])['data_records'][0]['fields_hex'],
                             ['46825139'])


class StandardExportTest(unittest.TestCase):
    def test_calendar_standard_floating_time_alarm_and_strict_interchange(self):
        path = FIXTURES / 'calendar/alarm-on-86box-trial-c.cln'
        result = bundle.prepare(path)
        document = json.loads(result.files['interchange-v1.json'])
        event, = interchange.load_document(document)
        self.assertTrue(document['items'][0]['alarm_enabled'])
        self.assertEqual(event.appointment.description, 'LPHa124')
        lines = unfold(result.files['calendar-01.ics'])
        self.assertIn('DTSTART:20261023T090000', lines)
        self.assertIn('DTEND:20261023T100000', lines)
        self.assertIn('X-DESKMATE-ALARM-ENABLED:TRUE', lines)
        self.assertIn('DTSTAMP:19800101T000000Z', lines)
        self.assertEqual(lines.count('BEGIN:VEVENT'), 1)
        self.assertEqual(lines.count('END:VEVENT'), 1)
        self.assertFalse(any('TZID' in line or 'VALARM' in line for line in lines))
        self.assertIn('calendar_control_records_omitted', codes(result))
        content = json.loads(result.files['content.json'])
        self.assertEqual(len(content['internal_records']), 1)
        self.assertEqual(content['appointments'][0]['raw_fields']['Protected'], '71')

    def test_multicalendar_separate_identities_and_interchange_refusal(self):
        path = FIXTURES / 'calendar/native-second-first-event-operator.cln'
        result = bundle.prepare(path)
        self.assertNotIn('interchange-v1.json', result.files)
        self.assertIn('interchange_unsupported_calendars', codes(result))
        first = unfold(result.files['calendar-01.ics'])
        second = unfold(result.files['calendar-02.ics'])
        self.assertIn('X-WR-CALNAME:PERSONAL', first)
        self.assertIn('X-WR-CALNAME:SECOND', second)
        self.assertEqual((first.count('BEGIN:VEVENT'), second.count('BEGIN:VEVENT')), (61, 1))
        uids = [line for line in first + second if line.startswith('UID:')]
        self.assertEqual(len(set(uids)), 62)
        self.assertTrue(all(result.manifest['source']['sha256'] in uid for uid in uids))

    def test_unknown_calendar_values_remain_raw_and_v1_stays_strict(self):
        original = FIXTURES / 'calendar/alarm-on-86box-trial-c.cln'
        native_calendar = calendar.parse_file(original, profile='sdk')
        record, = native_calendar.appointments
        with TemporaryDirectory() as directory:
            path = Path(directory) / original.name
            data = native_calendar.data
            raw = data[record.offset:record.offset + record.length]
            path.write_bytes(data[:record.offset] + raw.replace(b'\x01q\x01', b'\x01?\x01')
                             + data[record.offset + record.length:])
            result = bundle.prepare(path)
            self.assertNotIn('interchange-v1.json', result.files)
            self.assertNotIn('calendar-01.ics', result.files)
            self.assertIn('calendar_ical_record_omitted', codes(result))
            self.assertEqual(json.loads(result.files['content.json'])['appointments'][0]
                             ['raw_fields']['Protected'], '3f')

    def test_vcard_native_contacts_and_opaque_fields(self):
        path = FIXTURES / 'addressbook/native-two-contact-20261117.adr'
        result = bundle.prepare(path)
        content = json.loads(result.files['content.json'])
        self.assertIn('DateOne', content['contacts'][0]['opaque_fields_hex'])
        self.assertEqual(len(interchange.load_document(json.loads(result.files['interchange-v1.json']))), 2)
        lines = unfold(result.files['contacts.vcf'])
        self.assertEqual(lines.count('BEGIN:VCARD'), 2)
        self.assertIn('N:USER A;TEST;;;', lines)
        self.assertIn('TEL;TYPE=work;VALUE=text:555-0100', lines)
        self.assertFalse(any(line.startswith('BDAY:') for line in lines))
        with TemporaryDirectory() as directory:
            mutated = Path(directory) / path.name
            mutated.write_bytes(path.read_bytes().replace(b'Birthday', b'Zirthday'))
            opaque = bundle.prepare(mutated)
            self.assertIn('interchange_unsupported_fields', codes(opaque))
            self.assertIn('addressbook_vcard_opaque_fields_omitted', codes(opaque))
            self.assertNotIn('interchange-v1.json', opaque.files)
            self.assertEqual(opaque.files['contacts.vcf'], result.files['contacts.vcf'])

    def test_text_escaping_and_utf8_folding(self):
        self.assertEqual(pim._escape_text('a,;\\\r\nX', structured=True), r'a\,\;\\\nX')
        logical = 'NOTE:' + 'é' * 49 + '😀'
        self.assertEqual(unfold(pim._fold_lines([logical])), [logical])
        item = pim.Contact('A;B', 'C,D', city='R;M', work_phone='1,2')
        lines = pim._vcard(item)
        self.assertIn(r'N:C\,D;A\;B;;;', lines)
        self.assertIn(r'ADR:;;;R\;M;;;', lines)
        self.assertIn(r'TEL;TYPE=work;VALUE=text:1\,2', lines)


class CollectionTest(unittest.TestCase):
    def test_all_family_export_and_verification(self):
        with TemporaryDirectory() as directory:
            inputs = Path(directory) / 'inputs'
            output = inputs / 'archive'
            inputs.mkdir()
            for fixture in DEMO:
                shutil.copyfile(FIXTURES / fixture, inputs / Path(fixture).name)
            status, result = run_cli('export', inputs, '--output-dir', output)
            self.assertEqual(status, 0)
            self.assertEqual({item['application'] for item in result['entries']}, set(native.APPLICATIONS))
            self.assertEqual(run_cli('verify', output),
                             (0, {'verified': True, 'bundle_count': len(DEMO), 'failed_count': 0}))
            self.assertEqual(run_cli('export', inputs, '--output-dir', output)[1]['error'], 'output_exists')
            for item in result['entries']:
                child = output / item['directory']
                archived = bundle.verify(child)['source']
                original = inputs / item['filename']
                self.assertEqual((child / archived['path']).read_bytes(), original.read_bytes())
                self.assertEqual(sha256(original.read_bytes()).hexdigest(), archived['sha256'])
                self.assertIn(f'{item["directory"]}/preview.html'.encode(), (output / 'index.html').read_bytes())
            target = output / result['entries'][0]['directory'] / bundle.MANIFEST
            target.write_bytes(target.read_bytes() + b' ')
            self.assertEqual(run_cli('verify', output)[1]['error'], 'size_mismatch')

    def test_batch_keeps_earlier_and_later_good_outputs(self):
        with TemporaryDirectory() as directory:
            inputs = Path(directory) / 'inputs'
            inputs.mkdir()
            (inputs / 'unvisited').mkdir()
            data = (FIXTURES / 'worksheet/w01.wks').read_bytes()
            (inputs / 'A worksheet.wks').write_bytes(data)
            (inputs / 'B-wrong.txt').write_bytes(b'invalid')
            (inputs / 'C-worksheet.wks').write_bytes(data)
            output = Path(directory) / 'archive'
            status, result = run_cli('export', inputs, '--output-dir', output)
            self.assertEqual(status, 1)
            self.assertEqual([item['status'] for item in result['entries']], ['exported', 'failed', 'exported'])
            self.assertEqual(collection.verify(output), {'verified': True, 'bundle_count': 2, 'failed_count': 1})
            (output / 'extraneous.txt').write_text('stray', encoding='utf-8')
            self.assertEqual(run_cli('verify', output)[1]['error'], 'unexpected_artifact')

    def test_published_schema_validates_all_bundle_families_and_the_collection(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest('jsonschema is available in the portable CI environment')
        schema = json.loads((ROOT / 'docs/preservation-manifest-v1.schema.json').read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        with TemporaryDirectory() as directory:
            inputs = Path(directory) / 'inputs'
            inputs.mkdir()
            for fixture in DEMO:
                shutil.copyfile(FIXTURES / fixture, inputs / Path(fixture).name)
            (inputs / 'other').write_bytes(b'unrecognized')
            output = Path(directory) / 'archive'
            report = collection.export(inputs, output)
            validator.validate(report)
            for entry in report['entries']:
                if entry['status'] == 'exported':
                    validator.validate(bundle.verify(output / entry['directory']))
