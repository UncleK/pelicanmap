import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from activate_incremental import activate, publisher_path, validate_additions, verify_payload
from release_delta import inventory, metadata, package


class IncrementalActivationTests(unittest.TestCase):
    def fixture(self, root):
        base, stage, source = root/'server', root/'stage', root/'source'
        previous = base/'releases/20261009T114034Z'
        previous.mkdir(parents=True)
        stage.mkdir()
        old_catalog = {'items': [{'id': 'old'}], 'counts': {'cases': 1, 'timeline': 1}}
        new_catalog = {'items': [{'id': 'old'}, {'id': 'new'}], 'counts': {'cases': 2, 'timeline': 1}}
        files = {
            previous/'site/data/catalog.json': json.dumps(old_catalog),
            previous/'demos/index.html': 'old demo', previous/'runtime/server.mjs': 'old API',
            source/'public-site/data/catalog.json': json.dumps(new_catalog),
            source/'public-demos/index.html': 'old demo', source/'pelican-web/repos/pedalican.zip': 'source zip',
            source/'deploy-build/removed-public-pages.json': '[]',
            base/'state/additions.json': '[{"id":"old"}]', base/'state/publish.lock': '',
            base/'publisher/tools/source.py': 'old source',
            base/'publisher/site/deploy/pelicanmap-api.service': 'unchanged unit',
            root/'api.service': 'unchanged unit', stage/'additions.json': '[{"id":"old"},{"id":"new"}]',
            stage/'source.py': 'new source'
        }
        for path, value in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        (base/'current').symlink_to(previous)
        package(source, inventory(previous), stage/'pelicanmap-update.tar.gz', include_runtime=False)
        with tarfile.open(stage/'publisher-update.tar.gz', 'w:gz') as output:
            output.add(stage/'source.py', arcname='tools/source.py')
        request = {'baselineRelease': previous.name, 'baselineCounts': old_catalog['counts'],
            'additionsBeforeSha256': metadata(base/'state/additions.json')['sha256'],
            'apiUnitBeforeSha256': metadata(root/'api.service')['sha256'],
            'publisherChanges': {'tools/source.py': {'before': metadata(base/'publisher/tools/source.py'),
                                                   'after': metadata(stage/'source.py')}},
            'packages': {name: metadata(stage/name) for name in ['pelicanmap-update.tar.gz', 'publisher-update.tar.gz', 'additions.json']},
            'counts': new_catalog['counts'], 'affectedRecords': ['new'],
            'changedFiles': ['site/data/catalog.json', 'site/downloads/pedalican.zip']}
        (stage/'deployment.json').write_text(json.dumps(request))
        return base, stage, previous, root/'api.service'

    @unittest.skipIf(os.name == 'nt', 'Activation uses the server POSIX publication lock')
    def test_successful_content_activation_does_not_restart_units(self):
        with tempfile.TemporaryDirectory() as folder:
            base, stage, previous, unit = self.fixture(Path(folder))
            with patch('activate_incremental.wait_healthy'), patch('activate_incremental.subprocess.run') as run:
                report = activate(stage, base, api_unit=unit)
            self.assertNotEqual((base/'current').resolve(), previous)
            self.assertFalse(report['apiRestarted'])
            run.assert_not_called()
            self.assertEqual((base/'publisher/tools/source.py').read_text(), 'new source')

    @unittest.skipIf(os.name == 'nt', 'Rollback uses the server POSIX publication lock')
    def test_failed_health_restores_site_export_and_publisher(self):
        with tempfile.TemporaryDirectory() as folder:
            base, stage, previous, unit = self.fixture(Path(folder))
            before = (base/'state/additions.json').read_bytes()
            with patch('activate_incremental.wait_healthy', side_effect=[None, RuntimeError('health failed'), None]):
                with self.assertRaisesRegex(RuntimeError, 'health failed'):
                    activate(stage, base, api_unit=unit)
            self.assertEqual((base/'current').resolve(), previous)
            self.assertEqual((base/'state/additions.json').read_bytes(), before)
            self.assertEqual((base/'publisher/tools/source.py').read_text(), 'old source')

    def test_publisher_paths_cannot_escape_or_follow_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ['../secret', '/etc/passwd', 'tools/../../secret', 'site\\private', 'credentials/token']:
                with self.assertRaises(ValueError):
                    publisher_path(root, name)
            self.assertEqual(publisher_path(root, 'tools/release_delta.py'), root/'tools/release_delta.py')

    def test_new_export_preserves_old_ids_and_rejects_unpublished_records(self):
        catalog = {'items': [{'id': 'old'}, {'id': 'new'}]}
        validate_additions(catalog, [{'id': 'old'}, {'id': 'new'}], [{'id': 'old'}])
        for incoming in [[{'id': 'new'}], [{'id': 'old'}, {'id': 'missing'}], [{'id': 'old'}, {'id': 'old'}]]:
            with self.assertRaises(ValueError):
                validate_additions(catalog, incoming, [{'id': 'old'}])

    def test_publisher_archive_rejects_changed_bytes_and_unlisted_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'source.py'
            source.write_bytes(b'reviewed source')
            archive = root/'publisher.tar.gz'
            with tarfile.open(archive, 'w:gz') as output:
                output.add(source, arcname='tools/source.py')
            expected = {'tools/source.py': {'bytes': source.stat().st_size,
                        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}}
            verify_payload(archive, expected)
            with self.assertRaises(ValueError):
                verify_payload(archive, {})
            expected['tools/source.py']['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_payload(archive, expected)


if __name__ == '__main__':
    unittest.main()
