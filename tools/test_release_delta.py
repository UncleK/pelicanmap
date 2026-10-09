import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import release_delta as delta


class ReleaseDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous = self.root / 'old'
        for name, data in {'site/data/catalog.json': '{"items":[{"id":"old"}]}',
                           'site/media/unchanged.mp4': 'large unchanged original',
                           'site/media/replaced.svg': 'old SVG',
                           'site/specimens/old/index.html': 'obsolete page',
                           'demos/demos/animation/index.html': 'old animation',
                           'runtime/server.mjs': 'old API'}.items():
            self.write(self.previous / name, data)
        self.baseline = delta.inventory(self.previous)
        self.source = self.root / 'workspace'
        for name, data in {'public-site/data/catalog.json': '{"items":[{"id":"old"},{"id":"new"}]}',
                           'public-site/media/unchanged.mp4': 'large unchanged original',
                           'public-site/media/replaced.svg': 'reviewed new SVG',
                           'public-site/media/new.mp4': 'new reviewed recording',
                           'public-demos/demos/animation/index.html': 'new reviewed animation',
                           'pelican-web/repos/pedalican.zip': 'preserved source ZIP',
                           'deploy-build/server.mjs': 'new API',
                           'deploy-build/removed-public-pages.json': '["specimens/old/index.html"]'}.items():
            self.write(self.source / name, data)
        self.archive = self.root / 'update.tar.gz'
        delta.package(self.source, self.baseline, self.archive)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf8')

    def test_only_changes_are_uploaded_and_previous_originals_survive(self):
        with tarfile.open(self.archive) as archive:
            self.assertNotIn('site/media/unchanged.mp4', archive.getnames())
        target = self.root / 'new'
        delta.apply(self.archive, self.previous, target)
        self.assertEqual((target/'site/media/new.mp4').read_text(), 'new reviewed recording')
        self.assertEqual((target/'site/media/replaced.svg').read_text(), 'reviewed new SVG')
        self.assertEqual((self.previous/'site/media/replaced.svg').read_text(), 'old SVG')
        self.assertEqual((target/'site/media/unchanged.mp4').read_text(), 'large unchanged original')
        self.assertFalse((target/'site/specimens/old/index.html').exists())

    def test_changed_baseline_is_rejected_before_creating_release(self):
        self.write(self.previous/'site/media/unchanged.mp4', 'parallel publication')
        with self.assertRaisesRegex(ValueError, 'baseline changed'):
            delta.apply(self.archive, self.previous, self.root/'new')
        self.assertFalse((self.root/'new').exists())

    def test_missing_local_old_media_is_retained_without_deleting_it(self):
        (self.source/'public-site/media/unchanged.mp4').unlink()
        delta.package(self.source, self.baseline, self.archive)
        delta.apply(self.archive, self.previous, self.root/'new')
        self.assertTrue((self.root/'new/site/media/unchanged.mp4').is_file())

    def test_removing_a_live_id_or_media_is_rejected(self):
        self.write(self.source/'public-site/data/catalog.json', '{"items":[{"id":"new"}]}')
        with self.assertRaisesRegex(ValueError, 'Live catalog IDs'):
            delta.package(self.source, self.baseline, self.archive)
        self.write(self.source/'public-site/data/catalog.json', '{"items":[{"id":"old"}]}')
        self.write(self.source/'deploy-build/removed-public-pages.json', '["media/unchanged.mp4"]')
        with self.assertRaisesRegex(ValueError, 'removed specimen pages'):
            delta.package(self.source, self.baseline, self.archive)

    def test_unlisted_or_tampered_payload_is_rejected(self):
        bad = self.root/'bad.tar.gz'
        with tarfile.open(self.archive) as original, tarfile.open(bad, 'w:gz') as output:
            for member in original.getmembers():
                data = original.extractfile(member).read()
                if member.name == 'site/media/new.mp4':
                    data = b'tampered'
                    member.size = len(data)
                output.addfile(member, io.BytesIO(data))
        with self.assertRaisesRegex(ValueError, 'Uploaded file hash'):
            delta.apply(bad, self.previous, self.root/'new')
        self.assertFalse((self.root/'new').exists())

    def test_traversal_paths_are_rejected(self):
        for path in ['../private/key', '/site/media/a', 'site/../../key', 'site\\media\\a', 'demos/media/a']:
            with self.assertRaises(ValueError):
                delta.relative_path(path)

    def test_metadata_corrections_are_checked_but_derived_number_changes_are_not(self):
        self.write(self.source/'public-site/data/catalog.json',
                   '{"items":[{"id":"old","caseNumber":9},{"id":"new"}]}')
        delta.package(self.source, self.baseline, self.archive)
        with tarfile.open(self.archive) as archive:
            self.assertEqual(json.load(archive.extractfile(delta.MANIFEST))['affectedRecords'], ['new'])
        self.write(self.source/'public-site/data/catalog.json',
                   '{"items":[{"id":"old","title":"corrected attribution"},{"id":"new"}]}')
        delta.package(self.source, self.baseline, self.archive)
        with tarfile.open(self.archive) as archive:
            self.assertEqual(json.load(archive.extractfile(delta.MANIFEST))['affectedRecords'], ['new', 'old'])


if __name__ == '__main__':
    unittest.main()
