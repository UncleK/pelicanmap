"""Stage explicit source-labelled static outputs, without editing the museum.

URLs are the user's scope; parent prose and transcript sections are source
evidence. Never extract illustrative SVG snippets from reasoning traces.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from audit_user_history_links import ROOT, OUT, request

STAGE=OUT/'staged'
STAGE.mkdir(exist_ok=True)
sources=json.loads((OUT/'sources.json').read_text(encoding='utf8'))
linked=json.loads((OUT/'linked-gists.json').read_text(encoding='utf8'))
gists={x['sourceUrl'].rsplit('/',1)[-1]:x for x in sources+linked if x.get('files')}
candidates=[]

def response_blocks(text):
    headings=list(re.finditer(r'^#{2,3} Response:?\s*$',text,re.M))
    result=[]
    for h in headings:
        tail=text[h.end():]
        end=re.search(r'^#{1,3}\s+[^\n]+$',tail,re.M)
        result.append(re.findall(r'<svg\b[\s\S]*?</svg\s*>',tail[:end.start()] if end else tail,re.I))
    return result

def add(ident,source,date,model,variant,svg,media_url,selection=None,group=None,default=False,notes=None,prompt=None):
    if re.search(r'<(?:animate\w*|set|script)\b|@keyframes|\banimation\s*:',svg,re.I):
        print('EXCLUDED animation',ident)
        return
    data=svg.encode('utf8')
    (STAGE/(ident+'.svg')).write_bytes(data)
    c={'id':ident,'sourceUrl':source,'date':date,'sourcePublicationDate':date,'dateBasis':'source-publication','model':model,'author':'Hard Prompts' if 'hardprompts' in source else 'Simon Willison',
       'format':'svg','variant':variant,'unitType':'single-model-output','modelToMediaVerified':True,
       'title':{'zh':model+' · '+variant,'en':model+' · '+variant},
       'notes':notes or {'zh':'原始静态 SVG，按来源标注模型与运行设置；模型身份未独立认证。日期为来源公开日，不推测实际生成时间。保留失败造型，不重画。','en':'Original static SVG with source-reported model and run settings, not independently authenticated. The date is source publication, not an inferred generation date. Failed geometry is preserved without redrawing.'},
       'rights':{'zh':'作品权利归原作者；本站归档不改变原作品许可。','en':'Rights remain with the original author; archiving does not change the source licence.'},
       'prompt':prompt or 'Generate an SVG of a pelican riding a bicycle',
       'evidence':[source,media_url], 'sourceCodeUrl':source if 'gist.github' in source else '',
       'media':[{'url':media_url,'filename':ident+'.svg','sha256':hashlib.sha256(data).hexdigest(),'caption':{'zh':'原始静态 SVG · '+variant,'en':'Original static SVG · '+variant},**(selection or {})}]}
    if group:c['modelRunGroup']=group
    if default:c['authorDefault']=True
    candidates.append(c)

def gist_output(gid,name,index=0,svg_index=0,model=None,variant='source output',source=None,ident=None,group=None,default=False):
    s=gists[gid];f=next(f for f in s['files'] if f['name']==name)
    blocks=response_blocks(f['text'])
    svg=f['text'] if name.endswith('.svg') else blocks[index][svg_index]
    labels=re.findall(r'Model:\s*\*\*(.*?)\*\*',f['text'])
    model=model or labels[min(index,len(labels)-1)]
    ident=ident or 'history-'+gid[:8]+'-'+str(index)+'-'+str(svg_index)
    add(ident,source or s['sourceUrl'],s['created'][:10],model,variant,svg,f['url'],
        None if name.endswith('.svg') else {'svgFromTranscript':True,'responseIndex':index,'svgIndex':svg_index},group,default)

for gid,name,variant in [
    ('56217af454695a90be2c8e09c703198a','qwen-pelican-bicycle.md','source output'),
    ('4728316a9e4854c6e62fa25c40759bb6','animated.md','initial static response'),
    ('c34f7f0c94afcbeab77e170511f6f51f','gemini-pelican.md','source output'),
    ('5b61866cb4ce67899934c29a9de1b4be','pelican.md','source output'),
    ('d8765ea8413592b074ded45cbc585c54','r1-pelican.md','source output')]:
    gist_output(gid,name,variant=variant)

gist_output('32a85e337fbc6ee935d10d89726c0476','kimi-2.5-pelican.svg',model='Kimi K2.5',source='https://simonwillison.net/2026/Jan/27/kimi-k25/')
gist_output('1869e1bbcafe5bcad0f26351f6a978a6','pelican.svg',model='ornith-1.0-35b-Q4_K_M.gguf',source='https://simonwillison.net/2026/Jun/29/ornith/',ident='simon-ornith-2026-06-29')
gist_output('cb69816b3fb940f2782569a82a523af1','hy4.md',variant='high',source='https://simonwillison.net/2026/Aug/29/hy4/',ident='simon-hy4-2026-08-29-high',default=True)
for index,variant in enumerate(['default','high']):
    gist_output('83bfb1171792f1e7a4d8935b5e82317e','deepseek-flash.md',index=index,variant=variant,source='https://simonwillison.net/2026/Jul/31/deepseek-v4-flash-0731/',ident='simon-deepseek-v4-flash-0731-'+variant,group='simon-deepseek-v4-flash-0731-2026-07-31',default=index==0)

# Two quantizations, one source/date/model group. The visible article favourite
# is not relabelled as a default; medium from the Q2 rerun represents the axis.
for gid,name,quant in [('f9c69ebdab90d8a45b8de4742cc7b840','gistfile1.md','UD-IQ1_S'),('6ba7cbfc1a9336986703b41f7fccd73a','Q2.md','UD-Q2_K_XL')]:
    s=gists[gid];f=next(f for f in s['files'] if f['name']==name)
    responses=response_blocks(f['text'])
    offset=0 if quant=='UD-IQ1_S' else 1
    for index,effort in enumerate(['none','low','medium','xhigh']):
        variant=effort if quant=='UD-Q2_K_XL' else quant+' · '+effort
        gist_output(gid,name,index=index+offset,model='Qwen3.8-Flash-Next',variant=variant,source='https://simonwillison.net/2026/Aug/26/qwen38-flash-next/',ident='simon-qwen38-flash-next-'+quant.lower().replace('_','-')+'-'+effort,group='simon-qwen38-flash-next-2026-08-26')
        candidates[-1]['notes']={'zh':'作者在 DGX Spark 使用 '+quant+' 量化测试 '+effort+' 推理档位；原始 SVG 从 Response 区逐字提取，不使用 Reasoning 中的草稿。两个量化共用同日模型对照，Q2 的 medium 进入时间线；原文最爱不是默认档，不按好坏挑图。模型未独立认证。日期为 Gist 公开日。','en':'Source run on DGX Spark with '+quant+' quantization and '+effort+' reasoning. SVG is copied verbatim from Response, not draft snippets in Reasoning. Both quantizations share one dated model comparison; Q2 medium represents the timeline. The author’s favourite is not relabelled as a default or selected for quality. Model unverified; date is Gist publication.'}

hard='https://hardprompts.ai/topics/pelican-bicycle-svg.html'
html,_=request(hard)
soup=BeautifulSoup(html,'html.parser')
prompt=soup.select_one('.prompt-text').get_text('\n',strip=True)
for panel in soup.select('.iteration-content[data-model][data-iteration]'):
    model,run=panel['data-model'],panel['data-iteration']
    date=panel.select_one('.response-date')['data-timestamp'][:10]
    text=panel.select_one('pre code').get_text().strip()
    svgs=re.findall(r'<svg\b[\s\S]*?</svg\s*>',text,re.I)
    assert len(svgs)==1
    ident='hardprompts-2025-12-03-'+model.replace('.','-')+'-run-'+run
    add(ident,hard,date,model,'run '+run,svgs[0],hard,{'svgFromHardPrompts':True,'sourceModel':model,'sourceRun':run},group='hardprompts-2025-12-03-'+model.replace('.','-'),default=run=='4',
        notes={'zh':'Hard Prompts 公开的 '+model+' 第 '+run+' 次静态输出；日期取逐条 response timestamp。题面含鸟喙、踩踏和 400×300 画布等额外要求，不等同于 Simon 的无附加约束原题。模型由上游标注、未独立认证；运行耗时/成本不是本馆评分。页面默认展示 run 4，作为同日代表；其余独立输出计入全部作品。','en':'Hard Prompts public '+model+' run '+run+', dated by its response timestamp. The prompt adds beak, pedalling and roughly 400×300 canvas requirements, unlike Simon’s unconstrained original. Model is source-labelled, not authenticated. Runtime/cost are not museum scores. The page defaults to run 4 as its dated representative; other independent outputs count as works.'},prompt=prompt)
    candidates[-1].pop('sourcePublicationDate',None)
    candidates[-1]['dateBasis']='source-reported-response-timestamp'
    candidates[-1]['sourceResponseTimestamp']=panel.select_one('.response-date')['data-timestamp']

manifest={'reviewed':False,'batch':'2026-10-01-user-history-links','cases':candidates}
(OUT/'staged-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('Staged',len(candidates),'source-labelled outputs for deduplication and visual review')
