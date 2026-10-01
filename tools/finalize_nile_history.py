"""Explicit manual approval of the nine visually reviewed historical outputs."""
import copy
import json
import sys
from audit_nile_history import ROOT, OUT


def save_original(path, data):
    if path.exists():
        assert path.read_bytes() == data, 'Historical evidence cannot be overwritten'
    else:
        path.write_bytes(data)


def approve():
    staged = json.loads((OUT / 'manifest.json').read_text(encoding='utf8'))
    evidence = json.loads((OUT / 'dedup.json').read_text(encoding='utf8'))
    assert len(staged['cases']) == len(evidence) == 9
    assert all(not item['exact'] for item in evidence)
    approved = copy.deepcopy(staged)
    approved['reviewed'] = True
    approved['review'] = {
        'method': 'Original article paragraphs, model-labelled Gists, original previews and five SVG/preview pairs manually inspected. Nine previews compared by SHA and normalized render against 837 archived non-reference media; all nearest three candidates manually reviewed, no same output found.',
        'date': 'All nine dates are before 2026. Three original logs preserve response timestamps; otherwise source publication, not an independently authenticated generation date.',
        'timeline': 'Nine different source-labelled single-model runs; no competing same-model setting in these article/run groups. Each sole source output represents its dated run, not a score-selected best.',
        'held': [
            {'position': 27, 'reason': 'Qwen3-30B Thinking final SVG already collected; reasoning image is not a second work.'},
            {'position': 28, 'reason': 'Gemini 2.5 Deep Think is nickandbro’s HN output, not Simon’s run. Original HN attribution/time and reuploads still require separate review.'},
            {'positions': '31–55', 'reason': 'Primary pages archived and inventoried; full per-output mapping and dedup still pending. No claim of complete coverage.'},
        ],
    }
    save_original(OUT / 'approved-manifest.json', (json.dumps(approved, ensure_ascii=False, indent=2) + '\n').encode())
    print('Approved nine original 2025 works; metadata/visual review complete')


def apply_reviews():
    approved = json.loads((OUT / 'approved-manifest.json').read_text(encoding='utf8'))
    additions = json.loads((ROOT / 'site/additions.json').read_text(encoding='utf8'))
    assert {x['id'] for x in approved['cases']} <= {x['id'] for x in additions}
    path = ROOT / 'site/case-reviews.json'
    save_original(OUT / 'before-case-reviews.json', path.read_bytes())
    reviews = json.loads(path.read_text(encoding='utf8'))
    for c in approved['cases']:
        review = {'sourceUrl': c['sourceUrl'], 'role': 'case', 'timelineVisible': True,
                  'reason': 'One author-mapped static SVG output in the source-dated model run. Source publication or documented log day, not an inferred release date. Sole output for this model/run; no competing settings or quality-based selection.',
                  'evidence': c['evidence'], 'fields': {'reviewedModelNames': [c['model']]}}
        if c['id'] in reviews:
            assert reviews[c['id']] == review
        reviews[c['id']] = review
    path.write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Applied nine explicit model/media/date/timeline reviews')


if __name__ == '__main__':
    apply_reviews() if '--apply-reviews' in sys.argv else approve()
