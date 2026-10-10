"""Hash-based release packages; preserve unchanged media and the serving release."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
from content_cache import cached_hashes, sha256_file

MANIFEST = 'release-delta.json'


def relative_path(value):
    path = PurePosixPath(value)
    if not value or '\\' in value or path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise ValueError('Unsafe release path: ' + value)
    if path.parts[0] not in {'site', 'demos', 'runtime'} or len(path.parts) < 2:
        raise ValueError('Non-public release path: ' + value)
    if value.startswith(('demos/media/', 'site/_download-parts/')):
        raise ValueError('Duplicated media or static-only download parts: ' + value)
    return path


def safe_file(root, relative):
    relative_path(relative)
    root = Path(root).resolve()
    path = root.joinpath(*PurePosixPath(relative).parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError('Release path escapes its root: ' + relative)
    return path


def metadata(path):
    digest = sha256_file(path)
    return {'bytes': Path(path).stat().st_size, 'sha256': digest}


def files_under(base, prefix):
    base = Path(base)
    if base.is_symlink() or not base.is_dir():
        raise ValueError('Release input must be a real directory: ' + str(base))
    result = {}
    for folder, dirs, names in os.walk(base, followlinks=False):
        for name in list(dirs):
            path = Path(folder) / name
            relative = path.relative_to(base)
            if (prefix == 'demos' and relative.parts[0] == 'media') or relative.parts[0] == '_download-parts':
                dirs.remove(name)
            elif path.is_symlink():
                raise ValueError('Unexpected directory symlink: ' + str(path))
        for name in names:
            path = Path(folder) / name
            relative = path.relative_to(base)
            if relative.parts[0] in {'_headers', '_download-parts'} or (prefix == 'demos' and relative.parts[0] == 'media'):
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError('Release input must be a regular file: ' + str(path))
            key = prefix + '/' + relative.as_posix()
            relative_path(key)
            result[key] = path
    return result


def records(path):
    catalog = json.loads(Path(path).read_text(encoding='utf8'))
    ids = [x['id'] for x in catalog['items']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate catalog IDs')
    return sorted(ids)


def record_hashes(path):
    catalog = json.loads(Path(path).read_text(encoding='utf8'))
    # Collection numbering is derived globally; adding one work can renumber hundreds.
    return {item['id']: hashlib.sha256(json.dumps({k: v for k, v in item.items() if k != 'caseNumber'}, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode('utf8')).hexdigest()
            for item in catalog['items']}


def inventory(release):
    release = Path(release).resolve(strict=True)
    sources = {}
    for name in ('site', 'demos', 'runtime'):
        sources.update(files_under(release / name, name))
    return {'version': 1, 'release': release.name,
            'files': {key: metadata(path) for key, path in sorted(sources.items())},
            'recordIds': records(release / 'site/data/catalog.json'),
            'recordHashes': record_hashes(release / 'site/data/catalog.json')}


def file_stats(release):
    """Detect changes to immutable inputs without reading old media bytes."""
    sources = {}
    for name in ('site', 'demos', 'runtime'):
        sources.update(files_under(Path(release) / name, name))
    result = {}
    for name, path in sorted(sources.items()):
        stat = path.stat()
        result[name] = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
    return result


def save_inventory(release, value, cache_dir):
    release = Path(release).resolve(strict=True)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / (release.name + '.json')
    temporary = target.with_suffix('.next.json')
    payload = {'root': str(release), 'inventory': value, 'stats': file_stats(release)}
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding='utf8')
    temporary.chmod(0o600)
    temporary.replace(target)


def cached_inventory(release, cache_dir):
    release = Path(release).resolve(strict=True)
    target = Path(cache_dir) / (release.name + '.json')
    if not target.exists():
        value = inventory(release)
        save_inventory(release, value, cache_dir)
        return value
    cached = json.loads(target.read_text(encoding='utf8'))
    if (cached['root'] != str(release) or cached['inventory']['release'] != release.name or
            cached['stats'] != file_stats(release)):
        raise ValueError('Live baseline changed since its verified inventory')
    return cached['inventory']


def verify_files(root, expected):
    for relative, row in expected.items():
        path = safe_file(root, relative)
        if path.is_symlink() or not path.is_file() or metadata(path) != row:
            raise ValueError('Release content mismatch: ' + relative)


def package(root, baseline, destination, *, include_runtime=True):
    root = Path(root)
    if baseline.get('version') != 1 or not baseline.get('files') or 'recordHashes' not in baseline:
        raise ValueError('A complete verified release inventory is required')
    sources = files_under(root / 'public-site', 'site')
    sources.update(files_under(root / 'public-demos', 'demos'))
    if include_runtime:
        sources['runtime/server.mjs'] = root / 'deploy-build/server.mjs'
    sources['site/downloads/pedalican.zip'] = root / 'pelican-web/repos/pedalican.zip'
    with cached_hashes(root/'deploy-build/local-file-hashes.json') as hash_cache:
        current = {name: metadata(path) for name, path in sorted(sources.items())}
    new_ids = records(root / 'public-site/data/catalog.json')
    new_hashes = record_hashes(root / 'public-site/data/catalog.json')
    if not set(baseline['recordIds']) <= set(new_ids):
        raise ValueError('Live catalog IDs are missing; synchronize additions before building')
    changed = {name: row for name, row in current.items() if baseline['files'].get(name) != row}
    removed = {}
    removal_list = json.loads((root / 'deploy-build/removed-public-pages.json').read_text(encoding='utf8'))
    for relative in removal_list:
        key = 'site/' + relative
        relative_path(key)
        if not relative.startswith(('specimens/', 'en/specimens/')) or PurePosixPath(relative).name not in {'index.html', 'index.md'}:
            raise ValueError('Only explicit removed specimen pages may be deleted')
        if key in current:
            raise ValueError('A generated page cannot also be removed: ' + relative)
        if key in baseline['files']:
            removed[key] = baseline['files'][key]
    expected = {**baseline['files'], **current}
    for key in removed:
        expected.pop(key)
    manifest = {'version': 1, 'baseline': baseline, 'changed': changed,
                'removed': removed, 'files': expected, 'recordIds': new_ids,
                'affectedRecords': sorted(key for key, value in new_hashes.items()
                    if baseline['recordHashes'].get(key) != value)}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    try:
        with tarfile.open(temporary, 'w:gz', compresslevel=3) as archive:
            for name, row in changed.items():
                # Copy/hash the same bytes to reject an input changing during packaging.
                source = sources[name]
                member = archive.gettarinfo(str(source), arcname=name)
                with source.open('rb') as stream:
                    archive.addfile(member, stream)
                if metadata(source) != row:
                    raise ValueError('Release input changed while packaging: ' + name)
            payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode('utf8')
            member = tarfile.TarInfo(MANIFEST)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {'archive': str(destination), 'changedFiles': len(changed),
            'removedPages': len(removed), 'payloadBytes': sum(x['bytes'] for x in changed.values()),
            'archiveBytes': destination.stat().st_size, 'baseRelease': baseline['release'],
            'hashing': hash_cache.stats}


def apply(archive_path, previous, target, *, cache_dir=None):
    previous = Path(previous).resolve(strict=True)
    target = Path(target)
    if target.exists() or target.is_symlink():
        raise ValueError('Target release must not exist')
    with tarfile.open(archive_path, 'r:gz') as archive:
        members = archive.getmembers()
        names = [x.name for x in members]
        if len(names) != len(set(names)) or names.count(MANIFEST) != 1 or any(not x.isfile() for x in members):
            raise ValueError('Delta archive must contain unique regular files and one manifest')
        manifest = json.load(archive.extractfile(MANIFEST))
        if manifest.get('version') != 1:
            raise ValueError('Unsupported release delta')
        baseline = manifest['baseline']
        actual = cached_inventory(previous, cache_dir) if cache_dir else inventory(previous)
        if previous.name != baseline['release'] or actual != baseline:
            raise ValueError('Live baseline changed; rebuild the delta instead of overwriting it')
        if set(names) != {MANIFEST, *manifest['changed']}:
            raise ValueError('Archive payload differs from its reviewed file manifest')
        expected = {**baseline['files'], **manifest['changed']}
        for name, row in manifest['removed'].items():
            relative_path(name)
            if not name.startswith(('site/specimens/', 'site/en/specimens/')) or PurePosixPath(name).name not in {'index.html', 'index.md'} or baseline['files'].get(name) != row or name in manifest['changed']:
                raise ValueError('Unsafe or unreviewed removed page')
            expected.pop(name)
        if manifest['files'] != expected:
            raise ValueError('Final release manifest drops or changes unlisted files')
        # Validate every uploaded byte before creating a candidate release.
        for name, row in manifest['changed'].items():
            relative_path(name)
            member = archive.getmember(name)
            with archive.extractfile(member) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if member.size != row['bytes'] or digest != row['sha256']:
                raise ValueError('Uploaded file hash mismatch: ' + name)
        # Immutable old files are shared. Every replacement uses a new inode,
        # preserving the previous release and avoiding a full media copy.
        shutil.copytree(previous, target, symlinks=True, copy_function=os.link)
        for name in manifest['changed']:
            path = safe_file(target, name)
            if path.is_symlink():
                raise ValueError('Cannot replace a release symlink: ' + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.delta-tmp')
            with archive.extractfile(name) as source, temporary.open('xb') as output:
                shutil.copyfileobj(source, output)
            temporary.replace(path)
        for name in manifest['removed']:
            safe_file(target, name).unlink()
        verify_files(target, manifest['changed'])
        if set(file_stats(target)) != set(manifest['files']):
            raise ValueError('Candidate file set differs from the reviewed manifest')
        if records(target / 'site/data/catalog.json') != manifest['recordIds'] or not set(baseline['recordIds']) <= set(manifest['recordIds']):
            raise ValueError('Delta must preserve all live record IDs')
        if cache_dir:
            save_inventory(target, {'version': 1, 'release': target.name,
                'files': manifest['files'], 'recordIds': manifest['recordIds'],
                'recordHashes': record_hashes(target / 'site/data/catalog.json')}, cache_dir)
        return {'changedFiles': len(manifest['changed']), 'verifiedFiles': len(manifest['changed']),
                'reusedFiles': len(manifest['files']) - len(manifest['changed']),
                'verifiedBytes': sum(row['bytes'] for row in manifest['changed'].values()),
                'release': str(target), 'baseRelease': previous.name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snapshot = commands.add_parser('inventory')
    snapshot.add_argument('--release-root', type=Path, required=True)
    snapshot.add_argument('--output', type=Path, required=True)
    snapshot.add_argument('--cache-dir', type=Path)
    pack = commands.add_parser('package')
    pack.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    pack.add_argument('--baseline', type=Path, required=True)
    pack.add_argument('--output', type=Path, required=True)
    pack.add_argument('--content-only', action='store_true')
    activate = commands.add_parser('apply')
    activate.add_argument('--archive', type=Path, required=True)
    activate.add_argument('--previous', type=Path, required=True)
    activate.add_argument('--target', type=Path, required=True)
    activate.add_argument('--cache-dir', type=Path)
    args = parser.parse_args()
    if args.command == 'inventory':
        result = cached_inventory(args.release_root, args.cache_dir) if args.cache_dir else inventory(args.release_root)
        args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True), encoding='utf8')
        result = {'release': result['release'], 'files': len(result['files']), 'output': str(args.output)}
    elif args.command == 'package':
        result = package(args.root, json.loads(args.baseline.read_text(encoding='utf8')), args.output,
                         include_runtime=not args.content_only)
    else:
        result = apply(args.archive, args.previous, args.target, cache_dir=args.cache_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
