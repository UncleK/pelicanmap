"""Narrow regression allowance for one source-reviewed composite replacement."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_REMOVED = 'x-keth-space-bunny-alpha-animation-2026-09-30'


def user_requested_context_change(test, previous, current, key):
    """One explicitly removed recording; historical media/identity still frozen."""
    if previous['id'] != USER_REMOVED or key not in {'caseRole', 'caseVisible', 'timelineVisible', 'caseReview'}:
        return False
    review = json.loads((ROOT / 'site/case-reviews.json').read_text(encoding='utf8'))[USER_REMOVED]
    test.assertEqual(review['role'], 'context')
    test.assertFalse(review['timelineVisible'])
    test.assertIn("user's direct request on 2026-10-02", review['reason'])
    test.assertEqual(current['caseRole'], 'context')
    test.assertFalse(current['caseVisible'] or current['timelineVisible'])
    test.assertIsNone(current['caseNumber'])
    test.assertEqual(current['caseReview']['reason'], review['reason'])
    test.assertEqual(current['caseReview']['evidence'], previous['caseReview']['evidence'])
    for field in ['id', 'title', 'model', 'date', 'author', 'sourceUrl', 'updated', 'media', 'thumbnail']:
        test.assertEqual(current[field], previous[field], (USER_REMOVED, field))
    return True

PARENT = 'reddit-kylmawurr-claude-opus-5-5-2026-09-27'
CHILDREN = {
    'reddit-kylmawurr-opus55-medium-2026-09-27',
    'reddit-kylmawurr-opus55-high-2026-09-27',
    'reddit-kylmawurr-opus55-xhigh-2026-09-27',
    'reddit-kylmawurr-opus55-medium-refined-2026-09-27',
}


def reviewed_context_change(test, previous, current, key, by_id):
    """Do not freeze counted composites after their verified outputs are split.

    No generic exemption: exactly this reviewed parent, four documented children,
    unchanged historical identity/media, and four policy fields only.
    """
    if previous['id'] != PARENT or key not in {'caseRole', 'caseVisible', 'timelineVisible', 'caseReview'}:
        return False
    review = json.loads((ROOT / 'site/case-reviews.json').read_text(encoding='utf8'))[PARENT]
    test.assertEqual(review['role'], 'context')
    test.assertEqual(review['sourceUrl'], previous['sourceUrl'])
    test.assertEqual(current['caseRole'], 'context')
    test.assertFalse(current['caseVisible'] or current['timelineVisible'])
    test.assertEqual(current['caseReview']['reason'], review['reason'])
    test.assertEqual(current['caseReview']['evidence'], [previous['sourceUrl']])
    test.assertEqual(set(current['childIds']), CHILDREN)
    for field in ['id', 'model', 'date', 'author', 'sourceUrl', 'updated', 'media', 'thumbnail']:
        test.assertEqual(current[field], previous[field], (PARENT, field))
    for ident in CHILDREN:
        child = by_id[ident]
        test.assertTrue(child['caseVisible'])
        test.assertEqual(child['parentId'], PARENT)
        test.assertEqual(child['sourceUrl'], previous['sourceUrl'])
        test.assertEqual(child['date'], previous['date'])
        test.assertEqual(child['model'], previous['model'])
        test.assertTrue(child['media'][0]['src'].endswith('.webm'))
    test.assertEqual(sum(by_id[ident]['timelineVisible'] for ident in CHILDREN), 1)
    test.assertTrue(by_id['reddit-kylmawurr-opus55-medium-2026-09-27']['timelineVisible'])
    return True


def reviewed_motion_append(test, previous, current, key):
    """Exactly three byte-preserved MIT previews; no historical overwrite."""
    allowed = {
        'variora-gpt-6-sol-max-2026-09-23',
        'variora-gpt-6-astra-max-2026-09-14',
        'variora-mimo-v2-6-pro-2026-09-22',
    }
    if previous['id'] not in allowed or key not in {'notes', 'rights', 'i18n', 'previewUrl'}:
        return False
    audit = json.loads((ROOT / 'pelican-archive/research/2026-10-02-motion-recovery/import-audit.json').read_text())
    evidence = next(x for x in audit['augmented'] if x['id'] == previous['id'])
    test.assertEqual(current['previewUrl'], evidence['previewUrl'])
    test.assertFalse(current['interactive'] or current.get('demoUrl'))
    test.assertEqual(current['generationConditions']['animationArchive']['sha256'], evidence['sha256'])
    test.assertTrue(current['generationConditions']['animationArchive']['controlsArePlaybackOnly'])
    preview = ROOT / 'public-demos/demos/variora-motion-recovery' / previous['id']
    test.assertEqual(hashlib.sha256((preview / 'index.html').read_bytes()).hexdigest(), evidence['sha256'])
    test.assertIn('MIT License', (preview / 'LICENSE.txt').read_text())
    for field in ['id', 'model', 'date', 'author', 'sourceUrl', 'updated', 'media', 'thumbnail']:
        test.assertEqual(current[field], previous[field], (previous['id'], field))
    test.assertTrue(current['notes'].startswith(previous['notes']))
    test.assertIn('MIT License', current['rights'])
    for lang, old_values in previous['i18n'].items():
        new_values = current['i18n'][lang]
        for field, value in old_values.items():
            if field == 'notes':test.assertTrue(new_values[field].startswith(value))
            elif field == 'rights':test.assertIn('MIT License', new_values[field])
            else:test.assertEqual(new_values[field], value, (previous['id'], lang, field))
    return True
