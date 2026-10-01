import copy
import io
import json
import tempfile
import unittest
import threading
import urllib.request
import urllib.error
from unittest.mock import patch
from pathlib import Path
from PIL import Image,ImageDraw
import ingestion as app

def submission():
    return {'sourceUrl':'https://simonwillison.net/2026/Jul/18/test/','date':'2026-07-18','model':'test-model','author':'Simon Willison','format':'svg','unitType':'single-model-output','modelToMediaVerified':True,'title':{'zh':'测试','en':'Test'},'notes':{'zh':'测试记录','en':'Test record'},'media':['https://static.simonwillison.net/static/2026/test.png']}

class IngestionTests(unittest.TestCase):
    def test_authenticated_queue_and_idempotency(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(app,'STATE',Path(folder)),patch.dict(app.os.environ,{'PELICAN_INGEST_TOKEN':'test-only-token-that-is-at-least-32-characters'}):
            (Path(folder)/'jobs').mkdir();(Path(folder)/'pending').mkdir()
            server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            endpoint=f'http://127.0.0.1:{server.server_port}/api/v1/ingest'
            try:
                with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(endpoint)
                self.assertEqual(caught.exception.code,401)
                caught.exception.close()
                headers={'Authorization':'Bearer '+app.os.environ['PELICAN_INGEST_TOKEN'],'Content-Type':'application/json'}
                def post(value):return json.load(urllib.request.urlopen(urllib.request.Request(endpoint,json.dumps(value).encode(),headers)))
                a=post(submission());b=post(submission());self.assertEqual(a['id'],b['id'])
                self.assertEqual(len(list((Path(folder)/'pending').iterdir())),1)
                self.assertEqual(len(list((Path(folder)/'jobs').iterdir())),1)
                with self.assertRaises(urllib.error.HTTPError) as caught:post({'sourceUrl':'https://localhost'})
                self.assertEqual(caught.exception.code,400)
                caught.exception.close()
            finally:server.shutdown();server.server_close();thread.join()

    def test_schema_and_network_boundaries(self):
        p=submission();self.assertEqual(app.validate(p)['date'],'2026-07-18')
        for value in ['http://example.com','https://127.0.0.1','https://localhost','https://user:secret@example.com','https://example.com/%2e%2e/private']:
            with self.assertRaises(ValueError):app.url(value)
        for value in ['https://example.com/image.jpg','https://raw.githubusercontent.com/other/repo/main/x','https://static.simonwillison.net.evil.test/static/x']:
            with self.assertRaises(ValueError):app.permitted(value)
        for day in ['20260718','2099-01-01','2026-99-99']:
            bad=copy.deepcopy(p);bad['date']=day
            with self.assertRaises(ValueError):app.validate(bad)
        bad=copy.deepcopy(p);bad['title'].pop('en')
        with self.assertRaises(ValueError):app.validate(bad)

    def test_repository_provenance(self):
        p=app.validate(submission())
        p.update(sourceUrl='https://github.com/AzatJalilov/PelicanSdf/blob/main/data/results/test-run.json')
        def fetch(url):
            return json.dumps(['results/test-run.json'] if url.endswith('manifest.json') else {'id':'test-run','model':'test-model','createdAt':'2026-07-18','status':'unverified'}).encode()
        with self.assertRaisesRegex(ValueError,'reviewed batch import or a verified adapter'):app.verify_source(p,fetch)
        for key,value in [('model','wrong'),('date','2026-07-19'),('media',[app.RAW+'assets/thumbnails/other.jpg'])]:
            bad=copy.deepcopy(p);bad[key]=value
            with self.assertRaises(ValueError):app.verify_source(bad,fetch)

    def test_source_requires_linked_preview(self):
        p=app.validate(submission());p.update(sourceUrl='https://simonwillison.net/2026/Jul/18/test/',author='Simon Willison',media=['https://static.simonwillison.net/static/2026/test.png'])
        app.verify_source(p,lambda _:b'<p>test-model SVG</p><img src="https://static.simonwillison.net/static/2026/test.png">')
        with self.assertRaises(ValueError):app.verify_source(p,lambda _:b'<p>No image</p>')

    def test_image_decoding_and_blank_rejection(self):
        for content in [b'<html>Not an image</html>',b'<svg onload="bad()"></svg>']:
            with self.assertRaises(Exception):app.verify_image(content)
        im=Image.new('RGB',(480,270),'white');out=io.BytesIO();im.save(out,'PNG')
        with self.assertRaisesRegex(ValueError,'Blank'):app.verify_image(out.getvalue())
        ImageDraw.Draw(im).ellipse((20,20,200,200),fill='green');out=io.BytesIO();im.save(out,'PNG')
        result=app.verify_image(out.getvalue());self.assertEqual(result,out.getvalue())

    def test_identity_and_bilingual_warning(self):
        p=app.validate(submission());source={'warning':'unverified','demo':'https://example.com'}
        out=io.BytesIO();Image.new('RGB',(100,100)).save(out,'PNG')
        a=app.make_record(p,source,[out.getvalue()]);p['title']['zh']='更新标题';b=app.make_record(p,source,[out.getvalue()])
        self.assertEqual(a['id'],b['id']);self.assertIn('尚未独立复现',a['notes']);self.assertIn('not been independently',a['i18n']['en']['notes'])

    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'record.json';app.atomic_json(p,{'中文':1});app.atomic_json(p,{'中文':2})
            self.assertEqual(json.loads(p.read_text(encoding='utf8')),{'中文':2});self.assertEqual(len(list(p.parent.iterdir())),1)

if __name__=='__main__':unittest.main()
