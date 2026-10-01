"""Package only explicitly public outputs, not workspace files or credentials."""
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
target=root/'deploy-build'
target.mkdir(exist_ok=True)
with tarfile.open(target/'pelicanmap.tar.gz','w:gz',compresslevel=3) as archive:
    for base,name in [(root/'public-site','site'),(root/'public-demos','demos')]:
        for path in sorted(base.rglob('*')):
            rel=path.relative_to(base)
            if not path.is_file() or rel.parts[0] in ('_download-parts','_headers'):
                continue
            if name=='demos' and rel.parts[0]=='media':
                continue
            archive.add(path,arcname=f'{name}/{rel.as_posix()}',recursive=False)
    archive.add(root/'pelican-web/repos/pedalican.zip',arcname='site/downloads/pedalican.zip')
    archive.add(target/'server.mjs',arcname='runtime/server.mjs')
print(target/'pelicanmap.tar.gz', (target/'pelicanmap.tar.gz').stat().st_size)
