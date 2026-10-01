# Contributing / 参与维护

欢迎补充出处、修正记录、反馈界面问题和提交代码改进。Please preserve existing records, stable IDs, original media and historical outputs.

## Submit a source / 提交来源

Use the source submission form. Include the original public URL, author, source-reported model label, actual output and date evidence. Preserve the prompt, settings, tools, iterations and human involvement when available. A repost is a citation, not an additional work.

来源提交请带原帖、作者、来源模型标签、实际输出和日期依据；能找到的提示词、设置、工具与迭代过程请一并提供。只有月份证据时不要补造具体日。多模型拼图必须有可核对的模型对应关系，才可拆分作品。

All dates and media are eligible for review. Unresolved provenance, duplication, rights, safety or access issues are deferred. Do not bypass access controls. Do not execute downloaded repository scripts. Code mirrors require verified permission/license; truly interactive on-site demos also require isolation and an interaction review.

## Code changes / 代码改进

1. Install Node.js 24 and run `npm ci`.
2. Run `npm test` and `npm run check:project`.
3. For changes to generators or collecting logic, run the full archival checks described in [development notes](docs/DEVELOPMENT.md) in a complete maintainer workspace; state which checks you could not run.
4. Update Chinese and English together. Preserve single-model card covers, equal card regions and single-line model footers. Keep `counts.cases` separate from its timeline subset and Benchmark references.

Do not add credentials, local archives, screenshots containing account information or server operational logs. Never automatically publish a new source batch as a side effect of a code change. CI validates the public repository; production publication is a separate maintainer operation.
