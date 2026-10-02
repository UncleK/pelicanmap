"""Read-only verification of the published policy and unchanged artwork catalog."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://pelicanmap.aveniqa.com'
NONCE = str(time.time_ns())
checks = 0


def get_json(path):
    global checks
    # Public API query keys are allowlisted; cache-bust only static resources.
    separator = '&' if '?' in path else '?'
    url = BASE + path
    if not path.startswith('/api/'):
        url += separator + 'authority=' + NONCE
    request = urllib.request.Request(url, headers={
        'User-Agent': 'PelicanMap-CollectingAuthorityVerifier/1.0',
        'Cache-Control': 'no-cache',
    })
    with urllib.request.urlopen(request, timeout=40) as response:
        assert response.status == 200, path
        raw = response.read()
    checks += 1
    return json.loads(raw), raw


policy = json.loads((ROOT / 'site/collecting-policy.json').read_text(encoding='utf-8'))
remote_policy, raw_policy = get_json('/data/collecting-policy.json')
assert remote_policy == policy
assert remote_policy['publicationAuthority']['requiresPerBatchUserApproval'] is False
assert remote_policy['publicationAuthority']['reviewer'] == 'maintaining-agent'
assert remote_policy['publicationAuthority']['releaseChecksRequired'] is True
assert remote_policy['restrictedRetrievalFallback']['browser'] == 'user-already-signed-in-chrome'
assert remote_policy['restrictedRetrievalFallback']['bypassAccessControls'] is False

for prefix, lang in [('', 'zh'), ('/en', 'en')]:
    local_path = ROOT / 'public-site' / prefix.lstrip('/') / 'data/catalog.json'
    local = json.loads(local_path.read_text(encoding='utf-8'))
    remote, _ = get_json(prefix + '/data/catalog.json')
    assert remote == local, lang
    for route, count_key in [('specimens', 'cases'), ('timeline', 'timeline')]:
        data, _ = get_json('/api/v1/' + route + '?lang=' + lang + '&limit=1')
        assert data['total'] == local['counts'][count_key], (lang, route)
        assert data['rawRecords'] == local['counts'][count_key], (lang, route)
        assert all(not item.get('referenceOnly') for item in data['items'])

print(json.dumps({'checks': checks, 'directPublicationPolicy': 'verified',
                  'chromeFallbackPolicy': 'verified', 'bilingualCatalog': 'unchanged',
                  'policySha256': hashlib.sha256(raw_policy).hexdigest(),
                  'cases': local['counts']['cases'], 'timeline': local['counts']['timeline']},
                 ensure_ascii=False))
