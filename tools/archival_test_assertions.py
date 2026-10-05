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
    if reviewed_video_context_change(test, previous, current, key, by_id):
        return True
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


def reviewed_video_context_change(test, previous, current, key, by_id):
    """Four direct video outputs explicitly excluded by the latest user scope."""
    from generation_scope import DIRECT_VIDEO_IDS
    parent = previous['id']
    if parent not in DIRECT_VIDEO_IDS or key not in {'caseRole', 'caseVisible', 'timelineVisible', 'caseReview'}:
        return False
    review = json.loads((ROOT / 'site/case-reviews.json').read_text(encoding='utf8'))[parent]
    test.assertEqual(review['role'], 'context')
    test.assertEqual(review['sourceUrl'], previous['sourceUrl'])
    test.assertIn(previous['sourceUrl'], review['evidence'])
    test.assertIn('Latest direct user scope on 2026-10-03', review['reason'])
    test.assertEqual(current['caseRole'], 'context')
    test.assertFalse(current['caseVisible'] or current['timelineVisible'])
    test.assertIsNone(current['caseNumber'])
    test.assertEqual(current['caseReview']['reason'], review['reason'])
    test.assertEqual(current['caseReview']['evidence'], review['evidence'])
    test.assertEqual(current['generationMethod'], 'direct-text-to-video')
    test.assertEqual(current['childIds'], previous['childIds'])
    for field in ['id', 'title', 'model', 'date', 'author', 'sourceUrl', 'updated', 'media', 'thumbnail', 'rights']:
        test.assertEqual(current[field], previous[field], (parent, field))
    return True


def reviewed_motion_append(test, previous, current, key):
    """Exactly three byte-preserved MIT previews; no historical overwrite."""
    if reviewed_swe_motion_restoration(test, previous, current, key):
        return True
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


def reviewed_swe_motion_restoration(test, previous, current, key):
    """Individually reviewed pinned MIT originals, never a blanket exemption."""
    if reviewed_gemini_interaction_restoration(test, previous, current, key):
        return True
    reviewed = {
        'variora-swe-2-2026-09-22': ('d42e436747fb4ad5549dac340ffaa88ea1ada9686145542a7223db01ab4c5e64', 19255),
        'variora-mimo-v2-6-flash-free-2026-09-22': ('111be2ead35b66fc24df2834334b25eb3623f2694b2a6ae99f09937974f2ff48', 23128),
        'variora-grok-4-7-2026-09-22': ('81329983af7e1d59ed47f79722ac3908d2b31ef67b1d47059ae72249b4b3bf12', 26189),
        'variora-step-5-2026-09-20': ('7f86084541faa745cd028c21085ee80895401a04473d3092beea2f0fb7c3ca63', 39558),
    }
    ident = previous['id']
    fields = {'notes', 'rights', 'i18n', 'previewUrl', 'generationConditions'}
    if ident not in reviewed or key not in fields:
        return False
    preview = ROOT / 'public-demos/demos/variora-motion-recovery' / ident
    expected_sha, expected_bytes = reviewed[ident]
    test.assertEqual(hashlib.sha256((preview / 'index.html').read_bytes()).hexdigest(), expected_sha)
    test.assertEqual(hashlib.sha256((preview / 'LICENSE.txt').read_bytes()).hexdigest(),
                     '7b2f47de242cf53f6c5f53d6aeee902d064e5e8a4e151388ef8966a538b4f8f2')
    test.assertEqual(current['previewUrl'], 'https://pelicanmap-demos.aveniqa.com/demos/variora-motion-recovery/'+ident+'/')
    test.assertFalse(current['interactive'] or current.get('demoUrl'))
    expected = next(x for x in json.loads((ROOT / 'site/additions.json').read_text(encoding='utf8')) if x['id'] == ident)
    for field in fields:
        test.assertEqual(current[field], expected[field])
    archive = current['generationConditions']['animationArchive']
    test.assertEqual(archive['sha256'], expected_sha)
    test.assertEqual(archive['bytes'], expected_bytes)
    test.assertEqual(archive['license'], 'MIT')
    test.assertTrue(archive['controlsArePlaybackOnly'])
    for field in ['id', 'model', 'date', 'author', 'sourceUrl', 'updated', 'media', 'thumbnail']:
        test.assertEqual(current[field], previous[field], (ident, field))
    test.assertTrue(current['notes'].startswith(previous['notes']))
    for field, value in previous.get('generationConditions', {}).items():
        test.assertEqual(current['generationConditions'][field], value)
    for lang, old_values in previous['i18n'].items():
        for field, value in old_values.items():
            new_value = current['i18n'][lang][field]
            if field == 'notes':test.assertTrue(new_value.startswith(value))
            elif field == 'rights':
                if ident == 'variora-step-5-2026-09-20':
                    test.assertTrue(new_value.startswith(value))
                    test.assertIn('MIT', new_value)
                else:test.assertIn('MIT License', new_value)
            else:test.assertEqual(new_value, value)
    return True


def reviewed_swe_addition_restoration(test, previous, current):
    """Apply the same exact restoration guard to ingestion snapshots."""
    if previous['id'] == 'variora-gemini-3-8-flash-2026-09-20':
        for key, value in previous.items():
            if not reviewed_gemini_interaction_restoration(test, previous, current, key):
                test.assertEqual(current[key], value)
        test.assertEqual(set(current)-set(previous), {'generationConditions','interactive'}-set(previous))
        return True
    if previous['id'] not in {'variora-swe-2-2026-09-22', 'variora-mimo-v2-6-flash-free-2026-09-22', 'variora-grok-4-7-2026-09-22', 'variora-step-5-2026-09-20'}:
        return False
    for key, value in previous.items():
        if not reviewed_swe_motion_restoration(test, previous, current, key):
            test.assertEqual(current[key], value)
    test.assertEqual(set(current)-set(previous), {'generationConditions','previewUrl','interactive'}-set(previous))
    return True


def reviewed_gemini_interaction_restoration(test, previous, current, key):
    """One unchanged MIT app with verified wheelie/fish actions; no generic Play exemption."""
    ident = 'variora-gemini-3-8-flash-2026-09-20'
    fields = {'notes','rights','i18n','demoUrl','interactive','interactionControls','generationConditions'}
    if previous['id'] != ident or key not in fields:
        return False
    expected_sha = 'f3f600e77d2963ce8027bca5a30af929585e9f7333393859d7bae626fe7abd6a'
    demo = 'https://pelicanmap-demos.aveniqa.com/demos/variora-motion-recovery/'+ident+'/'
    directory = ROOT / 'public-demos/demos/variora-motion-recovery' / ident
    test.assertEqual((directory / 'index.html').stat().st_size, 73420)
    test.assertEqual(hashlib.sha256((directory / 'index.html').read_bytes()).hexdigest(), expected_sha)
    test.assertEqual(hashlib.sha256((directory / 'LICENSE.txt').read_bytes()).hexdigest(), '7b2f47de242cf53f6c5f53d6aeee902d064e5e8a4e151388ef8966a538b4f8f2')
    review = json.loads((ROOT / 'site/demo-reviews.json').read_text(encoding='utf8'))[ident]
    test.assertEqual(review['sourceSha256'], expected_sha)
    test.assertEqual(review['license'], 'MIT')
    test.assertEqual(review['demoUrl'], demo)
    test.assertEqual(len(review['verifiedActions']), 4)
    test.assertEqual(current['demoUrl'], demo)
    test.assertTrue(current['interactive'])
    if 'interactionControls' in current:
        test.assertEqual(current['interactionControls'], review['controls'])
    expected = next(x for x in json.loads((ROOT / 'site/additions.json').read_text(encoding='utf8')) if x['id'] == ident)
    for field in ['notes','rights','i18n','generationConditions']:
        test.assertEqual(current[field], expected[field])
    archive = current['generationConditions']['animationArchive']
    test.assertEqual(archive['sha256'], expected_sha)
    test.assertEqual(archive['bytes'], 73420)
    test.assertEqual(archive['license'], 'MIT')
    test.assertFalse(archive['controlsArePlaybackOnly'])
    for field in ['id','model','date','author','sourceUrl','updated','media','thumbnail']:
        test.assertEqual(current[field], previous[field], (ident,field))
    test.assertTrue(current['notes'].startswith(previous['notes']))
    return True
