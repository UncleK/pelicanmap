"""Verify the published bilingual edition and all newly captured previews."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

BASE='https://pelicanmap.aveniqa.com'
ROOT=Path(__file__).resolve().parents[1]
def get(path,body=None):
    headers={'User-Agent':'PelicanMap-Verifier/1.0'}
    if body:headers.update({'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode() if body else None,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as r:
        assert r.status==200,(path,r.status)
        return r.read()

def check_capture(item):
    for prefix in ['','/en']:
        soup=BeautifulSoup(get(prefix+item['path']),'html.parser')
        image=soup.select_one('.detail-gallery img')
        assert image and image['src']==item['media'][0]['src'],item['id']
        assert soup.select_one('a[data-language]')['href']==(item['path'] if prefix else '/en'+item['path'])
    assert get(item['media'][0]['src']).startswith(b'\xff\xd8\xff'),item['id']
    return item['id']

catalog=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
captures=json.loads((ROOT/'site/captures/manifest.json').read_text(encoding='utf8'))
items=[x for x in catalog['items'] if x['originalId'] in captures]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    print('Verified previews:',len(list(pool.map(check_capture,items))))
for path in ['/','/en/','/en/play/','/en/specimens/','/en/developers/','/en/llms.txt','/assets/og-cover-en.png']:
    get(path)
sitemap=ET.fromstring(get('/sitemap.xml'))
assert len(sitemap)==len(ET.fromstring((ROOT/'public-site/sitemap.xml').read_text(encoding='utf8'))),len(sitemap)
data=json.loads(get('/api/v1/specimens?lang=en&q=coast&limit=2'))
assert data['items'] and all('/en/specimens/' in x['url'] for x in data['items'])
item=data['items'][0]
assert json.loads(get('/api/v1/specimens/'+item['id']+'?lang=en'))==item
rpc=json.loads(get('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_specimen','arguments':{'id':item['id'],'lang':'en'}}}))
assert json.loads(rpc['result']['content'][0]['text'])==item
print(f"English pages, API, MCP, paired links and {len(sitemap)} sitemap URLs passed.")
