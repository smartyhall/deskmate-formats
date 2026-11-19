"""Exercise the manifest-gated visual comparison validators without lab media."""
from binascii import crc32
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from struct import pack
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import zlib

from deskmate_formats.supervisor import draw_comparison_audit as audit, repository_audit
from tools import audit_repository


def chunk(kind, data):
    return pack('>I', len(data)) + kind + data + pack('>I', crc32(kind + data))


def png(raw=b'\0\0\0\0', *, extra=b'', width=1, payload=None):
    header = chunk(b'IHDR', pack('>IIBBBBB', width, 1, 8, 2, 0, 0, 0))
    return (audit.PNG + header + extra
            + chunk(b'IDAT', zlib.compress(raw) if payload is None else payload) + chunk(b'IEND', b''))


SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><line x1="0" x2="1"/></svg>'


class DrawArtifactsTest(unittest.TestCase):
    def test_png_content_bounds(self):
        audit.check_png(png(), (1, 1))
        samples = [
            png() + b'payload',
            png(extra=chunk(b'tEXt', b'comment\0payload')),
            png(width=2049),
            png(raw=b'\5\0\0\0'),
            png(raw=bytes(1024)),
            png(payload=zlib.compress(b'\0' * 4) + zlib.compress(b'\0' * 4)),
            png(payload=zlib.compress(b'\0' * 4)[:-2]),
            png()[:-13] + bytes(13),
        ]
        for i, data in enumerate(samples):
            with self.subTest(i=i), self.assertRaises(ValueError):
                audit.check_png(data, (1, 1))

    def test_svg_content_allowlist(self):
        audit.check_svg(SVG)
        for extra in (b'<script/>', b'<image href="external"/>', b'<g onclick="code"/>',
                      b'<rect fill="url(target)"/>', b'<foreignObject/>', b'<![CDATA[x]]>'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                audit.check_svg(SVG.replace(b'</svg>', extra + b'</svg>'))


class DrawLibraryAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.milestone = audit.TREE / audit.BASELINE
        self.suite_path = audit.TREE.parent / 'suite-v1.json'
        self.manifest_path = self.milestone / 'manifest.json'
        self.suite = {'schema_version': 1, 'suite_version': 'v1', 'baseline_renderer_revision': audit.REVISION,
                      'featured_cases': [], 'diagnostic_draw_fixtures': []}
        self.manifest = {'schema_version': 1, 'suite_version': 'v1', 'milestone': audit.BASELINE,
                         'publication': 'original-synthetic-drawing-crops', 'renderer_revision': audit.REVISION,
                         'cases': []}
        self.files = []
        fixtures = []
        for key, ids in (('featured_cases', audit.FEATURED), ('diagnostic_draw_fixtures', audit.DIAGNOSTIC)):
            for case in ids:
                source = audit.FIXTURES + case + '.fig'
                data = b'\x14FIG' + case.encode()
                self.write(source, data)
                fixtures.append({'path': f'draw/{case}.fig', 'size': len(data), 'sha256': sha256(data).hexdigest(),
                                 'synthetic_data': True, 'origin': 'synthetic audit regression'})
                self.suite[key].append({'id': case, 'path': source, 'sha256': sha256(data).hexdigest(),
                                        'size': len(data), 'status': 'native-saved'})
                entry = {'id': case, 'source_path': source, 'source_sha256': sha256(data).hexdigest(),
                         'native_capture': {'framebuffer_sha256': '0' * 64, 'source_role': 'fresh-native-reopen',
                                            'crop_xyxy': [0, 0, 1, 1]},
                         'dimensions': [1, 1], 'artifacts': {}}
                for kind in audit.KINDS:
                    artifact = self.milestone / f'{case}-{kind}'
                    payload = png() if kind.endswith('.png') else SVG
                    self.write(artifact, payload)
                    self.write(str(artifact) + '.license', (
                        f'SPDX-FileCopyrightText: 2026 Author\nSPDX-License-Identifier: {audit.LICENSE}\n').encode())
                    entry['artifacts'][kind] = {'path': artifact.as_posix(), 'size': len(payload),
                                                'sha256': sha256(payload).hexdigest(), 'license': audit.LICENSE}
                    self.files.append(artifact)
                self.manifest['cases'].append(entry)
        self.write_json('tests/fixtures/application-generated/manifest.json', {'fixtures': fixtures})
        self.write_json(self.suite_path, self.suite)
        self.write_json(self.manifest_path, self.manifest)

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def write_json(self, relative, payload):
        self.write(relative, json.dumps(payload).encode())

    def audit(self, module):
        with patch.object(module, 'ROOT', self.root):
            return module.audit()

    def test_both_audits_accept_and_reject_unlisted(self):
        for module in (audit_repository, repository_audit):
            self.assertEqual(self.audit(module)['draw_comparison_artifacts_checked'], len(self.files))
        self.write(self.milestone / 'unlisted.png', png())
        for module in (audit_repository, repository_audit):
            with self.assertRaisesRegex(ValueError, 'unlisted Draw comparison'):
                self.audit(module)
        (self.root / self.milestone / 'unlisted.png').unlink()
        self.write('unrelated.png', png())
        with self.assertRaisesRegex(ValueError, 'excluded evidence/software type'):
            self.audit(audit_repository)

    def test_manifest_identity_and_budget(self):
        for field, value in [('path', '../outside.png'), ('size', audit.MAX_FILE + 1), ('license', 'CC0-1.0')]:
            bad = deepcopy(self.manifest)
            bad['cases'][0]['artifacts']['native.png'][field] = value
            self.write_json(self.manifest_path, bad)
            with self.assertRaisesRegex(ValueError, 'invalid artifact'):
                self.audit(audit_repository)
        bad = deepcopy(self.manifest)
        bad['cases'][0]['source_sha256'] = '0' * 64
        self.write_json(self.manifest_path, bad)
        with self.assertRaisesRegex(ValueError, 'invalid source'):
            self.audit(audit_repository)
        bad = deepcopy(self.manifest)
        bad['cases'].append(bad['cases'][0])
        self.write_json(self.manifest_path, bad)
        with self.assertRaisesRegex(ValueError, 'duplicate case'):
            self.audit(audit_repository)

    def test_digest_and_symlink(self):
        target = self.root / self.files[0]
        data = target.read_bytes()
        target.write_bytes(data[:-1] + bytes((data[-1] ^ 1,)))
        with self.assertRaisesRegex(ValueError, 'wrong digest'):
            self.audit(audit_repository)
        target.unlink()
        try:
            target.symlink_to(self.root / self.files[-1])
        except OSError:
            self.skipTest('symlink creation requires OS privileges')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.audit(audit_repository)

    def test_sdist_metadata_only_and_archive_exclusion(self):
        for rel in self.files:
            (self.root / rel).unlink()
        with self.assertRaisesRegex(ValueError, 'declared artifacts are missing'):
            self.audit(audit_repository)
        self.write('PKG-INFO', b'Metadata-Version: 2.4')
        self.assertEqual(self.audit(audit_repository)['draw_comparison_artifacts_checked'], 0)
        dist = self.root / 'dist'
        dist.mkdir()
        for prefix in ('project/', ''):
            with ZipFile(dist / 'bad.whl', 'w') as package:
                package.writestr(prefix + self.files[3].as_posix(), SVG)
            with self.assertRaisesRegex(ValueError, 'excluded file in archive'):
                self.audit(audit_repository)
