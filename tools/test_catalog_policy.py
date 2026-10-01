import unittest
from catalog_policy import apply_demo_policy, merge_additions, playable_records


class CatalogPolicyTests(unittest.TestCase):
    def test_animation_and_external_demo_are_not_interactive(self):
        records = [
            {'id': 'animation', 'demoUrl': 'https://pelicanmap-demos.aveniqa.com/demos/animation/', 'externalUrl': '', 'mediaStatus': 'interactive'},
            {'id': 'remote', 'demoUrl': 'https://example.com/game', 'externalUrl': '', 'mediaStatus': 'local'},
        ]
        reviewed = apply_demo_policy(records, {})
        self.assertEqual(playable_records(reviewed), [])
        self.assertEqual(reviewed[0]['previewUrl'], records[0]['demoUrl'])
        self.assertEqual(reviewed[1]['externalUrl'], records[1]['demoUrl'])
        self.assertTrue(all(not x['demoUrl'] and not x['interactive'] for x in reviewed))
        self.assertEqual(records[0]['mediaStatus'], 'interactive')

    def test_static_svg_stays_a_case_without_an_animation_wrapper(self):
        record = {'id': 'static', 'format': 'svg', 'demoUrl': 'https://pelicanmap-demos.aveniqa.com/demos/svg-selector/'}
        self.assertFalse(apply_demo_policy([record], {})[0]['previewUrl'])

    def test_verified_local_controls_and_shared_demo_are_deduplicated(self):
        url = 'https://pelicanmap-demos.aveniqa.com/demos/game/'
        records = [{'id': x, 'demoUrl': url, 'date': date} for x, date in [('one', '2026-09-20'), ('two', '2026-09-29')]]
        reviews = {x: {'controls': {'zh': '方向键骑行', 'en': 'Arrow keys to ride'}, 'demoUrl': url} for x in ['one', 'two']}
        reviewed = apply_demo_policy(records, reviews)
        self.assertTrue(all(x['interactive'] for x in reviewed))
        self.assertEqual([x['id'] for x in playable_records(reviewed)], ['two'])

    def test_reviews_cannot_turn_an_external_page_into_a_local_demo(self):
        record = {'id': 'remote', 'demoUrl': 'https://example.com/game'}
        review = {'remote': {'controls': {'zh': '方向键', 'en': 'Arrow keys'}, 'demoUrl': record['demoUrl']}}
        self.assertFalse(apply_demo_policy([record], review)[0]['interactive'])

    def test_sync_preserves_manual_cases_and_updates_ingested_cases(self):
        local = [{'id': 'manual', 'title': 'keep'}, {'id': 'ingest-one', 'title': 'old'}]
        remote = [{'id': 'ingest-one', 'title': 'new'}, {'id': 'ingest-two', 'title': 'added'}]
        merged = merge_additions(local, remote)
        self.assertEqual({x['id']: x['title'] for x in merged}, {'manual': 'keep', 'ingest-one': 'new', 'ingest-two': 'added'})


if __name__ == '__main__':
    unittest.main()
