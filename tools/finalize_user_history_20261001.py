"""Apply the explicit human source review, not a general-purpose classifier.

First invocation writes only a reviewed manifest. --apply-reviews may run only
after the importer has archived every accepted output. Existing media/IDs stay.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path
from audit_user_history_links import ROOT, OUT, request
from bs4 import BeautifulSoup

EXCLUDED={
    'history-56217af4-0-0':('duplicate','zoo-qwen-pelican-90951e0b','Same rendered SVG; X is also the same output. Earlier article publication is 2024-11-12, not the later Gist date.'),
    'history-4728316a-0-0':('duplicate','origin-gemini-exp-1206-svg-9bee0291','Initial static response already archived; later animation is excluded.'),
    'history-c34f7f0c-0-0':('duplicate','zoo-gemini-2-5-pro-pelican-c5edf61e','Same source drawing as existing upstream raster; manually checked, not a new output.'),
    'history-32a85e33-0-0':('duplicate','x-2016168039809773925-d33d226a','Same Kimi K2.5 drawing as existing source PNG.'),
    'hardprompts-2025-12-03-gemini-2-5-pro-run-2':('invalid-media',None,'Original SVG uses http://www.w.org/2000/svg; cannot decode as an SVG. Original is retained in private evidence, not repaired or counted.'),
}


def manifest():
    staged=json.loads((OUT/'staged-manifest.json').read_text(encoding='utf8'))
    cases=[copy.deepcopy(c) for c in staged['cases'] if c['id'] not in EXCLUDED]
    for c in cases:
        if c['id']=='history-5b61866c-0-0':
            c.update(sourceUrl='https://simonwillison.net/2025/May/20/gemini-25/',sourceCodeUrl='https://gist.github.com/simonw/5b61866cb4ce67899934c29a9de1b4be',variant='default',authorDefault=True,modelRunGroup='simon-gemini-flash-2025-05-20')
            c['evidence'].append(c['sourceUrl'])
            c['title']={'zh':c['model']+' · 默认 thinking','en':c['model']+' · default thinking'}
            c['notes']={'zh':'原文明确标为默认模型、thinking 开启的首次静态输出；不是随后 Now animate it 的动画。原始 SVG 从固定版本 Response 逐字提取，未重画。与同日 thinking_budget=0 的独立输出对照；时间线使用作者默认档。模型标签未独立认证，日期为原帖公开日。','en':'The article explicitly identifies this initial static output as the default model with thinking enabled, not the later Now animate it response. Original SVG is copied verbatim from a pinned Response. Compared with the independent same-day thinking_budget=0 output; the author default represents the timeline. Model unverified; date is source publication.'}
        if c['id'].startswith('simon-deepseek-v4-flash-0731-'):
            c['parentId']='x-2083342783071621224-719f9758'
            c['notes']['zh']+=' 对应已存 X 对照帖的单张输出，现按原文更早的公开日期拆分；不是额外的一次运行。'
            c['notes']['en']+=' This is one output already pictured in the X comparison archive, now split at the earlier article publication date; not an additional run.'
        if c['id'].startswith('hardprompts-'):
            c['sourceCodeUrl']=c['sourceUrl']+'#'+c['model']
    source='https://simonwillison.net/2025/Dec/19/introducing-gpt-52-codex/'
    image='https://static.simonwillison.net/static/2025/5.2-codex-pelican.png'
    data,meta=request(image)
    assert data.startswith(b'\x89PNG\r\n\x1a\n') and meta.get('status')==200
    ident='simon-gpt52-codex-medium-2025-12-19'
    c=copy.deepcopy(cases[0])
    c.update(id=ident,sourceUrl=source,sourceCodeUrl='',date='2025-12-19',sourcePublicationDate='2025-12-19',model='GPT-5.2-Codex',author='Simon Willison',variant='medium',evidence=[source,image],title={'zh':'GPT-5.2-Codex · medium','en':'GPT-5.2-Codex · medium'},notes={'zh':'作者使用 Codex CLI 的 GPT-5.2-Codex、effort medium 请求静态 SVG。保存原帖发布的 PNG 预览，不冒充已取得 SVG 源码；原帖未说明看图迭代，本站也不执行 CLI 或转录代码。模型归属按作者报告，未独立认证；日期为原帖公开日。','en':'The author requested a static SVG using GPT-5.2-Codex in Codex CLI at medium effort. This archives the article’s original PNG preview, not purported recovered SVG source. The article does not report visual-feedback iteration; no CLI or transcript code is executed here. Attribution is source-reported, not authenticated; date is article publication.'},media=[{'url':image,'filename':ident+'.png','sha256':hashlib.sha256(data).hexdigest(),'caption':{'zh':'原帖静态 SVG 的原始 PNG 预览','en':'Original upstream PNG preview of the static SVG'}}])
    for key in ['modelRunGroup','authorDefault','parentId']:c.pop(key,None)
    cases.append(c)
    assert len(cases)==38 and len({c['id'] for c in cases})==38
    result={'reviewed':True,'batch':staged['batch'],'cases':cases,'review':{'method':'Pinned source-response extraction plus SHA/normalized SVG/render comparison and manual contact-sheet/source inspection. User URL annotations were not inputs.','excluded':[{ 'id':k,'status':v[0],'canonicalId':v[1],'reason':v[2]} for k,v in EXCLUDED.items()]}}
    path=OUT/'approved-manifest.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf8'))==result,'Reviewed manifest changed'
    else:path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return result


def apply_reviews(m):
    added=json.loads((ROOT/'site/additions.json').read_text(encoding='utf8'))
    assert {c['id'] for c in m['cases']} <= {c['id'] for c in added},'Import all approved media before changing case reviews'
    path=ROOT/'site/case-reviews.json'
    reviews=json.loads(path.read_text(encoding='utf8'))
    snapshot=OUT/'before-case-reviews.json'
    if not snapshot.exists():snapshot.write_bytes(path.read_bytes())
    for c in m['cases']:
        fields={'reviewedModelNames':[c['model']]}
        if c['id'].startswith('hardprompts-'):
            fields.update(comparisonType='repeat-runs',dateBasis='source-reported-response-timestamp',sourcePublicationDate=None)
        reviews[c['id']]={'sourceUrl':c['sourceUrl'],'role':'case','reason':'Reviewed source-labelled single static output; exact bytes, settings/run and publication date preserved.','evidence':c['evidence'],'fields':fields}
    old='simon-gemini-flash-budget-zero-2025-05-20'
    reviews[old]={'sourceUrl':'https://simonwillison.net/2025/May/20/gemini-25/','role':'case','reason':'Source explicitly contrasts author-default thinking with thinking_budget=0. Only the default represents the date/model axis.','evidence':['https://simonwillison.net/2025/May/20/gemini-25/'],'fields':{'modelRunGroup':'simon-gemini-flash-2025-05-20'}}
    parent='x-2083342783071621224-719f9758'
    reviews[parent]={'sourceUrl':'https://x.com/simonw/status/2083342783071621224','role':'context','reason':'Original two-output repost retained; both static originals are now attributed to the earlier article and counted only as its children.','evidence':['https://simonwillison.net/2026/Jul/31/deepseek-v4-flash-0731/'],'fields':{'linkedCaseIds':['simon-deepseek-v4-flash-0731-default','simon-deepseek-v4-flash-0731-high']}}
    zoo='zoo-qwen-pelican-90951e0b'
    r=reviews[zoo]
    r['reason']='The Zoo SVG, original Gist and later X screenshot show the same output. Keep the earliest article publication, 2024-11-12, and original source model label; no additional work.'
    r['evidence']=list(dict.fromkeys(r['evidence']+['https://gist.github.com/simonw/56217af454695a90be2c8e09c703198a','https://x.com/simonw/status/1856712797054447970']))
    r['fields'].update(model='qwen2.5-coder:32b',reviewedModelNames=['qwen2.5-coder:32b'],title='qwen2.5-coder:32b',sourceCodeUrl='https://gist.github.com/simonw/56217af454695a90be2c8e09c703198a',sourcePublicationDate='2024-11-12')
    reviews['x-1856712797054447970-52885a83']={'sourceUrl':'https://x.com/simonw/status/1856712797054447970','role':'duplicate','reason':'Same output as the original static SVG, confirmed with source transcript and manual rendering comparison. Later screenshot is retained but not counted.','evidence':r['evidence'],'fields':{'canonicalId':zoo}}
    path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def correct_response_dates():
    """Preserve upstream response timestamps without claiming publication day."""
    data,_=request('https://hardprompts.ai/topics/pelican-bicycle-svg.html')
    soup=BeautifulSoup(data,'html.parser')
    timestamps={(p['data-model'],p['data-iteration']):p.select_one('.response-date')['data-timestamp'] for p in soup.select('.iteration-content[data-model][data-iteration]')}
    path=ROOT/'site/additions.json'
    before=path.read_bytes()
    backup=OUT/'before-response-date-correction-additions.json'
    if not backup.exists():backup.write_bytes(before)
    additions=json.loads(before)
    reviewed=ROOT/'site/case-reviews.json'
    reviews=json.loads(reviewed.read_text(encoding='utf8'))
    changed=[]
    for x in additions:
        if not x['id'].startswith('hardprompts-2025-12-03-'):continue
        run=x['originalLevel'].split()[-1]
        timestamp=timestamps[(x['model'],run)]
        assert timestamp[:10]==x['date']
        x.pop('sourcePublicationDate',None)
        x.update(dateBasis='source-reported-response-timestamp',sourceResponseTimestamp=timestamp)
        reviews[x['id']]['fields'].update(dateBasis=x['dateBasis'],sourcePublicationDate=None,sourceResponseTimestamp=timestamp)
        changed.append(x['id'])
    assert len(changed)==23
    path.write_text(json.dumps(additions,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    reviewed.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    correction=copy.deepcopy(json.loads((OUT/'approved-manifest.json').read_text(encoding='utf8')))
    for c in correction['cases']:
        if c['id'] in changed:
            c.pop('sourcePublicationDate',None)
            c['dateBasis']='source-reported-response-timestamp'
            c['sourceResponseTimestamp']=timestamps[(c['model'],c['variant'].split()[-1])]
    (OUT/'approved-manifest-v2.json').write_text(json.dumps(correction,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'response-date-correction.json').write_text(json.dumps({'reason':'The upstream response timestamp is not separately proven to be page publication time. Original dates/media preserved; false publication-date inference removed.','ids':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    if '--correct-response-dates' in sys.argv:
        correct_response_dates()
        print('Corrected date basis for 23 upstream response timestamps; no artwork/media/date changes')
        sys.exit(0)
    m=manifest()
    if '--apply-reviews' in sys.argv:apply_reviews(m)
    print(json.dumps({'approved':len(m['cases']),'excluded':len(EXCLUDED),'reviewsApplied':'--apply-reviews' in sys.argv}))
