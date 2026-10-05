"""Live code-generation scope, preserved originals and read-only default searches."""
import concurrent.futures,csv,hashlib,io,json,time,urllib.request,unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from generation_scope import DIRECT_VIDEO_IDS
from archival_test_assertions import reviewed_swe_motion_restoration
ROOT=Path(__file__).resolve().parents[1];BASE='https://pelicanmap.aveniqa.com';checks=0

def get(path,payload=None):
    global checks
    headers={'User-Agent':'PelicanMap-CodeScopeVerifier/1.0','Cache-Control':'no-cache'}
    if payload is not None:headers.update({'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
    req=urllib.request.Request(BASE+path,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=45) as r:assert r.status==200;body=r.read()
    checks+=1;return body

def main():
    global checks
    before=json.loads((ROOT/'pelican-archive/research/2026-10-03-code-generation-scope/before-catalog.json').read_text('utf8'))
    old={x['id']:x for x in before['items']};media={}
    for lang,prefix in [('zh',''),('en','/en')]:
        expected=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text('utf8'))
        actual=json.loads(get(prefix+'/data/catalog.json?code-scope='+str(time.time_ns())))
        assert actual==expected
        rows={x['id']:x for x in actual['items']};assert set(old)<=set(rows)
        if lang=='zh':preserved_rows=rows
        # Later source-reviewed intake may extend the archive without changing
        # the four withdrawals or any legacy source/media fields below.
        for id in set(rows)-set(old):
            row=rows[id]
            assert row['generationMethod']=='code-generated' and row['codeGenerationEvidence']
            assert row['unitType']=='single-model-output' and row['caseVisible']
            assert row['ingestion']['sourceChecked'] and row['ingestion']['imagesChecked']
        assert actual['counts']['cases']==sum(x['caseVisible'] for x in rows.values())
        assert actual['counts']['timeline']==sum(x['timelineVisible'] for x in rows.values())
        for id in DIRECT_VIDEO_IDS:
            row=rows[id];assert not row['caseVisible'] and not row['timelineVisible'] and row.get('caseNumber') is None
            result=json.loads(get('/api/v1/specimens/'+id+'?lang='+lang));assert result.get('item',result)==row
            assert get(row['path'])
            for scope in ['specimens','timeline']:
                found=json.loads(get('/api/v1/'+scope+'?q='+row['model'].replace(' ','%20')+'&lang='+lang+'&limit=50'))
                assert not (DIRECT_VIDEO_IDS&{x['id'] for x in found['items']})
            for m in row['media']:media[m['src']]=hashlib.sha256((ROOT/'public-site'/m['src'].lstrip('/')).read_bytes()).hexdigest()
        exported=list(csv.DictReader(io.StringIO(get(prefix+'/data/catalog.csv').decode())))
        for row in exported:
            if row['id'] in DIRECT_VIDEO_IDS:assert row['caseVisible']=='false' and row['timelineVisible']=='false' and row['generationMethod']=='direct-text-to-video'
        for path in ['/llms.txt','/about/','/developers/']:
            body=get(prefix+path).decode();assert 'codeGenerationEvidence' in body and ('直接文生视频' if lang=='zh' else 'Direct text-to-video' if path=='/llms.txt' else 'text-to-video') in body
        policy=json.loads(get('/data/collecting-policy.json?code-scope='+str(time.time_ns())))
        assert policy['generationScope']['excludedGenerationMethods']==['direct-text-to-video'] and policy['allMediaTypes']
    def check_media(pair):
        src,digest=pair;assert hashlib.sha256(get(src+'?code-scope=20261003')).hexdigest()==digest,src
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(check_media,media.items()))
    for id,row in old.items():
        current=preserved_rows[id]
        for key in ['id','model','author','date','sourceUrl','thumbnail','rights','media']:
            if not reviewed_swe_motion_restoration(unittest.TestCase(),row,current,key):assert current.get(key)==row.get(key),(id,key)
        if id not in DIRECT_VIDEO_IDS:assert (current['caseVisible'],current['timelineVisible'])==(row['caseVisible'],row['timelineVisible'])
    spec=json.loads(get('/openapi.json'));assert 'generationMethod' in spec['components']['schemas']['Record']['properties']
    sitemap=get('/sitemap.xml?code-scope='+str(time.time_ns()))
    assert sitemap==(ROOT/'public-site/sitemap.xml').read_bytes()
    assert not any('simon-veo2-output-' in x.text for x in ET.fromstring(sitemap).findall('{*}url/{*}loc'))
    rpc=json.loads(get('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_specimen','arguments':{'id':next(iter(DIRECT_VIDEO_IDS)),'lang':'zh'}}}))
    assert not rpc['result'].get('isError')
    for prefix in ['', '/en']:
        rpc=json.loads(get('/mcp',{'jsonrpc':'2.0','id':2,'method':'resources/read','params':{'uri':BASE+prefix+'/llms.txt'}}))
        assert 'codeGenerationEvidence' in rpc['result']['contents'][0]['text']
    print(json.dumps(dict(status='passed',checks=checks,excluded=4,works=actual['counts']['cases'],timeline=actual['counts']['timeline'],records=len(preserved_rows),originalMediaHashes=len(media),legacyIds='preserved',codeMotion='eligible')))

if __name__=='__main__':main()
