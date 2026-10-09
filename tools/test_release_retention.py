"""Destructive retention regression checks in disposable release directories."""
import os
from pathlib import Path
import tempfile
import unittest
from release_retention import plan_releases, prune_releases, release_time


@unittest.skipUnless(os.name == 'posix', 'Deployment symlinks require Linux')
class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.releases = self.base / 'releases'
        self.releases.mkdir()
        self.names = [f'20261003T10000{x}Z' for x in range(6)]
        for name in self.names:
            path = self.releases / name / 'site/data'
            path.mkdir(parents=True)
            (path / 'catalog.json').write_text('{}')
        (self.base / 'current').symlink_to(self.releases / self.names[-1])

    def test_prune_keeps_latest_three_and_is_idempotent(self):
        report = prune_releases(self.base)
        self.assertEqual(set(report['removed']), set(self.names[:3]))
        self.assertEqual({p.name for p in self.releases.iterdir()}, set(self.names[3:]))
        self.assertEqual(prune_releases(self.base)['removed'], [])
        self.assertTrue((self.base / 'current/site/data/catalog.json').is_file())

    def test_rollback_keeps_serving_release_and_two_newest(self):
        (self.base / 'current').unlink()
        (self.base / 'current').symlink_to(self.releases / self.names[0])
        self.assertEqual(set(prune_releases(self.base)['kept']), {self.names[0], *self.names[-2:]})

    def test_dry_run_preserves_all_files(self):
        report = prune_releases(self.base, dry_run=True)
        self.assertEqual(report['removed'], [])
        self.assertEqual(len(report['planned']), 3)
        self.assertEqual(len(list(self.releases.iterdir())), 6)

    def test_symlinks_and_unrecognized_directories_are_not_targets(self):
        outside = self.base / 'originals'
        outside.mkdir()
        (outside / 'original').write_bytes(b'original-media')
        (self.releases / '20260901T100000Z').symlink_to(outside)
        (self.releases / self.names[0] / 'media').symlink_to(outside)
        (self.releases / 'research').mkdir()
        report = prune_releases(self.base)
        self.assertEqual((outside / 'original').read_bytes(), b'original-media')
        self.assertEqual(set(report['ignored']), {'research', '20260901T100000Z'})

    def test_hardlinked_media_survives_old_version_deletion(self):
        old = self.releases / self.names[0] / 'original'
        old.write_bytes(b'unchanged-media')
        new = self.releases / self.names[-1] / 'original'
        os.link(old, new)
        prune_releases(self.base)
        self.assertEqual(new.read_bytes(), b'unchanged-media')

    def test_pending_link_and_outside_current_stop_before_deleting(self):
        pending = self.base / 'current.next'
        pending.symlink_to(self.releases / self.names[0])
        with self.assertRaisesRegex(ValueError, 'pending or rollback'):
            prune_releases(self.base)
        self.assertEqual(len(list(self.releases.iterdir())), 6)
        pending.unlink()
        (self.base / 'current').unlink()
        (self.base / 'current').symlink_to(self.base)
        with self.assertRaises(ValueError):
            prune_releases(self.base)
        self.assertEqual(len(list(self.releases.iterdir())), 6)

    def test_process_using_old_version_stops_before_deleting(self):
        cwd = Path.cwd()
        try:
            os.chdir(self.releases / self.names[0])
            with self.assertRaisesRegex(ValueError, 'running process'):
                prune_releases(self.base)
        finally:
            os.chdir(cwd)
        self.assertEqual(len(list(self.releases.iterdir())), 6)


class ReleaseTimeTests(unittest.TestCase):
    def test_fractional_auto_release_order_and_unknown_names(self):
        self.assertLess(release_time(Path('20261003T100000Z')), release_time(Path('20261003T100000123456Z-auto')))
        self.assertIsNone(release_time(Path('local-archive')))


if __name__ == '__main__':
    unittest.main()
