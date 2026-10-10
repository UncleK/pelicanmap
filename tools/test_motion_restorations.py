import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from motion_restorations import apply_restorations
from detail_presentation import apply_motion_previews, cover_media
from catalog_policy import apply_demo_policy


class MotionRestorationTests(unittest.TestCase):
    def test_source_module_hash_and_directory_boundary_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / 'demos/work/index.html'
            doc.parent.mkdir(parents=True)
            doc.write_bytes(b'<html>original host</html>')
            module = doc.with_name('original.js')
            module.write_bytes(b'export function render(t){}')
            item = {'id': 'work', 'sourceUrl': 'https://example.com/source'}
            review = {'work': {'reviewed': True, 'sourceUrl': item['sourceUrl'],
                'previewUrl': 'https://pelicanmap-demos.aveniqa.com/demos/work/',
                'sha256': hashlib.sha256(doc.read_bytes()).hexdigest(),
                'sourceArtifactPath': 'demos/work/original.js',
                'sourceArtifactSha256': hashlib.sha256(module.read_bytes()).hexdigest()}}
            self.assertEqual(apply_restorations([item], review, root)[0]['previewUrl'], review['work']['previewUrl'])
            module.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                apply_restorations([item], review, root)
            review['work']['sourceArtifactPath'] = '../outside.js'
            with self.assertRaises(ValueError):
                apply_restorations([item], review, root)

    def test_legacy_external_demo_does_not_clear_a_verified_local_animation(self):
        local = 'https://pelicanmap-demos.aveniqa.com/demos/work/'
        external = 'https://example.com/author-result'
        item = {'id': 'work', 'format': '3d', 'sourceUrl': 'https://example.com/source',
                'demoUrl': external, 'previewUrl': local}
        with patch('catalog_policy.apply_restorations', return_value=[copy.deepcopy(item)]), patch('catalog_policy.load_reviews', return_value={'work': {}}):
            result = apply_demo_policy([item], reviews={})[0]
        self.assertEqual(result['previewUrl'], local)
        self.assertEqual(result['demoSourceUrl'], external)
        self.assertEqual(result['demoUrl'], '')
        self.assertFalse(result['interactive'])

    def test_unreviewed_repository_gallery_does_not_replace_a_static_model_output(self):
        item = {'id': 'static-original', 'format': 'svg', 'sourceUrl': 'https://github.com/author/gallery',
                'previewUrl': 'https://pelicanmap-demos.aveniqa.com/demos/model-gallery/'}
        with patch('motion_restorations.load_reviews', return_value={}), patch('catalog_policy.load_reviews', return_value={}):
            result = apply_demo_policy([item], reviews={})[0]
        self.assertEqual(result['previewUrl'], '')
        self.assertFalse(result['interactive'])

    def test_complete_original_document_and_static_cover_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'demos/work/index.html'
            path.parent.mkdir(parents=True)
            original = b'<html><style>@keyframes wheel{to{transform:rotate(360deg)}}</style><svg class="wheel"></svg></html>'
            path.write_bytes(original)
            item = {'id': 'work', 'sourceUrl': 'https://github.com/author/work', 'format': 'svg',
                    'date': '2025-01-01', 'model': 'Source model', 'author': 'Author',
                    'title': 'Original output', 'thumbnail': '/media/poster.svg',
                    'media': [{'src': '/media/poster.svg'}]}
            review = {'work': {'reviewed': True, 'sourceUrl': item['sourceUrl'],
                'previewUrl': 'https://pelicanmap-demos.aveniqa.com/demos/work/',
                'sha256': hashlib.sha256(original).hexdigest()}}
            result = apply_restorations([item], review, root)[0]
            for key in item:
                self.assertEqual(result[key], item[key])
            self.assertEqual(path.read_bytes(), original)
            with patch('detail_presentation.load_reviews', return_value=review):
                result = apply_motion_previews([result], root)[0]
            self.assertEqual(result['motionPreview']['type'], 'iframe')
            self.assertIn('data-motion-src="'+review['work']['previewUrl']+'"', cover_media(result))
            self.assertIn('/media/poster.svg', cover_media(result))
            wrong = copy.deepcopy(review); wrong['work']['sourceUrl'] = 'https://github.com/another/work'
            with self.assertRaises(ValueError):
                apply_restorations([item], wrong, root)
            path.write_bytes(original + b'changed')
            with self.assertRaises(ValueError):
                apply_restorations([item], review, root)

    def test_review_cannot_target_an_external_or_missing_document(self):
        item = {'id': 'work', 'sourceUrl': 'https://example.com/source'}
        base = {'reviewed': True, 'sourceUrl': item['sourceUrl'], 'sha256': '0'*64}
        with tempfile.TemporaryDirectory() as root:
            for url in ['https://example.com/demos/work/',
                        'https://pelicanmap-demos.aveniqa.com/demos/missing/']:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    apply_restorations([item], {'work': {**base, 'previewUrl': url}}, root)


if __name__ == '__main__':
    unittest.main()
