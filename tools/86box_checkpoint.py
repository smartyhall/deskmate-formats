"""Verify a private 86Box inventory and restore an independent working machine."""
import argparse
import configparser
import csv
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import shutil
import socket
import stat
import subprocess
from tempfile import TemporaryDirectory
import uuid


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inside(root, name):
    relative = PureWindowsPath(name)
    if (relative.anchor or not relative.parts
            or any(part == '..' or ':' in part for part in relative.parts)):
        raise ValueError(f'unsafe inventory path: {name}')
    path = root.joinpath(*relative.parts).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f'not a file within checkpoint: {name}')
    return path


def verify_inventory(root, manifest):
    root = root.resolve(strict=True)
    files = {}
    identities = set()
    with manifest.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            path = inside(root, row['Path'])
            name = path.relative_to(root).as_posix()
            if name.casefold() in identities:
                raise ValueError(f'duplicate inventory entry: {name}')
            identities.add(name.casefold())
            sha = row['SHA256'].lower()
            if path.stat().st_size != int(row['Bytes']) or digest(path) != sha:
                raise ValueError(f'inventory verification failed: {name}')
            files[name] = sha
    if not files:
        raise ValueError('empty checkpoint inventory')
    return files


def config(path):
    result = configparser.ConfigParser(interpolation=None)
    result.read_string(path.read_text(encoding='utf-8-sig'))
    return result


def media_inventory(path):
    if path is None:
        return {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return {Path(row['Path']).resolve(strict=True): row for row in csv.DictReader(stream)}


def save(source, destination, names, seven_zip=None):
    """Checkpoint explicitly selected files from a powered-off machine."""
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists() or destination.is_relative_to(source):
        raise ValueError('checkpoint requires a new destination outside the source')
    if not names or '86box.cfg' not in {PureWindowsPath(name).as_posix() for name in names}:
        raise ValueError('checkpoint requires 86box.cfg and explicit file names')
    if (source / 'automation.token').exists():
        raise ValueError('source has an automation token; confirm it is powered off')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.with_name(f'{destination.name}.incomplete-{uuid.uuid4().hex}')
    payload = stage / 'machine'
    payload.mkdir(parents=True)
    manifest = stage / 'machine-files.csv'
    with manifest.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(('Path', 'Bytes', 'SHA256'))
        for name in names:
            path = inside(source, name)
            relative = path.relative_to(source)
            sha = digest(path)
            target = payload / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with path.open('rb') as original, target.open('xb') as output:
                shutil.copyfileobj(original, output, length=1024 * 1024)
            writer.writerow((relative.as_posix(), path.stat().st_size, sha))
    verified = verify_inventory(payload, manifest)
    if verify_inventory(source, manifest) != verified:
        raise ValueError('source changed during checkpoint')
    if seven_zip is not None:
        helper = seven_zip.resolve(strict=True)
        archive = stage / 'machine.incomplete.7z'
        def run(*args, cwd=None):
            subprocess.run([str(helper), *map(str, args)], cwd=cwd, check=True,
                           stdin=subprocess.DEVNULL, timeout=3600)

        run('a', '-t7z', '-mx=1', archive, '.', cwd=payload)
        with archive.open('rb') as stream:
            if stream.read(6) != b'7z\xbc\xaf\x27\x1c':
                raise ValueError('archive lacks 7z signature')
        run('t', '-t7z', archive)
        with TemporaryDirectory(dir=stage) as extracted:
            run('x', '-t7z', '-y', f'-o{extracted}', archive)
            extracted = Path(extracted)
            members = {p.relative_to(extracted).as_posix() for p in extracted.rglob('*') if p.is_file()}
            if members != verified.keys() or verify_inventory(extracted, manifest) != verified:
                raise ValueError('compressed round trip differs from inventory')
        archive.rename(stage / 'machine.7z')
    receipt = {'state': 'verified-unbooted', 'files': len(verified), 'compressed': seven_zip is not None}
    (payload / 'baseline-manifest.json').write_text(json.dumps(receipt), encoding='utf-8')
    for path in stage.rglob('*'):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~stat.S_IWRITE)
    if destination.exists():
        raise FileExistsError(destination)
    stage.rename(destination)
    return receipt


def restore(root, manifest, destination, original, port, media_manifest=None):
    root = root.resolve(strict=True)
    destination = destination.resolve()
    original = original.resolve(strict=True)
    if (destination.exists() or destination.is_relative_to(root)
            or destination.is_relative_to(original)):
        raise ValueError('restore requires a new destination outside the source machines')
    if not 1 <= port <= 65535:
        raise ValueError('invalid loopback port')
    # This detects conflicts at restore time. The launcher checks again at launch.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))
    files = verify_inventory(root, manifest)
    if '86box.cfg' not in files:
        raise ValueError('no verified machine configuration')
    cfg = config(root / '86box.cfg')
    external = media_inventory(media_manifest)
    copied = {'86box.cfg', *(name for name in files if name.startswith('nvr/'))}
    media = {}
    for section in cfg.sections():
        for key, value in cfg.items(section):
            if not value:
                continue
            if re.fullmatch(r'hdd_\d+_fn', key):
                local = Path(value)
                if local.is_absolute():
                    local = local.resolve().relative_to(original)
                name = inside(root, str(local)).relative_to(root).as_posix()
                if name not in files:
                    raise ValueError(f'unverified mutable disk: {name}')
                copied.add(name)
                cfg[section][key] = name
            elif re.fullmatch(r'(?:cdrom|fdd)_\d+_image_path', key):
                path = (original / value).resolve()
                if path.is_relative_to(original):
                    name = path.relative_to(original).as_posix()
                    if name not in files:
                        raise ValueError(f'unverified local media: {name}')
                    copied.add(name)
                    cfg[section][key] = name
                elif key.startswith('cdrom_') and path in external:
                    row = external[path]
                    sha = digest(path)
                    if path.stat().st_size != int(row['Bytes']) or sha != row['SHA256'].lower():
                        raise ValueError(f'external CD failed verification: {key}')
                    cfg[section][key] = str(path)
                    media[key] = {'path': str(path), 'sha256': sha}
                else:
                    raise ValueError(f'unverified or writable external media: {key}')
            elif PureWindowsPath(value).is_absolute():
                raise ValueError(f'unsupported absolute path in config: {section}/{key}')
    if not any(re.fullmatch(r'hdd_\d+_fn', k) and v
               for section in cfg.sections() for k, v in cfg.items(section)):
        raise ValueError('no independent hard disk configured')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.with_name(f'{destination.name}.incomplete-{uuid.uuid4().hex}')
    stage.mkdir()
    for name in sorted(copied):
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        if target.samefile(root / name) or digest(target) != files[name]:
            raise ValueError(f'working copy verification failed: {name}')
    with (stage / '86box.cfg').open('w', encoding='utf-8', newline='\n') as stream:
        cfg.write(stream)
    receipt = {'state': 'restored-unbooted', 'source': str(root),
               'verified_source_files': len(files), 'copied_original_hashes': {
                   name: files[name] for name in sorted(copied)},
               'restored_config_sha256': digest(stage / '86box.cfg'),
               'external_media': media, 'loopback_port': port}
    (stage / 'restore.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if destination.exists():
        raise FileExistsError(destination)
    stage.rename(destination)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('inventory', type=Path)
    clone = sub.add_parser('restore')
    clone.add_argument('inventory', type=Path)
    clone.add_argument('destination', type=Path)
    clone.add_argument('--original', required=True, type=Path,
                       help='former machine location for resolving external media')
    clone.add_argument('--port', required=True, type=int)
    clone.add_argument('--media-inventory', type=Path)
    checkpoint = sub.add_parser('save')
    checkpoint.add_argument('destination', type=Path)
    checkpoint.add_argument('--include', action='append', required=True)
    checkpoint.add_argument('--seven-zip', type=Path)
    args = parser.parse_args()
    if args.command == 'verify':
        result = {'state': 'verified', 'files': len(verify_inventory(args.source, args.inventory))}
    elif args.command == 'restore':
        result = restore(args.source, args.inventory, args.destination, args.original,
                         args.port, args.media_inventory)
    else:
        result = save(args.source, args.destination, args.include, args.seven_zip)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, configparser.Error, subprocess.SubprocessError) as exc:
        raise SystemExit(f'86Box checkpoint: {exc}')
