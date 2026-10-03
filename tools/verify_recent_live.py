import concurrent.futures
import json
import urllib.request
import urllib.error
import time
from pathlib import Path
from live_http import live_urlopen
ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
def get(path):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Verifier/1.0'})
    for attempt in range(3):
        try:
            with live_urlopen(req,timeout=40) as r:return r.status,dict(r.headers),r.read()
        except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()
        except urllib.error.URLError:
            if attempt==2:raise
            time.sleep(attempt+1)
def main():
    additions=json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
    catalog=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
    expected_records=catalog['counts'].get('cases',len(catalog['items']))
    expected_sitemap=(ROOT/'public-site/sitemap.xml').read_text(encoding='utf8').count('<loc>')
    checks=[]
    for item in additions:
        for lang in ['','en/']:checks.append(('/'+lang+item['path'].lstrip('/'),200))
        checks.append((item['thumbnail'],200))
        checks.append(('/api/v1/specimens/'+item['id']+'?lang=en',200))
    for item in json.loads((ROOT/'site/publication-exclusions.json').read_text(encoding='utf8')):
        for lang in ['','en/']:checks.append(('/'+lang+'specimens/'+item['id']+'/',404))
    checks.append(('/api/v1/ingest/export',401))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for (path,expected),(status,headers,body) in zip(checks,pool.map(lambda row:get(row[0]),checks)):
            assert status==expected,(path,status,expected)
            if expected==200 and path.endswith('.webp'):assert body[:4]==b'RIFF' and body[8:12]==b'WEBP'
    status,headers,body=get('/specimens/astra-grid-2026-09-04-ac0bd320/index.md')
    assert status==200 and 'charset=utf-8' in next(v for k,v in headers.items() if k.lower()=='content-type').lower()
    content=body.decode('utf8');assert '记录日期' in content and '\ufffd' not in content
    for language in ['zh','en']:
        data=json.loads(get('/api/v1/specimens?lang='+language+'&limit=1')[2]);assert data['total']==expected_records
    sitemap=get('/sitemap.xml')[2].decode();assert sitemap.count('<loc>')==expected_sitemap
    print(json.dumps({'checked_endpoints':len(checks)+4,'records':expected_records,'sitemap_pages':expected_sitemap,'markdown':'UTF-8','removed_records':'404','unauthenticated_ingestion':'401'}))
if __name__=='__main__':main()
