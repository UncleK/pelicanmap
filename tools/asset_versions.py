"""Keep published cache keys when only platform line endings differ."""
import hashlib
from pathlib import Path

NAMES = ('site.css', 'site.js', 'browse.js', 'motion.js')


def asset_version(source, published):
    source, published = Path(source), Path(published)
    originals = [(source/name).read_bytes() for name in NAMES]
    if all((published/name).is_file() for name in NAMES):
        deployed = [(published/name).read_bytes() for name in NAMES]
        if all(old.replace(b'\r\n', b'\n') == new.replace(b'\r\n', b'\n')
               for old, new in zip(originals, deployed)):
            return hashlib.sha256(b''.join(deployed)).hexdigest()[:12]
    return hashlib.sha256(b''.join(originals)).hexdigest()[:12]
