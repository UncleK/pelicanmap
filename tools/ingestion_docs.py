"""Public documentation contains no credentials or private host paths."""
def section(english=False):
    if english:
        return '''<section class="prose"><h2>Continuous submissions</h2><p>Authorized maintainers can submit bilingual static SVG output previews using a separate Bearer token. Public MCP stays read-only.</p><p>The current adapter covers Simon Willison dated articles. It verifies author/date, the source's model label and linked media ownership; static images are decoded and retained byte-for-byte. Source-attributed models are not independently authenticated. The collection and timeline accept all dates and media. This adapter remains limited to static previews; other sources and formats use reviewed local imports or verified new adapters, not weakened source/security checks.</p><p>Required fields: sourceUrl, date (YYYY-MM-DD), model, author, format (svg), title {zh,en}, notes {zh,en}, media (one static SVG-preview URL), unitType (single-model-output), modelToMediaVerified (true). prompt is optional. Split comparisons before submission; never submit a composite as one model's cover.</p><pre>POST /api/v1/ingest
Authorization: Bearer YOUR_PRIVATE_TOKEN
Content-Type: application/json

GET /api/v1/ingest/{submissionId}</pre><p>HTTP 202 returns a statusUrl. Final statuses are published, duplicate or needs_review. Authentication is required for submission, status and export. This is not an autonomous crawler. Image checks establish availability, not independent reproduction or a model quality score.</p></section>'''
    return '''<section class="prose"><h2>持续收录接口</h2><p>获授权维护者可使用独立 Bearer 密钥提交双语静态 SVG 输出预览；公开 MCP 仍只读。</p><p>当前适配 Simon 日期文章：校验作者、日期、来源模型标注、媒体链接及域名；静态图片解码后保留原始字节。模型归属按来源记录、未独立认证。馆藏和时间线均不限时间段和媒体类型；此接口适配器仍仅处理静态预览，其它类型走本地审核导入或经验证的新适配器，不取消来源/安全检查。</p><p>必填字段：sourceUrl、date（YYYY-MM-DD）、model、author、format（svg）、title {zh,en}、notes {zh,en}、media（一个静态 SVG 预览链接）、unitType（single-model-output）、modelToMediaVerified（true）；prompt 可选。多模型或多档位原帖应先拆成真实输出，拼图不得作为单模型封面。</p><pre>POST /api/v1/ingest
Authorization: Bearer YOUR_PRIVATE_TOKEN
Content-Type: application/json

GET /api/v1/ingest/{submissionId}</pre><p>HTTP 202 返回 statusUrl；最终状态为 published、duplicate 或 needs_review。提交、状态和导出需认证。接口不自动爬取全网，媒体可读不等于独立复现或模型能力评分。</p></section>'''
