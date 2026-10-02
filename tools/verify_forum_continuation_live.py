"""Read-only verification of the reviewed forum and public-X continuation release."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'pelican-archive/research/2026-10-02-forum-continuation'
AUDIT = json.loads((DIR / 'import-audit.json').read_text())
CAT = json.loads((ROOT / 'site/catalog.json').read_text())
BY = {item['id']: item for item in CAT['items']}
ENBY = {item['id']: item for item in json.loads((ROOT / 'public-site/en/data/catalog.json').read_text())['items']}
BASE = 'https://pelicanmap.aveniqa.com'


def get(path):
    request = urllib.request.Request(
        BASE + path, headers={'User-Agent': 'PelicanMap-Forum-Continuation-Verification/1.0'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def detail(task):
    ident, language = task
    item = BY[ident]
    prefix = '/en' if language == 'en' else ''
    html = get(prefix + item['path']).decode()
    doc = BeautifulSoup(html, 'html.parser')
    assert item['sourceUrl'] in html, (ident, language, 'source')
    assert doc.select_one('main figure')['data-media-src'] == item['media'][0]['src']
    if item['generationConditions']['previewOnly']:
        assert doc.select_one('[data-preview-only]') is not None
        assert doc.select_one('[data-detail-primary]') is None
    else:
        assert doc.select_one('[data-detail-primary]')['data-detail-primary'] == 'media'
    assert doc.select_one('[data-local-demo]') is None
    data = json.loads(get('/api/v1/specimens/' + ident + '?lang=' + language))
    data = data.get('item', data)
    expected = ENBY[ident] if language == 'en' else item
    for key in ['id', 'model', 'date', 'sourceUrl', 'caseVisible', 'timelineVisible', 'caseNumber', 'media']:
        assert data[key] == expected[key], (ident, language, key)
    return ident + ' ' + language


def media(asset):
    raw = get(asset['src'])
    assert len(raw) == asset['bytes'] and hashlib.sha256(raw).hexdigest() == asset['sha256'], asset['src']
    return asset['src']


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    pages = list(pool.map(detail, [(ident, lang) for ident in AUDIT['added'] for lang in ['zh', 'en']]))
    originals = list(pool.map(media, AUDIT['newOriginals']))

for endpoint, expected in [('specimens', CAT['counts']['cases']), ('timeline', CAT['counts']['timeline'])]:
    for lang in ['zh', 'en']:
        data = json.loads(get('/api/v1/' + endpoint + '?limit=1&lang=' + lang))
        assert data['total'] == expected and data['rawRecords'] == expected, (endpoint, lang)
for prefix in ['', '/en']:
    catalog = json.loads(get(prefix + '/data/catalog.json'))
    assert catalog['counts'] == CAT['counts']
    html = get(prefix + '/about/').decode()
    assert ('2026-10-02 论坛续查与 X 原帖' if not prefix else 'October 2 forum follow-up and X originals') in html

result = {
    'pagesAndIdApi': len(pages), 'newOriginalHashes': len(originals),
    'cases': CAT['counts']['cases'], 'timeline': CAT['counts']['timeline'],
    'newCases': 16, 'newRepresentatives': 16,
    'benchmarkReferenceRecords': CAT['counts']['referenceRecords'], 'verified': True,
}
(DIR / 'live-batch-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
