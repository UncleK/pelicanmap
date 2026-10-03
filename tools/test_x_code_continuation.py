"""Published author-labelled SVG effort panels: source facts, pixels and units."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageChops

ROOT=Path(__file__).resolve().parents[1]
BATCH='2026-10-03-x-code-continuation'
PREFIX='/media/collected/'+BATCH
IDS=['x-kevin-opus-'+model+'-'+effort+'-2026-09-23' for model in ['5-5','5'] for effort in ['low','medium','high','max']]
SOURCE='https://x.com/KevinShengHui/status/2102748654713086397'
ORIGINAL_SHA='0d76ac57b6fdc8e012b0f57e0f660f879e30d2d184d6295ab25dc266ce38df28'

class XCodeContinuationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.catalog=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
  cls.items={x['id']:x for x in cls.catalog['items']}
 def test_units_and_defaults(self):
  rows=[self.items[id] for id in IDS]
  self.assertEqual(sum(x['caseVisible'] for x in rows),8)
  self.assertEqual({x['id'] for x in rows if x['timelineVisible']},{IDS[1],IDS[6]})
  for x in rows:
   self.assertEqual(x['generationMethod'],'code-generated')
   self.assertIn(SOURCE,x['codeGenerationEvidence'])
   self.assertEqual(x['sourceUrl'],SOURCE)
   self.assertEqual(x['date'],'2026-09-23')
   self.assertEqual(x['sourcePublicationDate'],'2026-09-23')
   self.assertEqual(x['dateBasis'],'source-publication')
   self.assertEqual(x['datePrecision'],'day')
   self.assertEqual(x['unitType'],'single-model-output')
   self.assertEqual(len(x['comparisonIds']),4)
   self.assertEqual(x['generationConditions']['reportedRunsPerSetting'],3)
   self.assertEqual(x['generationConditions']['publishedOutputsPerSetting'],1)
   self.assertTrue(x['generationConditions']['sourceRunIndexUnknown'])
   self.assertFalse(x.get('referenceOnly',False))
   self.assertFalse(x.get('demoUrl'))
   self.assertFalse(x.get('sourceCodeUrl'))
 def test_original_pixels_and_hashes(self):
  original=ROOT/'pelican-web'/PREFIX.lstrip('/')/'kevin-pelican-ladder-original.jpg'
  self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),ORIGINAL_SHA)
  image=Image.open(original).convert('RGB')
  self.assertEqual(image.size,(3570,1900))
  for id in IDS:
   x=self.items[id];crop=x['cropProvenance'];media=x['media']
   self.assertEqual(crop['sourceSha256'],ORIGINAL_SHA)
   self.assertTrue(crop['decodedPixelsMatch'])
   self.assertEqual(len(media),2)
   self.assertFalse(media[0].get('detailOnly',False))
   self.assertTrue(media[1]['detailOnly'])
   self.assertEqual(media[1]['src'],PREFIX+'/kevin-pelican-ladder-original.jpg')
   file=ROOT/'pelican-web'/media[0]['src'].lstrip('/')
   self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),crop['cropSha256'])
   pixels=Image.open(file).convert('RGB')
   self.assertIsNone(ImageChops.difference(image.crop(crop['box']),pixels).getbbox())
   self.assertEqual(pixels.size,(784,588))
 def test_bilingual_detail_order(self):
  for id in IDS:
   x=self.items[id]
   for lang in ['', 'en/']:
    page=(ROOT/'public-site'/lang/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
    self.assertIn('Claude Code 2.1.280',page)
    self.assertIn('source-image-crop',json.dumps(x))
    self.assertLess(page.index('data-setting-comparison'),page.index('detail-layout'))
    self.assertIn(x['media'][1]['src'],page)
    self.assertIn(SOURCE,page)

if __name__=='__main__':unittest.main()
