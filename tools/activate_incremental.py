"""Activate a reviewed content delta and changed publisher files under one lock."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import time
import urllib.request

from release_delta import apply, metadata


def publisher_path(root, name):
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or '\\' in name or
            path.as_posix() != name or len(path.parts) < 2 or
            path.parts[0] not in {'tools', 'site', 'pelican-web'}):
        raise ValueError('Unsafe publisher path: ' + name)
    result = Path(root).joinpath(*path.parts)
    if not result.resolve().is_relative_to(Path(root).resolve()) or result.is_symlink():
        raise ValueError('Publisher path escapes its root: ' + name)
    return result


def verify_payload(archive_path, expected):
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        if (len(members) != len(expected) or {x.name for x in members} != set(expected) or
                any(not x.isfile() for x in members)):
            raise ValueError('Publisher archive differs from the reviewed manifest')
        for member in members:
            with archive.extractfile(member) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if member.size != expected[member.name]['bytes'] or digest != expected[member.name]['sha256']:
                raise ValueError('Publisher payload hash mismatch: ' + member.name)


def validate_additions(catalog, additions, previous):
    ids = [x['id'] for x in additions]
    if len(ids) != len(set(ids)) or not set(ids) <= {x['id'] for x in catalog['items']}:
        raise ValueError('Duplicate or unpublished additions')
    if not {x['id'] for x in previous} <= set(ids):
        raise ValueError('Refusing to drop existing additions')


def atomic_bytes(path, data, mode=0o644, ownership=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.incremental-next')
    with temporary.open('xb') as stream:
        stream.write(data)
    temporary.chmod(mode)
    if ownership is not None:
        os.chown(temporary, *ownership)
    temporary.replace(path)


def switch(base, target, name):
    link = base / name
    if link.exists() or link.is_symlink():
        raise ValueError('An existing publication link protects ' + str(link))
    link.symlink_to(target)
    link.replace(base / 'current')


def healthy(counts, ids=()):
    queries = {'/api/v1/specimens?lang=zh&limit=1': counts['cases'],
               '/api/v1/specimens?lang=en&limit=1': counts['cases'],
               '/api/v1/timeline?lang=en&limit=1': counts['timeline']}
    for path, total in queries.items():
        request = urllib.request.Request('http://127.0.0.1:48670' + path,
            headers={'User-Agent': 'PelicanMap-Incremental-Health/1.0'})
        with urllib.request.urlopen(request, timeout=5) as response:
            if json.load(response).get('total') != total:
                raise ValueError('API catalog did not follow the release switch')
    for ident in ids:
        request = urllib.request.Request('http://127.0.0.1:48670/api/v1/specimens/' + ident,
            headers={'User-Agent': 'PelicanMap-Incremental-Health/1.0'})
        with urllib.request.urlopen(request, timeout=5) as response:
            if json.load(response).get('id') != ident:
                raise ValueError('Affected API record is missing')


def wait_healthy(counts, ids=()):
    for attempt in range(6):
        try:
            healthy(counts, ids)
            return
        except (OSError, ValueError):
            if attempt == 5:
                raise
            time.sleep(1)


def activate(stage, base=Path('/srv/pelicanmap'), *, api_unit=Path('/etc/systemd/system/pelicanmap-api.service')):
    import fcntl
    stage, base = Path(stage).resolve(strict=True), Path(base).resolve(strict=True)
    request = json.loads((stage / 'deployment.json').read_text(encoding='utf8'))
    publisher = base / 'publisher'
    state = base / 'state/additions.json'
    lock_path = base / 'state/publish.lock'
    inherited = os.environ.get('PELICANMAP_LOCK_HELD') == '1'
    if inherited and (os.fstat(9).st_ino, os.fstat(9).st_dev) != (lock_path.stat().st_ino, lock_path.stat().st_dev):
        raise ValueError('Inherited descriptor is not publish.lock')
    lock = os.fdopen(os.dup(9), 'a') if inherited else lock_path.open('a')
    with lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = (base / 'current').resolve(strict=True)
        if previous.parent != base / 'releases' or previous.name != request['baselineRelease']:
            raise ValueError('Current advanced; synchronize and rebuild the batch')
        if metadata(state)['sha256'] != request['additionsBeforeSha256']:
            raise ValueError('Online additions advanced; synchronize and rebuild the batch')
        for name, row in request['publisherChanges'].items():
            path = publisher_path(publisher, name)
            before = metadata(path) if path.is_file() else None
            if before != row['before']:
                raise ValueError('Installed publisher changed: ' + name)
        for name, row in request['packages'].items():
            if Path(name).name != name or metadata(stage / name) != row:
                raise ValueError('Uploaded package hash mismatch: ' + name)
        if 'gates.json' in request['packages']:
            gates = json.loads((stage/'gates.json').read_text(encoding='utf8'))
            reviewed = json.loads((stage/'reviewed-manifest.json').read_text(encoding='utf8'))
            if not gates or any(row['exitCode'] != 0 for row in gates) or reviewed.get('reviewed') is not True:
                raise ValueError('Affected gates or source review failed')
            if not {row['id'] for row in reviewed['cases']} <= set(request['affectedRecords']):
                raise ValueError('Reviewed outputs are absent from the affected release records')
        expected = {name: row['after'] for name, row in request['publisherChanges'].items()}
        verify_payload(stage / 'publisher-update.tar.gz', expected)
        old_state, stat = state.read_bytes(), state.stat()
        atomic_bytes(stage / 'additions-before.json', old_state, 0o600)
        additions = json.loads((stage / 'additions.json').read_text(encoding='utf8'))
        release = base / 'releases' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        report = apply(stage / 'pelicanmap-update.tar.gz', previous, release,
                       cache_dir=base / 'state/release-inventories')
        catalog = json.loads((release / 'site/data/catalog.json').read_text(encoding='utf8'))
        if catalog['counts'] != request['counts']:
            raise ValueError('Candidate counts differ from the reviewed batch')
        validate_additions(catalog, additions, json.loads(old_state))
        old_publisher = {}
        unit = Path(api_unit)
        old_unit = unit.read_bytes()
        unit_changed = False
        switched = False
        api_restarted = False
        try:
            atomic_bytes(state, json.dumps(additions, ensure_ascii=False).encode('utf8'),
                         0o640, (stat.st_uid, stat.st_gid))
            switch(base, release, 'current.next')
            switched = True
            # First prove that content follows current without a code restart.
            wait_healthy(catalog['counts'], request['affectedRecords'])
            with tarfile.open(stage / 'publisher-update.tar.gz') as archive:
                for member in archive.getmembers():
                    path = publisher_path(publisher, member.name)
                    old_publisher[member.name] = path.read_bytes() if path.is_file() else None
                    if old_publisher[member.name] is not None:
                        atomic_bytes(stage / 'publisher-before' / member.name, old_publisher[member.name], 0o600)
                    with archive.extractfile(member) as stream:
                        atomic_bytes(path, stream.read())
                    if metadata(path) != expected[member.name]:
                        raise ValueError('Installed publisher hash mismatch: ' + member.name)
            new_unit = (publisher / 'site/deploy/pelicanmap-api.service').read_bytes()
            unit_changed = new_unit != old_unit
            if unit_changed:
                if metadata(unit)['sha256'] != request['apiUnitBeforeSha256']:
                    raise ValueError('Installed API unit changed during publication')
                atomic_bytes(unit, new_unit)
                subprocess.run(['systemctl', 'daemon-reload'], check=True)
            if unit_changed or any(name.startswith('runtime/') for name in request['changedFiles']):
                subprocess.run(['systemctl', 'restart', 'pelicanmap-api.service'], check=True)
                api_restarted = True
            wait_healthy(catalog['counts'], request['affectedRecords'])
        except Exception:
            if switched:
                switch(base, previous, 'current.rollback')
            atomic_bytes(state, old_state, 0o640, (stat.st_uid, stat.st_gid))
            for name, data in old_publisher.items():
                path = publisher_path(publisher, name)
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_bytes(path, data)
            if unit_changed:
                atomic_bytes(unit, old_unit)
                subprocess.run(['systemctl', 'daemon-reload'], check=True)
            if api_restarted:
                subprocess.run(['systemctl', 'restart', 'pelicanmap-api.service'], check=True)
            wait_healthy(request['baselineCounts'])
            raise
        report.update(status='published', counts=catalog['counts'],
                      publisherFilesChanged=len(expected), apiRestarted=api_restarted,
                      apiUnitChanged=unit_changed, serverRebuilt=False)
        try:
            import sys
            sys.path.insert(0, str(publisher / 'tools'))
            from release_retention import prune_releases
            report['retention'] = prune_releases(base)
        except Exception as error:
            report['retentionDeferred'] = str(error)
        atomic_bytes(stage / 'activation-report.json', json.dumps(report, indent=2).encode(), 0o600)
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(activate(args.stage), ensure_ascii=False, indent=2))
