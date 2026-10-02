"""Release-axis presentation, never a replacement for documented artwork dates."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def label_key(value):
    return re.sub(r'[\s_-]+', '-', str(value).strip().lower())

def apply_model_chronology(items):
    registry = json.loads((ROOT/'site/model-releases.json').read_text(encoding='utf8'))
    aliases = {}
    for row in registry['models']:
        assert re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?', row['date'])
        for label in [row['name'], *row['aliases']]:
            key = label_key(label)
            assert key not in aliases or aliases[key]['id'] == row['id'], label
            aliases[key] = row
    for item in items:
        item.pop('modelTimeline', None)
        if item.get('referenceOnly'):
            continue
        names = item.get('modelNames') or []
        # An incomplete label is not upgraded into a specific version by guesswork.
        label = names[0] if len(names) == 1 else item.get('model', '')
        row = (aliases.get(label_key(item.get('model',''))) or aliases.get(label_key(label))) if len(names) == 1 else None
        info = {'key': row['id'] if row else 'unverified:'+label_key(label),
                'label': row['name'] if row else label,
                'status': 'verified-release' if row else 'release-unverified'}
        if row:
            info.update(releaseDate=row['date'], datePrecision='day' if len(row['date'])==10 else 'month',
                        sourceUrl=row.get('url') or registry['sources'][row['source']])
            if ((item.get('date', '') and item['date'][:7] < row['date'][:7]) or
                (len(item.get('date',''))==10 and len(row['date'])==10 and item['date']<row['date'])):
                # Earlier source claims can reflect previews, aliases or mislabelling.
                # Preserve them and expose the discrepancy, never rewrite their date.
                info['sourceDatePredatesRelease'] = True
                info['status']='release-unverified'
                info['key']='unverified:'+label_key(label)
                info['candidateReleaseDate']=info.pop('releaseDate')
        item['modelTimeline'] = info
    return items

def timeline_year(item):
    return item.get('modelTimeline', {}).get('releaseDate', '')[:4] or 'unknown'

def timeline_month(item):
    return item.get('modelTimeline', {}).get('releaseDate', '')[:7] or 'unknown'

def ordered_timeline(items, sort='newest'):
    # Unknown releases stay last in BOTH directions; no invented release position.
    groups = {}
    for item in items:
        info = item.get('modelTimeline', {})
        key = info.get('key') or 'unverified:'+label_key(item.get('model', ''))
        groups.setdefault(key, []).append(item)
    known = [g for g in groups.values() if g[0].get('modelTimeline', {}).get('releaseDate')]
    unknown = [g for g in groups.values() if not g[0].get('modelTimeline', {}).get('releaseDate')]
    known.sort(key=lambda g:(g[0]['modelTimeline']['releaseDate'],g[0]['modelTimeline']['key']),reverse=sort!='oldest')
    unknown.sort(key=lambda g:g[0].get('modelTimeline',{}).get('key') or label_key(g[0].get('model','')))
    result = []
    for group in known+unknown:
        result.extend(sorted(group,key=lambda x:(x['date'],x['id']),reverse=sort!='oldest'))
    return result
