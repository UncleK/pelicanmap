"""Keep three Pelican Map releases. Call prune_releases only under publish.lock."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil

BASE = Path('/srv/pelicanmap')
KEEP = 3
RELEASE_NAME = re.compile(r'^(\d{8}T\d{6})(\d{6})?Z(?:-auto)?$')


def release_time(path):
    match = RELEASE_NAME.fullmatch(path.name)
    if not match:
        return None
    return dt.datetime.strptime(match[1] + (match[2] or '000000'), '%Y%m%dT%H%M%S%f')


def plan_releases(base=BASE):
    base = Path(base).resolve(strict=True)
    releases = base / 'releases'
    if releases.is_symlink() or not releases.is_dir():
        raise ValueError('Release root must be a real directory')
    current = (base / 'current').resolve(strict=True)
    if current.parent != releases or not (current / 'site/data/catalog.json').is_file():
        raise ValueError('Current release is outside the release root or incomplete')
    candidates = []
    ignored = []
    for path in releases.iterdir():
        if path.is_symlink() or not path.is_dir() or release_time(path) is None:
            ignored.append(path.name)
        else:
            candidates.append(path)
    candidates.sort(key=lambda path: (release_time(path), path.name), reverse=True)
    if current not in candidates:
        raise ValueError('Current release has an unrecognized name')
    # A rollback must never cause the serving release to be deleted.
    kept = [current] + [path for path in candidates if path != current][:KEEP - 1]
    removed = [path for path in candidates if path not in kept]
    for link in base.glob('current.*'):
        if link.is_symlink() and link.resolve() in removed:
            raise ValueError('A pending or rollback link protects ' + link.name)
    # Also protect a service still running from an older release after a switch.
    proc = Path('/proc')
    if proc.exists():
        for process in proc.iterdir():
            if not process.name.isdigit():
                continue
            for name in ('cwd', 'exe'):
                try:
                    target = (process / name).resolve(strict=True)
                except (OSError, RuntimeError):
                    continue
                if any(target == path or path in target.parents for path in removed):
                    raise ValueError('A running process still uses a retired release: ' + process.name)
    # Reject mounted subtrees; rmtree does not follow media symlinks.
    for path in removed:
        if path.resolve(strict=True).parent != releases or os.path.ismount(path):
            raise ValueError('Unsafe release target: ' + str(path))
        for root, dirs, _ in os.walk(path, followlinks=False):
            if any(os.path.ismount(Path(root) / name) for name in dirs):
                raise ValueError('Mounted subtree inside release: ' + str(path))
    return base, current, kept, removed, ignored


def prune_releases(base=BASE, *, dry_run=False):
    base, current, kept, removed, ignored = plan_releases(base)
    before = shutil.disk_usage(base).free
    report = {
        'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'keep': KEEP,
        'current': current.name, 'kept': [path.name for path in kept],
        'removed': [], 'planned': [path.name for path in removed],
        'ignored': ignored, 'dryRun': dry_run, 'freeBytesBefore': before,
    }
    if not dry_run:
        for path in removed:
            # Recheck just before deletion even though all publishers share the lock.
            if path.is_symlink() or path.resolve(strict=True).parent != base / 'releases':
                raise ValueError('Release target changed: ' + str(path))
            if (base / 'current').resolve(strict=True) != current:
                raise ValueError('Current changed without the publication lock')
            shutil.rmtree(path)
            report['removed'].append(path.name)
    report['freeBytesAfter'] = shutil.disk_usage(base).free
    report['freedBytes'] = report['freeBytesAfter'] - before
    if not dry_run:
        state = base / 'state'
        state.mkdir(exist_ok=True)
        temp = state / 'release-retention.next.json'
        temp.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
        temp.replace(state / 'release-retention.json')
    return report


def main():
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--lock-fd', type=int)
    args = parser.parse_args()
    lock_path = BASE / 'state/publish.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if args.lock_fd is not None:
        held, expected = os.fstat(args.lock_fd), os.stat(lock_path)
        if (held.st_dev, held.st_ino) != (expected.st_dev, expected.st_ino):
            raise ValueError('Inherited descriptor is not publish.lock')
        fcntl.flock(args.lock_fd, fcntl.LOCK_EX)
        report = prune_releases(dry_run=args.dry_run)
    else:
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            report = prune_releases(dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
