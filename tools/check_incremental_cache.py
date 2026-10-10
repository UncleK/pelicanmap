"""Check stable public entry URLs, so a fresh versioned URL cannot hide stale CDN data."""
import argparse
import json
from pathlib import Path
import tarfile
import urllib.error
import urllib.request

from check_delta_release import check_live_bytes

BASE = 'https://pelicanmap.aveniqa.com'
ENTRIES = ('index.html', 'en/index.html', 'data/catalog.json', 'en/data/catalog.json',
           'data/catalog.csv', 'en/data/catalog.csv', 'llms.txt', 'en/llms.txt',
           'index.md', 'en/index.md', 'openapi.json', 'feed.xml', 'en/feed.xml', 'sitemap.xml')


def check_cache(archive):
    with tarfile.open(archive) as source:
        manifest = json.load(source.extractfile('release-delta.json'))
    checked, stale = [], []
    for name in ENTRIES:
        key = 'site/'+name
        if key not in manifest['changed']:
            continue
        path = name.removesuffix('index.html') if name.endswith('index.html') else name
        url = BASE+'/'+path
        headers = {}
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'PelicanMap-Canonical-Verify/1.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                headers = {key: response.headers.get(key) for key in ['CF-Cache-Status', 'Age', 'Cache-Control']}
            check_live_bytes(key, data, manifest['changed'][key])
            checked.append({'url': url, 'headers': headers})
        except (ValueError, urllib.error.HTTPError) as error:
            stale.append({'url': url, 'error': str(error), 'headers': headers})
    return {'status': 'passed' if not stale else 'cache-refresh-required', 'checked': checked, 'stale': stale}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    result = check_cache(args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['stale']))
