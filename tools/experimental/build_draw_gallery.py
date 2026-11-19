"""Compile Draw comparison metadata into a file://-compatible catalogue."""
import json
from pathlib import Path

from deskmate_formats.supervisor import draw_comparison_audit as audit


ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / audit.TREE.parent


def build():
    fixtures_dir = ROOT / 'tests/fixtures/application-generated'
    fixtures = json.loads((fixtures_dir / 'manifest.json').read_text(encoding='utf-8'))['fixtures']
    indexed = {f'{fixtures_dir.relative_to(ROOT).as_posix()}/{item["path"]}': item for item in fixtures}
    artifacts, _ = audit.comparison_manifest(ROOT, indexed)
    suite = json.loads((LIBRARY / 'suite-v1.json').read_text(encoding='utf-8'))
    labels = {case['id']: case.get('description', case.get('purpose', ''))
              for key in ('featured_cases', 'diagnostic_draw_fixtures') for case in suite[key]}
    milestones = {}
    for path in sorted((ROOT / audit.TREE).glob('*/manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        milestone = manifest['milestone']
        for case in manifest['cases']:
            case['description'] = labels[case['id']]
            case['featured'] = case['id'] in audit.FEATURED
            for item in case['artifacts'].values():
                audit.check_artifact(ROOT, item['path'], artifacts[item['path']])
                item['href'] = (ROOT / item['path']).relative_to(LIBRARY).as_posix()
            case['source_href'] = '../../' + case['source_path']
        manifest['href'] = path.relative_to(LIBRARY).as_posix()
        milestones[milestone] = manifest
    data = json.dumps(milestones, ensure_ascii=True, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    (LIBRARY / 'catalog.js').write_text(f'window.drawComparisons = {data};\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    build()
