import hashlib
from pathlib import Path
import tempfile
import unittest

from asset_versions import NAMES, asset_version


class AssetVersionTests(unittest.TestCase):
    def test_line_ending_only_migration_keeps_the_published_cache_key(self):
        with tempfile.TemporaryDirectory() as directory:
            source, published = Path(directory)/'source', Path(directory)/'published'
            source.mkdir();published.mkdir()
            for name in NAMES:
                (source/name).write_bytes(b'reviewed code\n')
                (published/name).write_bytes(b'reviewed code\r\n')
            expected = hashlib.sha256(b'reviewed code\r\n'*len(NAMES)).hexdigest()[:12]
            self.assertEqual(asset_version(source, published), expected)
            (source/'site.js').write_bytes(b'changed behavior\n')
            self.assertNotEqual(asset_version(source, published), expected)

    def test_first_build_uses_the_current_source_version(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source';source.mkdir()
            for name in NAMES:(source/name).write_bytes(b'code\n')
            expected = hashlib.sha256(b'code\n'*len(NAMES)).hexdigest()[:12]
            self.assertEqual(asset_version(source, Path(directory)/'missing'), expected)


if __name__ == '__main__':unittest.main()
