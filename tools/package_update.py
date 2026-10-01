"""Package generated pages, shared presentation assets and API; media is unchanged."""
from pathlib import Path
import tarfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public-site'
dest=ROOT/'deploy-build/pelicanmap-update.tar.gz'
with tarfile.open(dest,'w:gz') as archive:
    for p in sorted(OUT.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(OUT)
        if rel.parts[0] in {'media','downloads','_download-parts'} or rel.name=='_headers':continue
        archive.add(p,arcname='site/'+rel.as_posix())
    archive.add(ROOT/'deploy-build/server.mjs',arcname='runtime/server.mjs')
    archive.add(ROOT/'deploy-build/removed-public-pages.json',arcname='removed-public-pages.json')
print(dest, dest.stat().st_size)
