"""Read-only catalogue audit of the user's explicit historical source URLs.

Archives fetched public evidence, but never writes museum records or media.
Annotations accompanying the URLs are deliberately not inputs.
"""
import concurrent.futures
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pelican-archive/research/2026-10-01-user-history-links'
URLS = '''
https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/
https://github.com/simonw/pelican-bicycle
https://simonwillison.net/2025/Jun/6/six-months-in-llms/
https://simonwillison.net/tags/pelican-riding-a-bicycle/
https://pelicanzoo.ai/
https://nilethebot.github.io/pelican-timeline/
https://dev.to/_94be737e156beb4d74df2/two-years-of-pelicans-on-bicycles-103-svgs-66-models-and-what-the-guy-who-invented-the-benchmark-4c7e
https://fedi.simonwillison.net/@simon/113370789677239232
https://gist.github.com/simonw/56217af454695a90be2c8e09c703198a
https://gist.github.com/simonw/4728316a9e4854c6e62fa25c40759bb6
https://static.simonwillison.net/static/cors-allow/2024/a-pelican-riding-a-bicycle.glb
https://gist.github.com/simonw/c34f7f0c94afcbeab77e170511f6f51f
https://x.com/simonw/status/1920132231328100449
https://gist.github.com/simonw/5b61866cb4ce67899934c29a9de1b4be
https://simonwillison.net/2025/May/20/google-io-pelican/
https://gist.github.com/simonw/d8765ea8413592b074ded45cbc585c54
https://simonwillison.net/2025/Aug/10/qwen3-4b/
https://hardprompts.ai/topics/pelican-bicycle-svg.html
https://simonwillison.net/2025/Nov/13/training-for-pelicans-riding-bicycles/
https://simonwillison.net/2025/Nov/18/gemini-3/
https://fedi.simonwillison.net/@simon/115572267878648433
https://simonwillison.net/2025/Dec/19/introducing-gpt-52-codex/
https://simonwillison.net/2025/Dec/31/the-year-in-llms/
https://simonwillison.net/2026/Jan/27/kimi-k25/
https://huggingface.co/datasets/sergiopaniego/pelican-svg-drawings
https://simonwillison.net/2026/Apr/16/
https://simonwillison.net/search/?tag=pelican-riding-a-bicycle&type=entry
https://simonwillison.net/2026/Jun/17/glm-52/
https://simonwillison.net/2026/Jun/29/ornith/
https://simonwillison.net/2026/Jul/14/pedalican/
https://simonwillison.net/2026/Jul/31/deepseek-v4-flash-0731/
https://simonwillison.net/2026/Aug/16/qwen-38-27b/
https://simonwillison.net/2026/Aug/26/qwen38-flash-next/
https://simonwillison.net/2026/Aug/29/hy4/
https://scosman.github.io/pelicans_riding_bicycles/
https://github.com/scosman/pelicans_riding_bicycles
https://scouts.yutori.com/6fd945b8-052c-43da-909f-b63999a7a799
'''.strip().splitlines()

def canonical(value):
    return value.split('#')[0].rstrip('/')

def request(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    raw = OUT / 'evidence' / (key + '.bin')
    meta = raw.with_suffix('.json')
    if raw.exists() and meta.exists():
        return raw.read_bytes(), json.loads(meta.read_text(encoding='utf8'))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'PelicanMap-SourceAudit/1.0'}), timeout=40) as r:
            data = r.read(12 * 1024 * 1024)
            info = {'url':url,'finalUrl':r.url,'status':r.status,'contentType':r.headers.get('Content-Type',''),'sha256':hashlib.sha256(data).hexdigest()}
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(data)
        meta.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf8')
        return data, info
    except Exception as exc:
        return b'', {'url':url,'error':str(exc)}

def inspect(url):
    fetch = 'https://api.github.com/gists/' + url.rsplit('/',1)[-1] if 'gist.github.com/' in url else url
    if 'fedi.simonwillison.net/@simon/' in url:
        fetch = 'https://fedi.simonwillison.net/api/v1/statuses/' + url.rsplit('/',1)[-1]
    data, info = request(fetch)
    result = {'sourceUrl':url, 'fetch':info}
    if not data:
        return result
    if fetch.startswith('https://api.github.com/gists/'):
        gist = json.loads(data)
        result.update(created= gist.get('created_at'), updated=gist.get('updated_at'), description=gist.get('description'), revision=gist.get('history',[{}])[0].get('version'),
                      files=[{'name':name,'url':f['raw_url'],'text':f.get('content',''),'truncated':f.get('truncated')} for name,f in gist['files'].items()])
        return result
    if '/api/v1/statuses/' in fetch:
        status=json.loads(data)
        result.update(created=status.get('created_at'), text=BeautifulSoup(status.get('content',''),'html.parser').get_text(' ',strip=True),
                      media=status.get('media_attachments'),links=re.findall(r'https?://[^\s<>"\']+',status.get('content','')))
        return result
    if url.endswith('.glb'):
        result['format']='glb'
        return result
    soup = BeautifulSoup(data,'html.parser')
    body = soup.select_one('.entry-body') or soup.select_one('article') or soup.select_one('main') or soup
    result.update(title=soup.title.get_text(' ',strip=True) if soup.title else '', text=body.get_text(' ',strip=True),
                  dates=[x.get('datetime') or x.get_text(' ',strip=True) for x in soup.select('time')],
                  images=[{'url':urljoin(url,x.get('src','')),'alt':x.get('alt','')} for x in body.select('img[src]')],
                  links=list(dict.fromkeys(urljoin(url,x['href']) for x in body.select('a[href]'))),
                  inlineSvgCount=len(body.select('svg')),preCount=len(body.select('pre')))
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    items=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))['items']
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        sources=list(pool.map(inspect,URLS))
    for s in sources:
        url=canonical(s['sourceUrl'])
        exact=[x for x in items if canonical(x['sourceUrl'])==url]
        evidence=[x for x in items if any(url==canonical(v) for v in x.get('ingestion',{}).get('evidence',[]))]
        s['existing']=[{'id':x['id'],'model':x['model'],'date':x['date'],'case':x.get('caseVisible'),'timeline':x.get('timelineVisible'),'media':[m['src'] for m in x['media']]} for x in exact]
        s['existingEvidenceIds']=[x['id'] for x in evidence]
        print(json.dumps({'url':s['sourceUrl'],'status':s['fetch'].get('status',s['fetch'].get('error')),'existing':len(exact),'works':sum(x.get('caseVisible',False) for x in exact),'images':len(s.get('images',s.get('media',[]))),'files':[(f['name'],len(f['text'])) for f in s.get('files',[])]},ensure_ascii=False),flush=True)
    (OUT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf8')

def details():
    sources=json.loads((OUT/'sources.json').read_text(encoding='utf8'))
    items=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))['items']
    for s in sources:
        if any(k in s['sourceUrl'] for k in ['tags/','search/','github.com/simonw/pelican-bicycle','nilethebot','dev.to/','pelicanzoo','hardprompts','scouts','scosman','huggingface','six-months']):
            continue
        print('\nURL',s['sourceUrl'])
        print('DATES',s.get('created') or s.get('dates'))
        print('TEXT',s.get('text','')[:6000])
        for f in s.get('files',[]):
            print('FILE',f['name'],'revision',s.get('revision'),'created',s.get('created'),'description',s.get('description'))
            print('HEAD',f['text'][:900])
            print('SVG BLOCKS',len(re.findall(r'<svg\b',f['text'],re.I)))
        for img in s.get('images',s.get('media',[])):
            url=img.get('url','')
            name=urlparse(url).path.rsplit('/',1)[-1]
            matches=[x['id'] for x in items if any(name and (name in m['src'] or name in m.get('source','')) for m in x['media'])]
            print('IMG',url,img.get('alt',img.get('description','')),'LOCAL',matches)
        print('LINKS',[x for x in s.get('links',[]) if any(k in x for k in ['gist.','static.','/202','github','pelican'])][:40])

def expand():
    sources=json.loads((OUT/'sources.json').read_text(encoding='utf8'))
    gids={}
    for s in sources:
        if not re.search(r'simonwillison.net/202[456]/',s['sourceUrl']):
            continue
        for u in s.get('links',[]):
            for gid in re.findall(r'gist.github.com/simonw/([a-f0-9]{32})',unquote(u)):
                gids.setdefault(gid,[]).append(s['sourceUrl'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(inspect,['https://gist.github.com/simonw/'+gid for gid in gids]))
    for s in results:
        s['parents']=gids[s['sourceUrl'].rsplit('/',1)[-1]]
        print(json.dumps({'gist':s['sourceUrl'],'created':s.get('created'),'error':s['fetch'].get('error'),'parents':s['parents'],
          'files':[{'name':f['name'],'length':len(f['text']),'models':re.findall(r'Model:\s*\*\*(.*?)\*\*',f['text']),'svgs':len(re.findall(r'<svg\b',f['text'],re.I)), 'animated':bool(re.search(r'<(?:animate\w*|set)\b|@keyframes',f['text'],re.I))} for f in s.get('files',[])]},ensure_ascii=False),flush=True)
    (OUT/'linked-gists.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')

def summary():
    sources=json.loads((OUT/'sources.json').read_text(encoding='utf8'))
    items=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))['items']
    for s in sources:
        print('\nURL',s['sourceUrl'])
        print('IMAGES',[(x.get('url'),[i['id'] for i in items if any(urlparse(x.get('url','')).path.rsplit('/',1)[-1] in m['src'] for m in i['media'])]) for x in s.get('images',[])])
        if any(k in s['sourceUrl'] for k in ['scouts','scosman','pelicanzoo','hardprompts','dev.to/']):
            print('TEXT',s.get('text','')[:1200])
            data,_=request(s['fetch']['url'])
            soup=BeautifulSoup(data,'html.parser')
            print('SCRIPTS',[(x.get('src'),len(x.text)) for x in soup.select('script')][:12])
            print('SVGATTR',[(x.name,x.attrs) for x in soup.select('pre,svg')][:3])
        if any(k in s['sourceUrl'] for k in ['kimi-k25','Apr/16','115572','introducing-gpt']):
            print('TEXT',s.get('text','')[:2400])

if __name__=='__main__':
    if 'expand' in sys.argv: expand()
    elif 'summary' in sys.argv: summary()
    elif 'details' in sys.argv: details()
    else: main()
