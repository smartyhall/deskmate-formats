"""Inventory private image occurrences without editing their originals."""
import argparse
from collections import Counter
from contextlib import suppress
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image


FORMATS = {'.png', '.bmp', '.gif', '.jpg', '.jpeg', '.webp'}
SCHEMA = 1


def identity(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=True).encode('ascii')).hexdigest()


def compare_pixels(image):
    with image.convert('L') as grayscale:
        with grayscale.resize((9, 8), Image.Resampling.LANCZOS) as small:
            pixels = small.tobytes()
    bits = ''.join(str(int(pixels[row + col] > pixels[row + col + 1]))
                   for row in range(0, 72, 9) for col in range(8))
    return f'{int(bits, 2):016x}'


def scan(roots, labels, previous):
    occurrences = {}
    images = {}
    gaps = []
    for label, root in sorted(roots.items()):
        try:
            root = root.resolve(strict=True)
        except OSError as error:
            gaps.append({'root_id': label, 'relative': None, 'error': str(error)})
            continue
        for path in sorted(root.rglob('*')):
            if path.suffix.casefold() not in FORMATS or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            occurrence = identity(label, relative)
            try:
                if not path.resolve(strict=True).is_relative_to(root):
                    raise ValueError('path leaves evidence root')
                metadata = path.stat()
                before = [metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns]
                cached = previous.get('occurrences', {}).get(occurrence, {})
                if before == cached.get('stat') and cached.get('locator') == str(path):
                    sha = cached['sha256']
                    images[sha] = previous['images'][sha]
                else:
                    with path.open('rb') as stream:
                        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
                        if sha not in images:
                            stream.seek(0)
                            with Image.open(stream) as image:
                                images[sha] = {
                                    'format': image.format, 'display_pixels': list(image.size),
                                    'pixel_mode': image.mode, 'frames': getattr(image, 'n_frames', 1),
                                    'first_frame_dhash64': compare_pixels(image),
                                }
                    metadata = path.stat()
                    if before != [metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns]:
                        raise ValueError('file changed during observation')
                provenance = {name: None for name in ('machine', 'application', 'version',
                              'capture_method', 'screen_state', 'focus', 'selection')}
                provenance.update(labels.get(label, {}))
                occurrences[occurrence] = {'root_id': label, 'relative': relative,
                    'locator': str(path), 'sha256': sha, 'stat': before, 'provenance': provenance}
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                gaps.append({'root_id': label, 'relative': relative, 'error': str(error)})
    active = {entry['sha256'] for entry in occurrences.values()}
    images = {sha: record for sha, record in images.items() if sha in active}
    # Equal 64-bit difference hashes are candidates for manual comparison only.
    candidates = {}
    for sha, record in images.items():
        key = identity(record['display_pixels'], record['first_frame_dhash64'])
        candidates.setdefault(key, []).append(sha)
    root_counts = Counter(row['root_id'] for row in occurrences.values())
    return {'schema_version': SCHEMA, 'occurrences': occurrences, 'images': images,
            'unobserved_previous_occurrences': sorted(previous.get('occurrences', {}).keys()
                                                       - occurrences.keys()),
            'near_duplicate_candidates': [sorted(group) for group in candidates.values()
                                          if len(group) > 1],
            'gaps': gaps, 'summary': {'occurrences': len(occurrences), 'identities': len(images),
                                     'occurrences_by_root': dict(root_counts)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--root', nargs=2, metavar=('LABEL', 'DIRECTORY'), action='append', required=True)
    parser.add_argument('--labels', type=Path, help='optional reviewed provenance by root label')
    args = parser.parse_args()
    roots = {label: Path(path) for label, path in args.root}
    if len(roots) != len(args.root):
        parser.error('root labels must be unique')
    if any(args.output.resolve().is_relative_to(path.resolve()) for path in roots.values()):
        parser.error('catalog must be outside the input roots')
    previous = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else {}
    if previous and previous.get('schema_version') != SCHEMA:
        parser.error('unsupported catalog schema')
    labels = json.loads(args.labels.read_text(encoding='utf-8-sig')) if args.labels else {}
    result = scan(roots, labels, previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', dir=args.output.parent, encoding='utf-8', delete=False) as stream:
        staging = Path(stream.name)
        json.dump(result, stream, indent=2, sort_keys=True)
    try:
        staging.replace(args.output)
    finally:
        with suppress(FileNotFoundError):
            staging.unlink()
    print(json.dumps({**result['summary'], 'gaps': len(result['gaps']),
                      'near_duplicate_groups': len(result['near_duplicate_candidates'])}, indent=2))


if __name__ == '__main__':
    main()
