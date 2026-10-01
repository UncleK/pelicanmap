"""Explicit source review for three outputs, not an unattended classifier.

The user supplied the Nile index. Its mixed descriptions/dates are not evidence;
only the linked author's labelled originals are used. Existing works stay intact.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pelican-archive/research/2026-10-01-nile-early'
GEMMA = ['simon-gemma3n-ollama-2025-06-26', 'simon-gemma3n-mlx-2025-06-26']


def save_original(path, data):
    if path.exists():
        assert path.read_bytes() == data, 'Refusing to overwrite historical evidence'
    else:
        path.write_bytes(data)


def approve():
    staged = json.loads((OUT / 'manifest.json').read_text(encoding='utf8'))
    approved = copy.deepcopy(staged)
    approved['reviewed'] = True
    approved['cases'] = [x for x in approved['cases'] if x['id'] != 'simon-mistral-small32-q4-2025-06-20']
    approved['review'] = {
        'method': 'Original articles and all four original previews inspected; 834 archived media compared by SHA and standardised render, nearest candidates manually checked.',
        'excluded': [{'id': 'simon-mistral-small32-q4-2025-06-20', 'canonicalId': 'x-1936219485431873899-b1334387', 'reason': 'Same distinctive drawing as the existing X screenshot, despite JPEG/PNG size differences. Article-update timing is not proven; no new work or guessed date correction.'}],
        'timeline': 'Only the sole Grok output enters the timeline. Gemma variants lack an explicit default/medium; do not invent a representative.',
    }
    assert len(approved['cases']) == 3
    save_original(OUT / 'approved-manifest.json', (json.dumps(approved, ensure_ascii=False, indent=2) + '\n').encode())
    if not (OUT / 'before-published-catalog.json').exists():
        save_original(OUT / 'before-published-catalog.json', (ROOT / 'public-site/data/catalog.json').read_bytes())
    return approved


def apply_reviews():
    approved = json.loads((OUT / 'approved-manifest.json').read_text(encoding='utf8'))
    additions = json.loads((ROOT / 'site/additions.json').read_text(encoding='utf8'))
    assert {x['id'] for x in approved['cases']} <= {x['id'] for x in additions}
    path = ROOT / 'site/case-reviews.json'
    if not (OUT / 'before-case-reviews.json').exists():
        save_original(OUT / 'before-case-reviews.json', path.read_bytes())
    reviews = json.loads(path.read_text(encoding='utf8'))
    for c in approved['cases']:
        fields = {'reviewedModelNames': [c['model']]}
        review = {'sourceUrl': c['sourceUrl'], 'role': 'case', 'reason': 'Author-labelled static SVG preview, original bytes preserved; publication date is not a separately authenticated generation day.', 'evidence': c['evidence'], 'fields': fields}
        if c['id'] in GEMMA:
            review['timelineVisible'] = False
            fields.update(comparisonIds=GEMMA, comparisonType='quantizations')
            review['reason'] += ' Source identifies two quantizations/runtimes, not reasoning levels. Neither has a documented default/medium representative.'
        reviews[c['id']] = review
    path.write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    if '--apply-reviews' in sys.argv:
        apply_reviews()
        print('Applied three explicit source reviews')
    else:
        print('Approved', len(approve()['cases']), 'previously missing outputs; excluded one repost')
