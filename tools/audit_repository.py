"""Reject unsafe proposed source content; never follow private/build directories."""
from pathlib import Path
import ast
import json
import re
import sys
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','build','dist','local-results','private-fixtures','.ruff_cache'}
BAD_EXT={'.exe','.com','.dll','.img','.ima','.iso','.zip','.7z','.cln','.png','.pdf',
         '.pdm','.res','.r89','.fil','.adr','.pcl','.hlp','.tut'}
PATTERNS={
    'host Windows user path':r'(?i)[a-z]:[\\/]Users[\\/]',
    'host POSIX user path':r'/(?:home|Users)/[^/\s]+',
    'GitHub credential':r'gh' + r'[pousr]_[A-Za-z0-9]{20,}',
    'fine-grained credential':r'github_' + r'pat_[A-Za-z0-9_]{20,}',
    'API credential':r'sk-' + r'[A-Za-z0-9]{20,}',
    'private key':r'-----BEGIN ' + r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'credential in URL':r'https?://[^\s/@:]+:[^\s/@]+@',
    'archive access query':r'(?i)[?&](?:access_token|auth_token|api_key|token)=[A-Za-z0-9_%.-]{8,}',
}

def source_files():
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if any(x in EXCLUDED or x.startswith('.venv') or x.endswith('.egg-info') or x=='__pycache__' for x in rel.parts):
            continue
        if p.is_file():yield p

def audit():
    count=0
    for p in source_files():
        rel=p.relative_to(ROOT).as_posix()
        if p.is_symlink():raise ValueError('symlink is not permitted: '+rel)
        if p.suffix.lower() in BAD_EXT or p.name.startswith('.env'):
            raise ValueError('excluded evidence/software type: '+rel)
        data=p.read_bytes()
        if data.startswith((b'MZ',bytes((3,70,73,76)))):raise ValueError('software/database bytes: '+rel)
        text=data.decode('utf-8')
        if '\0' in text:raise ValueError('binary content: '+rel)
        for label,pattern in PATTERNS.items():
            if re.search(pattern,text):raise ValueError(label+': '+rel)
        if p.suffix=='.py':ast.parse(text,filename=rel)
        count+=1
    # Archive names/content are checked as well; no installed trees or venvs leak.
    for p in (ROOT/'dist').glob('*'):
        if p.suffix=='.whl':
            with zipfile.ZipFile(p) as archive:
                members=[(n,archive.read(n)) for n in archive.namelist() if not n.endswith('/')]
        elif p.name.endswith('.tar.gz'):
            with tarfile.open(p,'r:gz') as archive:
                members=[(m.name,archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()]
        else:raise ValueError('unexpected build artifact: '+p.name)
        for name,data in members:
            if any(part in EXCLUDED or part.startswith('.venv') for part in Path(name).parts):
                raise ValueError('excluded directory in archive: '+name)
            if Path(name).suffix.lower() in BAD_EXT:raise ValueError('excluded file in archive: '+name)
            text=data.decode('utf-8')
            for label,pattern in PATTERNS.items():
                if re.search(pattern,text):raise ValueError(label+' in archive: '+name)
    return {'source_files_checked':count,'status':'passed',
            'fixed_format_signature':'Documented internal marker is not a personal credential.',
            'excluded':'Original binaries, media, snapshots, screenshots and real databases are not staged.'}

if __name__=='__main__':
    try:print(json.dumps(audit(),indent=2))
    except (ValueError,UnicodeError,SyntaxError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
