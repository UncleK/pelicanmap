"""Post-implementation acceptance of explicit original-source mappings."""
import hashlib,json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
from case_policy import apply_case_policy
from archival_test_assertions import reviewed_context_change, reviewed_motion_append

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'pelican-archive/research/2026-10-01-nile-late'
MANIFEST=json.loads((AUDIT/'approved-manifest.json').read_text(encoding='utf8'))
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}
ENTRIES=[BY[c['id']] for c in MANIFEST['cases']]

class NileLateTests(unittest.TestCase):
 def test_forty_four_outputs_thirty_two_representatives(self):
  self.assertEqual(len(ENTRIES),44)
  self.assertEqual(sum(x['caseVisible'] for x in ENTRIES),44)
  self.assertEqual(sum(x['timelineVisible'] for x in ENTRIES),32)
  self.assertEqual(sum(x['format']=='3d' for x in ENTRIES),15)
  self.assertEqual(sum(x['date']<'2026-01-01' for x in ENTRIES),40)
  self.assertTrue(all(not x.get('referenceOnly') and not x['interactive'] for x in ENTRIES))
  for c,x in zip(MANIFEST['cases'],ENTRIES):
   for key in ['model','sourceUrl','author','date','dateBasis']:
    self.assertEqual(c[key],x[key],(x['id'],key))
   self.assertEqual(x['modelNames'],[c['model']])
   self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')
   self.assertGreater(x['caseNumber'],0)

 def test_fifty_eight_original_files_and_fourteen_final_svgs(self):
  files=set();final_svgs=0
  for c,x in zip(MANIFEST['cases'],ENTRIES):
   self.assertEqual(len(c['media']),len(x['media']))
   self.assertEqual(x['thumbnail'],x['media'][0]['src'])
   self.assertTrue(all(m['detailOnly'] for m in x['media'][1:]))
   for original,m in zip(c['media'],x['media']):
    file=ROOT/'pelican-web'/m['src'].lstrip('/');files.add(m['src'])
    data=file.read_bytes()
    self.assertEqual(hashlib.sha256(data).hexdigest(),original['sha256'])
    self.assertEqual(m['sha256'],original['sha256'])
    if file.suffix=='.svg':
     self.assertEqual(ET.fromstring(data).tag,'{http://www.w3.org/2000/svg}svg')
     self.assertNotRegex(data.decode(),r'<(?:animate\w*|script|foreignObject)\b')
    else:
     with Image.open(file) as image:
      self.assertGreater(min(image.size),10);image.verify()
    if original.get('svgFromTranscript'):
     final_svgs+=1
     self.assertEqual(m['extraction']['kind'],'transcript-response')
  self.assertEqual(len(files),58)
  self.assertEqual(final_svgs,14)

 def test_source_dates_and_manual_feedback_not_repost_date(self):
  disabled=BY['simon-late-36-0-2025-09-20']
  enabled=BY['simon-late-36-1-2025-09-20']
  self.assertEqual(disabled['date'],'2025-09-21')
  self.assertEqual(enabled['date'],'2025-09-20')
  self.assertTrue(disabled['generationConditions']['manualXmlRepairByAuthor'])
  self.assertTrue(disabled['generationConditions']['previewOnly'])
  self.assertTrue(all(not m['src'].endswith('.svg') for m in disabled['media']))
  self.assertTrue(disabled['timelineVisible'] and enabled['timelineVisible'])
  for name,day in [('gpt5-1codex','2025-11-15'),('gpt5-1chat','2025-11-15'),('gpt5-1','2025-11-15'),('opus45','2025-11-25'),('gpt5-2','2025-12-12')]:
   x=BY[f'beetleb-pov-{name}-{day}']
   self.assertEqual(x['date'],day)
   self.assertEqual(x['dateBasis'],'source-reported-update-date')
   self.assertEqual(x['sourcePublicationDate'],'2025-10-25')
   self.assertEqual(x['generationConditions']['sourceUpdateDate'],day)
  for x in ENTRIES:
   if x['format']=='3d':
    self.assertTrue(x['generationConditions']['feedbackWorkflowReported'])
    self.assertEqual(x['generationConditions']['perModelIterationCount'],'not fully published')
    self.assertNotEqual(x['generationConditions'].get('oneShot'),True)
    self.assertEqual(x['generationConditions']['renderer'],'POV-Ray')
  codex=BY['simon-late-51-0-2025-11-19']
  self.assertFalse(BY['beetleb-pov-pro25-1-2025-10-25']['generationConditions']['visualFeedback'])
  self.assertTrue(BY['beetleb-pov-pro25-6-2025-10-25']['generationConditions']['visualFeedback'])
  flash=BY['beetleb-pov-flash25-2025-10-25']['generationConditions']
  self.assertTrue(flash['visualFeedbackReported'])
  self.assertEqual(flash['displayedIteration'],'not documented')
  self.assertNotIn('oneShot',flash)
  self.assertTrue(codex['timelineVisible'])
  self.assertEqual(codex['originalLevel'],'medium')
  self.assertEqual(BY['simon-late-51-1-2025-11-19']['representativeOf'],codex['id'])

 def test_bilingual_real_media_and_comparison_types(self):
  for x in ENTRIES:
   for prefix in ['', 'en/']:
    soup=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
    self.assertEqual(soup.html['lang'],'en' if prefix else 'zh-CN')
    self.assertTrue(soup.find('a',href=x['sourceUrl']))
    self.assertTrue(soup.find('img',src=x['thumbnail']))
    self.assertFalse(soup.select('iframe'))
    if x.get('modelRunGroup'):
     section=soup.select_one('[data-setting-comparison]')
     self.assertTrue(section)
     self.assertLess(str(soup).index('data-setting-comparison'),str(soup).index('class="detail-gallery"'))
     if x['comparisonType']=='visual-iterations':
      self.assertIn('visual-feedback iterations' if prefix else '视觉反馈迭代',section.get_text())
      self.assertIn('no timeline representative is guessed' if prefix else '不擅自挑一张',section.get_text())
     elif not any(BY[k]['timelineVisible'] for k in x['comparisonIds']):
      self.assertIn('no timeline representative is guessed' if prefix else '不擅自挑一张',section.get_text())
  for i in range(1,4):
   x=BY[f'sparkle-sonnet45-visual-v{i}-2026-02-15']
   self.assertEqual(x['model'],'Claude Sonnet 4.5')
   self.assertFalse(x['timelineVisible'])
   self.assertIn('MIT License',x['rights'])
   self.assertIn('Permission is hereby granted',x['i18n']['en']['rights'])
  gepa=BY['gepa-opus46-zeroshot-2026-02-18']
  self.assertEqual(gepa['generationConditions']['repositoryFirstPublicCommitDate'],'2026-02-19')
  self.assertTrue(gepa['generationConditions']['previewOnly'])

 def test_existing_metadata_media_and_references_preserved(self):
  before=json.loads((AUDIT/'before-catalog.json').read_text(encoding='utf8'))
  for old in before['items']:
   for key in old:
    if reviewed_context_change(self,old,BY[old['id']],key,BY):continue
    if reviewed_motion_append(self,old,BY[old['id']],key):continue
    if key in {'childIds','variantIds','comparisonIds'}:
     # A later, explicitly reviewed archive split may add relationships; it
     # must not remove old members or silently rewrite historical metadata.
     current=BY[old['id']].get(key,[])
     self.assertTrue(set(old[key])<=set(current),(old['id'],key))
     for ident in set(current)-set(old[key]):
      target=BY[ident]
      self.assertTrue(target['caseVisible'])
      if key=='childIds':self.assertEqual(target.get('parentId'),old['id'])
      elif key=='variantIds':self.assertEqual(target.get('representativeOf'),old['id'])
      else:self.assertEqual(target['modelNames'],BY[old['id']]['modelNames'])
    elif key!='caseNumber':self.assertEqual(old[key],BY[old['id']].get(key),(old['id'],key))
  self.assertGreaterEqual(CAT['counts']['cases'],before['counts']['cases']+44)
  self.assertGreaterEqual(CAT['counts']['timeline'],before['counts']['timeline']+32)
  self.assertEqual(CAT['counts']['referenceRecords'],before['counts']['referenceRecords'])
  self.assertEqual(CAT['items'],apply_case_policy(CAT['items'],ROOT/'public-site'))

if __name__=='__main__':unittest.main()
