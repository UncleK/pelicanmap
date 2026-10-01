"""Post-implementation regression for the bounded, source-reviewed Nile batch."""
import hashlib
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from case_policy import apply_case_policy

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'pelican-archive/research/2026-10-01-nile-early'
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}
MANIFEST=json.loads((ARCHIVE/'approved-manifest.json').read_text(encoding='utf8'))
GEMMA=['simon-gemma3n-ollama-2025-06-26','simon-gemma3n-mlx-2025-06-26']


class NileEarlyTests(unittest.TestCase):
    def test_three_original_previews_not_a_collection_or_benchmark(self):
        self.assertEqual(len(MANIFEST['cases']),3)
        for c in MANIFEST['cases']:
            x=BY[c['id']]
            self.assertTrue(x['caseVisible'])
            self.assertFalse(x.get('referenceOnly') or x.get('interactive'))
            self.assertEqual(x['format'],'svg')
            self.assertEqual(x['modelNames'],[c['model']])
            self.assertEqual(x['date'],c['date'])
            self.assertEqual(x['sourcePublicationDate'],c['date'])
            self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')
            self.assertEqual(len(x['media']),1)
            p=ROOT/'pelican-web'/x['media'][0]['src'].lstrip('/')
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),c['media'][0]['sha256'])
            with Image.open(p) as image:image.verify()

    def test_quantizations_are_not_reasoning_levels_or_a_guessed_representative(self):
        for ident in GEMMA:
            x=BY[ident]
            self.assertFalse(x['timelineVisible'])
            self.assertEqual(set(x['comparisonIds']),set(GEMMA))
            self.assertEqual(x['comparisonType'],'quantizations')
            for prefix,heading in [('', '同一模型 · 量化与运行环境对照'),('en/','Same model · quantizations and runtimes')]:
                soup=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                section=soup.select_one('[data-setting-comparison]')
                self.assertEqual(section.h2.get_text(),heading)
                self.assertEqual(len(section.select('figure')),2)
                images=soup.select('main img')
                self.assertTrue(all(i.find_parent('section',attrs={'data-setting-comparison':True})==section for i in images[:2]))
                self.assertEqual(images[2]['src'],x['thumbnail'])
        self.assertTrue(BY['simon-grok4-openrouter-2025-07-10']['timelineVisible'])

    def test_duplicate_mistral_is_not_a_fourth_work(self):
        excluded=MANIFEST['review']['excluded'][0]
        self.assertNotIn(excluded['id'],BY)
        self.assertTrue(BY[excluded['canonicalId']]['caseVisible'])
        self.assertEqual(BY[excluded['canonicalId']]['date'],'2025-06-21')

    def test_old_sources_media_and_policy_are_preserved(self):
        before=json.loads((ARCHIVE/'before-published-catalog.json').read_text(encoding='utf8'))
        for x in before['items']:
            current=BY[x['id']]
            self.assertEqual(current['sourceUrl'],x['sourceUrl'])
            self.assertTrue({m['src'] for m in x['media']} <= {m['src'] for m in current['media']})
        self.assertEqual(apply_case_policy(CAT['items'],ROOT/'public-site'),CAT['items'])
        self.assertEqual(CAT['counts']['cases'],sum(bool(x['caseVisible']) for x in CAT['items']))
        self.assertEqual(CAT['counts']['timeline'],sum(bool(x['timelineVisible']) for x in CAT['items']))


if __name__=='__main__':unittest.main()
