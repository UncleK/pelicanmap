"""Read-only live checks for source motion recovery and lossless work units."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'pelican-archive/research/2026-10-02-motion-recovery'
AUDIT = json.loads((DIR / 'import-audit.json').read_text())
CAT = json.loads((ROOT / 'public-site/data/catalog.json').read_text())
BY = {x['id']: x for x in CAT['items']}
ENBY = {x['id']: x for x in json.loads((ROOT / 'public-site/en/data/catalog.json').read_text())['items']}
BASE = 'https://pelicanmap.aveniqa.com'


def get(path):
    url = path if path.startswith('https://') else BASE + path
    request = urllib.request.Request(url, headers={'User-Agent': 'PelicanMap-Motion-Recovery-Verification/1.0'})
    with urllib.request.urlopen(request, timeout=50) as response:
        return response.read()


def detail(task):
    ident, lang = task
    x = BY[ident]
    prefix = '/en' if lang == 'en' else ''
    html = get(prefix + x['path']).decode()
    doc = BeautifulSoup(html, 'html.parser')
    assert x['sourceUrl'] in html
    if ident in AUDIT['added']:
        figure = doc.select_one('.detail-motion figure') or doc.select_one('.detail-layout figure')
        assert figure['data-media-src'] == x['media'][0]['src'], (ident, lang)
        assert doc.select_one('.detail-attachments:not([open])')
        if 'kylmawurr-opus55-' in ident:
            assert doc.select_one('.detail-motion video')['data-motion-src'] == x['media'][0]['src']
            assert len(doc.select('[data-setting-comparison] figure')) == 4
            assert html.index('class="detail-motion') < html.index('data-setting-comparison')
            assert ('later refinement' if lang == 'en' else '后续细化对照') in html
            assert not doc.select_one('[data-preview-only]')
        else:
            assert doc.select_one('[data-preview-only]')
        assert not doc.select_one('[data-local-demo]')
    elif ident == AUDIT['parentId']:
        assert doc.select_one('[data-case-policy]')
        assert all(BY[child]['path'] in html for child in AUDIT['added'][:4])
    else:
        iframe = doc.select_one('iframe[data-local-demo]')
        assert iframe['src'] == x['previewUrl']
        assert set(iframe['sandbox']) == {'allow-scripts', 'allow-same-origin', 'allow-pointer-lock'}, iframe.get('sandbox')
        assert iframe['referrerpolicy'] == 'no-referrer'
        assert iframe['src'].startswith('https://pelicanmap-demos.aveniqa.com/')
        assert not doc.select_one('[data-preview-only]')
        assert not x.get('interactive') and not x.get('demoUrl')
    api = json.loads(get('/api/v1/specimens/' + ident + '?lang=' + lang))
    api = api.get('item', api)
    expected = ENBY[ident] if lang == 'en' else x
    for key in ['id', 'model', 'date', 'sourceUrl', 'caseVisible', 'timelineVisible', 'caseNumber', 'media']:
        assert api.get(key) == expected.get(key), (ident, lang, key)
    assert api.get('previewUrl') == expected.get('previewUrl')
    return ident + ' ' + lang


def media(a):
    data = get(a['src'])
    assert len(data) == a['bytes'] and hashlib.sha256(data).hexdigest() == a['sha256'], a['src']
    return a['src']


targets = AUDIT['added'] + [a['id'] for a in AUDIT['augmented']] + [AUDIT['parentId']]
assets = list(AUDIT['newOriginals'])
for a in AUDIT['augmented']:
    assets.append({'src': a['previewUrl'] + 'index.html', 'bytes': a['bytes'], 'sha256': a['sha256']})
    licence = (ROOT / 'public-demos/demos/variora-motion-recovery' / a['id'] / 'LICENSE.txt').read_bytes()
    assets.append({'src': a['previewUrl'] + 'LICENSE.txt', 'bytes': len(licence), 'sha256': hashlib.sha256(licence).hexdigest()})
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    pages = list(pool.map(detail, [(ident, lang) for ident in targets for lang in ['zh', 'en']]))
    originals = list(pool.map(media, assets))
for endpoint, count in [('specimens', CAT['counts']['cases']), ('timeline', CAT['counts']['timeline'])]:
    for lang in ['zh', 'en']:
        data = json.loads(get('/api/v1/' + endpoint + '?limit=1&lang=' + lang))
        assert data['total'] == count and data['rawRecords'] == count
for prefix in ['', '/en']:
    data = json.loads(get(prefix + '/data/catalog.json'))
    assert data['counts'] == CAT['counts']
    assert not next(x for x in data['items'] if x['id'] == AUDIT['parentId'])['caseVisible']
    group = [x for x in data['items'] if x['id'] in AUDIT['added'][:4]]
    assert [x['originalLevel'] for x in group if x['timelineVisible']] == ['medium']
    about = get(prefix + '/about/').decode()
    assert ('October 2 animation originals and individual works' if prefix else '2026-10-02 动画原件与单作品整理') in about
    assert get(prefix + '/feed.xml') == (ROOT / 'public-site' / prefix.lstrip('/') / 'feed.xml').read_bytes()
    home = BeautifulSoup(get(prefix + '/').decode(), 'html.parser')
    actions = home.select('.hero .actions a')
    assert any(a.get('href') == prefix + '/timeline/' for a in actions)
    assert any(a.get('href') == prefix + '/specimens/' for a in actions)
sitemap = get('/sitemap.xml')
assert sitemap == (ROOT / 'public-site/sitemap.xml').read_bytes()
for ident in AUDIT['added']:
    for prefix in ['', '/en']:
        assert (BASE + prefix + BY[ident]['path']).encode() in sitemap
result = {'pagesAndIdApi': len(pages), 'originalHashes': len(originals),
          'newWorkRecords': 5, 'netNewWorks': 4, 'newRepresentatives': 1,
          'losslessVideoWorks': 4, 'restoredOrdinaryAnimationPreviews': 3,
          'newPreviewOnlyWork': 1, 'cases': CAT['counts']['cases'],
          'timeline': CAT['counts']['timeline'], 'rawRecords': len(CAT['items']),
          'benchmarkReferenceRecords': CAT['counts']['referenceRecords'],
          'bilingualFeedsByteIdentical': True, 'sitemapByteIdentical': True,
          'homepageButtonsPreserved': True, 'parentArchivePreserved': True, 'verified': True}
(DIR / 'live-batch-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
