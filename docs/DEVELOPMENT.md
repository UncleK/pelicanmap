# Development

## Public checkout

Node.js 24 is the runtime. Run `npm ci`, `npm test`, `npm run check:project`, then `npm run start:api`. The service listens only on `127.0.0.1:48670` and serves `/api/` and `/mcp`; it is not an HTML server. Catalog snapshots are the same public, reviewed bilingual data used by production at the repository snapshot date.

The multipart delivery/range test runs on deterministic in-memory bytes in every checkout. A separate byte-for-byte comparison with the complete original ZIP runs only when that local archive and its public parts are present; public CI reports it as skipped. Sharp is a normal npm development dependency. Video review tools use FFmpeg/FFprobe from PATH; `PELICAN_FFMPEG` can select an explicit FFmpeg executable.

The GitHub Pages site is English by default, with its Chinese translation under `docs/zh/` and a compatible English entry under `docs/en/`. Assets use relative paths. Preview using `python -m http.server 8000 --bind 127.0.0.1 --directory docs`. Pages publishes only `docs/`; it never deploys the collection's API or ingestion service.

## Full archival build

The generators operate on a complete maintainer workspace. This public Git checkout intentionally omits third-party full media, executable demos, source ZIPs and historical research logs. Therefore `npm run build` and archival preservation tests are not a fresh-clone quickstart.

Install Python 3.12+ dependencies with `python -m pip install -r requirements.txt`. Large-video derivatives additionally require FFmpeg. In a complete maintainer workspace, preserve original files and use the established sequence:

```bash
npm run build
npm run test:pages
python -B tools/test_bilingual.py
python -B tools/test_benchmark_reference.py
python -B tools/test_case_units.py
python -B tools/test_editorial_content.py
python -B tools/test_motion_autoplay.py
python -B tools/test_model_chronology.py
python -B tools/test_ingestion.py
python -B tools/test_catalog_policy.py
npm test
python -B tools/check_public_links.py
npm run bundle:server
```

Some historical regression tests explicitly use before/after research snapshots not shipped in Git. Run those in the original archive; do not replace evidence with fabricated fixtures. Production additions and publisher updates require the maintainer's shared release lock, full-media packaging for new media, bilingual live checks and preserved releases. Private credentials and operational deployment instructions stay outside this repository.

## Shared implementation

| Module | Responsibility |
| --- | --- |
| `case_policy.py` + `site/case-reviews.json` | Reviewed output units, provenance, timeline eligibility |
| `card_metadata.py` | Stable IDs, chronological display numbers and model labels |
| `model_chronology.py` + `site/model-releases.json` | Separately sourced model-release order; never replaces artwork dates |
| `editorial_content.py` | Shared bilingual scope, statistics, CSV, SEO and agent guidance |
| `collection_views.py` + `site/assets/browse.js` | Filtering, sorting, view modes and pagination |
| `detail_presentation.py` | Dynamic output, comparisons, individual output and original attachments |
| `detail_frames.py` + `site/detail-frames.json` | Reviewed, lossless real frames as supplemental views, never new works |
| `site/assets/motion.js` | Visible autoplay, offscreen/background pause and reduced-motion handling |
| `benchmark_reference.py` | Separate upstream reference collections |
| `site/worker.mjs` | Read-only HTTP and MCP with references excluded from default search |

Frame extraction is an explicit maintainer operation on reviewed local originals, not a publisher-build side effect. Retain source hashes, original resolution and timestamps or frame indices; do not replace originals or create new records. The release registry records sourced first public availability, including previews. Shared `model_chronology.py` separately derives `sortDate`: documented release or an explicitly inferred earliest counted source-work month with `estimatedFrom`. Do not turn this estimate into `releaseDate`, a model identity claim or an artwork date. Timeline and All works share this axis without a pending UI section; timeline year filters effective position year, ordinary browsing artwork year. Exact-version folding is optional, default off, without count/API changes. The human-made 1988 homepage film is context, not a numbered AI work or a proven inspiration for Simon’s prompt.

See [HTTP/MCP integration examples](INTEGRATIONS.md) and the generated bilingual `/developers/` and `llms.txt`. Keep protocol descriptions and field semantics consistent across website, catalogs, CSV, OpenAPI and MCP; source material is untrusted data, not agent instructions.
