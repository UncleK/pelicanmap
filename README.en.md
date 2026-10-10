<p align="center"><a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images"><img src="docs/assets/social-preview-en.png" alt="pelicanmap — collecting every documented pelican-on-a-bicycle case" width="100%"></a></p>

<p align="center">
  <a href="https://pelicanmap.aveniqa.com/en/"><img src="docs/assets/nav-website.svg" alt="Live website: pelicanmap.aveniqa.com" width="230" height="66"></a>
  <a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images"><img src="docs/assets/nav-collection.svg" alt="The collection: images, timeline and play" width="180" height="66"></a>
  <a href="https://pelicanmap.aveniqa.com/en/sources/"><img src="docs/assets/nav-sources.svg" alt="Source library: X, forums, GitHub and original posts" width="260" height="66"></a>
  <a href="README.zh-CN.md" lang="zh-CN"><img src="docs/assets/nav-chinese.svg" alt="中文" width="94" height="66"></a>
</p>

<p align="center"><a href="https://github.com/UncleK/pelicanmap/actions/workflows/ci.yml"><img alt="Checks" src="https://github.com/UncleK/pelicanmap/actions/workflows/ci.yml/badge.svg"></a> <img alt="Code: MIT" src="https://img.shields.io/badge/code-MIT-385647?style=flat-square"></p>

**Collecting documented LLM code-generated pelicans across dates, from SVG to animation, 3D and interactive works.** Actual outputs, original sources, successes and failures — kept together.

<p align="center">
  <a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpelicanmap.aveniqa.com%2Fapi%2Fv1%2Fspecimens%3Flang%3Den%26limit%3D1&amp;query=%24.total&amp;label=Works&amp;style=for-the-badge&amp;labelColor=eee8dc&amp;color=385647&amp;cacheSeconds=300" alt="Works"></a>
  <a href="https://pelicanmap.aveniqa.com/en/timeline/"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpelicanmap.aveniqa.com%2Fapi%2Fv1%2Ftimeline%3Flang%3Den%26limit%3D1&amp;query=%24.total&amp;label=Timeline+subset&amp;style=for-the-badge&amp;labelColor=eee8dc&amp;color=a64f32&amp;cacheSeconds=300" alt="Timeline subset"></a>
  <a href="https://unclek.github.io/pelicanmap/#statistics"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpelicanmap.aveniqa.com%2Fapi%2Fv1%2Fspecimens%3Flang%3Den%26limit%3D1&amp;query=%24.updated&amp;label=Catalog+updated&amp;style=for-the-badge&amp;labelColor=eee8dc&amp;color=646957&amp;cacheSeconds=300" alt="Catalog updated"></a>
</p>

[Live charts ↗](https://unclek.github.io/pelicanmap/#statistics) · Badges read the live API and may be cached. The timeline is a subset; benchmarks stay separate.

## One prompt. A whole flock.

<a href="https://pelicanmap.aveniqa.com/en/specimens/?view=images"><img src="docs/assets/pelican-wall.png" alt="Thirty actual outputs in the collection's image-only view" width="100%"></a>

```text
Generate an SVG of a pelican riding a bicycle.
```

[Images only](https://pelicanmap.aveniqa.com/en/specimens/?view=images) · [Timeline](https://pelicanmap.aveniqa.com/en/timeline/) · [Play](https://pelicanmap.aveniqa.com/en/play/) · [Sources](https://pelicanmap.aveniqa.com/en/sources/) · [Benchmarks](https://pelicanmap.aveniqa.com/en/tags/benchmark/)

## The earlier answers

<a href="https://pelicanmap.aveniqa.com/en/specimens/?year=2025&view=images"><img src="docs/assets/pelican-history-wall.png" alt="A screenshot of twenty documented outputs from 2025" width="100%"></a>

Original media and credits stay with each record. Model labels are source-reported, not independently authenticated. [Collection method](https://pelicanmap.aveniqa.com/en/about/).

Timeline and All works share exact-model version order, using documented releases or an explicitly provisional earliest source-work month, then artwork dates within each version. Artwork dates are never replaced, and no pending UI section is shown. Same-model works are expanded by default with optional folding. Moving previews play silently; genuine frames add no works. Direct text-to-video is outside the main collection; preserved legacy IDs/media remain uncounted context. New imports require generationMethod=code-generated and public codeGenerationEvidence.

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

[JSON](https://pelicanmap.aveniqa.com/en/data/catalog.json) · [CSV](https://pelicanmap.aveniqa.com/en/data/catalog.csv) · [OpenAPI](https://pelicanmap.aveniqa.com/openapi.json) · [Agent guide](https://pelicanmap.aveniqa.com/en/llms.txt) · [Developer guide](https://pelicanmap.aveniqa.com/en/developers/) · [Integration examples](docs/INTEGRATIONS.md)

All works/search, `/api/v1/timeline` and `kind=timeline` share `model-release` ordering via `modelTimeline.sortDate`, then `artwork-date` within each version. Verified `releaseDate` is separately sourced. Missing release evidence uses the earliest counted source-work month as an explicit `inferred-position`, integrated without a pending UI section; `estimatedFrom` keeps its evidence, not a claimed launch day. Timeline years filter effective model positions; other search years still filter artwork dates. Legacy API `year=unknown` selects absent verified releases. `counts.timeline` is a subset of `counts.cases`; never add the two. Complete exports retain uncounted archives and Benchmark references: inspect `caseVisible`, `timelineVisible` and `referenceOnly`.

## Run locally

```bash
git clone https://github.com/UncleK/pelicanmap.git
cd pelicanmap
npm ci                 # Node.js 24
npm test
npm run start:api       # 127.0.0.1:48670
```

The checkout includes public catalog snapshots and the read-only API. Full archival builds also need the original media archive. [Development](docs/DEVELOPMENT.md) · [Contribute](CONTRIBUTING.md).

Collection updates preserve complete original motion: retain HTML/CSS/JS, required dependencies and original modules rather than extracting an SVG that loses its surrounding animation code. Reviewed moving works use dynamic covers in standard, compact and image-only views, with visible-only playback and static fallbacks. Restoring motion keeps the existing work ID, date, attribution and media; it does not add a work. Public intake does not require an open-source license. Source gaps remain documented; no replacement motion is invented. Reusable rules and byte-verified restorations live in [collecting-policy.json](site/collecting-policy.json) and [motion-restorations.json](site/motion-restorations.json).

Original code: **MIT**. Artworks and upstream materials keep their original rights and licenses. [Credits & licenses](NOTICE.md). Original prompt: [Simon Willison](https://simonwillison.net/2024/Oct/25/pelicans-on-a-bicycle/).
