# Contributing

Source submissions, corrections and code improvements are welcome. Preserve existing records, stable IDs, original media and historical outputs.

## Source submissions

Use the source submission form. Include the original public URL, author, source-reported model label, actual output and date evidence. Preserve the prompt, settings, tools, iterations and human involvement when available. A repost is a citation, not an additional work.

Keep month-only dates at month precision. Split a multi-model image only with a verified model-to-image mapping.

Artwork dates and model release dates are different facts. Never move a work's source date to a model's launch day. Exact-version release ordering requires its own public evidence; ambiguous labels remain unverified. Frames, previews, recordings and full composites of an existing work are supplementary views, not new works. Preserve original bytes, source attribution and crop/frame hashes.

All dates and presentation media of source-reviewed LLM code-generated works are eligible. Direct text-to-video is outside the main collection, while genuine recordings of code-generated animation, 3D or interaction remain eligible. New imports require generationMethod=code-generated and public codeGenerationEvidence. Unknown workflows, unresolved provenance, duplication, rights, safety or access issues are deferred. Do not bypass access controls. Do not execute downloaded repository scripts. Code mirrors require verified permission/license; truly interactive on-site demos also require isolation and an interaction review.

## Code changes

1. Install Node.js 24 and run `npm ci`.
2. Run `npm test` and `npm run check:project`.
3. For changes to generators or collecting logic, run the full archival checks described in [development notes](docs/DEVELOPMENT.md) in a complete maintainer workspace; state which checks you could not run.
4. Update Chinese and English together. Preserve single-model card covers, equal card regions and single-line model footers. Keep `counts.cases` separate from its timeline subset and Benchmark references.

Do not add credentials, local archives, screenshots containing account information or server operational logs. Never automatically publish a new source batch as a side effect of a code change. CI validates the public repository; production publication is a separate maintainer operation.
