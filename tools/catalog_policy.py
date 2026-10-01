"""Shared rules for manual builds, sync and automatic publication."""
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

DEMO_ORIGIN = 'https://pelicanmap-demos.aveniqa.com'


def local_demo(url):
    parsed = urlsplit(url or '')
    return parsed.scheme == 'https' and parsed.netloc == urlsplit(DEMO_ORIGIN).netloc and parsed.path.startswith('/demos/')


def merge_additions(local, remote):
    merged = {x['id']: x for x in local}
    for item in remote:
        if item['id'] not in merged or item['id'].startswith('ingest-'):
            merged[item['id']] = item
    return list(merged.values())


def apply_demo_policy(items, reviews=None):
    if reviews is None:
        reviews = json.loads((Path(__file__).resolve().parents[1]/'site/demo-reviews.json').read_text(encoding='utf8'))
    result = copy.deepcopy(items)
    for item in result:
        original = item.get('demoUrl') or item.get('previewUrl') or ''
        review = reviews.get(item['id'], {})
        demo = review.get('demoUrl') or original
        controls = review.get('controls', {})
        item['interactive'] = bool(local_demo(demo) and controls.get('zh') and controls.get('en'))
        item['interactionControls'] = controls if item['interactive'] else {}
        item['demoUrl'] = demo if item['interactive'] else ''
        item['previewUrl'] = original if local_demo(original) and not item['interactive'] and item.get('format') != 'svg' else ''
        if original and not local_demo(original):
            item['demoSourceUrl'] = original
            if not item.get('externalUrl'):
                item['externalUrl'] = original
        if not item['interactive'] and item.get('mediaStatus') == 'interactive':
            item['mediaStatus'] = 'local'
    return result


def playable_records(items):
    chosen = {}
    by_id = {x['id']:x for x in items}
    for item in sorted(items, key=lambda x: (x.get('date', ''), x['id']), reverse=True):
        if item.get('interactive') and local_demo(item.get('demoUrl')):
            canonical=by_id.get(item.get('canonicalId'))
            if canonical and canonical.get('interactive') and canonical.get('demoUrl')==item['demoUrl']:
                item=canonical
            chosen.setdefault(item['demoUrl'], item)
    return list(chosen.values())
