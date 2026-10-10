"""Purge only stale Pelican Map entry URLs, then verify their actual public bytes."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from check_incremental_cache import BASE, ENTRIES, check_cache

ZONE_ID = '1781c0b726803f61db5650c49a8d8f09'
TOKEN_CONFIG = Path.home()/'.config/pelicanmap/cloudflare.json'
ALLOWED_URLS = {BASE+'/'+(name.removesuffix('index.html') if name.endswith('index.html') else name)
                for name in ENTRIES}


def purge_payload(urls):
    urls = list(dict.fromkeys(urls))
    if not urls or any(url not in ALLOWED_URLS for url in urls):
        raise ValueError('Only exact Pelican Map entry URLs may be purged')
    return {'files': urls}


def load_token(token_file=None):
    if token_file is None:
        token = os.environ.get('CLOUDFLARE_API_TOKEN', '').strip()
        if token:
            return token
        if TOKEN_CONFIG.is_file():
            config = json.loads(TOKEN_CONFIG.read_text(encoding='utf-8-sig'))
            token_file = Path(config['tokenFile'])
    if token_file is None:
        raise ValueError('Set CLOUDFLARE_API_TOKEN or supply --token-file')
    text = Path(token_file).read_text(encoding='utf-8-sig').strip()
    matches = set(re.findall(r'cfut_[A-Za-z0-9_-]+', text))
    if not matches:
        matches = set(re.findall(r'(?m)^\s*(?:CLOUDFLARE_API_TOKEN|CF_API_TOKEN)\s*=\s*[\"\']?([A-Za-z0-9_-]+)', text))
    if not matches and re.fullmatch(r'[A-Za-z0-9_-]{20,}', text):
        matches = {text}
    if len(matches) != 1:
        raise ValueError('Credential file must identify exactly one API token')
    return matches.pop()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def request_purge(token, payload):
    request = urllib.request.Request(
        'https://api.cloudflare.com/client/v4/zones/'+ZONE_ID+'/purge_cache',
        data=json.dumps(payload).encode(), method='POST',
        headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json',
                 'User-Agent': 'PelicanMap-Incremental-Purge/1.0'})
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            status, body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        status = error.code
        try:
            body = json.loads(error.read())
        except ValueError:
            body = {}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {'success': False, 'error': 'Cloudflare API transport failed'}
    return {'httpStatus': status, 'success': body.get('success') is True,
            'errorCodes': [row.get('code') for row in body.get('errors', [])],
            'result': {'id': (body.get('result') or {}).get('id')}}


def run(batch, token_file=None):
    before = check_cache(batch/'pelicanmap-update.tar.gz')
    (batch/'canonical-cache-check.json').write_text(json.dumps(before, indent=2)+'\n', encoding='utf8')
    if not before['stale']:
        return {'status': 'no-cache-refresh-needed', 'canonicalCache': before}
    urls = [row['url'] for row in before['stale']]
    payload = purge_payload(urls)
    result = request_purge(load_token(token_file), payload)
    result.update(checkedAt=dt.datetime.now(dt.timezone.utc).isoformat(), operation='purge_files', urls=urls)
    result['status'] = 'purge-accepted-awaiting-verification' if result['success'] else 'purge-failed'
    previous_file = batch/'cloudflare-purge.json'
    previous = json.loads(previous_file.read_text(encoding='utf8')) if previous_file.exists() else None
    previous_file.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    if result['success']:
        result['canonicalCache'] = check_cache(batch/'pelicanmap-update.tar.gz')
        result['status'] = ('purged-and-verified' if not result['canonicalCache']['stale']
                            else 'cache-refresh-required')
    else:
        result['status'] = 'purge-failed'
    history_file = batch/'cloudflare-purge-attempts.json'
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    if not history and previous is not None:
        history.append(previous)
    history.append(result)
    for path, value in [(history_file, history), (previous_file, result)]:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--token-file', type=Path)
    args = parser.parse_args()
    result = run(args.batch.resolve(), args.token_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result['status'] not in ['no-cache-refresh-needed', 'purged-and-verified'])
