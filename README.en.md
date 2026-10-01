<p align="center"><a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images"><img src="docs/assets/social-preview-en.png" alt="pelicanmap — collecting every documented pelican-on-a-bicycle case" width="100%"></a></p>

<p align="center"><a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images">Browse the collection ↗</a> · <a href="https://unclek.github.io/pelicanmap/">Project home</a> · <a href="README.zh-CN.md">Chinese</a></p>

<p align="center"><a href="https://github.com/UncleK/pelicanmap/actions/workflows/ci.yml"><img alt="Checks" src="https://github.com/UncleK/pelicanmap/actions/workflows/ci.yml/badge.svg"></a> <img alt="Code: MIT" src="https://img.shields.io/badge/code-MIT-385647?style=flat-square"></p>

**Collecting all documented pelican-riding-a-bicycle cases across AI models, dates and media.** Actual outputs, original sources, successes and failures — kept together.

**824 works · 543 timeline representatives · all media.** Snapshot: October 1, 2026. The timeline is a subset; benchmarks stay separate.

## One prompt. A whole flock.

<a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images"><img src="docs/assets/pelican-wall.png" alt="Thirty actual outputs in the collection's image-only view" width="100%"></a>

```text
Generate an SVG of a pelican riding a bicycle.
```

[Images only](https://pelicanmap.aveniqa.com/en/specimens/?view=images) · [Timeline](https://pelicanmap.aveniqa.com/en/timeline/) · [Play](https://pelicanmap.aveniqa.com/en/play/) · [Sources](https://pelicanmap.aveniqa.com/en/sources/) · [Benchmarks](https://pelicanmap.aveniqa.com/en/tags/benchmark/)

## The earlier answers

<a href="https://pelicanmap.aveniqa.com/en/specimens/?year=2025&view=images"><img src="docs/assets/pelican-history-wall.png" alt="A screenshot of twenty documented outputs from 2025" width="100%"></a>

Original media and credits stay with each record. Model labels are source-reported, not independently authenticated. [Collection method](https://pelicanmap.aveniqa.com/en/about/).

## Explore the field guide

<a href="https://pelicanmap.aveniqa.com/en/"><img src="docs/assets/selected-works-en.png" alt="Selected works with models, dates and credited records" width="100%"></a>

## API & MCP

```bash
curl 'https://pelicanmap.aveniqa.com/api/v1/specimens?q=Gemini&lang=en&limit=3'
```

```text
MCP  https://pelicanmap.aveniqa.com/mcp
     search_specimens · get_specimen · get_timeline
```

[JSON](https://pelicanmap.aveniqa.com/en/data/catalog.json) · [CSV](https://pelicanmap.aveniqa.com/en/data/catalog.csv) · [OpenAPI](https://pelicanmap.aveniqa.com/openapi.json) · [Developer guide](https://pelicanmap.aveniqa.com/en/developers/)

## Run locally

```bash
git clone https://github.com/UncleK/pelicanmap.git
cd pelicanmap
npm ci                 # Node.js 24
npm test
npm run start:api       # 127.0.0.1:48670
```

The checkout includes public catalog snapshots and the read-only API. Full archival builds also need the original media archive. [Development](docs/DEVELOPMENT.md) · [Contribute](CONTRIBUTING.md).

Original code: **MIT**. Artworks and upstream materials keep their original rights and licenses. [Credits & licenses](NOTICE.md). Original prompt: [Simon Willison](https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/).
