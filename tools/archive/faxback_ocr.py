# SPDX-FileCopyrightText: 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render indexed Faxback scans and store private, resumable page OCR."""

import argparse
import hashlib
import json
import platform
import re
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory


SCHEMA = """
CREATE TABLE IF NOT EXISTS profile(id TEXT PRIMARY KEY, config TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS document(
    url TEXT NOT NULL, digest TEXT NOT NULL, path TEXT NOT NULL,
    number TEXT NOT NULL, catalog TEXT NOT NULL, pages INTEGER NOT NULL,
    PRIMARY KEY(url, digest));
CREATE TABLE IF NOT EXISTS page(
    id INTEGER PRIMARY KEY, digest TEXT NOT NULL, number INTEGER NOT NULL,
    profile TEXT NOT NULL REFERENCES profile(id), raster TEXT NOT NULL,
    language TEXT NOT NULL, UNIQUE(digest, number, profile));
CREATE TABLE IF NOT EXISTS failure(
    url TEXT NOT NULL, digest TEXT NOT NULL, number INTEGER NOT NULL,
    profile TEXT NOT NULL, stage TEXT NOT NULL,
    PRIMARY KEY(url, digest, number, profile));
CREATE TABLE IF NOT EXISTS metadata_check(
    url TEXT NOT NULL, digest TEXT NOT NULL, profile TEXT NOT NULL, evidence TEXT NOT NULL,
    PRIMARY KEY(url, digest, profile));
CREATE VIRTUAL TABLE IF NOT EXISTS page_text USING fts5(body);
"""


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def process(args, timeout):
    return subprocess.run(args, capture_output=True, encoding='utf-8', errors='replace',
                          timeout=timeout, check=False)


def metadata_evidence(lines, number, expected_catalog):
    """Keep OCR strings separate from the file and index identities."""
    body = '\n'.join(lines)
    labels = re.findall(r'(?i)(?:fax\s*back|document)\s*(?:doc\.?\s*)?'
                        r'(?:#|no\.?|number)\s*[:#]?\s*([0-9]{3,8})\b', body)
    catalogs = set(re.findall(r'\b[0-9]{1,3}\s*[-–]\s*[0-9]{3,4}[A-Za-z]?\b', body))
    catalogs = {re.sub(r'\s', '', value).replace('–', '-') for value in catalogs}

    def catalog_key(value):
        # Leading zeros are equivalent only when the revision suffix also agrees.
        match = re.fullmatch(r'([0-9]{1,3})-([0-9]{3,4})([A-Za-z]?)', value)
        if match is None:
            return None
        return (int(match[1]), int(match[2]), match[3].upper())

    close = {actual for actual in catalogs for expected in expected_catalog
             if actual != expected and catalog_key(actual) is not None
             and catalog_key(actual) == catalog_key(expected)}
    return {
        'number_exact': number in labels,
        'number_zero_variant': any(n != number and int(n) == int(number) for n in labels),
        'number_conflict': any(int(n) != int(number) for n in labels),
        'catalog_exact': sorted(catalogs.intersection(expected_catalog)),
        'catalog_zero_variant': sorted(close),
    }


def candidates(index, library, minimum):
    with closing(sqlite3.connect(f'{index.resolve().as_uri()}?mode=ro', uri=True)) as source:
        source.execute('ATTACH DATABASE ? AS library', (f'{library.resolve().as_uri()}?mode=ro',))
        query = """
            SELECT r.url, r.path, r.sha256, r.number FROM record AS r
            WHERE r.format = 'pdf' AND r.number >= ? AND EXISTS (
                SELECT 1 FROM library.analysis AS a
                WHERE a.kind = 'pdf' AND a.digest = r.sha256 AND a.status = 'unsupported'
                    AND (a.detail LIKE '%; ocr-triage'
                         OR a.detail = 'no-pdf-text-ocr-required'))
            ORDER BY r.number, r.url
        """
        for url, path, digest, number in source.execute(query, (minimum,)):
            catalogs = tuple(row[0] for row in source.execute(
                'SELECT DISTINCT catalog FROM catalog_ref WHERE url = ? ORDER BY catalog', (url,)))
            yield url, path, digest, number, catalogs


def failure(db, url, digest, number, profile, stage):
    with db:
        db.execute('INSERT OR REPLACE INTO failure VALUES (?,?,?,?,?)',
                   (url, digest, number, profile, stage))


def render(path, page, output, pixels):
    return process(['pdftoppm', '-f', str(page), '-l', str(page), '-scale-to', str(pixels),
                    '-gray', '-singlefile', '-png', str(path), str(output)], 25).returncode == 0


def record_pages(db, path, url, digest, pages, profile, args, worker, counts):
    work = set()
    with TemporaryDirectory(prefix='faxback-ocr-', dir=args.output.parent) as scratch:
        directory = Path(scratch)
        for number in pages:
            counts['attempted'] += 1
            prefix = directory / str(number)
            try:
                if render(path, number, prefix, args.pixels) and (directory / f'{number}.png').is_file():
                    work.add(number)
                    continue
            except subprocess.TimeoutExpired:
                pass
            failure(db, url, digest, number, profile, 'render')
        if not work:
            return
        try:
            result = process(['powershell.exe', '-NoProfile', '-NonInteractive',
                              '-ExecutionPolicy', 'RemoteSigned', '-File', str(worker),
                              '-Directory', str(directory), '-Language', args.language], 75)
            output = result.stdout
            if result.returncode and not output.strip():
                raise RuntimeError(f'Windows OCR worker failed before producing a page ({result.returncode})')
        except subprocess.TimeoutExpired as error:
            output = (error.stdout or b'').decode('utf-8', errors='replace')
        for raw in output.splitlines():
            row = json.loads(raw)
            number = int(row['name'])
            if number not in work:
                raise RuntimeError('OCR returned an unexpected raster name')
            with db:
                key = db.execute('INSERT INTO page(digest,number,profile,raster,language) VALUES (?,?,?,?,?)',
                                 (digest, number, profile, sha256(directory / f'{number}.png'),
                                  row['language'])).lastrowid
                db.execute('INSERT INTO page_text(rowid,body) VALUES (?,?)', (key, '\n'.join(row['lines'])))
                db.execute('DELETE FROM failure WHERE url=? AND digest=? AND number=? AND profile=?',
                           (url, digest, number, profile))
            work.remove(number)
            counts['recognized'] += 1
        for number in work:
            failure(db, url, digest, number, profile, 'recognition')


def run(db, args):
    worker = Path(__file__).with_name('faxback_winocr.ps1').resolve()
    poppler = process(['pdftoppm', '-v'], 30)
    version = re.search(r'(?m)^pdftoppm version .+$', poppler.stdout + poppler.stderr)
    if not version:
        raise RuntimeError('Could not identify Poppler pdftoppm version')
    config = json.dumps({
        'poppler': version[0], 'pixels': args.pixels, 'grayscale': True,
        'engine': 'Windows.Media.Ocr', 'engine_version': None, 'windows_build': platform.version(),
        'language': args.language, 'worker_sha256': sha256(worker), 'confidence': None,
    }, sort_keys=True)
    profile = hashlib.sha256(config.encode()).hexdigest()
    with db:
        db.execute('INSERT OR IGNORE INTO profile VALUES (?,?)', (profile, config))
    counts = dict(attempted=0, recognized=0, verified_documents=0)
    for url, relative, digest, _, catalogs in candidates(args.index, args.library, args.minimum):
        root = args.originals.resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256(path) != digest:
            failure(db, url, digest, 0, profile, 'source-verification')
            continue
        counts['verified_documents'] += 1
        previous = db.execute('SELECT pages FROM document WHERE url=? AND digest=?', (url, digest)).fetchone()
        if previous:
            pages = previous[0]
        else:
            try:
                info = process(['pdfinfo', str(path)], 25)
                match = re.search(r'(?m)^Pages:\s+([1-9][0-9]*)\s*$', info.stdout)
            except subprocess.TimeoutExpired:
                match = None
            if not match:
                failure(db, url, digest, 0, profile, 'page-enumeration')
                continue
            pages = int(match[1])
        with db:
            db.execute('INSERT OR REPLACE INTO document VALUES (?,?,?,?,?,?)',
                       (url, digest, relative, Path(relative).stem, json.dumps(catalogs), pages))
            db.execute('DELETE FROM failure WHERE url=? AND digest=? AND number=0 AND profile=?',
                       (url, digest, profile))
        complete = {row[0] for row in db.execute('SELECT number FROM page WHERE digest=? AND profile=?',
                                                (digest, profile))}
        pending = [page for page in range(1, pages + 1) if page not in complete]
        while pending and counts['attempted'] < args.pages:
            batch = min(12, args.pages - counts['attempted'])
            record_pages(db, path, url, digest, pending[:batch], profile, args, worker, counts)
            pending = pending[batch:]
        first = db.execute('''SELECT t.body FROM page AS p JOIN page_text AS t ON t.rowid=p.id
                              WHERE p.digest=? AND p.number=1 AND p.profile=?''', (digest, profile)).fetchone()
        if first:
            evidence = metadata_evidence(first[0].splitlines(), Path(relative).stem, catalogs)
            with db:
                db.execute('INSERT OR REPLACE INTO metadata_check VALUES (?,?,?,?)',
                           (url, digest, profile, json.dumps(evidence)))
        if counts['attempted'] >= args.pages:
            break
    print(json.dumps(dict(counts, profile=profile), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('index', 'library', 'originals', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--minimum', type=int, default=0, help='First Faxback number to consider')
    parser.add_argument('--pages', type=int, default=100, help='Maximum pages attempted per run')
    parser.add_argument('--pixels', type=int, default=2000, help='Rendered long edge in pixels')
    parser.add_argument('--language', default='en-US')
    args = parser.parse_args()
    if args.pages < 1 or not 100 <= args.pixels <= 2500:
        parser.error('pages must be positive and pixels must be between 100 and 2500')
    if args.output.resolve() in (args.index.resolve(), args.library.resolve()):
        parser.error('output must be a separate private database')
    with closing(sqlite3.connect(args.output)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript(SCHEMA)
        run(db, args)


if __name__ == '__main__':
    main()
