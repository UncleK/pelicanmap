"""Preserve two source-labelled 2025 SVG outputs without inventing source code."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AiWartsHistory(unittest.TestCase):
 def test_independent_original_previews(self):
  cat=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
  records=[x for x in cat['items'] if x['id'] in {'x-aiwarts-ring-1t-svg-2025-10-14','x-aiwarts-deepseek-v3-2-svg-2025-10-14'}]
  self.assertEqual(len(records),2);self.assertEqual({x['model'] for x in records},{'Ring-1T','DeepSeek V3.2'})
  self.assertEqual({x['generationConditions']['sourceImagePosition'] for x in records},{'left','right'})
  self.assertEqual(len({x['media'][0]['sha256'] for x in records}),2)
  for x in records:
   with self.subTest(id=x['id']):
    self.assertTrue(x['caseVisible']);self.assertTrue(x['timelineVisible']);self.assertFalse(x.get('referenceOnly',False))
    self.assertEqual(x['date'],'2025-10-14');self.assertEqual(x['dateBasis'],'source-publication')
    self.assertEqual(x['generationConditions']['sourcePublicationTimestamp'],'2025-10-14T15:44:07.000Z')
    self.assertTrue(x['generationConditions']['generationDateUnknown']);self.assertTrue(x['generationConditions']['staticPreviewOnly'])
    self.assertEqual(x['generationMethod'],'code-generated');self.assertEqual(x['codeGenerationEvidence'],[x['sourceUrl']])
    self.assertFalse(x['demoUrl']);self.assertFalse(x['sourceCodeUrl']);self.assertFalse(x.get('motionPreview'))
    self.assertEqual(len(x['media']),1);self.assertEqual(x['thumbnail'],x['media'][0]['src'])
    self.assertIn('未取得原 SVG',x['notes']);self.assertIn('no open licence',x['i18n']['en']['rights'].lower())
    m=x['media'][0];self.assertEqual(hashlib.sha256((ROOT/'pelican-web'/m['src'].lstrip('/')).read_bytes()).hexdigest(),m['sha256'])
if __name__=='__main__':unittest.main()
