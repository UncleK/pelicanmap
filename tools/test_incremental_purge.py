import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

from purge_incremental_cache import load_token, purge_payload, request_purge, run


class IncrementalPurgeTests(unittest.TestCase):
    def test_other_sites_and_broad_purge_inputs_are_rejected(self):
        for urls in [[], ['https://aveniqa.com/'], ['https://pelicanmap.aveniqa.com/other'],
                     ['https://pelicanmap.aveniqa.com/data/catalog.json?anything=1']]:
            with self.assertRaises(ValueError):
                purge_payload(urls)
        url = 'https://pelicanmap.aveniqa.com/data/catalog.json'
        self.assertEqual(purge_payload([url, url]), {'files': [url]})

    def test_permission_denial_does_not_expose_server_error_text(self):
        body = io.BytesIO(b'{"success":false,"errors":[{"code":10000,"message":"PRIVATE"}]}')
        error = urllib.error.HTTPError('https://api.cloudflare.com/', 401, 'Denied', {}, body)
        with patch('purge_incremental_cache.urllib.request.build_opener') as build:
            build.return_value.open.side_effect = error
            result = request_purge('PRIVATE-TOKEN', {'files': ['https://pelicanmap.aveniqa.com/']})
        self.assertEqual(result['errorCodes'], [10000])
        self.assertFalse(result['success'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_accepted_purge_still_requires_actual_byte_verification(self):
        stale = {'status': 'cache-refresh-required', 'checked': [], 'stale': [
            {'url': 'https://pelicanmap.aveniqa.com/data/catalog.json'}]}
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory)
            with patch('purge_incremental_cache.check_cache', side_effect=[stale, stale]), \
                    patch('purge_incremental_cache.load_token', return_value='PRIVATE-TOKEN'), \
                    patch('purge_incremental_cache.request_purge', return_value={'success': True}):
                result = run(batch)
            self.assertEqual(result['status'], 'cache-refresh-required')
            self.assertNotIn('PRIVATE', (batch/'cloudflare-purge.json').read_text())

    def test_pasted_credential_file_can_be_used_without_copying_token(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory)/'token.txt'
            token_file.write_text('Earlier supplied API: cfut_test_example_value\n')
            self.assertEqual(load_token(token_file), 'cfut_test_example_value')


if __name__ == '__main__':
    unittest.main()
