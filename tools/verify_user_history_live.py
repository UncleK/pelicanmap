"""Read-only checks of the historical URL batch across public boundaries."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
ARCHIVE=ROOT/'pelican-archive/research/2026-10-01-user-history-links'
MANIFEST=json.loads((ARCHIVE/'approved-manifest.json').read_text(encoding='utf8'))
LOCAL=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
BY={x['id']:x for x in LOCAL['items']}


def get(path):
    with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-HistoryVerifier/1.0'}),timeout=40) as response:
        assert response.status==200,path
        return response.read()


def check(c):
    x=BY[c['id']]
    media=get(x['media'][0]['src'])
    assert hashlib.sha256(media).hexdigest()==c['media'][0]['sha256'],c['id']
    for lang,prefix in [('zh',''),('en','/en')]:
        page=BeautifulSoup(get(prefix+x['path']),'html.parser')
        assert page.find('img',src=x['thumbnail']),c['id']
        assert x['model'] in page.get_text(' ',strip=True),c['id']
        assert page.find('a',href=c['sourceUrl']),c['id']
        assert page.find('link',rel='canonical')['href']==BASE+prefix+x['path']
        api=json.loads(get('/api/v1/specimens/'+c['id']+'?lang='+lang))
        for key in ['date','model','caseNumber','timelineVisible','sourceUrl']:
            assert api[key]==x[key],(c['id'],key)
        if c['id'].startswith('hardprompts-'):
            assert api['dateBasis']=='source-reported-response-timestamp'
            assert not api.get('sourcePublicationDate')
            assert api['sourceResponseTimestamp'][:10]==api['date']
        if x.get('modelRunGroup'):
            section=page.select_one('[data-setting-comparison]')
            assert len(section.select('figure'))==len(x['comparisonIds'])
            if c['id'].startswith('hardprompts-'):
                assert ('independent runs' if lang=='en' else '多次独立输出') in section.get_text(' ',strip=True)
    return c['id']


def main():
    stamp=hashlib.sha256((ROOT/'site/catalog.json').read_bytes()).hexdigest()[:12]
    remote=json.loads(get('/data/catalog.json?history-links='+stamp))
    assert remote==LOCAL,'Published catalogue does not match this build'
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        checked=list(pool.map(check,MANIFEST['cases']))
    for lang in ['zh','en']:
        prefix='/en' if lang=='en' else ''
        total=json.loads(get('/api/v1/specimens?limit=1&lang='+lang))
        timeline=json.loads(get('/api/v1/timeline?limit=1&lang='+lang))
        assert total['total']==LOCAL['counts']['cases'] and timeline['total']==LOCAL['counts']['timeline']
        hard=json.loads(get('/api/v1/specimens?q=Hard%20Prompts&limit=50&lang='+lang))
        assert {x['id'] for x in hard['items'] if x['id'].startswith('hardprompts-')}=={c['id'] for c in MANIFEST['cases'] if c['id'].startswith('hardprompts-')}
        by=json.loads(get('/api/v1/timeline?year=2025&family=Gemini&sort=oldest&limit=50&lang='+lang))
        assert 'history-5b61866c-0-0' in {x['id'] for x in by['items']}
        assert 'simon-gemini-flash-budget-zero-2025-05-20' not in {x['id'] for x in by['items']}
        alias=json.loads(get('/api/v1/specimens/x-1856712797054447970-52885a83?lang='+lang))
        assert alias['canonicalId']=='zoo-qwen-pelican-90951e0b' and not alias['caseVisible'] and alias['caseNumber'] is None
        about=BeautifulSoup(get(prefix+'/about/'),'html.parser').get_text(' ',strip=True)
        assert ('36 missing static outputs' if lang=='en' else '新增 36 张漏收静态输出') in about
        assert ((str(LOCAL['counts']['cases'])+' independent works') if lang=='en' else (str(LOCAL['counts']['cases'])+' 个独立作品')) in about
    result={'approved_records':len(checked),'exact_upstream_media_hashes':len(checked),'bilingual_details_and_id_api':2*len(checked),'cases':LOCAL['counts']['cases'],'timeline':LOCAL['counts']['timeline'],'benchmark':'still excluded','comparison_labels':'verified','catalog':'equal to local build'}
    (ARCHIVE/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
