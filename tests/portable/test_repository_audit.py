"""Publication audit tests for application-generated synthetic-data specimens."""
import hashlib
import json
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


if __name__ == '__main__':
    unittest.main()
