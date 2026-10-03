import unittest
import urllib.request
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from live_http import live_url,live_urlopen

class LiveHttpTests(unittest.TestCase):
    def test_static_version_does_not_change_origin_or_existing_queries(self):
        url=live_url('https://pelicanmap.aveniqa.com/en/data/catalog.json?collection=abcd','123')
        parsed=urlsplit(url)
        self.assertEqual(parsed.path,'/en/data/catalog.json')
        self.assertEqual(parse_qs(parsed.query),{'collection':['abcd'],'live-verification':['123']})
        for url in ['https://pelicanmap.aveniqa.com/api/v1/specimens?lang=en&limit=1','https://pelicanmap.aveniqa.com/mcp','https://example.com/data.json']:
            self.assertEqual(live_url(url,'123'),url)
    def test_method_headers_and_original_request_are_preserved(self):
        request=urllib.request.Request('https://pelicanmap.aveniqa.com/data/catalog.json',headers={'User-Agent':'Verifier','Cache-Control':'no-cache'})
        with patch('urllib.request.urlopen') as send:
            live_urlopen(request,timeout=45)
        passed=send.call_args.args[0]
        self.assertEqual(request.full_url,'https://pelicanmap.aveniqa.com/data/catalog.json')
        self.assertEqual(passed.get_method(),'GET')
        self.assertEqual(passed.get_header('User-agent'),'Verifier')
        self.assertEqual(send.call_args.kwargs,{'timeout':45})
        self.assertIn('live-verification=',passed.full_url)

if __name__=='__main__':unittest.main()
