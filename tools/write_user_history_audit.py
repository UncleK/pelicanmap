"""Generate the local source-decision ledger from this reviewed batch only."""
import json
from audit_user_history_links import ROOT, OUT, URLS, request

decisions={
    URLS[0]:('已有/重复','原点的 22 个后续完整 SVG 已在馆内，初次发布与后补日期已有审核；不按文章再计一遍。'),
    URLS[1]:('已有/重复','仓库 22 个静态 SVG 与现有原点文件对应；不运行仓库脚本。'),
    URLS[2]:('已有/重复','上一批已按作者标签拆出 22 个模型面板，其中 o1-pro 回链旧图；完整演讲图片已留详情。'),
    URLS[3]:('索引入口','实际标签页可读；只用作原文导航，不将文章索引计成作品。旧文按本批原文/Gist 核验，不宣称全索引穷尽。'),
    URLS[4]:('已有/无合格增量','原 HTML 提取 124 个 /p/ ID，112 个对应馆内旧 ID；其余 12 个是缺少可信模型/真实输出映射的测试条目，不收。聚合日期与模型不替代原始出处。'),
    URLS[5]:('索引待继续','实际有约 60 个模型卡入口，首卡正文混入另一篇 Qwen 描述；因此只使用原媒体和原文回链，不信任聚合标签。URL 差异不能证明作品缺失，本轮不据此批量搬运，尚未完成全部 60 项原文逐张复核。'),
    URLS[6]:('综述/不计数','原文自述汇总 Simon 作品并回链 Pelican Zoo；不是另一次生成，正文讨论与重复配图不增加作品。'),
    URLS[7]:('已有/重复','原点当天的 Mastodon 分享不再生成第二组作品；保留原仓库/原文对应关系。'),
    URLS[8]:('已有/去重更正','原始 Gist 的 SVG 与 Zoo SVG 渲染相同，X 图也相同；原文更早公开于 2024-11-12。保留原 SVG、补精确 qwen2.5-coder:32b 标签，X 详情改为不计数重复出处。'),
    URLS[9]:('已有/部分暂缓','首次静态 Response 与原点 gemini-exp-1206 已有图一致；之后动画 Response 不收。'),
    URLS[10]:('异介质暂缓','原文件是 GLB 三维模型，不是静态 SVG，不入普通馆藏。'),
    URLS[11]:('已有/重复','2025-03-25 Gist SVG 与已收 Gemini 2.5 Pro 原预览对应；逐图人工核验，不重复计数。'),
    URLS[12]:('已有/重复','原帖 Gemini 2.5 Pro 图已存在，未因 X 与 Gist/文章 URL 不同而重复新增。'),
    URLS[13]:('新增 1','原始默认 thinking 的静态 Response 可逐字提取；原文明确为作者默认，与已有 thinking_budget=0 共用同日对照，后续动画不收。'),
    URLS[14]:('异介质暂缓','原帖演示 p5.js 动画，不当作静态 SVG 新作品。'),
    URLS[15]:('新增 1','原始 deepseek-reasoner 静态 Response 独立输出，保留失败造型与 Gist 公开日，不按综述日期重复收。'),
    URLS[16]:('已有/重复','Qwen3-4B 的 pelican Thinking / Instruct 已有；human-on-bicycle 是另一题，不当成新鹈鹕输出。'),
    URLS[17]:('新增 23','6 个来源模型各 4 次原始运行，23 个静态 SVG 能解码；Gemini 2.5 Pro run 2 的上游命名空间错误，不修、不计。时间线按原页默认 run 4 选 6 张，详情明确是重复运行而非推理档位；无本站评分标签。'),
    URLS[18]:('已有/重复','文章复用 GPT-5 代表图，训练/方法论不是新图日期。'),
    URLS[19]:('已有/重复','Gemini 3 classic / strengthened prompt、low/high 与其对照模型已在旧图与上一批审核关系中，不再计数。'),
    URLS[20]:('已有/重复','Gemini 3 / GPT-5.1 / Claude Sonnet 4.5 的加强题媒体与已有图对应。'),
    URLS[21]:('新增 1','原帖明确 GPT-5.2-Codex、effort medium 和静态 SVG 请求；保存其公开的原始 PNG 预览，不声称取得 SVG 源码、不执行 CLI。'),
    URLS[22]:('已有/重复','年终文章复用先前 GPT-5 输出；不以回顾文章日期覆盖旧作品。'),
    URLS[23]:('已有/重复','Kimi K2.5 Gist SVG 与已存上游 PNG 同一图；不增加作品。'),
    URLS[24]:('已有/参考','仍属独立 HF/OpenEnv Benchmark 参考合集，不进主时间线、总数或编号。'),
    URLS[25]:('已有/重复','日归档中 Qwen3.6-35B-A3B / Opus 4.7 对照已有原帖与作品关系，不按日归档重收。'),
    URLS[26]:('入口受限','搜索 URL 的自动读取返回 403；使用可读标签页和已提供的直接原文核验，不绕过限制，不把搜索摘要当输出。'),
    URLS[27]:('异介质暂缓','本页鹈鹕 SVG 响应包含 SMIL 动画；不拆一帧冒充新静态 SVG。其它非鹈鹕题未扩大到本次普通增量。'),
    URLS[28]:('新增 1','原帖链接的 pelican.svg 可打开；模型保留来源文件标签 ornith-1.0-35b-Q4_K_M.gguf，非独立认证。'),
    URLS[29]:('异介质暂缓','精灵表/宠物与动画输出，不入新的普通静态图鉴。'),
    URLS[30]:('拆分 2','default/high 两个原始 Response 对应已存 X 对照帖；按更早原文公开日 2026-07-31 拆成 2 个作品，时间线仅 default。不是 2 张此前从未出现过的图。'),
    URLS[31]:('已有/部分暂缓','Qwen3.8-27B thinking/non-thinking 图已存；文中动画与非本题工具演示不新增。'),
    URLS[32]:('新增 8','两份量化转录各 none/low/medium/xhigh，逐个 Response 提取原始静态 SVG；Reasoning 示例不收。共 8 输出，Q2 的 medium 只占 1 张时间线代表。'),
    URLS[33]:('新增 1','原始 high Response 可打开；作者明确默认 high，不按画得最好替换默认档。'),
    URLS[34]:('归属不足暂缓','网页的 7 张 SVG 没有可核验逐图模型身份，含 Anonymous attribution 和人类署名；不能用于单模型进化轴，不猜模型或生成日期。'),
    URLS[35]:('归属不足暂缓','README 是策展/戏仿收藏描述，不提供逐图模型与运行日期证据；与网页同组，不新增 7 个未知模型案例。'),
    URLS[36]:('二级入口/暂缓','后台浏览器读到 2025-07-15 的报告，回链 SVGViewer 与 SVGStud.io；这是报告日，不是输出日。SVGStud.io 原页有 4 图与 CC-BY-SA 4.0，但仅匿名 Free User、无逐图模型/生成日期；SVGViewer 本轮无法核实，均不强收。'),
}
assert set(decisions)==set(URLS)
catalog=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
snapshot=OUT/'before-published-catalog.json'
if not snapshot.exists():
    data,meta=request('https://pelicanmap.aveniqa.com/data/catalog.json?before-history-links=20261001')
    before=json.loads(data)
    assert before['counts']['cases']==700 and before['counts']['timeline']==401,'Published baseline changed; recheck the batch before deployment'
    snapshot.write_bytes(data)
manifest=json.loads((OUT/'approved-manifest.json').read_text(encoding='utf8'))
rows=[{'url':u,'decision':decisions[u][0],'reason':decisions[u][1]} for u in URLS]
(OUT/'decisions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
lines=['# 用户历史链接核验 · 2026-10-01','','仅以 37 个去重 URL 及实际原文为输入；不使用用户的日期、数量、模型或介质备注作为证据。','',
       '## 本批结果','',f'- 导入 38 条独立作品记录：36 张漏收输出，2 张从已有 DeepSeek 对照拆分的输出。',
       '- 合并 1 组旧 Qwen 重复出处；主馆从 700 到 737（净增 37），时间线从 401 到 412（净增 11）。',
       '- 42 份 SVG 候选逐个源版本/Response 审核，4 份重复排除，1 份上游损坏排除；另纳入 1 份原帖明确为静态 SVG 的原始 PNG 预览。',
       '- 37 份 SVG 与 1 份 PNG 本地归档，哈希与逐字提取校验；不执行下载源码。',
       '- 字节/规范化 SVG 对照与 48px 渲染最近邻只用作线索，六张联系表及原文逐图人工核验；不能保证检测所有任意裁切/变形重复。',
       '- Hard Prompts 同页多次输出以 model/run 选择器 + 精确媒体哈希区分，不能把页面 URL 当唯一图像。日期与模型均按上游保留，未独立认证。',
       '- Benchmark 仍 1 个合集、138 个旧参考行；本批不新增动画、3D、精灵表、游戏或未知模型作品。','',
       '## 逐链接决定','','| URL | 决定 | 实际证据与处理 |','| --- | --- | --- |']
lines.extend('| '+r['url']+' | '+r['decision']+' | '+r['reason']+' |' for r in rows)
lines+=['','## 新增明细','','| 模型 | 日期 | 档位／运行 | 本站详情 |','| --- | --- | --- | --- |']
lines.extend('| '+c['model']+' | '+c['date']+' | '+c['variant']+' | https://pelicanmap.aveniqa.com/specimens/'+c['id']+'/ |' for c in manifest['cases'])
lines+=['','## 文件与复用边界','','- sources.json / linked-gists.json：公开来源正文、版本和回链。','- evidence/：来源原响应与 SHA-256，staged/：逐字提取候选，不公开损坏候选。','- dedup.json / review-1.jpg 至 review-6.jpg：候选重复线索与人工对照。','- approved-manifest.json / reviewed-manifest.json / import-audit.json：明确批准的模型输出映射和实际导入结果。','- before-case-reviews.json：修改前审核关系备份。','- tools/import_collection_batch.mjs：通用固定转录 / Hard Prompts 选择器与媒体去重；本批脚本只是明确审核映射，不是自动猜测采集器。','- Nile 60 卡原文和更广的索引覆盖尚未穷尽，不能标记历史已收全。','']
(OUT/'audit.md').write_text('\n'.join(lines),encoding='utf8')
print(json.dumps({'urls':len(rows),'approved_records':len(manifest['cases']),'counts':catalog['counts']}))
