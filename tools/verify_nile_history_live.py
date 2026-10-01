"""Public bilingual/media/API verification for the nine new 2025 works."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import verify_user_history_live as shared
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pelican-archive/research/2026-10-01-nile-history'
MANIFEST = json.loads((OUT / 'approved-manifest.json').read_text(encoding='utf8'))


def check(c):
    shared.check(c)
    x = shared.BY[c['id']]
    for m in x['media']:
        assert hashlib.sha256(shared.get(m['src'])).hexdigest() == m['sha256']
    assert x['date'] < '2026-01-01' and x['caseVisible'] and x['timelineVisible']
    for lang in ['zh', 'en']:
        url = '/api/v1/timeline?year=2025&lang=' + lang + '&q=' + quote(c['model']) + '&limit=50'
        result = json.loads(shared.get(url))
        assert c['id'] in {i['id'] for i in result['items']}, c['id']
        if x['dateBasis'] == 'source-reported-response-timestamp':
            prefix = '/en' if lang == 'en' else ''
            text = BeautifulSoup(shared.get(prefix + x['path']), 'html.parser').get_text()
            assert ('response timestamp in the original log' if lang == 'en' else '响应时间戳') in text
            assert '日期依据原文公开日' not in text
    return len(x['media'])


def main():
    stamp = hashlib.sha256((ROOT / 'site/catalog.json').read_bytes()).hexdigest()[:12]
    remote = json.loads(shared.get('/data/catalog.json?nile-history=' + stamp))
    assert remote == shared.LOCAL
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        media = sum(pool.map(check, MANIFEST['cases']))
    for lang in ['zh', 'en']:
        total = json.loads(shared.get('/api/v1/specimens?lang=' + lang + '&limit=1'))
        axis = json.loads(shared.get('/api/v1/timeline?lang=' + lang + '&limit=1'))
        assert total['total'] == remote['counts']['cases']
        assert axis['total'] == remote['counts']['timeline']
    result = {'works': 9, 'original_media_hashes': media, 'bilingual_details_and_id_api': 18,
              'bilingual_timeline_memberships': 18, 'counts': remote['counts']}
    (OUT / 'live-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
