"""Dependency-aware detail rendering with unchanged output and media reuse."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote

from atomic_files import replace_with_retry
from content_cache import cached_hashes, identity, save_json, sha256_file

ROOT = Path(__file__).resolve().parents[1]
CURRENT = None
RENDER_MODULES = ('build_public_site', 'build_english', 'incremental_site', 'editorial_content',
    'detail_presentation', 'case_policy', 'collection_views', 'card_metadata', 'model_chronology',
    'experiment_batches', 'benchmark_reference', 'historical_context', 'thumbnail_overrides',
    'record_overrides', 'detail_frames', 'source_layout', 'catalog_policy', 'generation_scope')
RELATIONS = ('comparisonIds', 'childIds', 'linkedCaseIds', 'relatedSourceIds', 'variantIds', 'duplicateIds')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':')).encode('utf8')).hexdigest()


class SiteCache:
    def __init__(self, root, output, date, code):
        self.root, self.output, self.date, self.code = Path(root), Path(output), date, code
        self.path = self.root/'deploy-build/incremental-pages.json'
        value = json.loads(self.path.read_text(encoding='utf8')) if self.path.exists() else {}
        self.rows = value.get('rows', {}) if value.get('output') == str(self.output.resolve()) else {}
        self.dirty_html = set()
        self.contexts = {}
        self.list_hashes = {}
        self.stats = {'detailsRendered': 0, 'detailsReused': 0, 'pagesRendered': 0,
                      'pagesReused': 0, 'writtenFiles': 0, 'copiedFiles': 0,
                      'mediaInspections': 0, 'mediaInspectionsReused': 0}

    def key(self, path):
        return str(Path(path).resolve())

    def valid_output(self, path):
        path = Path(path)
        row = self.rows.get('output:'+self.key(path))
        if not path.is_file() or not row:
            return False
        if identity(path) != row['identity']:
            if sha256_file(path) != row['sha256']:
                return False
            row['identity'] = identity(path)
        return True

    def remember(self, path):
        self.rows['output:'+self.key(path)] = {'identity': identity(path), 'sha256': sha256_file(path)}

    def write(self, path, text):
        path = Path(path)
        # Match the project's existing UTF-8/newline output on each host.
        data = text.replace('\n', '\r\n').encode('utf8') if __import__('os').name == 'nt' else text.encode('utf8')
        digest = hashlib.sha256(data).hexdigest()
        if path.is_file() and sha256_file(path) == digest:
            self.remember(path)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name+'.tmp')
        temporary.write_bytes(data)
        replace_with_retry(temporary, path)
        self.remember(path)
        self.stats['writtenFiles'] += 1
        if path.suffix == '.html' and path.is_relative_to(self.output):
            self.dirty_html.add(path)

    def page(self, path, dependency, outputs):
        key = 'page:'+path
        digest = fingerprint([self.code, dependency])
        previous = self.rows.get(key)
        skip = previous and previous['digest'] == digest and all(self.valid_output(p) for p in outputs)
        self.rows[key] = {'digest': digest, 'date': previous.get('date', self.date) if skip else self.existing_date(outputs[0]) if previous is None else self.date}
        self.stats['pagesReused' if skip else 'pagesRendered'] += 1
        return bool(skip), self.rows[key]['date']

    def existing_date(self, path):
        path = Path(path)
        if path.is_file():
            text = path.read_text(encoding='utf8')
            found = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})', text)
            if found:
                return found.group(1)
        return self.date

    def prepare_details(self, items, language):
        by_id = {x['id']: x for x in items}
        hashes = {key: fingerprint(value) for key, value in by_id.items()}
        groups = {}
        for item in items:
            if item.get('referenceOnly') or item.get('caseVisible') is not False:
                groups.setdefault((bool(item.get('referenceOnly')), item['source'], item['format']), []).append(item['id'])
        self.contexts[language] = (by_id, hashes, groups)

    def collection_version(self, items):
        key=tuple(id(x) for x in items)
        if key not in self.list_hashes:
            # Keep references alive so object IDs cannot be recycled in this build.
            self.list_hashes[key]=(tuple(items),fingerprint(items)[:20])
        return self.list_hashes[key][1]

    def last_modified(self, path):
        if '/specimens/' in path and '/page/' not in path:
            language='en' if path.startswith('/en/') else 'zh'
            key='detail:'+language+':'+path.strip('/').split('/')[-1]
            if key in self.rows:return self.rows[key]['date']
        return self.rows.get('page:'+path,{}).get('date',self.date)

    def detail(self, item, language):
        by_id, hashes, groups = self.contexts[language]
        referenced = set()
        for key in RELATIONS:
            referenced.update(item.get(key, []))
        for key in ('canonicalId', 'parentId', 'representativeOf'):
            if item.get(key):
                referenced.add(item[key])
        related = groups.get((bool(item.get('referenceOnly')), item['source'], item['format']), [])
        related = [key for key in related[:4] if key != item['id']][:3]
        referenced.update(related)
        media = []
        for value in [item.get('thumbnail'), *[m['src'] for m in item['media']]]:
            if value and value.startswith('/'):
                path = self.output/unquote(value).lstrip('/')
                if not path.resolve().is_relative_to(self.output.resolve()):
                    raise ValueError('Unsafe local presentation media path')
                if path.is_file():
                    media.append([value, sha256_file(path)])
        digest = fingerprint([self.code, hashes[item['id']],
            sorted((key, hashes.get(key)) for key in referenced), media])
        key = 'detail:'+language+':'+item['id']
        outputs = [self.output/item['path'].lstrip('/')/'index.html', self.output/item['markdown'].lstrip('/')]
        previous = self.rows.get(key)
        skip = previous and previous['digest'] == digest and all(self.valid_output(p) for p in outputs)
        date = previous['date'] if skip else self.date
        if previous is None and outputs[0].is_file():
            text = outputs[0].read_text(encoding='utf8')
            found = re.search(r'(?:\u66f4\u65b0\u65e5\u671f|Last updated)</dt><dd>(\d{4}-\d{2}-\d{2})', text)
            if found:
                date = found.group(1)
        self.rows[key] = {'digest': digest, 'date': date}
        self.stats['detailsReused' if skip else 'detailsRendered'] += 1
        return bool(skip), date

    def asset_group(self, name, inputs, outputs):
        digest = fingerprint([self.code, [(str(p), sha256_file(p)) for p in inputs]])
        key = 'assets:'+name
        skip = self.rows.get(key) == digest and all(self.valid_output(p) for p in outputs)
        self.rows[key] = digest
        return bool(skip)

    def save(self):
        save_json(self.path, {'version': 1, 'output': str(self.output.resolve()), 'rows': self.rows})


def write_text(path, text):
    if CURRENT is not None:
        CURRENT.write(path, text)
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Full builds also retain identical files and timestamps.
    if path.is_file() and path.read_text(encoding='utf8') == text:
        return
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(text, encoding='utf8')
    replace_with_retry(temporary, path)


def copy_file(source, dest):
    source, dest = Path(source), Path(dest)
    source_hash = sha256_file(source)
    if not dest.is_file() or sha256_file(dest) != source_hash:
        dest.parent.mkdir(parents=True, exist_ok=True)
        temporary = dest.with_name(dest.name+'.tmp')
        shutil.copy2(source, temporary)
        replace_with_retry(temporary, dest)
        if CURRENT is not None:
            CURRENT.stats['copiedFiles'] += 1
    if CURRENT is not None:
        CURRENT.remember(dest)
    return str(dest)


def inspect_file(path, kind, inspect):
    if CURRENT is None:
        return inspect()
    key = 'inspection:'+kind+':'+str(Path(path).resolve())
    digest = sha256_file(path)
    previous = CURRENT.rows.get(key)
    if previous and previous['digest'] == digest and previous.get('code') == CURRENT.code:
        CURRENT.stats['mediaInspectionsReused']+=1
        return previous['value']
    CURRENT.stats['mediaInspections']+=1
    value = inspect()
    CURRENT.rows[key] = {'digest': digest, 'value': value, 'code': CURRENT.code}
    return value


def collection_version(items):
    return CURRENT.collection_version(items) if CURRENT else fingerprint(items)[:20]


def build(date=None, *, items=None, prepare=True):
    global CURRENT
    import build_public_site as zh
    import build_english as en
    from detail_presentation import motion_kind
    motion_kind.cache_clear()
    date = date or dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    with cached_hashes(ROOT/'deploy-build/local-file-hashes.json') as hashes:
        code = fingerprint([sha256_file(ROOT/'tools'/f'{name}.py') for name in RENDER_MODULES]+[zh.ASSET_VERSION])
        cache = SiteCache(ROOT, zh.OUT, date, code)
        CURRENT = cache
        zh.BUILD_CACHE = en.BUILD_CACHE = cache
        zh.UPDATED = en.UPDATED = date
        try:
            zh.build(items=items, prepare=prepare)
            en.build()
            cache.save()
            return {'status': 'built', 'generation': cache.stats, 'hashing': hashes.stats}
        finally:
            CURRENT = None
            zh.BUILD_CACHE = en.BUILD_CACHE = None


if __name__ == '__main__':
    from incremental_site import build as run_build
    print(json.dumps(run_build(), ensure_ascii=False))
