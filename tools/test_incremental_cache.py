import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import hashlib

from check_incremental_cache import check_cache


class CanonicalCacheTests(unittest.TestCase):
    def test_stale_stable_url_fails_even_when_the_versioned_payload_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory)/'update.tar.gz'
            payload = b'{"counts":{"cases":1038}}'
            manifest = {'changed': {'site/data/catalog.json': {
                'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}}}
            data = json.dumps(manifest).encode()
            with tarfile.open(archive, 'w:gz') as output:
                member = tarfile.TarInfo('release-delta.json');member.size = len(data)
                output.addfile(member, io.BytesIO(data))
            class Response:
                headers = {'CF-Cache-Status': 'HIT', 'Age': '47384', 'Cache-Control': 'max-age=300'}
                def __enter__(self):return self
                def __exit__(self, *args):pass
                def read(self):return b'{"counts":{"cases":1022}}'
            with patch('check_incremental_cache.urllib.request.urlopen', return_value=Response()) as fetch:
                result = check_cache(archive)
            self.assertEqual(result['status'], 'cache-refresh-required')
            self.assertEqual(result['stale'][0]['url'], 'https://pelicanmap.aveniqa.com/data/catalog.json')
            self.assertNotIn('?v=', fetch.call_args.args[0].full_url)


if __name__ == '__main__':unittest.main()
