"""Post-intake acceptance: explicit labels, unchanged crops, same-work dedup."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'pelican-archive/research/2026-10-01-x-browser-batch'
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}
MANIFEST=json.loads((AUDIT/'approved-manifest.json').read_text(encoding='utf8'))

class XBrowserBatchTests(unittest.TestCase):
 def test_five_works_from_two_public_posts(self):
  records=[BY[c['id']] for c in MANIFEST['cases']]
  self.assertEqual(len(records),5)
  self.assertEqual(len({x['sourceUrl'] for x in records}),2)
  self.assertEqual({x['model'] for x in records},{'Opus 5','Opus 5.5','Sonnet 5','Sonnet 5.5','Claude Opus 5.5'})
  self.assertTrue(all(x['caseVisible'] and x['timelineVisible'] and not x['interactive'] and not x.get('referenceOnly') for x in records))
  self.assertTrue(all(x['date']=='2026-09-30' and x['dateBasis']=='source-publication' for x in records))
  jast=BY['x-jast-opus55-2026-09-30']
  self.assertEqual(len(jast['media']),3)
  self.assertEqual(jast['format'],'svg')
  self.assertTrue(jast['generationConditions']['animationPending'])

 def test_crop_pixels_hashes_and_complete_originals(self):
  assets=set()
  for c in MANIFEST['cases']:
   x=BY[c['id']];crop=x['cropProvenance']
   for m in x['media']:
    file=ROOT/'pelican-web'/m['src'].lstrip('/');assets.add(m['src'])
    self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),m['sha256'])
    with Image.open(file) as im:im.verify()
   with Image.open(ROOT/'pelican-web'/crop['original'].lstrip('/')) as original,Image.open(ROOT/'pelican-web'/crop['crop'].lstrip('/')) as actual:
    expected=original.crop(crop['box'])
    self.assertEqual(expected.size,actual.size)
    self.assertEqual(expected.tobytes(),actual.tobytes())
   self.assertTrue(all(m['detailOnly'] for m in x['media'][1:]))
   for prefix in ['', 'en/']:
    soup=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
    self.assertTrue(soup.find('img',src=crop['crop']))
    self.assertTrue(soup.find('img',src=crop['original']))
    self.assertTrue(soup.find('a',href=x['sourceUrl']))
  self.assertEqual(len(assets),8)

 def test_prior_records_and_counts_preserved(self):
  before=json.loads((AUDIT/'before-catalog.json').read_text(encoding='utf8'))
  self.assertGreaterEqual(CAT['counts']['cases'],before['counts']['cases']+5)
  self.assertGreaterEqual(CAT['counts']['timeline'],before['counts']['timeline']+5)
  self.assertEqual(CAT['counts']['referenceRecords'],before['counts']['referenceRecords'])
  for x in before['items']:
   for key in ['date','model','author','sourceUrl','media','thumbnail','caseVisible','timelineVisible']:
    self.assertEqual(x.get(key),BY[x['id']].get(key),(x['id'],key))

if __name__=='__main__':unittest.main()
