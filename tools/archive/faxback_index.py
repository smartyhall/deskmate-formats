"""Build a private, searchable cross-reference of verified Faxback documents."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3

from archive_intelligence import contained, read_receipts, read_transfer_state


PREFIX = 'tandy1000/faxback/'
FILE = re.compile(r'(\d{5})\.(txt|pdf|gif|jpg|png|zip)', re.I)
INDEX = re.compile(r'^\s*(\d{5})\.([a-z]+)\s+(.+)$', re.I)
NUMBER = re.compile(r'\b(?:faxback(?:\s+doc(?:ument)?\.?)?|document)\s*#\s*(\d{3,6})\b', re.I)
CATALOG = re.compile(r'\b(?:\d{2}|\d{3})-\d{3,5}[a-z]?\b', re.I)
DATE = re.compile(r'\b(?:\d{1,2}[/.-]\d{1,2}[/.-](?:19\d\d|20\d\d|\d\d)|'
                  r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+'
                  r'\d{1,2},?\s+(?:19|20)\d\d)\b', re.I)
LISTED = re.compile(r'^\s*(\d{3,6})\s{2,}\D')
SCHEMA = """
CREATE TABLE IF NOT EXISTS configuration(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS record(
  url TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL,
  number INTEGER NOT NULL, format TEXT NOT NULL, display_title TEXT,
  product_candidate TEXT, subject_candidate TEXT, identity_state TEXT NOT NULL,
  stated_number INTEGER, text_state TEXT NOT NULL, dates_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS record_number ON record(number);
CREATE TABLE IF NOT EXISTS catalog_ref(
  url TEXT NOT NULL REFERENCES record(url) ON DELETE CASCADE,
  catalog TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(url,catalog,evidence)
);
CREATE INDEX IF NOT EXISTS catalog_number ON catalog_ref(catalog);
CREATE TABLE IF NOT EXISTS document_ref(
  url TEXT NOT NULL REFERENCES record(url) ON DELETE CASCADE,
  number INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(url,number,evidence)
);
CREATE VIRTUAL TABLE IF NOT EXISTS text USING fts5(url UNINDEXED, title, body);
"""


def original(root, row):
    p = contained(root, row['local'])
    if row['bytes'] > 16 * 1024**2 or p.stat().st_size != row['bytes']:
        raise ValueError('Faxback original exceeds the limit or differs in size')
    with p.open('rb') as stream:
        data = stream.read(row['bytes'] + 1)
    if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Faxback original differs from its transfer receipt')
    return data


def clean_header(text):
    anchor = NUMBER.search(text)
    return text[:anchor.start()].strip() if anchor else text.strip()


def metadata(title, body, number):
    candidates = body.splitlines()[:6]
    for line in candidates:
        if match := NUMBER.search(line):
            stated = int(match[1])
            title = clean_header(line) or title
            state = 'body-confirmed' if number == stated else 'body-conflict'
            break
    else:
        state, stated = 'archive-index' if title else 'filename-only', None
    columns = re.split(r'\s{2,}', title or '', maxsplit=1)
    return title, columns[0] or None, columns[1] if len(columns) == 2 else None, state, stated


def index(root, database):
    root = root.resolve(strict=True)
    if database.resolve().is_relative_to(root):
        raise ValueError('Faxback database must be outside the mirror')
    snapshot = datetime.now(timezone.utc).isoformat()
    rows = list(read_receipts(read_transfer_state(root / 'transfer-state/mirror.sqlite3')))
    subset = [r for r in rows if r['rel'].startswith(PREFIX)]
    verified = {r['rel']: r for r in subset if r['status'] == 'verified'}
    master = verified.get(PREFIX + '00_index.txt')
    titles = {}
    if master:
        for line in original(root, master).decode('cp437').splitlines():
            if match := INDEX.match(line):
                titles[f'{match[1]}.{match[2].lower()}'] = clean_header(match[3])
    master_hash = master['sha256'] if master else None
    failures = []
    with closing(sqlite3.connect(database)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript(SCHEMA)
        with db:
            indexed = {url: sha for url, sha in db.execute('SELECT url,sha256 FROM record')}
            recorded_master = db.execute("SELECT value FROM configuration WHERE key='master_sha256'").fetchone()
            changed_master = recorded_master is not None and recorded_master[0] != (master_hash or '')
            available = {row['url'] for row in verified.values()}
            for url in indexed.keys() - available:
                db.execute('DELETE FROM text WHERE url=?', (url,))
                db.execute('DELETE FROM record WHERE url=?', (url,))
            for row in verified.values():
                name = PurePosixPath(row['rel']).name.lower()
                match = FILE.fullmatch(name)
                if not match or (not changed_master and indexed.get(row['url']) == row['sha256']):
                    continue
                try:
                    data = original(root, row)
                except (OSError, ValueError) as error:
                    failures.append({'path': row['rel'], 'error': str(error)})
                    db.execute('DELETE FROM text WHERE url=?', (row['url'],))
                    db.execute('DELETE FROM record WHERE url=?', (row['url'],))
                    continue
                number, fmt = int(match[1]), match[2]
                body = data.decode('cp437') if fmt == 'txt' else ''
                title, product, subject, state, stated = metadata(titles.get(name), body, number)
                date_lines = [line.strip() for line in body.splitlines()
                              if DATE.search(line) and any(k in line.casefold()
                                  for k in ('update', 'publish', 'revis', 'date', 'last modified'))]
                catalogs = {(m[0].upper(), 'title') for m in CATALOG.finditer(title or '')}
                catalogs.update((m[0].upper(), 'body') for m in CATALOG.finditer(body))
                docs = {(int(m[1]), 'explicit') for m in NUMBER.finditer(body) if int(m[1]) != number}
                if subject and subject.casefold() == 'catalog listing':
                    docs.update((int(m[1]), 'catalog-listing') for line in body.splitlines()
                                if (m := LISTED.match(line)) and int(m[1]) != number)
                url = row['url']
                db.execute('DELETE FROM text WHERE url=?', (url,))
                db.execute('DELETE FROM record WHERE url=?', (url,))
                db.execute('INSERT INTO record VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                           (url, row['rel'], row['sha256'], number, fmt, title,
                            product, subject, state, stated, 'indexed' if fmt == 'txt'
                            else 'text-not-extracted', json.dumps(date_lines)))
                db.execute('INSERT INTO text VALUES (?,?,?)', (url, title, body))
                db.executemany('INSERT INTO catalog_ref VALUES (?,?,?)',
                               ((url, key, source) for key, source in sorted(catalogs)))
                db.executemany('INSERT INTO document_ref VALUES (?,?,?)',
                               ((url, key, source) for key, source in sorted(docs)))
            if not failures:
                db.execute("INSERT OR REPLACE INTO configuration VALUES ('master_sha256',?)",
                           (master_hash or '',))
        return {'snapshot_started_utc': snapshot,
                'latest_recorded_completion': max((r.get('observed') or '' for r in verified.values()), default=None),
                'mirror_file_status': dict(Counter(r['status'] for r in rows)),
                'faxback_file_status': dict(Counter(r['status'] for r in subset)),
                'title_index_sha256': master_hash,
                'formats': dict(db.execute('SELECT format,count(*) FROM record GROUP BY format')),
                'identity_states': dict(db.execute('SELECT identity_state,count(*) FROM record GROUP BY identity_state')),
                'catalog_edges': db.execute('SELECT count(*) FROM catalog_ref').fetchone()[0],
                'document_edges': db.execute('SELECT count(*) FROM document_ref').fetchone()[0],
                'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mirror', type=Path)
    parser.add_argument('database', type=Path)
    args = parser.parse_args()
    print(json.dumps(index(args.mirror, args.database), indent=2))


if __name__ == '__main__':
    main()
