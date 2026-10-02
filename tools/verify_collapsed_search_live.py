"""User-requested browse controls and one removed recording; read-only checks."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public-site'
AUDIT = ROOT / 'pelican-archive/research/2026-10-02-collapsed-search'
REMOVED = 'x-keth-space-bunny-alpha-animation-2026-09-30'
BASE = 'https://pelicanmap.aveniqa.com'
local_only = '--local' in sys.argv


def get(path):
    if local_only:
        target = OUT / path.lstrip('/')
        if path.endswith('/'): target /= 'index.html'
        return target.read_bytes()
    request = urllib.request.Request(BASE+path, headers={
        'User-Agent': 'PelicanMap-Browse-Verifier/1.0', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=45) as response:
        assert response.status == 200
        return response.read()


catalog = json.loads(get('/data/catalog.json'))
expected = json.loads((OUT / 'data/catalog.json').read_text(encoding='utf8'))
assert catalog == expected
before = json.loads((AUDIT / 'before-catalog.json').read_text(encoding='utf8'))
by_id = {item['id']: item for item in catalog['items']}
assert {item['id'] for item in before['items']} <= set(by_id)
for previous in before['items']:
    current = by_id[previous['id']]
    for key, value in previous.items():
        if key == 'caseNumber': continue
        if previous['id'] == REMOVED and key in {'caseRole', 'caseVisible', 'timelineVisible', 'caseReview'}: continue
        assert current[key] == value, (previous['id'], key)
removed = by_id[REMOVED]
assert removed['caseRole'] == 'context'
assert not removed['caseVisible'] and not removed['timelineVisible']
assert removed['caseNumber'] is None
assert catalog['counts']['cases'] >= before['counts']['cases']-1
assert catalog['counts']['timeline'] >= before['counts']['timeline']-1
assert catalog['counts']['records'] >= before['counts']['records']
pages = 0
for prefix in ['', '/en']:
    assert json.loads(get(prefix+'/data/catalog.json')) == json.loads((OUT / prefix.lstrip('/') / 'data/catalog.json').read_text(encoding='utf8'))
    for scope in ['specimens', 'timeline']:
        for suffix in ['', 'page/2/']:
            path = prefix+'/'+scope+'/'+suffix
            page = BeautifulSoup(get(path), 'html.parser')
            assert not page.select_one('.page-top p')
            panel = page.select_one('[data-search]')
            assert panel.has_attr('hidden')
            toggle = page.select_one('[data-search-toggle]')
            assert toggle['aria-expanded'] == 'false' and toggle['aria-controls'] == panel['id']
            assert [bool(button.has_attr(key)) for button,key in zip(page.select('.browse-buttons button'), ['data-search-toggle','data-sort-toggle','data-density-toggle'])] == [True]*3
            assert not page.select_one('[data-results] a[href*="'+REMOVED+'"]')
            if not local_only:
                for selector in ['script[src^="/assets/browse.js"]', 'link[href^="/assets/site.css"]']:
                    asset = page.select_one(selector)
                    url = asset.get('src') or asset['href']
                    assert get(url) == (OUT / url.split('?')[0].lstrip('/')).read_bytes()
            pages += 1
    for path in ['feed.xml','data/catalog.csv','llms.txt']:
        assert get(prefix+'/'+path) == (OUT / prefix.lstrip('/') / path).read_bytes()
    if not local_only:
        lang = 'en' if prefix else 'zh'
        for scope, count in [('specimens','cases'),('timeline','timeline')]:
            api = json.loads(get('/api/v1/'+scope+'?limit=1&lang='+lang))
            assert api['total'] == catalog['counts'][count]
        search = json.loads(get('/api/v1/specimens?q=space-bunny-alpha&lang='+lang))
        assert not any(item['id'] == REMOVED for item in search['items'])
        record = json.loads(get('/api/v1/specimens/'+REMOVED+'?lang='+lang))
        assert record['caseVisible'] is False and record['timelineVisible'] is False
    detail = BeautifulSoup(get(prefix+removed['path']), 'html.parser')
    assert detail.find('a', href=removed['sourceUrl'])
    assert detail.select_one('[data-case-policy]')
for media in removed['media']:
    assert hashlib.sha256(get(media['src'])).digest() == hashlib.sha256((OUT / media['src'].lstrip('/')).read_bytes()).digest()
assert get('/sitemap.xml') == (OUT / 'sitemap.xml').read_bytes()
if not local_only:
    assert get('/openapi.json') == (OUT / 'openapi.json').read_bytes()
result = {'mode': 'local' if local_only else 'live', 'bilingualListingPages': pages,
          'cases': catalog['counts']['cases'], 'timeline': catalog['counts']['timeline'],
          'preservedRecords': len(by_id), 'removedFromMainCollection': REMOVED,
          'originalMediaPreserved': True, 'collapsedControlsAndPublicResources': 'passed'}
(AUDIT / ('local-checks.json' if local_only else 'live-checks.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
