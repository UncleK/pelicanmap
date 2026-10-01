"""Regression checks for independently counted upstream benchmark references."""
import json
import unittest
from collections import Counter
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
from benchmark_reference import FIELDS, load, model_path, stats
from import_hf_reference import validate_svg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'public-site'


class BenchmarkReferenceTests(unittest.TestCase):
    def test_raw_fields_and_denominators_are_preserved(self):
        data = load()
        self.assertEqual(len(data['rows']),169)
        self.assertIsNone(data['runDate'])
        main = [x for x in data['rows'] if x['config']=='default']
        self.assertEqual(len(main),139)
        self.assertEqual(len({x['model'] for x in main}),7)
        self.assertEqual(sum(bool(x['localPng']) for x in main),138)
        kimi = [x for x in main if x['model']=='moonshotai/Kimi-K3']
        self.assertEqual(stats(kimi)['n'],19)
        self.assertAlmostEqual(stats(kimi)['reward'],0.8836988304093567)
        self.assertEqual(sum(stats(kimi)['species'].values()),19)
        failed = [x for x in main if x['png'] is None]
        self.assertEqual(len(failed),1)
        self.assertEqual(failed[0]['reward'],0)
        self.assertIsNone(failed[0]['localPng'])
        for row in data['rows']:
            self.assertTrue(set(FIELDS)<=set(row))
            if row['task']!='pelican_bicycle':
                self.assertIn('benchmark-catalogue',row['tags'])
        self.assertEqual(sum('benchmark-catalogue' in x['tags'] for x in data['rows']),29)
        original=[json.loads(line) for line in (ROOT/'pelican-archive/research/2026-10-01-source-backfill/hf-data.jsonl').read_text(encoding='utf8').splitlines()]
        by_id={x['id']:x for x in main}
        for row in original:
            for key,value in row.items():self.assertEqual(by_id[row['id']][key],value)

    def test_local_media_opens_and_no_animation_is_mirrored(self):
        for row in load()['rows']:
            if row['localPng']:
                with Image.open(OUT/row['localPng'].lstrip('/')) as image:image.verify()
            if row['localSvg']:
                self.assertTrue(validate_svg((OUT/row['localSvg'].lstrip('/')).read_bytes()))
            if row.get('svgDeferredReason'):
                self.assertIsNone(row['localSvg'])
                self.assertIn(row['sourceUrl'],(ROOT/'deferred.md').read_text(encoding='utf8'))

    def test_collection_directory_model_pages_and_controlled_scope(self):
        data=load()
        main=[x for x in data['rows'] if x['config']=='default']
        for prefix in ['', 'en/']:
            index=BeautifulSoup((OUT/prefix/'tags/benchmark/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(index.select('[data-benchmark-collection]')),1)
            self.assertIn('OpenEnv',index.get_text())
            collection=BeautifulSoup((OUT/prefix/'collections/openenv-2026-07-29/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(collection.select('tbody tr')),7)
            self.assertEqual(len(collection.select('.batch-model')),7)
            self.assertFalse(collection.select('.batch-model[open]'))
            self.assertEqual(len(collection.select('[data-batch-sample]')),139)
            self.assertIsNotNone(collection.select_one('[data-reference-only=true]'))
            for model in {x['model'] for x in main}:
                page=BeautifulSoup((OUT/prefix/model_path(model).lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertEqual(len(page.select('.benchmark-representatives .benchmark-sample')),2)
                self.assertTrue(page.select_one('.benchmark-disclaimer'))
            coverage=BeautifulSoup((OUT/prefix/'benchmarks/openenv-2026-07-29/catalogue/index.html').read_text(encoding='utf8'),'html.parser')
            self.assertEqual(len(coverage.select('[data-batch-sample]')),30)
            for listing in ['timeline','specimens']:
                for file in (OUT/prefix/listing).rglob('index.html'):
                    results=BeautifulSoup(file.read_text(encoding='utf8'),'html.parser').select_one('[data-results]')
                    if results:
                        self.assertNotIn('hf-openenv-',str(results))
                        self.assertNotIn('/collections/openenv-2026-07-29/',str(results))


if __name__=='__main__':unittest.main()
