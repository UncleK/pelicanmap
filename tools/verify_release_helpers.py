"""Run focused activation regression once for each exact helper/test version."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FILES = ('release_delta.py', 'activate_incremental.py', 'content_cache.py',
         'test_release_delta.py', 'test_incremental_activation.py', 'verify_release_helpers.py')


def verify(stage, state):
    stage, state = Path(stage), Path(state)
    state.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(''.join(hashlib.sha256((stage/name).read_bytes()).hexdigest()
        for name in FILES).encode()).hexdigest()
    with (state/'publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt = state/'release-helper-tests.json'
        previous = json.loads(receipt.read_text()) if receipt.exists() else {}
        if previous.get('sha256') == digest and previous.get('status') == 'passed':
            return {**previous, 'reused': True}
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', str(stage), '-p', 'test_*.py'], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('Release helper regression failed: '+(result.stdout+result.stderr)[-2500:])
        value = {'status': 'passed', 'sha256': digest, 'reused': False, 'log': result.stdout+result.stderr}
        temporary = receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(value)+'\n')
        temporary.replace(receipt)
        return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--state', type=Path, default=Path('/srv/pelicanmap/state'))
    args = parser.parse_args()
    print(json.dumps(verify(args.stage, args.state)))
