"""Explicit, source-checked repairs to existing records, shared by publishers."""
import copy
import hashlib
from content_cache import sha256_file
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_record_overrides(items, media_root=None):
    overrides = json.loads((ROOT/'site/record-overrides.json').read_text(encoding='utf8'))
    result = copy.deepcopy(items)
    matched = set()
    for item in result:
        repair = overrides.get(item['id'])
        if not repair:
            continue
        assert item['sourceUrl'] == repair['sourceUrl'], 'Record repair source changed'
        fields = repair['fields']
        assert not set(fields)-{'title', 'model', 'notes', 'promptStatus', 'thumbnail', 'media', 'i18n', 'recordRepair'}
        originals = {m['src'] for m in item['media']}
        if 'media' in fields:
            assert originals <= {m['src'] for m in fields['media']}, 'Keep every old attachment'
            checked_media = fields['media']
        else:
            # Metadata-only contextual enrichment never reserializes old media.
            assert set(fields)=={'recordRepair'}, 'Content repairs require checked media'
            assert len(item['media'])==1 and fields['recordRepair'].get('mediaSha256')
            checked_media = [dict(item['media'][0],sha256=fields['recordRepair']['mediaSha256'])]
        if media_root is not None:
            root = Path(media_root).resolve()
            for media in checked_media:
                assert media['src'].startswith('/media/')
                path = (root/media['src'].lstrip('/')).resolve()
                assert path.is_relative_to(root) and path.is_file(), str(path)
                assert sha256_file(path) == media['sha256'], str(path)
        item.update(copy.deepcopy(fields))
        matched.add(item['id'])
    assert matched == set(overrides), 'Repair target is missing'
    return result
