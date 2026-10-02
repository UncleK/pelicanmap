"""Post-intake tests for nine explicitly reviewed pre-2026 source outputs."""
import hashlib
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from case_policy import apply_case_policy
from archival_test_assertions import reviewed_context_change
from prepare_nile_history import output_svg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pelican-archive/research/2026-10-01-nile-history'
MANIFEST = json.loads((OUT / 'approved-manifest.json').read_text(encoding='utf8'))
CAT = json.loads((ROOT / 'site/catalog.json').read_text(encoding='utf8'))
BY = {x['id']: x for x in CAT['items']}


class NileHistoryTests(unittest.TestCase):
    def test_nine_single_model_originals_and_timeline_mapping(self):
        self.assertEqual(len(MANIFEST['cases']), 9)
        for c in MANIFEST['cases']:
            x = BY[c['id']]
            self.assertEqual(x['modelNames'], [c['model']])
            self.assertEqual(x['date'], c['date'])
            self.assertLess(x['date'], '2026-01-01')
            self.assertTrue(x['caseVisible'] and x['timelineVisible'])
            self.assertFalse(x.get('referenceOnly') or x.get('interactive'))
            self.assertEqual(x['dateBasis'], c['dateBasis'])
            self.assertEqual(x['modelClaimStatus'], 'source-reported-not-independently-authenticated')
            self.assertEqual(x['thumbnail'], x['media'][0]['src'])
            self.assertEqual(x['sourceUrl'], c['sourceUrl'])

    def test_original_media_sha_and_final_response_not_reasoning_draft(self):
        for c in MANIFEST['cases']:
            x = BY[c['id']]
            self.assertEqual(len(x['media']), len(c['media']))
            for original, media in zip(c['media'], x['media']):
                path = ROOT / 'pelican-web' / media['src'].lstrip('/')
                data = path.read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), original['sha256'])
                if path.suffix == '.svg':
                    raw = OUT / 'evidence' / (hashlib.sha256(original['url'].encode()).hexdigest()[:16] + '.bin')
                    self.assertEqual(data, output_svg(raw.read_text(encoding='utf8')))
                    self.assertNotRegex(data.decode(), r'<(?:animate\w*|set|script)\b')
                else:
                    with Image.open(path) as image:
                        image.verify()

    def test_bilingual_details_source_previews_and_numbered_single_images(self):
        for c in MANIFEST['cases']:
            x = BY[c['id']]
            for prefix in ['', 'en/']:
                soup = BeautifulSoup((ROOT / 'public-site' / prefix / x['path'].lstrip('/') / 'index.html').read_text(encoding='utf8'), 'html.parser')
                self.assertEqual(soup.select('main img')[0]['src'], x['thumbnail'])
                self.assertIsNotNone(soup.find('a', href=c['sourceUrl']))
                self.assertIn(c['model'], soup.get_text())
                self.assertEqual(x['caseNumber'] > 0, True)
                if x['dateBasis'] == 'source-reported-response-timestamp':
                    self.assertIn('响应时间戳' if not prefix else 'response timestamp in the original log', soup.get_text())
                    self.assertNotIn('日期依据原文公开日', soup.get_text())

    def test_old_ids_sources_and_media_preserved_and_counts_not_sum(self):
        old = json.loads((OUT / 'before-published-catalog.json').read_text(encoding='utf8'))
        for previous in old['items']:
            current = BY[previous['id']]
            # Timeline eligibility is intentionally broadened by the latest
            # all-media authorization, not frozen to this static-only batch.
            for key in ['sourceUrl', 'date', 'model', 'caseVisible']:
                if reviewed_context_change(self,previous,current,key,BY):continue
                self.assertEqual(current[key], previous[key], (previous['id'], key))
            self.assertEqual(current['media'], previous['media'])
        self.assertEqual(CAT['counts']['cases'], sum(bool(x.get('caseVisible')) for x in CAT['items']))
        self.assertEqual(CAT['counts']['timeline'], sum(bool(x.get('timelineVisible')) for x in CAT['items']))
        self.assertGreaterEqual(CAT['counts']['cases'], old['counts']['cases'] + 9)
        self.assertGreaterEqual(CAT['counts']['timeline'], old['counts']['timeline'] + 9)
        self.assertEqual(CAT['counts']['referenceRecords'], old['counts']['referenceRecords'])
        self.assertEqual(CAT['items'], apply_case_policy(CAT['items'], ROOT / 'public-site'))


if __name__ == '__main__':
    unittest.main()
