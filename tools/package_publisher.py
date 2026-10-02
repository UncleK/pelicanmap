import tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=['tools/ingestion.py','tools/build_public_site.py','tools/build_english.py','tools/source_layout.py','pelican-web/data.js','site/captures/manifest.json','site/publication-exclusions.json','site/i18n/record-strings.json','site/i18n/records.en.txt']
files += ['tools/ingestion_docs.py']
files += ['tools/catalog_policy.py','tools/collection_views.py','site/demo-reviews.json']
files += ['tools/experiment_batches.py','site/experiment-batches.json']
files += ['tools/card_metadata.py']
files += ['tools/model_chronology.py','tools/detail_frames.py','site/model-releases.json','site/detail-frames.json']
files += ['tools/historical_context.py']
files += ['tools/editorial_content.py']
files += ['tools/detail_presentation.py']
files += ['tools/atomic_files.py']
files += ['tools/case_policy.py','site/case-reviews.json','site/collecting-policy.json']
files += ['tools/thumbnail_overrides.py','site/thumbnail-overrides.json']
files += ['tools/record_overrides.py','site/record-overrides.json']
files += ['tools/benchmark_reference.py','site/benchmarks/openenv-2026-07-29.json','site/benchmarks/index.json']
files += [str(x.relative_to(ROOT)) for x in (ROOT/'site/assets').iterdir() if x.is_file()]
files += [str(x.relative_to(ROOT)) for x in (ROOT/'site/deploy').iterdir() if x.is_file()]
with tarfile.open(ROOT/'deploy-build/pelicanmap-publisher.tar.gz','w:gz') as tar:
    for file in files:tar.add(ROOT/file,arcname=Path(file).as_posix())
print('Publisher package ready')
