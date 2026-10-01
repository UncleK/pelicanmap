"""Apply reviewed source-video poster replacements without changing originals."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_thumbnail_overrides(items, media_root=None):
    manifest = ROOT / 'site/thumbnail-overrides.json'
    overrides = json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else {}
    result = []
    for item in items:
        override = overrides.get(item['originalId'])
        if not override:
            result.append(item)
            continue
        updated = copy.deepcopy(item)
        override_type = override.get('type','source-video-frame')
        assert override_type in {'source-video-frame','archived-source-image','svg-render'}
        source_path = (override['poster'] if override_type == 'archived-source-image' else
                       override['sourceSvg'] if override_type == 'svg-render' else override['video'])
        source_media = next((media for media in updated['media'] if media['src'] == source_path), None)
        assert source_media is not None, f"Poster source media missing: {item['id']}"
        assert source_media['source'] == override['source'], f"Poster source changed: {item['id']}"
        media_root = Path(media_root) if media_root is not None else ROOT / 'pelican-web'
        path = (media_root / override['poster'].lstrip('/')).resolve()
        assert path.is_relative_to((media_root / 'media').resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == override['sha256']
        if override_type == 'source-video-frame':
            source_media['poster'] = override['poster']
        elif override_type == 'svg-render':
            original_path=(media_root / source_path.lstrip('/')).resolve()
            assert original_path.is_relative_to((media_root / 'media').resolve())
            assert hashlib.sha256(original_path.read_bytes()).hexdigest()==override['sourceSha256']
            source_media['preview']=override['poster']
            source_media['caption']=override['caption']
            source_media['captionEn']=override['captionEn']
            if not updated.get('sourceCodeUrl'):updated['sourceCodeUrl']=source_path
        updated['thumbnail'] = override['poster']
        updated['thumbnailProvenance'] = dict(override, type=override_type)
        result.append(updated)
    assert set(overrides) <= {item['originalId'] for item in items}, 'Unknown thumbnail override ID'
    return result
