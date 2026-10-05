"""Regression for the source-reviewed, MIT-licensed 2025 Nebius outputs."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = '2026-10-05-nebius-historical'


class NebiusHistory(unittest.TestCase):
    def test_original_units_dates_and_permission(self):
        catalog = json.loads((ROOT / 'site/catalog.json').read_text(encoding='utf8'))
        records = [x for x in catalog['items'] if x['id'].startswith('nebius-')]
        self.assertEqual(len(records), 11)
        self.assertEqual(sum(x['timelineVisible'] for x in records), 3)
        self.assertEqual({x['date'] for x in records}, {'2025-08-05', '2025-08-07', '2025-08-08'})
        self.assertEqual(len({x['model'] for x in records}), 7)
        license_path = '/media/collected/' + BATCH + '/LICENSE.txt'
        notice = (ROOT / 'pelican-web' / license_path.lstrip('/')).read_bytes()
        self.assertEqual(hashlib.sha256(notice).hexdigest(), '7ad744bf9ec35d79134525a6dca8fe4a4b942c67252d91048406cd3048e0f4a8')
        hashes = set()
        for record in records:
            with self.subTest(id=record['id']):
                self.assertTrue(record['caseVisible'])
                self.assertFalse(record.get('referenceOnly', False))
                self.assertEqual(record['generationMethod'], 'code-generated')
                self.assertEqual(record['unitType'], 'single-model-output')
                self.assertEqual(record['dateBasis'], 'source-publication')
                self.assertTrue(record['generationConditions']['generationDateUnknown'])
                self.assertTrue(record['generationConditions']['effortUnknown'])
                self.assertIn('github.com/nebius/token-factory-cookbook/blob/', record['sourceUrl'])
                self.assertEqual(len(record['codeGenerationEvidence']), 2)
                self.assertEqual(record['sourceCodeUrl'], record['codeGenerationEvidence'][1])
                self.assertEqual(record['licenseUrl'], license_path)
                self.assertFalse(record['demoUrl'])
                self.assertEqual(len(record['media']), 3)
                self.assertEqual(record['thumbnail'], record['media'][0]['src'])
                self.assertEqual(record['timelineVisible'], not bool(record.get('modelRunGroup')))
                self.assertTrue(all(x['detailOnly'] for x in record['media'][1:]))
                for media in record['media']:
                    self.assertNotIn(media['sha256'], hashes)
                    hashes.add(media['sha256'])
                    original = ROOT / 'pelican-web' / media['src'].lstrip('/')
                    self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), media['sha256'])
        self.assertEqual(len(hashes), 33)


if __name__ == '__main__':
    unittest.main()
