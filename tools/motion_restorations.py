"""Apply source-exact, reviewed complete animation documents without changing work identity."""
import copy
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from content_cache import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def load_reviews():
    path = ROOT / 'site/motion-restorations.json'
    return json.loads(path.read_text(encoding='utf8')) if path.is_file() else {}


def apply_restorations(items, reviews=None, demo_root=None):
    reviews = load_reviews() if reviews is None else reviews
    demo_root = Path(demo_root or ROOT / 'public-demos').resolve()
    result = copy.deepcopy(items)
    for item in result:
        review = reviews.get(item.get('id'))
        if not review:
            continue
        if review.get('reviewed') is not True or review.get('sourceUrl') != item['sourceUrl']:
            raise ValueError('Animation restoration needs a reviewed matching source: ' + item['id'])
        parsed = urlsplit(review['previewUrl'])
        if parsed.scheme != 'https' or parsed.netloc != 'pelicanmap-demos.aveniqa.com' or not parsed.path.startswith('/demos/'):
            raise ValueError('Animation restoration needs the isolated demo origin')
        path = (demo_root / unquote(parsed.path).lstrip('/') / 'index.html').resolve()
        if not path.is_relative_to(demo_root) or not path.is_file() or sha256_file(path) != review['sha256']:
            raise ValueError('Original animation document differs from review: ' + item['id'])
        if review.get('sourceArtifactPath'):
            original = (demo_root / review['sourceArtifactPath']).resolve()
            if not original.is_relative_to(demo_root) or not original.is_file() or sha256_file(original) != review['sourceArtifactSha256']:
                raise ValueError('Original animation module differs from review: ' + item['id'])
        item['previewUrl'] = review['previewUrl']
        if review.get('notes'):
            item['notes'] = review['notes']['zh']
            item.setdefault('i18n', {}).setdefault('en', {})['notes'] = review['notes']['en']
    return result
