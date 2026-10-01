<p align="center"><a href="https://pelicanmap.aveniqa.com/en/"><img src="docs/assets/social-preview.png" alt="pelicanmap · One bird. One bicycle. A small history of AI." width="100%"></a></p>
<p align="center"><a href="https://pelicanmap.aveniqa.com/en/">Visit the collection ↗</a> · <a href="https://pelicanmap.aveniqa.com/en/timeline/">Timeline</a> · <a href="https://unclek.github.io/pelicanmap/en/">Project home</a> · <a href="README.md">中文</a></p>

## A small prompt. An unfolding story.

**“Generate an SVG of a pelican riding a bicycle.”**

From SVG to animation, video, 3D, games and documented visual-agent iterations, this small question keeps finding new answers. **pelicanmap** is a bilingual field guide to those actual outputs, with original sources, source-reported model labels, dates and generation conditions.

Good drawings deserve a closer look. Failed drawings deserve a place in the archive, too.

| Independent works | Timeline representatives | Source articles | Benchmark collections |
| :---: | :---: | :---: | :---: |
| **824** | **543** | **144** | **1** |

Snapshot: October 1, 2026; checked against the public catalog on October 2. Timeline entries are a subset of works, not an additional total. The benchmark is separate upstream reference data, not our ranking. [Current catalog](https://pelicanmap.aveniqa.com/en/data/catalog.json).

<details><summary>A look inside the collection ↗</summary>

[![Live collection screenshot](docs/assets/collection-preview.png)](https://pelicanmap.aveniqa.com/en/)

*Screenshot of the live website. Artwork attribution and original source: [full record](https://pelicanmap.aveniqa.com/en/specimens/simon-gpt61-sol-medium-2026-09-29/).*

</details>

## Explore

- [Selected works](https://pelicanmap.aveniqa.com/en/): one output, one record, from early experiments to recent work.
- [Timeline](https://pelicanmap.aveniqa.com/en/timeline/): dates, years and model families.
- [Collection](https://pelicanmap.aveniqa.com/en/specimens/): search and filter; standard, compact and image views.
- [Play](https://pelicanmap.aveniqa.com/en/play/): reviewed interactive demos isolated on a separate origin.
- [Benchmarks](https://pelicanmap.aveniqa.com/en/tags/benchmark/): HF / OpenEnv upstream scoring references.
- [Sources](https://pelicanmap.aveniqa.com/en/sources/): original posts, repositories and attribution.

## Keep the output. Explain the provenance.

One documented output by one source-labelled model at one established time is one work. Actual different settings are recorded separately; reposts, composites and multiple frames of the same video do not add works. Faithful crops keep coordinates, hashes and the complete original. Failed outputs are never redrawn or improved.

Dates retain their evidence precision. A month stays a month; publication is not authenticated generation time. Model identities are source-reported, not independently authenticated. Timeline representatives follow reviewed selection: author default, otherwise medium within explicit run groups. Missing evidence is not guessed. Individual examples are not model capability rankings.

All dates and media are eligible for review. Tools, iterations and human involvement remain explicit. Read the [method](https://pelicanmap.aveniqa.com/en/about/) and [rights notice](https://pelicanmap.aveniqa.com/en/rights/).

## Readable by people and programs

One reviewed catalog powers Chinese and English HTML, JSON, CSV, Markdown, RSS, sitemap, HTTP API and MCP.

```bash
curl 'https://pelicanmap.aveniqa.com/api/v1/specimens?q=Gemini&lang=en&limit=3'
curl 'https://pelicanmap.aveniqa.com/api/v1/timeline?family=Claude&lang=en&sort=oldest&limit=10'
```

Remote MCP: **`https://pelicanmap.aveniqa.com/mcp`**, Streamable HTTP, no login. Tools: `search_specimens`, `get_specimen`, `get_timeline`; `lang: zh/en`. Default search excludes source/context records and benchmark references; direct stable-ID lookup remains available. The public service is read-only and never executes artwork code.

[JSON](https://pelicanmap.aveniqa.com/en/data/catalog.json) · [CSV](https://pelicanmap.aveniqa.com/en/data/catalog.csv) · [OpenAPI](https://pelicanmap.aveniqa.com/openapi.json) · [llms.txt](https://pelicanmap.aveniqa.com/en/llms.txt) · [RSS](https://pelicanmap.aveniqa.com/en/feed.xml) · [Developer guide](https://pelicanmap.aveniqa.com/en/developers/)

## Run locally

Requires **Node.js 24**. Published bilingual catalog snapshots are included:

```bash
git clone https://github.com/UncleK/pelicanmap.git
cd pelicanmap
npm ci
npm test
npm run start:api
```

Visit `http://127.0.0.1:48670/api/v1/specimens?lang=en&limit=3`. To preview the project landing page:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Visit `http://127.0.0.1:8000/en/`. The full collection is hosted on the [live website](https://pelicanmap.aveniqa.com/en/). Its generators are included, but a complete archival build also needs original media, demos and historical verification files not distributed through Git. See [development notes](docs/DEVELOPMENT.md).

| Path | Purpose |
| --- | --- |
| `docs/` | Bilingual project landing pages, matching the collection’s paper / green / rust palette |
| `site/assets/` | Production styles and browsing logic |
| `site/catalog*.json` | Published catalog snapshots |
| `site/*.json` | Reviewed units, provenance, representatives and demo policies |
| `site/worker.mjs` | Read-only HTTP / MCP |
| `tools/` | Generators, review, import and verification tools |
| `pelican-web/data.js` | Structured historical base records |
| `.github/` | CI, Pages deployment and issue forms |

## Contribute and credit

Source submissions, attribution/date corrections, broken-link reports and code improvements are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md).

Original project code is **MIT licensed**. Third-party artworks, upstream code, quoted text and source material keep their own rights and licenses; inclusion does not make them MIT. Full third-party media, source ZIPs, credentials, retrieval logs and private operational files are excluded from Git. See [NOTICE.md](NOTICE.md).

The original prompt and early experiments come from [Simon Willison](https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/). Thanks to everyone who preserved an output and its creation context.

<p align="center"><sub>PELICAN MAP · AN AI FIELD GUIDE<br>One bird. One bicycle. A small history of AI.</sub></p>
