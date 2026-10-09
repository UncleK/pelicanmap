"""Verify copied maintenance inputs without changing files or printing contents."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def verify(manifest, root):
    root = Path(root).resolve()
    errors = []
    for row in manifest['files']:
        path = (root / row['path']).resolve()
        if not path.is_relative_to(root):
            errors.append({'path': row['path'], 'error': 'unsafe path'})
            continue
        if not path.is_file():
            errors.append({'path': row['path'], 'error': 'missing'})
            continue
        if path.stat().st_size != row['bytes']:
            errors.append({'path': row['path'], 'error': 'size mismatch'})
            continue
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != row['sha256']:
            errors.append({'path': row['path'], 'error': 'hash mismatch'})
    expected = manifest.get('gitCommit')
    if expected:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                capture_output=True, text=True, check=False)
        if result.returncode or result.stdout.strip() != expected:
            errors.append({'path': '.git', 'error': 'checkout differs from handoff commit'})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf8'))
    errors = verify(manifest, args.root)
    print(json.dumps({'checkedFiles': len(manifest['files']), 'errors': errors},
                     ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
