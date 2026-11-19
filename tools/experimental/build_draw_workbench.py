"""Build the standalone offline Draw Workbench from audited synthetic inputs."""
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'examples/draw-workbench'


def build():
    suite = json.loads((APP.parent / 'draw-comparison/suite-v1.json').read_text(encoding='utf-8'))
    samples = []
    for entry in suite['featured_cases']:
        path = ROOT / entry['path']
        data = path.read_bytes()
        if len(data) != entry['size'] or sha256(data).hexdigest() != entry['sha256']:
            raise ValueError(f'example bytes do not match the frozen suite for {entry["id"]}')
        samples.append({'id': entry['id'], 'title': entry['title'], 'name': entry['native_dos_name'],
                        'data': b64encode(data).decode('ascii')})
    source = (APP / 'workbench.template.html').read_text(encoding='utf-8')
    pieces = {
        'css': (APP / 'workbench.css').read_text(encoding='utf-8'),
        'samples': json.dumps(samples, separators=(',', ':'), ensure_ascii=True).replace('<', '\\u003c'),
        'codec': (APP / 'fig.js').read_text(encoding='utf-8'),
        'script': (APP / 'workbench.js').read_text(encoding='utf-8'),
    }
    for key, fragment in pieces.items():
        marker = f'/* workbench-{key} */'
        if source.count(marker) != 1:
            raise ValueError(f'expected a single template slot for {key}')
        source = source.replace(marker, fragment)
    (APP / 'workbench.html').write_text(source, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    build()
