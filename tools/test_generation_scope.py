"""The scope follows generated code, not the presentation media extension."""
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from generation_scope import DIRECT_VIDEO_IDS, is_direct_video, require_code_generation

ROOT=Path(__file__).resolve().parents[1]

class GenerationScopeTests(unittest.TestCase):
    def test_new_intake_requires_code_proof(self):
        require_code_generation('code-generated',['https://example.com/original-code'],'Claude')
        for method,evidence,model in [(None,[], 'Claude'),('direct-text-to-video',['https://example.com'],'Veo 2'),
                ('code-generated',[],'Claude'),('code-generated',['file:///private'],'Claude'),
                ('code-generated',['https://example.com'],'Sora')]:
            with self.assertRaises(ValueError):require_code_generation(method,evidence,model)

    def test_extension_does_not_classify_workflow(self):
        for kind in ('video','animation','3d','interactive','svg'):
            self.assertFalse(is_direct_video({'id':'code-work','format':kind,'model':'Claude','media':[{'src':'/x.mp4'}]}))
        self.assertFalse(is_direct_video({'id':'unknown-legacy','model':'Veo 2'}))
        self.assertTrue(is_direct_video({'id':'reviewed','generationMethod':'direct-text-to-video'}))

    def test_reviewed_direct_video_is_preserved_context(self):
        catalog=json.loads((ROOT/'site/catalog.json').read_text('utf-8'))
        items={x['id']:x for x in catalog['items']}
        for identifier in DIRECT_VIDEO_IDS:
            row=items[identifier]
            self.assertEqual(row['generationMethod'],'direct-text-to-video')
            self.assertEqual(row['caseRole'],'context')
            self.assertFalse(row['caseVisible']);self.assertFalse(row['timelineVisible'])
            self.assertIsNone(row.get('caseNumber'))
            self.assertTrue(row['media']);self.assertTrue(row['sourceUrl']);self.assertTrue(row['date'])
        self.assertFalse(any(x['id'].startswith('simon-veo2-output-') for x in catalog['items']))
        self.assertEqual(catalog['counts']['cases'],sum(bool(x.get('caseVisible')) for x in catalog['items']))
        self.assertEqual(catalog['counts']['timeline'],sum(bool(x.get('timelineVisible')) for x in catalog['items']))

    def test_sitemap_does_not_publish_withdrawn_outputs(self):
        root=ET.parse(ROOT/'public-site/sitemap.xml').getroot()
        locations=[x.text for x in root.findall('{*}url/{*}loc')]
        self.assertFalse(any('simon-veo2-output-' in x for x in locations))
        for url in locations:
            path=url.removeprefix('https://pelicanmap.aveniqa.com').lstrip('/')
            self.assertTrue((ROOT/'public-site'/path/'index.html').is_file(),url)

if __name__=='__main__':unittest.main()
