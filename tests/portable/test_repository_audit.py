"""Publication audit tests for application-generated synthetic-data specimens."""
import hashlib
import json
from binascii import crc32
import zlib
import tempfile
import unittest
from pathlib import Path
from struct import pack
from unittest.mock import patch
from zipfile import ZipFile

from tools import audit_repository


class FixtureAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / 'tests/fixtures/application-generated'
        self.base.mkdir(parents=True)

    def manifest(self, items):
        (self.base / 'manifest.json').write_text(
            json.dumps({'fixtures': items}), encoding='utf-8')

    @staticmethod
    def entry(name, data):
        return {'path': name, 'sha256': hashlib.sha256(data).hexdigest(),
                'size': len(data), 'origin': 'DeskMate 3.05 controlled experiment',
                'synthetic_data': True}

    def audit(self):
        with patch.object(audit_repository, 'ROOT', self.root):
            return audit_repository.audit()

    def test_only_the_manifested_information_center_database_is_allowed(self):
        name = audit_repository.SYNTHETIC_DB
        fixture = Path(__file__).resolve().parents[2] / audit_repository.FIXTURE_DIR / name
        data = fixture.read_bytes()
        self.assertEqual(len(data), 6144)
        self.assertIn(b'ATLAS LAB MESSAGE\x01PAT\x01LEE', data)
        target = self.base / name
        target.parent.mkdir()
        target.write_bytes(data)
        self.manifest([self.entry(name, data)])
        self.assertEqual(self.audit()['application_generated_fixtures_checked'], 1)

        different = 'information-center/other.db'
        self.manifest([self.entry(different, data)])
        with self.assertRaisesRegex(ValueError, 'unexpected fixture extension'):
            self.audit()
        self.manifest([])
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_note_storage_exceptions_are_path_and_digest_specific(self):
        for name in ('corkboard/rsx-two-lines/DMCORKBD', 'notebook/rsx-two-loans.db',
                     'collections/rsx-two-items.col'):
            with self.subTest(name=name):
                fixture = Path(__file__).resolve().parents[2] / audit_repository.FIXTURE_DIR / name
                data = fixture.read_bytes()
                target = self.base / name
                target.parent.mkdir(parents=True)
                target.write_bytes(data)
                self.manifest([self.entry(name, data)])
                self.assertEqual(self.audit()['application_generated_fixtures_checked'], 1)
                target.write_bytes(data[:-1] + b'x')
                with self.assertRaisesRegex(ValueError, 'fixture digest or size mismatch'):
                    self.audit()
                self.manifest([self.entry('unreviewed/' + target.name, data)])
                with self.assertRaisesRegex(ValueError, 'unexpected fixture extension'):
                    self.audit()
                target.unlink()

    def test_aol_note_preserves_native_dos_line_endings(self):
        name = 'aol/rsxnote.txt'
        fixture = Path(__file__).resolve().parents[2] / audit_repository.FIXTURE_DIR / name
        data = fixture.read_bytes()
        self.assertEqual(data, b'RSX AOL OFFLINE SAMPLE\r\nSECOND LINE')
        target = self.base / name
        target.parent.mkdir()
        target.write_bytes(data)
        self.manifest([self.entry(name, data)])
        self.assertEqual(self.audit()['application_generated_fixtures_checked'], 1)

        target.write_bytes(data.replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'fixture digest or size mismatch'):
            self.audit()
        self.manifest([self.entry('aol/other.txt', data)])
        with self.assertRaisesRegex(ValueError, 'unexpected fixture extension'):
            self.audit()

    @staticmethod
    def example_site_png():
        def chunk(kind, payload):
            return pack('>I', len(payload)) + kind + payload + pack('>I', crc32(kind + payload))
        header = pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        pixels = zlib.compress(b'\x00\xaa\xbb\xcc')
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', pixels) + chunk(b'IEND', b'')

    def site_image(self, data=None, with_sidecar=True):
        data = data if data is not None else self.example_site_png()
        rel = 'calendar/day-view.png'
        base = self.root / audit_repository.SITE_IMAGE_DIR
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if with_sidecar:
            (path.parent / (path.name + '.license')).write_text(
                'SPDX-FileCopyrightText: 2026 Example contributor\n'
                'SPDX-License-Identifier: LicenseRef-DeskMate-Documentary-Capture\n',
                encoding='utf-8')
        spec = {'schema_version': 1, 'images': [{
            'id': 'ui.calendar.day-view',
            'path': rel,
            'sha256': hashlib.sha256(data).hexdigest(),
            'source_sha256': hashlib.sha256(data).hexdigest(),
            'size': len(data), 'width': 1, 'height': 1,
            'origin': 'documentary-software-ui-capture',
            'source_id': 'capture-test-001',
            'caption': 'Synthetic Calendar day-view test',
            'alt': 'One-pixel test image standing in for a calendar screenshot',
            'rights_note': 'Illustrative synthetic-content UI capture; vendor art not relicensed.',
        }]}
        manifest = self.root / audit_repository.SITE_IMAGE_MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(spec), encoding='utf-8')
        return path, spec

    def test_manifested_ordinary_site_screenshot_passes_publication_audit(self):
        self.manifest([])
        self.site_image()
        self.assertEqual(self.audit()['documentary_site_images_checked'], 1)

    def test_site_screenshot_digest_and_missing_sidecar_are_rejected(self):
        self.manifest([])
        path, _ = self.site_image()
        path.write_bytes(path.read_bytes() + b'garbage')
        with self.assertRaisesRegex(ValueError, 'digest or size mismatch'):
            self.audit()
        path, _ = self.site_image(with_sidecar=False)
        path.with_suffix('.png.license').unlink()
        with self.assertRaisesRegex(ValueError, 'requires accurate REUSE sidecar'):
            self.audit()

    def test_unlisted_or_mislocated_site_screenshot_is_still_forbidden(self):
        self.manifest([])
        path, spec = self.site_image()
        spec['images'] = []
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'unlisted site image'):
            self.audit()
        path.unlink()
        path.with_suffix('.png.license').unlink()
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        stray = self.root / 'unknown.png'
        stray.write_bytes(self.example_site_png())
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_site_png_embedded_text_and_traversal_rejected(self):
        self.manifest([])
        png = self.example_site_png()
        def chunk(kind, payload):
            return pack('>I', len(payload)) + kind + payload + pack('>I', crc32(kind + payload))
        png = png[:-12] + chunk(b'tEXt', b'Comment\x00private metadata') + png[-12:]
        path, spec = self.site_image(data=png)
        with self.assertRaisesRegex(ValueError, 'unsafe site PNG chunk'):
            self.audit()
        spec['images'][0]['path'] = '../outside.png'
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'unsafe site image path'):
            self.audit()

    def historical_site_image(self, license_id='LicenseRef-Third-Party-Historical-Advertising'):
        data = self.example_site_png()
        rel = 'history/offer.png'
        base = self.root / audit_repository.SITE_IMAGE_DIR
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        (path.parent / (path.name + '.license')).write_text(
            'SPDX-FileCopyrightText: Example publisher\n'
            f'SPDX-License-Identifier: {license_id}\n', encoding='utf-8')
        entry = {
            'id': 'history.hx-1988-offer', 'path': rel,
            'sha256': hashlib.sha256(data).hexdigest(), 'source_sha256': '1' * 64,
            'size': len(data), 'width': 1, 'height': 1,
            'origin': 'historical-advertising-excerpt', 'source_id': 'catalog-test-001',
            'publisher': 'Example publisher', 'publication_title': 'Example 1988 catalog',
            'publication_date': '1988', 'page_reference': 'printed p. 9',
            'source_url': 'https://example.org/scan.pdf#page=9',
            'provenance': 'Synthetic test provenance for a catalog crop.',
            'attribution': 'Example publisher, 1988 catalog, printed p. 9.',
            'caption': 'Synthetic historical advertising test',
            'alt': 'One-pixel test image standing in for a catalog excerpt',
            'rights_note': 'Third-party historical advertising; publisher rights retained.',
        }
        spec = {'schema_version': 1, 'images': [entry]}
        manifest = self.root / audit_repository.SITE_IMAGE_MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(spec), encoding='utf-8')
        return path, spec

    def test_historical_advertising_excerpt_passes_publication_audit(self):
        self.manifest([])
        self.historical_site_image()
        self.assertEqual(self.audit()['documentary_site_images_checked'], 1)

    def test_incomplete_historical_advertising_record_is_rejected(self):
        self.manifest([])
        _, spec = self.historical_site_image()
        del spec['images'][0]['publisher']
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'missing historical advertising publisher'):
            self.audit()

    def test_historical_advertising_cannot_reuse_software_capture_classification(self):
        self.manifest([])
        self.historical_site_image(license_id='LicenseRef-DeskMate-Documentary-Capture')
        with self.assertRaisesRegex(ValueError, 'incorrect site image rights classification'):
            self.audit()

    def test_historical_identifier_and_origin_must_agree(self):
        self.manifest([])
        _, spec = self.historical_site_image()
        spec['images'][0]['origin'] = 'documentary-software-ui-capture'
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'historical identifier requires historical origin'):
            self.audit()
        spec['images'][0]['origin'] = 'historical-advertising-excerpt'
        spec['images'][0]['id'] = 'ui.history.offer'
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'historical advertising requires a history'):
            self.audit()

    def test_historical_advertising_source_must_be_https(self):
        self.manifest([])
        _, spec = self.historical_site_image()
        spec['images'][0]['source_url'] = 'http://example.org/scan.pdf'
        (self.root / audit_repository.SITE_IMAGE_MANIFEST).write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'must be an https URL'):
            self.audit()

    def test_generated_fil_database_accepted(self):
        data = b'\x03FIL' + b'\x00' * 24
        path = self.base / 'calendar/E02.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/E02.cln', data)])
        self.assertEqual(self.audit()['application_generated_fixtures_checked'], 1)

    def test_tampering_rejected(self):
        data = b'\x03FIL' + b'\x00' * 24
        path = self.base / 'addressbook/A01.adr'
        path.parent.mkdir()
        path.write_bytes(data + b'!')
        self.manifest([self.entry('addressbook/A01.adr', data)])
        with self.assertRaisesRegex(ValueError, 'digest or size mismatch'):
            self.audit()

    def test_unlisted_binary_rejected(self):
        self.manifest([])
        (self.base / 'unlisted.cln').write_bytes(b'\x03FIL')
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_ff1_exception_requires_the_generated_resource_and_exact_path(self):
        from deskmate_formats.ff1 import serialize_resource
        from deskmate_formats.ff1_geometric import geometric_face

        name = audit_repository.SYNTHETIC_FF1
        path = self.base / name
        path.parent.mkdir()
        data = serialize_resource(geometric_face('Labgrid', face_id=28))
        path.write_bytes(data)
        self.manifest([self.entry(name, data)])
        self.assertEqual(self.audit()['application_generated_fixtures_checked'], 1)
        other = serialize_resource(geometric_face('Different', face_id=28))
        path.write_bytes(other)
        self.manifest([self.entry(name, other)])
        with self.assertRaisesRegex(ValueError, 'independent generator'):
            self.audit()
        self.manifest([self.entry('draw/other.ff1', data)])
        with self.assertRaisesRegex(ValueError, 'unexpected fixture extension'):
            self.audit()

    def test_missing_declared_binary_rejected(self):
        self.manifest([self.entry('calendar/E02.cln', b'data')])
        with self.assertRaisesRegex(ValueError, 'missing declared fixtures'):
            self.audit()

    def test_executable_outside_rejected(self):
        self.manifest([])
        (self.root / 'installer.com').write_bytes(b'MZ')
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_disguised_executable_rejected(self):
        data = b'MZ' + b'\x00' * 16
        path = self.base / 'calendar/fake.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/fake.cln', data)])
        with self.assertRaisesRegex(ValueError, 'executable disguised'):
            self.audit()

    def test_text_specimens_are_manifested_and_git_only(self):
        text = self.base / 'text'
        text.mkdir()
        native, exported = b'\rDOC\x00native\x1a', b'document \x1a'
        (text / 'page.doc').write_bytes(native)
        (text / 'page.txt').write_bytes(exported)
        self.manifest([self.entry('text/page.doc', native), self.entry('text/page.txt', exported)])
        self.assertEqual(self.audit()['application_generated_fixtures_checked'], 2)

        dist = self.root / 'dist'
        dist.mkdir()
        with ZipFile(dist / 'test.whl', 'w') as wheel:
            wheel.writestr('tests/fixtures/application-generated/text/page.txt', exported)
        with self.assertRaisesRegex(ValueError, 'excluded file in archive'):
            self.audit()

    def test_unlisted_text_documents_and_exports_rejected(self):
        self.manifest([])
        (self.root / 'private.doc').write_bytes(b'document')
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()
        (self.root / 'private.doc').unlink()
        text = self.base / 'text'
        text.mkdir()
        (text / 'unlisted.txt').write_bytes(b'document')
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()

    def test_traversal_rejected(self):
        self.manifest([self.entry('../outside.cln', b'data')])
        with self.assertRaisesRegex(ValueError, 'unsafe fixture path'):
            self.audit()

    def test_manifested_binary_with_access_token_rejected(self):
        data = b'\x03FIL\x00' + (b'https://example.invalid/?access_' + b'token=EXAMPLE12345678')
        path = self.base / 'calendar/E03.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/E03.cln', data)])
        with self.assertRaisesRegex(ValueError, 'archive access query'):
            self.audit()

    def test_manifested_binary_with_private_host_path_rejected(self):
        data = b'\x03FIL\x00C:\\Users\\example\\Secrets'
        path = self.base / 'calendar/E04.cln'
        path.parent.mkdir()
        path.write_bytes(data)
        self.manifest([self.entry('calendar/E04.cln', data)])
        with self.assertRaisesRegex(ValueError, 'host Windows user path'):
            self.audit()

    def test_source_distribution_with_omitted_binary_is_auditable(self):
        self.manifest([self.entry('calendar/E02.cln', b'private-test-file')])
        (self.root / 'PKG-INFO').write_text('Metadata-Version: 2.4\n')
        self.assertEqual(self.audit()['status'], 'passed')

    def test_private_observatory_spool_rejected_in_checkout_and_archive(self):
        self.manifest([])
        journal = self.root / 'events.jsonl'
        journal.write_bytes(b'{"summary":"fictional private content"}\n')
        with self.assertRaisesRegex(ValueError, 'private Observatory spool file'):
            self.audit()
        journal.unlink()
        dist = self.root / 'dist'
        dist.mkdir()
        with ZipFile(dist / 'test.whl', 'w') as wheel:
            wheel.writestr('data/writer.lock', b'')
        with self.assertRaisesRegex(ValueError, 'private Observatory spool file in archive'):
            self.audit()

    def test_renamed_source_trace_and_modified_approved_jsonl_rejected(self):
        self.manifest([])
        trace = self.root / 'renamed.ndjson'
        trace.write_text('{"type":"turn.started"}\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'unlisted JSONL trace'):
            self.audit()
        trace.unlink()
        approved = self.root / audit_repository.TELEMETRY_FIXTURE_DIR / 'success.jsonl'
        approved.parent.mkdir()
        approved.write_text('{"type":"turn.started"}\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'synthetic JSONL fixture digest mismatch'):
            self.audit()

    def test_renamed_trace_in_wheel_rejected(self):
        self.manifest([])
        dist = self.root / 'dist'
        dist.mkdir()
        with ZipFile(dist / 'test.whl', 'w') as wheel:
            wheel.writestr('somewhere/codex-trace.jsonl', b'{}\n')
        with self.assertRaisesRegex(ValueError, 'JSONL trace in wheel'):
            self.audit()

    def listening_example(self):
        audit = audit_repository
        base = self.root / audit.LISTENING_DIR
        directory = base / 'baseline-pr118'
        directory.mkdir(parents=True)
        synthetic = 'sound/control.snd'
        score = 'music/control.sng'
        bank_bytes, score_bytes = b'synthetic fixture', b'score fixture'
        for path, data in ((synthetic, bank_bytes), (score, score_bytes)):
            dest = self.base / path
            dest.parent.mkdir()
            dest.write_bytes(data)
        self.manifest([self.entry(synthetic, bank_bytes), self.entry(score, score_bytes)])
        sound_sha = hashlib.sha256(bank_bytes).hexdigest()
        score_sha = hashlib.sha256(score_bytes).hexdigest()
        banks = {}
        cases = []
        recordings = []
        frames = audit.MIN_LISTENING_FRAMES
        pcm = b'\0\0' * frames
        wav = pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(pcm), b'WAVE', b'fmt ',
                   16, 1, 1, 48000, 96000, 2, 16, b'data', len(pcm)) + pcm
        for bank, (slots, rights) in audit.LISTENING_BANKS.items():
            banks[bank] = [{'slot': slot, 'sha256': sound_sha,
                            'fixture_path': f'{audit.FIXTURE_DIR.as_posix()}/{synthetic}',
                            'source_archive': 'test.zip', 'archive_member': 'test.snd'}
                           for slot in sorted(slots)]
            for name in audit.LISTENING_CASES:
                case = f'oem-{name}' if bank == 'oem' else name
                cases.append({'id': case, 'bank': bank, 'score_sha256': score_sha,
                              'score_path': f'{audit.FIXTURE_DIR.as_posix()}/{score}'})
                for role in ('native', 'renderer'):
                    target = directory / f'{case}-{role}.wav'
                    target.write_bytes(wav)
                    target.with_suffix('.wav.license').write_text(
                        f'SPDX-License-Identifier: {audit.LISTENING_LICENSE}\n# Tandy material notice\n')
                    recordings.append({
                        **self.entry(target.relative_to(self.root).as_posix(), wav),
                        'case': case, 'playback': role, 'bank': bank, 'classification': rights,
                        'license': audit.LISTENING_LICENSE, 'score_sha256': score_sha,
                        'instrument_sha256': {str(slot): sound_sha for slot in slots},
                        'frames': frames, 'raw_frames': frames, 'tap': 'pssj-dac-pre-mix',
                        'raw_sha256': sound_sha, 'first_capture_frame': 0, 'rate': 48000,
                        'render_frames': frames, 'first_render_frame': 0,
                        'render_pcm_sha256': hashlib.sha256(pcm).hexdigest(),
                        'model': 'rsx-dac-approximation-v1',
                    })
        (base.parent / 'suite-v1.json').write_text(
            json.dumps({'schema_version': 1, 'banks': banks, 'cases': cases}))
        manifest = {'schema_version': 1, 'milestone': directory.name, 'authorization': 'operator-2026-11-18',
                    'emulator_sha256': sound_sha, 'renderer_sha256': sound_sha,
                    'renderer_revision': 'f9fe4f174790b6fa19801d5c107994db8e57f0dc',
                    'recordings': recordings}
        manifest_path = directory / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        return manifest_path, manifest, wav

    def test_paired_listening_audio_accepted_but_excluded_from_archive(self):
        _, _, wav = self.listening_example()
        self.assertEqual(self.audit()['listening_wavs_checked'], 20)
        dist = self.root / 'dist'
        dist.mkdir()
        with ZipFile(dist / 'test.whl', 'w') as wheel:
            wheel.writestr('examples/music-listening/v1/baseline-pr118/major-scale-native.wav', wav)
        with self.assertRaisesRegex(ValueError, 'excluded file in archive'):
            self.audit()

    def test_listening_unlisted_out_of_scope_and_tampered(self):
        path, manifest, wav = self.listening_example()
        target = path.with_name('unknown-native.wav')
        target.write_bytes(wav)
        with self.assertRaisesRegex(ValueError, 'unlisted listening file'):
            self.audit()
        target.unlink()
        target = self.root / 'other.wav'
        target.write_bytes(wav)
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit()
        target.unlink()
        target = self.root / manifest['recordings'][0]['path']
        target.write_bytes(wav[:-1] + b'!')
        with self.assertRaisesRegex(ValueError, 'listening WAV digest'):
            self.audit()

    def test_listening_rejects_noncanonical_path_and_riff_payload(self):
        path, manifest, wav = self.listening_example()
        entry = manifest['recordings'][0]
        original = entry['path']
        entry['path'] = original.replace('/v1/', '/v1/./')
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'invalid listening identity'):
            self.audit()
        entry['path'] = original
        extra = wav[:36] + b'JUNK' + wav[40:]
        entry['sha256'] = hashlib.sha256(extra).hexdigest()
        (self.root / original).write_bytes(extra)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'expected PCM-only'):
            self.audit()

    def test_metadata_only_listening_sdist_is_auditable(self):
        path, _, _ = self.listening_example()
        for wav in path.parent.glob('*.wav'):
            wav.unlink()
        (self.root / 'PKG-INFO').write_text('Metadata-Version: 2.4\n')
        self.assertEqual(self.audit()['listening_wavs_checked'], 0)

    def test_fresh_canonical_reference_must_match_baseline_identity(self):
        baseline, manifest, wav = self.listening_example()
        milestone = baseline.parent.parent / 'interleaved-v2'
        milestone.mkdir()
        later = milestone / 'manifest.json'
        manifest['milestone'] = milestone.name
        native = []
        for entry in manifest['recordings']:
            if entry['playback'] == 'native':
                native.append(entry)
                entry['native_reference'] = 'fresh-byte-identical'
            else:
                target = milestone / Path(entry['path']).name
                target.write_bytes(wav)
                target.with_suffix('.wav.license').write_text(
                    f'SPDX-License-Identifier: {audit_repository.LISTENING_LICENSE}\n# Tandy material notice\n')
                entry['path'] = target.relative_to(self.root).as_posix()
        later.write_text(json.dumps(manifest))
        self.assertEqual(self.audit()['listening_wavs_checked'], 30)
        native[0]['sha256'] = '0' * 64
        later.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'unverified canonical listening reference'):
            self.audit()


if __name__ == '__main__':
    unittest.main()

