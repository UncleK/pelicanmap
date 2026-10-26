import hashlib
import unittest
from unittest.mock import patch

from check_delta_release import check_api_record, check_live_bytes, verify_live_jobs, TRAFFIC_SCRIPT


class DeltaLiveTests(unittest.TestCase):
    def test_parallel_public_reads_check_every_byte_and_api_field(self):
        original=b'original';expected={'id':'work','caseNumber':42}
        jobs=[('bytes','site/a.txt','https://example.com/a',{'sha256':hashlib.sha256(original).hexdigest()}),('api','work','https://example.com/api',expected)]
        with patch('check_delta_release.fetch',side_effect=lambda url:original if url.endswith('/a') else b'{"id":"work","caseNumber":42}') as fetch:
            self.assertEqual(verify_live_jobs(jobs),2)
            self.assertEqual(fetch.call_count,2)
        with patch('check_delta_release.fetch',side_effect=lambda url:original if url.endswith('/a') else b'{"id":"work","caseNumber":41}'):
            with self.assertRaisesRegex(ValueError,'caseNumber'):verify_live_jobs(jobs)
        with patch('check_delta_release.fetch',side_effect=OSError('public fetch failed')):
            with self.assertRaisesRegex(OSError,'public fetch failed'):verify_live_jobs(jobs)

    def test_a_matching_id_does_not_hide_stale_api_fields(self):
        expected = {'id': 'existing', 'caseNumber': 123, 'modelTimeline': {'sortDate': '2026-09'}}
        check_api_record(expected, dict(expected))
        with self.assertRaisesRegex(ValueError, 'caseNumber'):
            check_api_record(expected, {**expected, 'caseNumber': 122})
        with self.assertRaisesRegex(ValueError, 'modelTimeline'):
            check_api_record(expected, {**expected, 'modelTimeline': {'sortDate': '2026-10'}})

    def test_only_the_known_analytics_injection_is_allowed(self):
        original = b'<html><head></head><body>new work</body></html>'
        expected = {'sha256': hashlib.sha256(original).hexdigest()}
        check_live_bytes('site/index.html', original, expected)
        check_live_bytes('site/index.html', original.replace(b'</head>', TRAFFIC_SCRIPT+b'</head>'), expected)
        for altered in (original.replace(b'new work', b'old work'),
                        original.replace(b'</head>', b'<script src="/unexpected.js"></script></head>'),
                        original.replace(b'</head>', TRAFFIC_SCRIPT*2+b'</head>')):
            with self.assertRaises(ValueError):
                check_live_bytes('site/index.html', altered, expected)


if __name__ == '__main__':
    unittest.main()
