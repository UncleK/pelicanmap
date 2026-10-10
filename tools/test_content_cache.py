import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from content_cache import cached_hashes, sha256_file


class ContentCacheTests(unittest.TestCase):
    def test_warm_cache_does_not_read_unchanged_bytes_and_detects_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);path = root/'media.bin';cache_path = root/'cache.json'
            path.write_bytes(b'old-media')
            with cached_hashes(cache_path) as cache:before = sha256_file(path)
            self.assertEqual(cache.stats['readFiles'], 1)
            with patch('content_cache.hashlib.file_digest', side_effect=AssertionError('old bytes reread')):
                with cached_hashes(cache_path) as cache:self.assertEqual(sha256_file(path), before)
            self.assertEqual(cache.stats['readFiles'], 0)
            stamp = path.stat()
            replacement = root/'replacement';replacement.write_bytes(b'new-media');replacement.replace(path)
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            with cached_hashes(cache_path) as cache:self.assertNotEqual(sha256_file(path), before)
            self.assertEqual(cache.stats['readFiles'], 1)

    def test_input_change_during_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);path = root/'file';path.write_bytes(b'content')
            real = __import__('hashlib').file_digest
            def race(stream, algorithm):
                value = real(stream, algorithm)
                path.write_bytes(b'new-content')
                return value
            with cached_hashes(root/'cache.json'), patch('content_cache.hashlib.file_digest', side_effect=race):
                with self.assertRaisesRegex(ValueError, 'changed while hashing'):sha256_file(path)


if __name__ == '__main__':unittest.main()
