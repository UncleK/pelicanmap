"""Historical code-generated intake: actual units, iterations and original pixels."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];PREFIX='/media/collected/2026-10-03-historical-intensive/'
class HistoricalIntensiveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.items=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))['items'];cls.rows=[x for x in cls.items if any(m['src'].startswith(PREFIX) for m in x['media'])]
 def test_actual_units_and_scope(self):
  self.assertEqual(len(self.rows),44);self.assertEqual(sum(x['caseVisible'] for x in self.rows),44);self.assertEqual(sum(x['timelineVisible'] for x in self.rows),41)
  self.assertEqual(sum(x['date'].startswith('2024') for x in self.rows),1);self.assertEqual(sum(x['date'].startswith('2025') for x in self.rows),43)
  for x in self.rows:
   self.assertEqual(x['generationMethod'],'code-generated');self.assertTrue(x['codeGenerationEvidence']);self.assertFalse(x.get('referenceOnly',False));self.assertFalse(x['demoUrl'])
   self.assertEqual(x['date'],x['sourcePublicationDate']);self.assertTrue(x['generationConditions']['generationDateUnknown']);self.assertNotEqual(x['date'],x['updated'])
 def test_visual_iteration_is_one_work_per_run(self):
  rows=[x for x in self.rows if x['id'].startswith('youngbrioche-')];self.assertEqual(len(rows),13);self.assertEqual(sum(len(x['media']) for x in rows),67)
  for x in rows:
   self.assertEqual(x['generationConditions']['workflow'],'visual-agent-iteration');self.assertEqual(len(x['media']),x['generationConditions']['iterationPreviewCount']);self.assertTrue(all(m['detailOnly'] for m in x['media'][1:]))
   if x.get('modelRunGroup'):self.assertEqual(x['timelineVisible'],x['originalLevel']=='medium')
   self.assertIn('/blob/b49f0ae9ab773910ad477d896433a0f0eee20e2b/',x['sourceCodeUrl'])
  gemini=next(x for x in rows if x['model']=='Gemini 3 Pro');self.assertIn('pelican_v10.jpg',gemini['media'][0]['src'])
 def test_original_bytes_and_faithful_crops(self):
  assets={m['src']:m['sha256'] for x in self.rows for m in x['media']};self.assertEqual(len(assets),105)
  for src,sha in assets.items():
   p=ROOT/'pelican-web'/src.lstrip('/');self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),sha)
   with Image.open(p) as im:im.load();self.assertGreater(im.width,50);self.assertGreater(im.height,50)
  for x in self.rows:
   if not x.get('cropProvenance'):continue
   crop=x['cropProvenance'];self.assertTrue(crop['decodedPixelsMatch']);self.assertTrue(x['media'][1]['detailOnly'])
   with Image.open(ROOT/'pelican-web'/crop['original'].lstrip('/')) as original,Image.open(ROOT/'pelican-web'/crop['crop'].lstrip('/')) as panel:
    self.assertIsNone(ImageChops.difference(original.convert('RGB').crop(crop['box']),panel.convert('RGB')).getbbox())
 def test_bilingual_pages_and_default_comparisons(self):
  for x in self.rows:
   for lang in ['', 'en/']:
    page=(ROOT/'public-site'/lang/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8');self.assertIn(x['media'][0]['src'],page);self.assertIn(x['sourceUrl'],page);self.assertIn('detail-layout',page)
    if x.get('modelRunGroup'):self.assertLess(page.index('data-setting-comparison'),page.index('detail-layout'))
    for m in x['media'][1:]:self.assertIn(m['src'],page)
if __name__=='__main__':unittest.main()
