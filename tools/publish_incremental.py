"""Prepare and publish a source-reviewed batch without a full website package."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import urllib.request
import uuid

from catalog_policy import merge_additions
from package_publisher import ROOT, publisher_files
from release_delta import metadata, package
from check_delta_release import check
from check_incremental_cache import check_cache
from content_cache import cached_hashes


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')


class Connection:
    def __init__(self, host, key):
        if not re.fullmatch(r'[A-Za-z0-9.-]+', host) or not Path(key).is_file():
            raise ValueError('Valid SSH host and existing key are required')
        self.target = 'root@' + host
        self.options = ['-i', str(Path(key).resolve()), '-o', 'BatchMode=yes',
                        '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
                        '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3']

    def command(self, command, *, data=None, timeout=120):
        result = subprocess.run(['ssh', *self.options, self.target, command],
            input=data, capture_output=True, text=True, encoding='utf8', timeout=timeout)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout)[-2500:])
        return result.stdout

    def python(self, script, timeout=120):
        return json.loads(self.command('python3 -B -', data=script, timeout=timeout))

    def upload(self, source, destination):
        result = subprocess.run(['scp', '-q', *self.options, str(Path(source).resolve()),
                                 self.target + ':' + destination],
                                capture_output=True, text=True, encoding='utf8', timeout=180)
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:])


def prepare(batch, connection):
    if (batch/'baseline.json').exists():
        raise ValueError('This batch already has a baseline; use a fresh batch for a new baseline')
    batch.mkdir(parents=True, exist_ok=True)
    stage = '/tmp/pelicanmap-incremental-' + uuid.uuid4().hex
    connection.command('mkdir -m 700 ' + shlex.quote(stage))
    for name in ['release_delta.py', 'activate_incremental.py', 'content_cache.py', 'verify_release_helpers.py', 'test_release_delta.py', 'test_incremental_activation.py']:
        connection.upload(ROOT/'tools'/name, stage+'/'+name)
    names = publisher_files()
    script = '''import fcntl,json,sys,re,hashlib
from pathlib import Path
sys.path.insert(0, STAGE)
from release_delta import cached_inventory,metadata
root=Path('/srv/pelicanmap')
with (root/'state/publish.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    current=(root/'current').resolve(strict=True)
    cache=root/'state/release-inventories'
    seeded=not (cache/(current.name+'.json')).exists()
    baseline=cached_inventory(current,cache)
    additions=root/'state/additions.json'
    html=(current/'site/index.html').read_text(encoding='utf8')
    asset_version=re.search(r'/assets/site\\.css\\?v=([a-f0-9]{12})',html).group(1)
    asset_names=['site.css','site.js','browse.js','motion.js']
    semantic_hashes={name:hashlib.sha256((root/'publisher/site/assets'/name).read_bytes().replace(b'\\r\\n',b'\\n')).hexdigest() for name in asset_names}
    sources={}
    for name in NAMES:
        path=root/'publisher'/name
        sources[name]=metadata(path) if path.is_file() else None
    print(json.dumps({'baseline':baseline,'catalog':json.loads((current/'site/data/catalog.json').read_text()),
        'additions':json.loads(additions.read_text()),'additionsMeta':metadata(additions),'publisherSources':sources,
        'apiUnitMeta':metadata(Path('/etc/systemd/system/pelicanmap-api.service')),'inventorySeeded':seeded,
        'assetVersion':asset_version,'assetSemanticHashes':semantic_hashes,
        'serverPending':[p.name for p in (root/'state/pending').iterdir() if p.is_file()],
        'serverSubmissions':[json.loads((root/'state/jobs'/(p.stem+'.json')).read_text()) for p in (root/'state/pending').iterdir() if p.is_file() and re.fullmatch(r'[a-f0-9]{24}\\.job',p.name)]}))
'''.replace('STAGE', repr(stage)).replace('NAMES', repr(names))
    snapshot = connection.python(script)
    write_json(batch/'baseline.json', snapshot['baseline'])
    write_json(batch/'catalog-before.json', snapshot['catalog'])
    write_json(batch/'additions-server-before.json', snapshot['additions'])
    write_json(batch/'ingest-submissions-before.json',snapshot.pop('serverSubmissions',[]))
    local = ROOT/'site/additions.json'
    (batch/'additions-local-before.json').write_bytes(local.read_bytes())
    merged = merge_additions(json.loads(local.read_text(encoding='utf8')), snapshot['additions'])
    for record in merged:
        for media in record['media']:
            if not media['src'].startswith('/media/ingested/'):
                continue
            target = (ROOT/'pelican-web'/media['src'].lstrip('/')).resolve()
            if not target.is_relative_to((ROOT/'pelican-web/media/ingested').resolve()):
                raise ValueError('Unsafe ingested media path')
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                request = urllib.request.Request('https://pelicanmap.aveniqa.com'+media['src'],
                    headers={'User-Agent': 'PelicanMap-Incremental-Sync/1.0'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    target.write_bytes(response.read())
    write_json(local, merged)
    snapshot.pop('baseline')
    snapshot.pop('catalog')
    snapshot.pop('additions')
    snapshot['stage'] = stage
    write_json(batch/'prepare.json', snapshot)
    return {'status': 'prepared', 'baselineRelease': json.loads((batch/'baseline.json').read_text(encoding='utf8'))['release'],
            'additions': len(merged), 'inventorySeeded': snapshot['inventorySeeded'], 'stage': stage}


def reuse_published_bytes(batch, baseline, reviewed):
    """Keep untouched web derivatives and byte-equivalent assets on migration."""
    ids = {x['id'] for x in reviewed['cases']}
    catalog = json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
    allowed = set()
    for record in catalog['items']:
        if record['id'] in ids:
            allowed.update('site'+m['src'] for m in record['media'])
            allowed.update('site'+path for path in record.get('licenseFiles', []))
    reused = []
    for name, expected in baseline['files'].items():
        if name in allowed or not (name.startswith('site/media/') or name in
                {'site/assets/site.css', 'site/assets/site.js', 'site/assets/browse.js', 'site/assets/motion.js'}):
            continue
        path = ROOT/'public-site'/name.removeprefix('site/')
        if not path.is_file() or metadata(path) == expected:
            continue
        request = urllib.request.Request('https://pelicanmap.aveniqa.com/'+name.removeprefix('site/')+
            '?v='+expected['sha256'][:12], headers={'User-Agent': 'PelicanMap-Incremental-Reuse/1.0'})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise ValueError('Published baseline bytes could not be verified: '+name)
        path.write_bytes(data)
        reused.append({'path': name, **expected})
    if reused:
        write_json(batch/'published-bytes-reused.json', reused)
    return reused


def build(batch, include_runtime=False):
    prepared = json.loads((batch/'prepare.json').read_text(encoding='utf8'))
    baseline = json.loads((batch/'baseline.json').read_text(encoding='utf8'))
    reviewed = json.loads((batch/'reviewed-manifest.json').read_text(encoding='utf8'))
    gates = json.loads((batch/'gates.json').read_text(encoding='utf8'))
    if reviewed.get('reviewed') is not True or not gates or any(row['exitCode'] != 0 for row in gates):
        raise ValueError('Reviewed source manifest and successful affected gates are required')
    for name, expected in prepared['assetSemanticHashes'].items():
        actual = hashlib.sha256((ROOT/'site/assets'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        if actual != expected:
            raise ValueError('Shared website assets changed; use the shared-code release gates: '+name)
    if not re.fullmatch('[a-f0-9]{12}', prepared['assetVersion']):
        raise ValueError('The verified asset version is invalid')
    with cached_hashes(ROOT/'deploy-build/local-file-hashes.json'):
        reuse_published_bytes(batch, baseline, reviewed)
    compiled = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    entry = "import sys,json;sys.path.insert(0,sys.argv[2]);import build_public_site as zh;import build_english as en;from incremental_site import build;zh.ASSET_VERSION=en.ASSET_VERSION=sys.argv[1];print(json.dumps(build(sys.argv[3])))"
    result = subprocess.run([sys.executable, '-B', '-c', entry, prepared['assetVersion'], str(ROOT/'tools'), compiled],
                            cwd=ROOT, capture_output=True, text=True, timeout=600)
    (batch/'build.log').write_text(result.stdout+'\n'+result.stderr, encoding='utf8')
    if result.returncode:
        raise RuntimeError('Build failed; see the batch build.log')
    if include_runtime:
        subprocess.run(['node', str(ROOT/'tools/bundle_server.mjs')], cwd=ROOT, check=True)
    archive = batch/'pelicanmap-update.tar.gz'
    packaged = package(ROOT, baseline, archive, include_runtime=include_runtime)
    checked = check(archive)
    write_json(batch/'delta-package.json', packaged)
    write_json(batch/'delta-local-check.json', checked)
    if not checked['affectedRecords'] and not include_runtime:
        status = {'status': 'no-content-changes', 'reason': 'No reviewed artwork or media changed; compilation timestamps alone do not justify publication'}
        write_json(batch/'build-status.json', status)
        return status
    changes = {}
    for name in publisher_files():
        after = metadata(ROOT/name)
        before = prepared['publisherSources'].get(name)
        if before != after:
            changes[name] = {'before': before, 'after': after}
    publisher_archive = batch/'publisher-update.tar.gz'
    with tarfile.open(publisher_archive, 'w:gz', compresslevel=3) as output:
        for name in changes:
            output.add(ROOT/name, arcname=name, recursive=False)
    additions = batch/'additions.json'
    additions.write_bytes((ROOT/'site/additions.json').read_bytes())
    with tarfile.open(archive) as source:
        delta = json.load(source.extractfile('release-delta.json'))
    if not delta['affectedRecords'] and not delta['changed'] and not changes:
        return {'status': 'no-changes'}
    payloads = {name: metadata(batch/name) for name in
                ['pelicanmap-update.tar.gz', 'publisher-update.tar.gz', 'additions.json',
                 'reviewed-manifest.json', 'review.json', 'gates.json']}
    request = {'baselineRelease': baseline['release'],
        'baselineCounts': json.loads((batch/'catalog-before.json').read_text(encoding='utf8'))['counts'],
        'additionsBeforeSha256': prepared['additionsMeta']['sha256'],
        'apiUnitBeforeSha256': prepared['apiUnitMeta']['sha256'],
        'publisherChanges': changes, 'packages': payloads, 'changedFiles': list(delta['changed']),
        'counts': checked['counts'], 'affectedRecords': checked['affectedRecords'],
        'reviewedManifestSha256': metadata(batch/'reviewed-manifest.json')['sha256'],
        'gatesSha256': metadata(batch/'gates.json')['sha256']}
    write_json(batch/'deployment.json', request)
    write_json(batch/'build-status.json', {'status': 'ready-to-upload'})
    return {'status': 'ready-to-upload', 'websitePackage': packaged,
            'publisherChangedFiles': list(changes), 'publisherPackageBytes': publisher_archive.stat().st_size,
            'localChecks': checked}


def verify(batch):
    activation = json.loads((batch/'activation-report.json').read_text(encoding='utf8'))
    packaged = json.loads((batch/'delta-package.json').read_text(encoding='utf8'))
    request = json.loads((batch/'deployment.json').read_text(encoding='utf8'))
    prepared = json.loads((batch/'prepare.json').read_text(encoding='utf8'))
    live = check(batch/'pelicanmap-update.tar.gz', live=True)
    write_json(batch/'delta-live-check.json', live)
    canonical = check_cache(batch/'pelicanmap-update.tar.gz')
    write_json(batch/'canonical-cache-check.json', canonical)
    if canonical['stale']:
        (batch/'cdn-purge-urls.txt').write_text('\n'.join(row['url'] for row in canonical['stale'])+'\n', encoding='utf8')
    else:
        (batch/'cdn-purge-urls.txt').write_text('', encoding='utf8')
    result = {'status': 'published-and-verified' if not canonical['stale'] else 'published-cache-refresh-required',
              'canonicalCache': canonical, 'checkedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
              'release': Path(activation['release']).name, 'counts': live['counts'],
              'affectedRecords': live['affectedRecords'], 'websitePackage': packaged,
              'publisherChangedFiles': len(request['publisherChanges']),
              'publisherPackageBytes': (batch/'publisher-update.tar.gz').stat().st_size,
              'activation': activation, 'live': live, 'serverStage': prepared['stage']}
    write_json(batch/'publication-audit.json', result)
    return result


def publish(batch, connection):
    status_file = batch/'build-status.json'
    if status_file.exists() and json.loads(status_file.read_text(encoding='utf8'))['status'] == 'no-content-changes':
        return {'status': 'no-content-changes'}
    if (batch/'activation-report.json').exists():
        return verify(batch)
    prepared = json.loads((batch/'prepare.json').read_text(encoding='utf8'))
    request = json.loads((batch/'deployment.json').read_text(encoding='utf8'))
    payloads = request['packages']
    for name, expected in payloads.items():
        if metadata(batch/name) != expected:
            raise ValueError('Local upload payload changed after verification: '+name)
    if metadata(ROOT/'site/additions.json') != payloads['additions.json']:
        raise ValueError('Local additions changed after building')
    for name, row in request['publisherChanges'].items():
        if metadata(ROOT/name) != row['after']:
            raise ValueError('Local publisher changed after building: '+name)
    if (metadata(batch/'reviewed-manifest.json')['sha256'] != request['reviewedManifestSha256'] or
            metadata(batch/'gates.json')['sha256'] != request['gatesSha256']):
        raise ValueError('Review or gate evidence changed after building')
    stage = prepared['stage']
    # Source files may have changed after prepare; stage the tested current code.
    for name in ['release_delta.py', 'activate_incremental.py', 'content_cache.py', 'verify_release_helpers.py', 'test_release_delta.py', 'test_incremental_activation.py']:
        connection.upload(ROOT/'tools'/name, stage+'/'+name)
    server_tests = connection.command('python3 -B '+shlex.quote(stage+'/verify_release_helpers.py')+' --stage '+shlex.quote(stage))
    write_json(batch/'server-release-tests.json',json.loads(server_tests))
    for name in [*payloads, 'deployment.json']:
        connection.upload(batch/name, stage+'/'+name)
    activation = json.loads(connection.command('python3 -B '+shlex.quote(stage+'/activate_incremental.py')+
                                               ' --stage '+shlex.quote(stage), timeout=180))
    write_json(batch/'activation-report.json', activation)
    return verify(batch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'build', 'publish', 'verify'])
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--host', default='65.21.248.102')
    parser.add_argument('--ssh-key', type=Path, default=Path.home()/'.ssh/polybtc_vps')
    parser.add_argument('--include-runtime', action='store_true')
    args = parser.parse_args()
    batch = args.batch.resolve()
    if not batch.is_relative_to((ROOT/'pelican-archive/research').resolve()):
        raise ValueError('Batch evidence must be inside pelican-archive/research')
    connection = Connection(args.host, args.ssh_key)
    if args.mode == 'prepare':result = prepare(batch, connection)
    elif args.mode == 'build':result = build(batch, args.include_runtime)
    elif args.mode == 'publish':result = publish(batch, connection)
    else:result = verify(batch)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result['status'] == 'published-cache-refresh-required')
