"""Reuse verified hashes while file identity, size and timestamps remain unchanged."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import uuid

ACTIVE = None


def identity(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected a regular file: '+str(path))
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf8')
    temporary.replace(path)


class HashCache:
    def __init__(self, path):
        self.path = Path(path)
        self.rows = json.loads(self.path.read_text(encoding='utf8')) if self.path.exists() else {}
        self.stats = {'readFiles': 0, 'readBytes': 0, 'reusedFiles': 0}

    def digest(self, path):
        path = Path(path)
        identity(path)
        path = path.resolve()
        key, stamp = str(path), identity(path)
        row = self.rows.get(key)
        if row and row['identity'] == stamp:
            self.stats['reusedFiles'] += 1
            return row['sha256']
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if identity(path) != stamp:
            raise ValueError('File changed while hashing: '+str(path))
        self.rows[key] = {'identity': stamp, 'sha256': digest}
        self.stats['readFiles'] += 1
        self.stats['readBytes'] += stamp[2]
        return digest

    def remember(self, path, digest):
        self.rows[str(Path(path).resolve())] = {'identity': identity(path), 'sha256': digest}

    def save(self):
        save_json(self.path, self.rows)


def sha256_file(path):
    if ACTIVE is not None:
        return ACTIVE.digest(path)
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@contextmanager
def cached_hashes(path):
    global ACTIVE
    previous = ACTIVE
    cache = HashCache(path)
    ACTIVE = cache
    try:
        yield cache
        cache.save()
    finally:
        ACTIVE = previous
