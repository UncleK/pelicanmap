"""Archive primary-source evidence for Nile's remaining pre-2026 backlinks.

Index labels are not provenance. This command never changes museum records.
"""
import concurrent.futures
import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import audit_user_history_links as fetcher

ROOT = fetcher.ROOT
OUT = ROOT / 'pelican-archive/research/2026-10-01-nile-history'
fetcher.OUT = OUT


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = 'https://nilethebot.github.io/pelican-timeline/'
    soup = BeautifulSoup(fetcher.request(index)[0], 'html.parser')
    links = []
    excluded = []
    for position, entry in enumerate(soup.select('article.entry'), 1):
        if position <= 20:
            continue
        urls = [x['href'] for x in entry.select('a[href]') if 'simonwillison.net/' in x['href']]
        assert len(urls) == 1
        url = urls[0]
        if not re.search(r'/202[45]/', url):
            excluded.append({'position': position, 'sourceUrl': url, 'reason': 'Source falls outside pre-2026 intake.'})
            continue
        links.append((position, url))
    catalog = json.loads((ROOT / 'public-site/data/catalog.json').read_text(encoding='utf8'))
    items = catalog['items']
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        sources = list(pool.map(fetcher.inspect, [url for _, url in links]))
    for (position, url), source in zip(links, sources):
        source['position'] = position
        source['existing'] = [{'id': x['id'], 'model': x['model'], 'case': x.get('caseVisible'), 'media': x['media']}
                              for x in items if fetcher.canonical(x['sourceUrl']) == fetcher.canonical(url)]
        for image in source.get('images', []):
            name = urlparse(image['url']).path.rsplit('/', 1)[-1]
            image['existingIds'] = [x['id'] for x in items if any(
                image['url'] == m.get('source') or name and name in m['src'] for m in x['media'])]
        print(json.dumps({'position': position, 'url': url, 'status': source['fetch'],
                          'images': source.get('images'), 'existing': [x['id'] for x in source['existing']]}, ensure_ascii=False), flush=True)
    result = {'index': index, 'scope': 'positions 21–60, primary URLs dated before 2026',
              'beforeCounts': catalog['counts'], 'sources': sources, 'outsideScope': excluded}
    (OUT / 'sources.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def gists():
    result = json.loads((OUT / 'sources.json').read_text(encoding='utf8'))
    gids = {}
    for source in result['sources']:
        if source['position'] > 30:
            continue
        for url in source.get('links', []):
            for gid in re.findall(r'gist.github.com/simonw/([a-f0-9]{32})', url):
                gids.setdefault(gid, []).append(source['sourceUrl'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        sources = list(pool.map(fetcher.inspect, ['https://gist.github.com/simonw/' + gid for gid in gids]))
    for source in sources:
        source['parents'] = gids[source['sourceUrl'].rsplit('/', 1)[-1]]
        print(json.dumps({'gist': source['sourceUrl'], 'created': source.get('created'), 'updated': source.get('updated'),
                          'revision': source.get('revision'), 'parents': source['parents'], 'files':
                          [{'name': f['name'], 'length': len(f['text']), 'head': f['text'][:400],
                            'svg': len(re.findall(r'<svg\b', f['text'])),
                            'animated': bool(re.search(r'<(?:animate\w*|set)\b|@keyframes', f['text'], re.I))}
                           for f in source.get('files', [])]}, ensure_ascii=False), flush=True)
    (OUT / 'linked-gists.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    import sys
    gists() if '--gists' in sys.argv else main()
