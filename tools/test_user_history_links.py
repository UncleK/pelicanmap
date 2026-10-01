"""Regression checks for the reviewed URL batch, after implementation."""
import hashlib
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'pelican-archive/research/2026-10-01-user-history-links'
CAT=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in CAT['items']}
MANIFEST=json.loads((ARCHIVE/'approved-manifest.json').read_text(encoding='utf8'))


class HistoryLinkTests(unittest.TestCase):
    def test_reviewed_static_outputs_and_original_hashes(self):
        self.assertEqual(len(MANIFEST['cases']),38)
        for c in MANIFEST['cases']:
            x=BY[c['id']]
            self.assertTrue(x['caseVisible'])
            self.assertFalse(x.get('referenceOnly') or x.get('interactive'))
            self.assertEqual(x['format'],'svg')
            self.assertEqual(x['modelNames'],[c['model']])
            self.assertEqual(x['date'],c['date'])
            self.assertLess(x['date'],'2026-09')
            path=ROOT/'pelican-web'/x['media'][0]['src'].lstrip('/')
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),c['media'][0]['sha256'])
            if path.suffix=='.svg':
                self.assertEqual(path.read_bytes(),(ARCHIVE/'staged'/path.name).read_bytes())
            else:
                with Image.open(path) as image:image.verify()
            self.assertEqual(x['modelClaimStatus'],'source-reported-not-independently-authenticated')

    def test_invalid_and_duplicate_candidates_not_imported(self):
        for r in MANIFEST['review']['excluded']:
            self.assertNotIn(r['id'],BY)
        self.assertFalse(BY['x-1856712797054447970-52885a83']['caseVisible'])
        self.assertEqual(BY['x-1856712797054447970-52885a83']['canonicalId'],'zoo-qwen-pelican-90951e0b')
        self.assertEqual(BY['zoo-qwen-pelican-90951e0b']['date'],'2024-11-12')
        self.assertEqual(BY['zoo-qwen-pelican-90951e0b']['model'],'qwen2.5-coder:32b')
        # Later approved batches may grow the archive; these are live counts,
        # not the frozen totals of this historical release.
        self.assertEqual(CAT['counts']['cases'],sum(bool(x.get('caseVisible')) and not x.get('referenceOnly') for x in CAT['items']))
        self.assertEqual(CAT['counts']['timeline'],sum(bool(x.get('timelineVisible')) for x in CAT['items']))

    def test_groups_retain_every_valid_output_but_only_one_representative(self):
        hard=[BY[c['id']] for c in MANIFEST['cases'] if c['id'].startswith('hardprompts-')]
        self.assertEqual(len(hard),23)
        self.assertEqual(sum(x['timelineVisible'] for x in hard),6)
        self.assertEqual({x['originalLevel'] for x in hard if x['timelineVisible']},{'run 4'})
        for x in hard:
            self.assertEqual(x['comparisonType'],'repeat-runs')
            self.assertEqual(x['dateBasis'],'source-reported-response-timestamp')
            self.assertFalse(x.get('sourcePublicationDate'))
            self.assertEqual(x['sourceResponseTimestamp'][:10],x['date'])
            self.assertEqual(len(x['comparisonIds']),3 if x['model']=='gemini-2.5-pro' else 4)
            for prefix,text in [('', '同一模型 · 多次独立输出'),('en/','Same model · independent runs')]:
                page=BeautifulSoup((ROOT/'public-site'/prefix/x['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertEqual(page.select_one('[data-setting-comparison] h2').get_text(),text)
        qwen=[BY[c['id']] for c in MANIFEST['cases'] if c['id'].startswith('simon-qwen38-flash-next-')]
        self.assertEqual(len(qwen),8)
        self.assertEqual([x['id'] for x in qwen if x['timelineVisible']],['simon-qwen38-flash-next-ud-q2-k-xl-medium'])
        self.assertTrue(BY['history-5b61866c-0-0']['timelineVisible'])
        self.assertFalse(BY['simon-gemini-flash-budget-zero-2025-05-20']['timelineVisible'])

    def test_existing_comparison_is_split_not_an_extra_run(self):
        parent=BY['x-2083342783071621224-719f9758']
        self.assertFalse(parent['caseVisible'])
        self.assertEqual(len(parent['childIds']),2)
        children=[BY[k] for k in parent['childIds']]
        self.assertEqual({x['date'] for x in children},{'2026-07-31'})
        self.assertEqual([x['originalLevel'] for x in children if x['timelineVisible']],['default'])
        self.assertTrue(all(x['sourceUrl']=='https://simonwillison.net/2026/Jul/31/deepseek-v4-flash-0731/' for x in children))

    def test_previously_published_ids_and_original_media_are_preserved(self):
        baseline=json.loads((ARCHIVE/'before-published-catalog.json').read_text(encoding='utf8'))
        self.assertEqual(baseline['counts']['cases'],700)
        for old in baseline['items']:
            current=BY[old['id']]
            self.assertEqual(current['sourceUrl'],old['sourceUrl'])
            self.assertTrue({m['src'] for m in old['media']}<={m['src'] for m in current['media']})
            self.assertTrue((ROOT/'public-site'/current['path'].lstrip('/')/'index.html').is_file())


if __name__=='__main__':unittest.main()
