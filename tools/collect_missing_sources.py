"""Collect the project's already-listed sources; never execute downloaded code."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'pelican-web'
AUDIT = ROOT / 'pelican-archive/audit/2026-09-27'
AUDIT.mkdir(parents=True, exist_ok=True)
RAW = AUDIT / 'sources'
RAW.mkdir(exist_ok=True)
for name in ['data.js', 'index.html', 'COLLECTED.md']:
    backup = AUDIT / ('before-' + name)
    if not backup.exists():
        shutil.copy2(WEB / name, backup)
data = json.loads((WEB / 'data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))

posts = {}
for page in sorted((ROOT / 'pelican-archive/raw/simon-tag-pages').glob('page*.html')):
    soup = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
    for segment in soup.select('.segment'):
        link = segment.select_one('a[rel=bookmark]') or segment.select_one('.entryFooter a[title]')
        if not link:
            continue
        url = urljoin('https://simonwillison.net', link['href'])
        heading = segment.select_one('h3 a') or segment.select_one('p strong a')
        title = heading.get_text(' ', strip=True) if heading else segment.get_text(' ', strip=True)[:120]
        parts = urlsplit(url).path.strip('/').split('/')
        months = dict(zip('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), range(1, 13)))
        date = f'{parts[0]}-{months[parts[1]]:02d}-{int(parts[2]):02d}'
        posts[url] = dict(title=title, url=url, date=date, page=page.name, kind=segment.get('data-type'))
(AUDIT / 'simon-posts-complete.json').write_text(json.dumps(list(posts.values()), ensure_ascii=False, indent=2), encoding='utf-8')

jobs = {url: 'simon' for url in posts}
for group in ['timeline', 'gallery']:
    for item in data[group]:
        if item.get('media') and not item['media'].startswith(('http:', 'https:')):
            continue
        url = item.get('url', '')
        status = re.search(r'https://(?:x|twitter)\.com/[^/]+/status/(\d+)', url)
        if status:
            jobs['https://api.fxtwitter.com/status/' + status[1]] = 'x-api'
        elif url.startswith('https:'):
            jobs[url] = group
        if item.get('media', '').startswith(('http:', 'https:')):
            jobs[item['media']] = 'external-media-page'

previous = {}
manifest_path = AUDIT / 'retrieval.json'
if manifest_path.exists():
    previous = {x['url']: x for x in json.loads(manifest_path.read_text(encoding='utf-8'))}

def fetch(job):
    url, kind = job
    old = previous.get(url)
    if old and old.get('status') == 200 and (ROOT / old['file']).is_file():
        return old
    result = {'url': url, 'kind': kind}
    try:
        with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 (Pelican personal archive validation)'}), timeout=25) as response:
            payload = response.read(25 * 1024 * 1024)
            content_type = response.headers.get('content-type', '')
            suffix = '.json' if 'json' in content_type else '.html'
            path = RAW / (hashlib.sha256(url.encode()).hexdigest()[:20] + suffix)
            path.write_bytes(payload)
            result.update(status=response.status, content_type=content_type, bytes=len(payload), final_url=response.url, file=path.relative_to(ROOT).as_posix())
    except Exception as exc:
        result.update(status=getattr(exc, 'code', None), error=str(exc))
    return result

results = []
with ThreadPoolExecutor(max_workers=6) as pool:
    futures = [pool.submit(fetch, job) for job in jobs.items()]
    for n, future in enumerate(as_completed(futures), 1):
        result = future.result()
        results.append(result)
        if n % 20 == 0 or result.get('error'):
            print(f'{n}/{len(jobs)} {result["url"]}: {result.get("status") or result.get("error")}', flush=True)
        previous[result['url']] = result
        manifest_path.write_text(json.dumps(list(previous.values()), ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'posts': len(posts), 'sources': len(results), 'downloaded': sum(x.get('status') == 200 for x in results), 'failed': [x for x in results if x.get('status') != 200]}, ensure_ascii=False), flush=True)
