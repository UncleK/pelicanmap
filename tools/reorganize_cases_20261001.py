"""Explicit source-reviewed migration, not an unattended scraper.

Preserves old IDs/media, creates faithful crops, and writes reusable review data.
Run after sync; rerunning uses the immutable pre-migration catalog and stable IDs.
"""
import copy
import hashlib
import json
import re
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'pelican-archive/research/2026-10-01-case-units'
ARCHIVE.mkdir(parents=True,exist_ok=True)
before=ARCHIVE/'before-catalog.json'
if not before.exists():
    before.write_bytes((ROOT/'public-site/data/catalog.json').read_bytes())
items=json.loads(before.read_text(encoding='utf8'))['items']
byid={x['id']:x for x in items}
additions=json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
existing={x['id'] for x in additions}
reviews={}
created=[]


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def review(ident,role=None,reason='',fields=None,**extra):
    item=byid[ident]
    current=reviews.setdefault(ident,{'sourceUrl':item['sourceUrl'],'role':role or 'case','reason':reason,'evidence':[item['sourceUrl']],'fields':{}})
    if role is not None:current['role']=role
    current.update(reason=reason or current['reason'],**extra)
    current['fields'].update(fields or {})
    return current


def oid(original):
    exact=[x['id'] for x in items if x['originalId']==original]
    if exact:return exact[0]
    slug=re.sub('[^a-z0-9]+','-',original.lower()).strip('-')
    matches=[x['id'] for x in items if re.fullmatch(re.escape(slug)+r'-[a-f0-9]{8}',x['id'])]
    assert len(matches)==1, ('Ambiguous or missing source record',original,matches)
    return matches[0]


def crop(media,box,ident):
    original=ROOT/'pelican-web'/media['src'].lstrip('/')
    src='/media/collected/2026-10-01-case-units/'+ident+'-'+hashlib.sha256(str(box).encode()).hexdigest()[:8]+'.png'
    out=ROOT/'pelican-web'/src.lstrip('/')
    out.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(original) as im:
        im.load()
        assert 0<=box[0]<box[2]<=im.width and 0<=box[1]<box[3]<=im.height
        panel=im.crop(box)
        if out.exists():
            with Image.open(out) as old:
                assert old.size==panel.size and old.convert('RGBA').tobytes()==panel.convert('RGBA').tobytes()
        else:panel.save(out,'PNG')
    provenance={'original':media['src'],'crop':src,'box':list(box),'sourceSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'cropSha256':hashlib.sha256(out.read_bytes()).hexdigest(),'method':'pixel-crop-no-redraw'}
    return {'src':src,'source':media['source'],'caption':'原图裁切 · '+ident,'captionEn':'Faithful source crop · '+ident,'poster':'','sha256':provenance['cropSha256']},provenance


def child(parent,ident,model,index=0,box=None,date=None,variant='',task='pelican_bicycle',date_basis=None):
    p=byid[parent]
    m=copy.deepcopy(p['media'][index])
    prov=None
    if box:
        m,prov=crop(m,box,ident)
        media=[m,copy.deepcopy(p['media'][index])]
    else:media=[m]
    day=date or p['date']
    x=copy.deepcopy(p)
    for key in ['batch','caseNumber','modelNames','originalMetadata','caseReview','canonicalId','representativeOf','childIds','variantIds','duplicateIds','cropProvenance','thumbnailProvenance']:
        x.pop(key,None)
    note='从同一原帖按明确的模型／图片对应关系拆出；模型标签为来源自报，未独立认证。'+('仅按原图像素裁切，完整原图保留在详情页，未重画或优化。' if box else '原始媒体保持不变。')
    note_en='Split from the same source using its explicit model-to-image mapping. Model attribution is source-reported, not independently authenticated. '+('Only original pixels were cropped; the complete source image is retained below, without redrawing or improvement.' if box else 'The original media is unchanged.')
    if date_basis=='source-described-month':
        note+=' 原文只可证明作品所在月份，具体生成日未知，不补造某一天。'
        note_en+=' The source establishes only the month; the exact generation day is unknown and has not been invented.'
    x.update(id=ident,originalId=ident,title=model+' · '+(variant or '静态 SVG'),model=model,author=p['author'] or 'Simon Willison',date=day,month=day[:7],kind='timeline',
             format='svg',formatLabel='静态 SVG',originalForm='svg-source-crop' if box else 'svg-static-preview',originalLevel=variant,media=media,thumbnail=m['src'],representativeMedia=m['src'],
             notes=note,sourceCodeUrl=p.get('sourceCodeUrl',''),demoUrl='',previewUrl='',externalUrl='',interactive=False,parentId=parent,task=task,
             reviewedModelNames=[model],dateBasis=date_basis or 'source-publication',sourcePublicationDate=p['date'],updated='2026-10-01',path='/specimens/'+ident+'/',url='https://pelicanmap.aveniqa.com/specimens/'+ident+'/',markdown='/specimens/'+ident+'/index.md',
             i18n={'en':{'title':model+' · '+(variant or 'static SVG'),'notes':note_en,'promptStatus':p.get('i18n',{}).get('en',{}).get('promptStatus','See the original source for the complete per-run prompt.')}})
    if prov:x['cropProvenance']=prov
    byid[ident]=x
    if ident not in existing:
        additions.append(x);existing.add(ident);created.append(ident)
    else:
        old=next(a for a in additions if a['id']==ident)
        assert old.get('parentId')==parent and old['sourceUrl']==x['sourceUrl'], 'Do not overwrite an unrelated record'
        additions[additions.index(old)]=x
    review(ident,reason='Explicit source/image labels; faithful source panel or unchanged original attachment.',fields={'reviewedModelNames':[model]})
    return ident


def duplicate(old,target,reason):
    review(old,'duplicate',reason,{'canonicalId':target},timelineVisible=False)


def attach_full(ident,media,parent):
    x=byid[ident]
    new=copy.deepcopy(reviews.get(ident,{}).get('fields',{}).get('media',x['media']))
    if media['src'] not in {m['src'] for m in new}:new.append(copy.deepcopy(media))
    review(ident,fields={'media':new,'parentId':parent})


# Correct origin repository chronology using dated file-addition commits, not
# model names or release-day guesses. Blank gallery authors are now attributed.
commits={
    'gemini-exp-1114':('2024-11-22','38e520dc8d446ee29ca673b27042235bb076fe9f'),
    'gemini-exp-1121':('2024-11-22','38e520dc8d446ee29ca673b27042235bb076fe9f'),
    'gemini-exp-1206':('2024-12-06','5ee0fcf9f9533ee2702483995ea4d63adfb6ad85'),
    'us.amazon.nova':('2024-12-04','56a97961df9d00dd44434b64f61eef51f851765a')}
for x in items:
    if x['source']=='origin':
        f={'author':'Simon Willison','parentId':oid('github-simonw-pelican-bicycle'),'dateBasis':'source-publication'}
        for prefix,(day,commit) in commits.items():
            if x['model'].startswith(prefix):
                f.update(date=day,month=day[:7],dateBasis='first-file-public-commit',dateEvidenceUrl='https://github.com/simonw/pelican-bicycle/commit/'+commit)
        review(x['id'],reason='Original single SVG; repository additions retain documented first-publication dates.',fields=f)

# Zoo normalizes outer viewport attrs. Deduplicate only when the complete inner
# XML and all non-viewport attributes match the known original repository file.
for x in items:
    if x['source']=='zoo' and x['media'][0]['src'].endswith('.svg'):
        name=Path(x['media'][0]['src']).name.removeprefix('live_')
        original=next((y for y in items if y['source']=='origin' and Path(y['media'][0]['src']).name==name),None)
        if original:
            def xml_body(item):
                node=ET.fromstring((ROOT/'pelican-web'/item['media'][0]['src'].lstrip('/')).read_bytes())
                for k in ['width','height','viewBox']:node.attrib.pop(k,None)
                return ET.canonicalize(ET.tostring(node,encoding='unicode'),strip_text=True)
            if xml_body(x)==xml_body(original):
                duplicate(x['id'],original['id'],'Same original SVG; only outer viewport normalization differs in the Zoo mirror.')

# Earliest existing Simon source snapshot linking each exact media filename.
data=json.loads((ROOT/'pelican-web/data.js').read_text(encoding='utf8').split('=',1)[1].strip().rstrip(';'))
source_images={}
for post in sorted(data['simon'],key=lambda x:x['date']):
    path=ROOT/'pelican-web'/post['snapshot']
    if path.is_file():
        soup=BeautifulSoup(path.read_text(encoding='utf8'),'html.parser')
        for im in soup.select('.entry img'):
            src=im.get('src','')
            if 'static.simonwillison.net' in src:
                source_images.setdefault(src.rsplit('/',1)[-1],post)
for x in items:
    if x['source']=='zoo' and 'ai-worlds-fair' not in x['id']:
        name=Path(x['media'][0]['src']).name.removeprefix('specimen_').removeprefix('live_')
        post=source_images.get(name)
        if post:
            review(x['id'],fields={'author':'Simon Willison','date':post['date'],'month':post['date'][:7],'dateBasis':'earliest-source-publication','dateEvidenceUrl':post['url']})
            reviews[x['id']]['evidence'].append(post['url'])
            if x['id'].startswith('zoo-olmo2-pelican'):
                review(x['id'],fields={'model':'mlx-community/OLMo-2-0325-32B-Instruct-4bit','reviewedModelNames':['OLMo-2-0325-32B-Instruct-4bit']})
            if name=='gpt-2.5-pelican.png':
                review(x['id'],fields={'model':'GPT-5.2','reviewedModelNames':['GPT-5.2']})

for original in ['github-simonw-pelican-bicycle','origin-simon-2024-10-25','elo-june-2025','qwen36-beats-opus47-2026-04-16']:
    review(oid(original),'source-collection','Source compilation; its actual outputs are linked separately, not counted twice.')

# Original X comparisons reuse the already archived original SVGs.
for original,names in [('x-1849855301044011441',['gemini-1.5-flash-001.svg','gemini-1.5-flash-002.svg']),('x-simon-origin-tweet-2024-10-25',['claude-3-5-sonnet-20240620.svg','claude-3-5-sonnet-20241022.svg'])]:
    parent=oid(original);review(parent,'source-collection','Original comparison post; drawings already have individual original-SVG records.')
    for name in names:
        target=next(y for y in items if y['source']=='origin' and Path(y['media'][0]['src']).name==name)
        review(target['id'],fields={'relatedSourceIds':[parent]})

# June talk: every labelled panel is extracted. Only month precision is known
# for these particular slide outputs, unless an identical earlier case exists.
parent=oid('elo-june-2025')
slides={int(re.search(r'-(\d+)\.jpeg',m['source'])[1]):m for m in byid[parent]['media'] if re.search(r'-(\d+)\.jpeg',m['source'])}
plans=[
 (5,'Amazon Nova Lite','2024-12',(25,380,625,867)),(5,'Amazon Nova Micro','2024-12',(678,620,1279,1050)),(5,'Amazon Nova Pro','2024-12',(1332,370,1892,806)),
 (6,'Llama 3.1 405B','2024-12',(85,417,885,1017)),(6,'Llama 3.3 70B','2024-12',(1060,414,1784,1080)),
 (7,'DeepSeek V3','2024-12',(541,362,1341,1080)),(10,'DeepSeek R1','2025-01',(410,275,1510,953)),
 (11,'Mistral Small 3','2025-01',(420,383,1500,1080)),(13,'Claude 3.7 Sonnet','2025-02',(420,300,1500,1080)),
 (15,'GPT-4.5','2025-02',(643,13,1277,678)),(18,'o1-pro','2025-03',(560,230,1360,805)),
 (19,'Gemini 2.5 Pro','2025-03',(566,225,1354,785)),
 (23,'Llama 4 Scout','2025-04',(39,350,945,1080)),(23,'Llama 4 Maverick','2025-04',(1015,376,1878,952)),
 (24,'gpt-4.1-nano','2025-04',(64,490,611,929)),(24,'gpt-4.1-mini','2025-04',(685,490,1234,929)),(24,'gpt-4.1','2025-04',(1320,490,1868,929)),
 (25,'o3','2025-04',(112,435,917,1080)),(25,'o4-mini','2025-04',(999,430,1804,1080)),
 (26,'Claude Sonnet 4','2025-05',(67,420,614,766)),(26,'Claude Opus 4','2025-05',(686,420,1234,805)),(26,'gemini-2.5-pro-preview-05-06','2025-05',(1306,315,1854,805))]
panel_ids={}
for number,model,day,box in plans:
    # Explicit single-output slide boundaries were visually reviewed at 1920x1080.
    index=next(i for i,m in enumerate(byid[parent]['media']) if m['src']==slides[number]['src'])
    ident='simon-june-slides-'+re.sub('[^a-z0-9]+','-',model.lower()).strip('-')+'-'+day
    panel_ids.setdefault(number,[]).append(child(parent,ident,model,index,box,day,date_basis='source-described-month'))
for x in items:
    if 'zoo-ai-worlds-fair' in x['id']:
        number=int(re.search(r'fair-2025-(\d+)',x['id'])[1])
        if number in panel_ids:
            review(x['id'],'source-collection','Retrospective slide, not one model output.',fields={'linkedCaseIds':panel_ids[number]})
        elif number==32:
            review(x['id'],'source-collection','Reuses the already split Gemini / Llama panels; not another generation.',fields={'linkedCaseIds':[panel_ids[26][-1],panel_ids[6][-1]]})
        else:review(x['id'],'context','Score-command screenshot or non-SVG image-generation slide, not a bicycle SVG case.')
review(oid('x-1933846598942965983'),'source-collection','Repost of the June comparison; same Gemini/Llama outputs.',fields={'linkedCaseIds':[panel_ids[26][-1],panel_ids[6][-1]]})
duplicate(oid('deepseek-r1-stock-pelican-2025-01'),panel_ids[10][0],'Same original slide and drawing; original January month retained in the individual case.')

# Reuse each existing individual output in the Qwen/Opus compilation.
parent=oid('qwen36-beats-opus47-2026-04-16')
for m in byid[parent]['media']:
    target=next(x for x in items if x['source']=='zoo' and x['media'][0]['src']==m['src'])
    review(target['id'],fields={'author':'Simon Willison','parentId':parent,'dateBasis':'source-publication'})
review(parent,role='source-collection',fields={'linkedCaseIds':[x['id'] for x in items if x['source']=='zoo' and any(m['src']==x['media'][0]['src'] for m in byid[parent]['media'])]})

# Verified X source text lists the models in media order. Keep full screenshots.
splits=[
 ('x-1993132584159920192',[(0,'Claude Opus 4.5'),(1,'Claude Sonnet 4.5'),(2,'Claude Haiku 4.5')]),
 ('x-1993181270407606284',[(0,'Gemini 3 Pro'),(2,'Claude Opus 4.5 Thinking')]),
 ('x-2069994185466507631',[(0,'doubao-seed-pro-2.1'),(1,'gpt-5.5'),(2,'Opus-4.8')]),
 ('x-2049990855260324012',[(0,'Qwen 3.6-35B-A3B (base)'),(1,'Qwen 3.6-35B-A3B (Claude Opus 4.7 reasoning distilled)')]),
]
for original,mapping in splits:
    parent=oid(original)
    response=urllib.request.urlopen(urllib.request.Request('https://api.fxtwitter.com/status/'+original.removeprefix('x-'),headers={'User-Agent':'PelicanMap-Archive/1.0'}),timeout=30).read()
    (ARCHIVE/(original+'-source.json')).write_bytes(response)
    assert json.loads(response)['code']==200
    review(parent,'source-collection','Verified source text and ordered media map each named model to its original output.')
    for index,model in mapping:
        child(parent,original+'-'+re.sub('[^a-z0-9]+','-',model.lower()).strip('-'),model,index)

# The November enhanced-prompt post is exactly the three existing Zoo images.
parent=oid('x-2085156425303830595')
review(parent,'source-collection','Version comparison reuses April 8 and July 9 outputs; it is not three new August 6 generations.')
review(oid('zoo-muse-spark-thinking-pelican'),fields={'relatedSourceIds':[parent]})
linked=[oid('zoo-muse-spark-thinking-pelican')]
for index,model,day in [(1,'Muse Spark 1.1','2026-07-09'),(2,'Muse Spark 1.2','2026-08-05')]:
    ident=child(parent,'simon-muse-spark-'+('11' if index==1 else '12')+'-'+day,model,index,date=day,date_basis='original-source-publication')
    review(ident,fields={'dateEvidenceUrl':'https://simonwillison.net/2026/Aug/5/muse-code-and-muse-spark-12/'})
    linked.append(ident)
review(parent,fields={'linkedCaseIds':linked})

parent=oid('x-1990859659595731046')
review(parent,'source-collection','Enhanced-prompt comparison; three existing individual source outputs are reused.')
review(parent,fields={'linkedCaseIds':[oid('zoo-gemini-3-breeding-pelican-high'),oid('zoo-gpt-5-1-breeding-pelican'),oid('zoo-claude-sonnet-4-5-breeding-pelican')]})

# Static grids: archive every real output, count each once, and choose medium
# only for timeline display. A missing output (Astra none, Opus max) is not art.
parent=oid('astra-grid-2026-09-04')
review(parent,'source-collection','Four-model grid (not just Astra); medium row is the timeline representative.')
grid_ids=[]
for model,left,right in [('gpt-6-astra',134,397),('gpt-5.6-sol',421,680),('gpt-5.6-terra',706,966),('gpt-5.6-luna',990,1252)]:
    representative='simon-grid-2026-09-04-'+model+'-medium'
    grid_ids.append(representative)
    for effort,top,bottom in [('max',161,355),('xhigh',421,615),('high',681,875),('medium',942,1137),('low',1202,1397),('none',1462,1637)]:
        if model=='gpt-6-astra' and effort=='none':continue
        ident=child(parent,'simon-grid-2026-09-04-'+model+'-'+effort,model,0,(left,top,right,bottom),variant=effort)
        review(ident,fields={'modelRunGroup':parent+':'+model,**({'representativeOf':representative} if effort!='medium' else {})})
parent=oid('x-jp-ai-joryushi-2026-09-23')
review(parent,'source-collection','Reposts Simon grids; existing earlier outputs are linked, not re-dated September 23.')
for model,left,right in [('gpt-6-sol',362,580),('gpt-6-luna',606,824)]:
    representative='simon-grid-2026-09-22-'+model+'-medium'
    for effort,top,bottom in [('max',57,218),('xhigh',286,447),('high',515,676),('medium',744,916),('low',972,1140),('none',1201,1370)]:
        ident=child(parent,'simon-grid-2026-09-22-'+model+'-'+effort,model,0,(left,top,right,bottom),date='2026-09-22',variant=effort,date_basis='original-grid-publication')
        review(ident,fields={'modelRunGroup':parent+':'+model,**({'representativeOf':representative} if effort!='medium' else {})})
for model,left,right in [('Claude Fable 5.1',118,379),('Claude Opus 5.5',405,664),('Claude Opus 5',690,950),('Claude Sonnet 5',976,1236)]:
    stem='simon-grid-2026-09-22-'+re.sub('[^a-z0-9]+','-',model.lower())
    for effort,top,bottom in [('max',58,252),('xhigh',333,540),('high',622,829),('medium',909,1117),('low',1198,1402)]:
        if model=='Claude Opus 5.5' and effort=='max':continue
        ident=child(parent,stem+'-'+effort,model,1,(left,top,right,bottom),date='2026-09-22',variant=effort,date_basis='original-grid-publication')
        review(ident,fields={'modelRunGroup':parent+':'+model,**({'representativeOf':stem+'-medium'} if effort!='medium' else {})})
review(parent,fields={'linkedCaseIds':grid_ids,'dateEvidenceUrl':'https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/'})

parent='reddit-emu001-codex-pelican-matrix-2026-09-26'
review(parent,'source-collection','Seven explicitly labelled models; medium row only on the evolution axis. The second image repeats source comparison outputs.')
for i,model in enumerate(['gpt-6-astra','gpt-6-sol','gpt-6-luna','gpt-5.6-sol','gpt-5.6-terra','gpt-5.6-luna','gpt-5.5']):
    left=[46,191,338,486,634,783,931][i]
    representative='reddit-emu001-2026-09-26-'+model+'-medium'
    for effort,top,bottom in [('max',94,192),('xhigh',242,340),('high',391,489),('medium',536,638),('low',685,785)]:
        ident=child(parent,'reddit-emu001-2026-09-26-'+model+'-'+effort,model,0,(left,top,left+136,bottom),variant=effort)
        review(ident,fields={'modelRunGroup':parent+':'+model,**({'representativeOf':representative} if effort!='medium' else {})})

# Single-model same-day settings remain in the museum but fold on the timeline.
parent=oid('x-2033992486096670733')
review(parent,'source-collection','Image explicitly labels GPT-5.4 nano/mini/full and five efforts; not one GPT-5.4 output.')
for model,left,right in [('gpt-5.4-nano',258,931),('gpt-5.4-mini',967,1639),('gpt-5.4',1675,2347)]:
    stem='x-2033992486096670733-'+model
    for effort,top,bottom in [('none',119,628),('low',671,1181),('medium',1223,1733),('high',1774,2284),('xhigh',2326,2836)]:
        ident=child(parent,stem+'-'+effort,model,0,(left,top,right,bottom),variant=effort)
        review(ident,fields={'modelRunGroup':parent+':'+model,**({'representativeOf':stem+'-medium'} if effort!='medium' else {})})

settings=[
 ('simon-gemini-flash-budget-zero-2025-04-17','simon-gemini-flash-default-2025-04-17'),
 (oid('x-1912973864558379177'),'simon-gemini-flash-default-2025-04-17'),
 (oid('zoo-pelican-claude-3.7-sonnet-thinking'),oid('zoo-pelican-claude-3.7-sonnet')),
 (oid('zoo-opus-4.7-pelican-max'),oid('zoo-opus-4.7-pelican')),
 (oid('github-bbinwang-qwen36-prism-agent-2026-08-02'),oid('github-bbinwang-qwen36-prism-code-2026-08-02')),
 (oid('zoo-muse-spark-thinking-pelican'),oid('zoo-muse-spark-instant-pelican')),
]
for old,target in settings:
    review(old,reason='Same model/date alternative setting; default or source-first representative selected, not best score.',fields={'representativeOf':target},timelineVisible=False)
for prefix,selected in [('zoo-gemini-3-flash-preview-thinking-level-','medium'),('zoo-gemini-3.1-flash-lite-','medium'),('zoo-claude-opus-4.8-','medium')]:
    normalized=re.sub('[^a-z0-9]+','-',prefix.lower())
    members=[x for x in items if x['id'].startswith(normalized)]
    default=next((x for x in members if selected in x['id']),None)
    if default:
        for x in members:
            if x!=default:review(x['id'],reason='Same model/date effort variant; medium is the timeline representative.',fields={'representativeOf':default['id']},timelineVisible=False)

# Exact media reuse observed in the whole-catalog audit (originals are kept).
zoo_settings={}
for x in items:
    match=re.fullmatch(r'zoo:(.+)-(none|minimal|low|medium|high|xhigh|max)',x['originalId'])
    if not match or x['sourceUrl']!='https://pelicanzoo.ai/p/'+match[1]+'-'+match[2]:continue
    zoo_settings.setdefault((match[1],x['date'],x['model']),[]).append((x,match[2]))
for (stem,day,model),members in zoo_settings.items():
    if not any(effort=='medium' for _,effort in members):continue
    group='zoo-named-settings-'+stem+'-'+day
    for x,effort in members:
        if reviews.get(x['id'],{}).get('role')=='duplicate':continue
        review(x['id'],reason='Upstream page slug names the setting; original catalogue L-label retained separately. Medium represents this source-labelled series.',fields={'modelRunGroup':group,'runSourceUrl':'https://pelicanzoo.ai/','legacyCatalogueLevel':x['originalLevel'],'originalLevel':effort})

# Gemini 3 exposes only low/high. The author's article explicitly states that
# high is the default; this is a source-supported default, not a quality pick.
for effort in ['low','high']:
    ident=oid('zoo:gemini-3-pelican-'+effort)
    review(ident,reason='November 18 original article explicitly identifies high as the default thinking level.',fields={
        'modelRunGroup':'simon-gemini3-classic-2025-11-18',
        'runSourceUrl':'https://simonwillison.net/2025/Nov/18/gemini-3/',
        'originalLevel':effort,'legacyCatalogueLevel':byid[ident]['originalLevel'],
        'authorDefault':effort=='high','comparisonType':'prompt-and-settings'})
    reviews[ident]['evidence'].append('https://simonwillison.net/2025/Nov/18/gemini-3/')

# The enhanced breeding-plumage prompt is a different output, but the same
# author's same-day model comparison: count it, not another evolution card.
ident=oid('zoo:gemini-3-breeding-pelican-high')
review(ident,fields={'modelRunGroup':'simon-gemini3-classic-2025-11-18',
    'runSourceUrl':'https://simonwillison.net/2025/Nov/18/gemini-3/',
    'originalLevel':'enhanced-prompt-high','legacyCatalogueLevel':byid[ident]['originalLevel'],
    'authorDefault':False,'comparisonType':'prompt-and-settings'})

for effort in ['default','xhigh']:
    ident=oid('zoo:gpt-5.5-pelican'+('-xhigh' if effort=='xhigh' else ''))
    review(ident,reason='April 23 source explicitly contrasts default and xhigh outputs; preserve both, default on the timeline.',fields={
        'modelRunGroup':'simon-gpt55-classic-2026-04-23',
        'runSourceUrl':'https://simonwillison.net/2026/Apr/23/gpt-5-5/',
        'originalLevel':effort,'legacyCatalogueLevel':byid[ident]['originalLevel'],
        'authorDefault':effort=='default'})
    reviews[ident]['evidence'].append('https://simonwillison.net/2026/Apr/23/gpt-5-5/')

# Source grid and original SVG were rendered side by side and inspected at
# matching sizes (deploy-build/source-duplicate-review.png). The nine panels
# are exactly the earlier artworks, not new September 22 generations. Keep
# both archives, put the full comparison in each canonical detail, count once.
comparison_source='https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/'
for model,stem,efforts in [
    ('fable-5.1','claude-fable-5-1',['low','medium','high','xhigh','max']),
    ('claude-opus-5.5','claude-opus-5-5',['low','medium','high','xhigh'])]:
    for effort in efforts:
        canonical=oid('zoo:'+model+'-'+effort)
        alias='simon-grid-2026-09-22-'+stem+'-'+effort
        full=byid[alias]['media'][-1]
        attach_full(canonical,full,oid('x-jp-ai-joryushi-2026-09-23'))
        review(canonical,fields={'author':'Simon Willison','originalSourceUrl':comparison_source})
        reviews[canonical]['evidence'].append(comparison_source)
        duplicate(alias,canonical,'Source comparison reuses the exact original SVG artwork; side-by-side geometry verified. Earlier canonical date and original media retained.')
        review(alias,fields={'comparisonGroupAlias':reviews[canonical]['fields']['modelRunGroup']})

for old,target in [
 ('v2-prompt-gemini3-2025-11','zoo-gemini-3-breeding-pelican-high'),('x-1990858057153142870','zoo-gemini-3-breeding-pelican-high'),
 ('fable-51-max-animated-2026-09-01','zoo-fable-5.1-max'),('x-1865186263713849592','x-simon-gemini-exp1206-2024-12-06'),
 ('x-goodside-unsaturated-2026-02-13','x-2022012222059499949'),('x-jp-aichan-opus-oneprompt-games-2026-09-25','claude-opus-playable-coast')]:
    duplicate(oid(old),oid(target),'Exact already archived primary media; a repost/context page does not create a new artwork.')

# Older source posts also contain multiple independently generated outputs.
# The original posts establish these mappings, rather than attachment count.
older_runs=[
    ('x-1887198978334482514','2025-02-05','https://simonwillison.net/2025/Feb/5/gemini-2/',[
        ('gemini-2.0-flash-lite-preview-02-05','', 'pelican_bicycle'),
        ('gemini-2.0-flash','', 'pelican_bicycle'),
        ('gemini-2.0-pro-exp-02-05','', 'pelican_bicycle')]),
    ('x-1902509366244471291','2025-03-19','https://simonwillison.net/2025/Mar/19/o1-pro/',[
        ('o1-pro','default','pelican_bicycle'),('o1-pro','high','pelican_bicycle')]),
    ('x-1989123523206578351','2025-11-13','https://simonwillison.net/2025/Nov/13/gpt-51/',[
        ('GPT-5.1','none','pelican_bicycle'),('GPT-5.1','high','pelican_bicycle')]),
    ('x-2024544280451350689','2026-02-19','https://simonwillison.net/2026/Feb/19/gemini-31-pro/',[
        ('Gemini 3.1 Pro','standard','pelican_bicycle'),('Gemini 3.1 Pro','enhanced','pelican_bicycle')]),
    ('x-simon-qwen36-2026-04-22','2026-04-22','https://simonwillison.net/2026/Apr/22/qwen36-27b/',[
        ('unsloth/Qwen3.6-27B-GGUF:Q4_K_M','pelican','pelican_bicycle'),
        ('unsloth/Qwen3.6-27B-GGUF:Q4_K_M','opossum','opossum_escooter')])]
older_children={}
for original,day,article,mapping in older_runs:
    parent=oid(original)
    review(parent,'source-collection','Original article explicitly identifies separate model/settings/prompt outputs. Keep the complete source archive; count individual outputs only.')
    reviews[parent]['evidence'].append(article)
    members=[]
    for index,(model,setting,task) in enumerate(mapping):
        ident='simon-source-'+original.removeprefix('x-')+'-'+re.sub('[^a-z0-9]+','-',model.lower()).strip('-')+('-'+setting if setting else '')
        members.append(child(parent,ident,model,index,date=day,variant=setting,task=task,date_basis='original-source-publication'))
        review(ident,fields={'dateEvidenceUrl':article,'originalSourceUrl':article})
        reviews[ident]['evidence'].append(article)
    older_children[original]=members
    if original in {'x-1902509366244471291','x-1989123523206578351'}:
        for index,ident in enumerate(members):
            review(ident,fields={'modelRunGroup':parent+':classic','authorDefault':index==0})
    elif original in {'x-2024544280451350689','x-simon-qwen36-2026-04-22'}:
        for ident in members:review(ident,fields={'comparisonType':'prompt'})
        review(members[1],fields={'representativeOf':members[0]},timelineVisible=False)
    review(parent,fields={'linkedCaseIds':members})

# The June talk reuses the March 19 high-effort o1-pro drawing, including its
# distinctive body/legs/wheels. Keep the source-month alias; count the original
# March output once, and preserve the full talk slide on its detail page.
alias='simon-june-slides-o1-pro-2025-03'
canonical=older_children['x-1902509366244471291'][1]
full=byid[alias]['media'][-1]
attach_full(canonical,full,oid('x-1902509366244471291'))
review(canonical,fields={'relatedSourceIds':[oid('elo-june-2025')]})
duplicate(alias,canonical,'June retrospective reuses the March 19 high-effort o1-pro output. Source illustration and distinctive geometry visually verified; no new generation date.')
review(alias,fields={'comparisonGroupAlias':reviews[canonical]['fields']['modelRunGroup']})

# The May retrospective is not a new May run. Its static Gemini drawing is
# the February output; its Qwen/Opus collage reuses the April originals, and
# the Gemini animation comparison is context only (not a static SVG case).
alias=oid('zoo:5-minutes-llms.016')
canonical=older_children['x-2024544280451350689'][0]
attach_full(canonical,byid[alias]['media'][0],oid('x-2024544280451350689'))
review(canonical,fields={'relatedSourceIds':[alias]})
duplicate(alias,canonical,'May talk explicitly describes the February Gemini 3.1 Pro output; original image and full slide visually identical.')
parent=oid('zoo:5-minutes-llms.025')
linked=[oid('zoo:Qwen3.6-35B-A3B-UD-Q4_K_S-pelican'),oid('zoo:opus-4.7-pelican')]
review(parent,'source-collection','May talk reuses the April 16 Qwen/Opus comparison, not a new Qwen-only output.',fields={'linkedCaseIds':linked})
for canonical in linked:
    attach_full(canonical,byid[parent]['media'][0],oid('qwen36-beats-opus47-2026-04-16'))
review(oid('zoo:5-minutes-llms.017'),'context','Source explicitly identifies an animated SVG model comparison; not a static single-model output.',fields={'dateEvidenceUrl':'https://simonwillison.net/2026/May/19/5-minute-llms/'})
ident=oid('zoo:5-minutes-llms.019')
original=byid[ident]['media'][0]
panel,provenance=crop(original,(560,255,1360,940),ident)
review(ident,reason='May talk identifies this Gemma 4 26B-A4B drawing in April. Crop only presentation padding; retain the complete original slide. Exact run day unconfirmed.',fields={
    'model':'Gemma 4 26B-A4B (17.99GB)','reviewedModelNames':['Gemma 4 26B-A4B'],
    'author':'Simon Willison','date':'2026-04','month':'2026-04','dateBasis':'source-described-month',
    'sourcePublicationDate':'2026-05-19','dateEvidenceUrl':'https://simonwillison.net/2026/May/19/5-minute-llms/',
    'media':[panel,copy.deepcopy(original)],'thumbnail':panel['src'],'representativeMedia':panel['src'],'cropProvenance':provenance})

# Pollution / human mashups / unknown mapping stay accessible as context.
for original in ['wrapper-precache-break-2026-09-26','x-sree-mythos-trace-cheat-2026-09-22','x-1896464903247995080','x-2066462341081059725','x-1958469381538947450','jimu-14model-ik-score','juejin-12model-3d-2026-09-13','x-1911917042522792127','x-2093971320685932895']:
    review(oid(original),'context','Pollution allegation, manual mashup or animation comparison; not a verified independent static SVG output.')

write(ROOT/'site/case-reviews.json',reviews)
write(ROOT/'site/additions.json',additions)
manifest_path=ROOT/'deploy-build/history-static-reviewed.json'
if manifest_path.exists():
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    assert len(manifest['cases'])==5 and all(x['format']=='svg' for x in manifest['cases'])
    for candidate in manifest['cases']:
        candidate.update(unitType='single-model-output',modelToMediaVerified=True)
    write(manifest_path,manifest)
write(ARCHIVE/'migration.json',{'policy':'2026-10-01-case-unit-v1','reviewedOverrides':len(reviews),'createdIds':created,'allDerivedIds':[k for k in byid if k not in {x['id'] for x in items}],'beforeRawRecords':len(items),'preservedOldIds':True,'preservedOldMedia':True})
print(json.dumps({'reviews':len(reviews),'newDerivedRecords':len(created),'additions':len(additions)},ensure_ascii=False))
