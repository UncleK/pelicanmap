"""Read-only live checks, including archive download integrity and MCP."""
import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE='https://pelicanmap.aveniqa.com'
def request(path, method='GET', data=None, headers=None):
    req=urllib.request.Request(BASE+path,data=data,method=method,headers={'User-Agent':'PelicanMap-Verifier/1.0',**(headers or {})})
    try: return urllib.request.urlopen(req,timeout=40)
    except urllib.error.HTTPError as err: return err

for path,status in [('/',200),('/sitemap.xml',200),('/robots.txt',200),('/llms.txt',200),('/openapi.json',200),('/missing-page-qa',404),('/.env',404),('/_headers',404)]:
    with request(path) as response:
        assert response.status==status,(path,response.status)
        if path=='/': assert response.headers.get('Server')=='cloudflare'
        print(path,response.status)
with request('/api/v1/specimens?limit=1') as response:
    expected=json.loads((Path(__file__).resolve().parents[1]/'site/catalog.json').read_text(encoding='utf8'))['counts']['cases']
    catalog=json.load(response); assert catalog['total']==expected
    item=catalog['items'][0]
for path in [item['path'],item['markdown'],item['thumbnail'],item['media'][0]['src']]:
    with request(path,'HEAD') as response: assert response.status==200,(path,response.status)
with request('/api/v1/specimens?limit=1000') as response: assert response.status==400
with request('/api/v1/specimens','POST',b'{}') as response: assert response.status==405
def mcp(method,params,ident):
    with request('/mcp','POST',json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params}).encode(),{'Content-Type':'application/json','Accept':'application/json, text/event-stream'}) as response:
        assert response.status==200,response.status
        return json.load(response)
assert mcp('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'live-check','version':'1'}},1)['result']['serverInfo']['name']=='pelican-map'
assert len(mcp('tools/list',{},2)['result']['tools'])==3
result=mcp('tools/call',{'name':'search_specimens','arguments':{'q':'GPT','limit':2}},3)
assert len(json.loads(result['result']['content'][0]['text'])['items'])==2
print('API, record media and MCP passed')
with request('/downloads/pedalican.zip',headers={'Range':'bytes=8388600-8388620'}) as response:
    assert response.status==206; assert len(response.read())==21
with request('/downloads/pedalican.zip') as response:
    digest=hashlib.file_digest(response,'sha256').hexdigest()
print('pedalican.zip SHA256',digest)
