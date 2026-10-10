"""Shared case-unit rules for manual builds and the server publisher.

No image recognition or model/date guessing. Explicit source-reviewed mappings
live in case-reviews.json. Unresolved comparisons stay reachable as context.
"""
import copy
import hashlib
from content_cache import sha256_file
from incremental_site import inspect_file
import json
import re
from pathlib import Path
from card_metadata import model_names
from generation_scope import is_direct_video

ROOT = Path(__file__).resolve().parents[1]


def is_case(item):
    return not item.get('referenceOnly') and item.get('caseVisible', True)


def in_timeline(item):
    return is_case(item) and item.get('timelineVisible', item.get('kind') == 'timeline')


def family(model):
    """Source label taxonomy, not a certification of the claimed model."""
    value = model.lower()
    for key, pattern in [
        ('Gemini',r'gemini'), ('Gemma',r'gemma'), ('GPT',r'gpt|\bo[134](?:[- ]|$)|astra|\bsol\b|\bluna\b'),
        ('Claude',r'claude|sonnet|opus|haiku|fable'), ('Qwen',r'qwen|qwq'), ('DeepSeek',r'deepseek'),
        ('Llama',r'llama'), ('Grok',r'grok'), ('Mistral',r'mistral|magistral'), ('GLM',r'glm'),
        ('Kimi',r'kimi'), ('Nova',r'\bnova\b'), ('Phi',r'\bphi'), ('OLMo',r'olmo'),
        ('Muse',r'muse'), ('MiniMax',r'minimax'), ('Doubao',r'doubao|豆包')]:
        if re.search(pattern,value):
            return key
    return 'Other'


def static_media(item, root):
    """Determine medium only; this never infers its model or image content."""
    if item.get('previewUrl', '').startswith('https://pelicanmap-demos.aveniqa.com/demos/'):
        return False
    primary = item.get('representativeMedia') or item['media'][0]['src']
    if primary.lower().endswith('.svg'):
        path = Path(root)/primary.lstrip('/')
        if not path.is_file():return False
        def inspect():
            text=path.read_text(encoding='utf8',errors='replace')
            return bool(text and not re.search(r'<(?:animate\w*|set|script)\b|@keyframes|\banimation\s*:',text,re.I))
        return inspect_file(path,'static-svg',inspect)
    return (item['format'] == 'svg' or (item['source'] == 'zoo' and item['originalForm'] in {'png print','jpg print','jpeg print'})) and not re.search(r'\.(mp4|webm|gif)$',primary,re.I)


def timeline_media(item, root):
    """All media are eligible; cards require a real, locally archived cover.

    A cover does not prove attribution or create a new work. Video frames and
    project views still belong to the one reviewed output. No network/code runs.
    """
    cover = item.get('thumbnail') or ''
    return bool(cover.startswith(('/media/','/assets/')) and
                re.search(r'\.(svg|png|jpe?g|webp|gif|avif)$',cover,re.I) and
                (Path(root)/cover.lstrip('/')).is_file())


def apply_case_policy(items, media_root, reviews=None):
    reviews = reviews if reviews is not None else json.loads((ROOT/'site/case-reviews.json').read_text(encoding='utf8'))
    result = copy.deepcopy(items)
    by_id = {x['id']:x for x in result}
    assert set(reviews) <= set(by_id), 'Case review target missing'
    for item in result:
        if item.get('referenceOnly'):
            item.update(caseRole='reference',caseVisible=False,timelineVisible=False)
            continue
        review = reviews.get(item['id'], {})
        if review:
            assert review['sourceUrl'] == item['sourceUrl'], 'Case review source changed'
            item.setdefault('originalMetadata', {k:copy.deepcopy(item.get(k)) for k in ('title','model','author','date','sourceUrl','kind','format','thumbnail')})
            item.update(copy.deepcopy(review.get('fields',{})))
        names = item.get('reviewedModelNames') or model_names(item['model'])
        role = review.get('role') or ('case' if len(names)==1 else 'needs-attribution')
        if is_direct_video(item):
            role = 'context'
            item['generationMethod'] = 'direct-text-to-video'
        # Museum originals remain archived; commentary/physical media is not a
        # dated model drawing. Only reviewed legacy works remain in main lists.
        if not review and item['format']=='text' and item['source']=='community':
            role = 'context'
        item['caseRole'] = role
        item['caseVisible'] = role == 'case'
        item['modelClaimStatus'] = 'source-reported-not-independently-authenticated'
        item['dateBasis'] = item.get('dateBasis') or 'recorded-source-date-run-date-unverified'
        item['modelFamilies'] = sorted({family(name) for name in names}) if names else []
        item['reviewedModelNames'] = names
        item['representativeMedia'] = item.get('representativeMedia') or item['media'][0]['src']
        assert item['representativeMedia'] in {m['src'] for m in item['media']}
        if item.get('cropProvenance'):
            crop = item['cropProvenance']
            assert crop['original'] in {m['src'] for m in item['media']}, 'Full original missing'
            assert item['thumbnail'] == crop['crop'], 'Composite cannot be the cover'
            for key, pathkey in [('sourceSha256','original'),('cropSha256','crop')]:
                path = Path(media_root)/crop[pathkey].lstrip('/')
                assert path.is_file() and sha256_file(path)==crop[key]
        static = static_media(item,media_root)
        if static and item['caseVisible']:
            item['format']='svg';item['formatLabel']='静态 SVG'
        category = (item.get('task') or item.get('promptCategory') or '').lower()
        derivative = any(word in category+' '+item['id'] for word in ['beagle','parrot','flamingo','possum','dog','hamster'])
        item['task'] = item.get('task') or ('derived' if derivative else 'pelican_bicycle')
        item['datePrecision'] = 'day' if re.fullmatch(r'\d{4}-\d{2}-\d{2}',item['date']) else 'month' if re.fullmatch(r'\d{4}-\d{2}',item['date']) else 'year'
        item['timelineVisible'] = bool(item['caseVisible'] and timeline_media(item,media_root) and len(names)==1 and re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',item['date']) and not derivative)
        if 'timelineVisible' in review:
            item['timelineVisible'] = bool(review['timelineVisible'] and item['timelineVisible'])
        if item.get('representativeOf'):
            item['timelineVisible'] = False
        for key in ['canonicalId','representativeOf','parentId']:
            if item.get(key):
                assert item[key] in by_id and item[key]!=item['id'], 'Broken case relationship'
        item['caseReview'] = {'policyVersion':review.get('policyVersion','2026-10-01-all-media-v2'),'reason':review.get('reason','Single source-labelled output; legacy attribution and recorded date retained.'),'evidence':review.get('evidence',[])}
    # Only explicit, source-reviewed run groups may select a default setting.
    # Missing default/medium is held out of the axis, never replaced by "best".
    groups={}
    named_settings={}
    for item in result:
        if is_case(item) and not item.get('modelRunGroup') and not item.get('representativeOf') and timeline_media(item,media_root) and str(item.get('originalLevel','')).lower() in {'default','none','minimal','low','medium','high','xhigh','max'}:
            key=(item['sourceUrl'],item['author'],item['date'],tuple(item['reviewedModelNames']))
            # Keep existing static sweep identities. An animated/3D/etc. test
            # in the same post is not automatically a setting of that SVG run.
            if item['format']!='svg':key=key+(item['format'],)
            named_settings.setdefault(key,[]).append(item)
    for key,members in named_settings.items():
        if len({x['originalLevel'] for x in members})<2:continue
        # Different media/prompts can share a model, date and level. They are
        # not automatically one settings sweep; require explicit source review.
        if len({x['originalLevel'] for x in members})!=len(members):
            for item in members:item['timelineVisible']=False
            continue
        group='source-settings-'+hashlib.sha256(repr(key).encode()).hexdigest()[:16]
        for item in members:
            item['modelRunGroup']=group
            if item['originalLevel']=='default':item['authorDefault']=True
    for item in result:
        if item.get('modelRunGroup') and is_case(item):groups.setdefault(item['modelRunGroup'],[]).append(item)
    for members in groups.values():
        assert len({(x.get('runSourceUrl') or x['sourceUrl'],x['author'],x['date'],tuple(x['reviewedModelNames'])) for x in members})==1, 'Run groups cannot conflate sources, models or dates'
        defaults=[x for x in members if x.get('authorDefault') is True]
        medium=[x for x in members if str(x.get('originalLevel','')).lower()=='medium']
        assert len(defaults)<=1 and len(medium)<=1, 'Ambiguous timeline representative'
        chosen=(defaults or medium or [None])[0]
        for item in members:
            if chosen is None:item['timelineVisible']=False
            elif item['id']!=chosen['id']:item['representativeOf']=chosen['id'];item['timelineVisible']=False
    # Relationships are explicit. Never collapse merely by model/date/artist.
    for item in result:
        item['childIds'] = [x['id'] for x in result if x.get('parentId')==item['id']]
        item['variantIds'] = [x['id'] for x in result if x.get('representativeOf')==item['id']]
        item['duplicateIds'] = [x['id'] for x in result if x.get('canonicalId')==item['id']]
        if item.get('modelRunGroup') or item.get('comparisonGroupAlias'):
            group = item.get('comparisonGroupAlias') or item['modelRunGroup']
            item['comparisonIds'] = [x['id'] for x in result if x.get('modelRunGroup')==group and is_case(x)]
        elif item.get('representativeOf') or item.get('variantIds'):
            main = item.get('representativeOf') or item['id']
            item['comparisonIds'] = [x['id'] for x in result if x['id']==main or x.get('representativeOf')==main]
    return result


def relationship_html(item, items, language='zh', section='all'):
    import html
    en = language=='en'
    E = lambda v: html.escape(str(v),quote=True)
    by_id = {x['id']:x for x in items}
    link = lambda x: '<a href="'+E(x['path'])+'">'+E(x['model']+' · '+x['date'])+'</a>'
    text = []
    if item.get('canonicalId'):
        text.append(('Same output, not an additional case: ' if en else '同一作品的来源存档，不重复计数：')+link(by_id[item['canonicalId']]))
    if item.get('parentId'):
        text.append(('Full source collection: ' if en else '完整原帖合集：')+link(by_id[item['parentId']]))
    if item.get('representativeOf'):
        text.append(('Same-day alternative; timeline representative: ' if en else '同日其它输出，时间线代表作品：')+link(by_id[item['representativeOf']]))
    if item.get('caseVisible') is False and not item.get('referenceOnly') and not item.get('canonicalId'):
        text.append('Source/context archive, excluded from the artwork count and evolution timeline.' if en else '原帖／资料存档，不计独立作品数，不进入进化时间线。')
    crop = item.get('cropProvenance')
    if crop:
        text.append(('Faithful source crop; original retained below. Pixel rectangle: ' if en else '按原图裁切，未重画；完整原图保留在下方。裁切坐标：')+E(str(crop['box'])))
    result = '<aside class="callout" data-case-policy>'+''.join('<p>'+x+'</p>' for x in text)+'</aside>' if text else ''
    if item.get('dateBasis'):
        publication=item.get('sourcePublicationDate')
        if en:
            dated='Source publication: '+E(publication) if publication else 'Recorded date: '+E(item['date'])+'; source publication / generation date not separately verified'
            result += '<p class="small">Date precision / evidence: '+E(item.get('datePrecision',''))+' / '+E(item['dateBasis'])+'. '+dated+'. Generation date is not independently authenticated.</p>'
        else:
            dated='原帖公开日：'+E(publication) if publication else '已记录时间：'+E(item['date'])+'；公开日／生成日未另行核实'
            result += '<p class="small">日期依据：'+E(item.get('datePrecision',''))+' / '+E(item['dateBasis'])+'；'+dated+'。生成日期未另行认证。</p>'
    context = result
    result = ''
    comparison = [by_id[x] for x in item.get('comparisonIds',[]) if x in by_id]
    if len(comparison)>1:
        order={'default':0,'none':1,'minimal':2,'low':3,'medium':4,'high':5,'xhigh':6,'max':7}
        if item.get('comparisonType')=='settings-and-iterations':
            order['medium + detailed prompt']=8
        comparison.sort(key=lambda x:(order.get(x.get('originalLevel'),0),x['id']))
        prompt_comparison=item.get('comparisonType')=='prompt'
        heading=('Same model · prompt comparison' if en else '同一模型 · 题面对照') if prompt_comparison else ('Same model · settings comparison' if en else '同一模型 · 不同档位对照')
        explanation=('Separate source prompts, not reasoning settings. Each real output counts once; the classic pelican prompt represents the timeline.' if en else '不同题面，不是推理档位；每个真实输出单独计数，经典鹈鹕骑车题面进入时间线。') if prompt_comparison else ('Each real output counts once; only the default/medium representative enters the timeline. Source-reported settings, not a ranking.' if en else '每个真实输出计一个案例；时间线只展示作者默认档／medium 代表图。档位按来源标注，非排名。')
        if item.get('comparisonType')=='prompt-and-settings':
            heading='Same model · prompts and settings' if en else '同一模型 · 题面与档位对照'
            explanation='Source-labelled prompts and settings are distinct. All outputs count; the classic prompt at the author default represents the timeline.' if en else '题面和推理档位按原文区分；各真实输出均计数，时间线只显示经典题面的作者默认档。'
        if item.get('comparisonType')=='repeat-runs':
            heading='Same model · independent runs' if en else '同一模型 · 多次独立输出'
            explanation='Separate source runs, not reasoning settings or a ranking. Every valid output counts once; the source page’s default run represents the timeline. Invalid source media is not repaired or counted.' if en else '不同独立运行，不是推理档位或排名；可打开的真实输出分别计数，时间线采用原页面默认展示的运行。原始媒体损坏的运行不修图、不计数。'
        if item.get('comparisonType')=='source-files':
            heading='Same model · published outputs' if en else '同一模型 · 公开输出对照'
            explanation='Distinct source files, not documented reasoning settings or attempt order. Each output counts once. The source specifies no default or medium, so no timeline representative is guessed.' if en else '不同来源文件，不是已证推理档位或运行先后；每份输出计一件。作者未说明默认或 medium，不擅自挑选时间线代表。'
        if item.get('comparisonType')=='quantizations':
            heading='Same model · quantizations and runtimes' if en else '同一模型 · 量化与运行环境对照'
            explanation='Source-labelled quantizations and runtimes, not reasoning levels or a ranking. Each actual output counts once. With no documented default/medium representative, these alternatives remain outside the evolution timeline.' if en else '量化版本与运行环境按原文标注，不是推理档位或排名；每份真实输出分别计数。未明确默认／medium 代表时，这些输出仅留全部作品，不擅自选入进化轴。'
        if item.get('comparisonType')=='access-and-prompts':
            heading='Same model · access and prompt conditions' if en else '同一模型 · 账号与题面条件对照'
            explanation='The source labels free/paid access and basic/advanced prompts; all four outputs use the same reported high setting. These are not four reasoning levels or a museum ranking. Each actual output counts once. No source-default condition is documented, so no timeline representative is guessed.' if en else '来源区分免费／付费账号及基础／加严题面，四份输出都标 high；不是四种推理档位，也不是本馆排名。各真实输出分别计数；作者未明确默认条件，不擅自挑时间线代表。'
        if item.get('comparisonType')=='visual-iterations':
            heading='Same model · visual-feedback iterations' if en else '同一模型 · 视觉反馈迭代对照'
            explanation='Documented output versions after rendering and visual feedback, not reasoning-effort settings or independent blind attempts. Each actual version counts once; views and recordings are not extra works. No source-default iteration is documented, so no timeline representative is guessed.' if en else '按来源记录渲染、看图反馈后的实际输出版本，不是推理档位或相互独立的盲测。每个真实版本分别计数，同版本的多视角和录屏不增加作品。来源未指定默认迭代，因此不擅自挑一张进入时间线。'
        if item.get('comparisonType')=='settings-and-iterations':
            heading='Same model · settings and later refinement' if en else '同一模型 · 档位与后续细化对照'
            explanation='Medium, high and xhigh are source-labelled fresh sessions. The fourth output is a later detailed-prompt refinement in the medium session, not a fourth reasoning level or a one-shot result. Each real output counts once; the original medium output represents the timeline, not the most polished image.' if en else 'medium、high、xhigh 是来源标注的新会话；第四份是 medium 会话追加详细提示后的细化结果，不是第四种推理档位，也不是一次生成。每份真实输出分别计数；原始 medium 代表时间线，不挑最精致的图。'
        if item.get('comparisonType') in {'settings','prompt','prompt-and-settings','repeat-runs'} and not any(in_timeline(x) for x in comparison):
            explanation='Source-labelled prompts, settings or separate runs are preserved without treating them as a ranking. Each real output counts once. No default/medium setting or source-default run is documented, so no timeline representative is guessed.' if en else '保留来源标注的题面、设置或多次独立运行，不构成排名；每份真实输出分别计数。来源未明确默认／medium 档或默认运行，因此不擅自挑一张进入时间线。'
        result += '<section data-setting-comparison><h2>'+heading+'</h2><p>'+explanation+'</p><div class="setting-comparison">'
        for x in comparison:
            label=x.get('originalLevel') or ('Source default' if en else '来源默认档')
            if item.get('comparisonType')=='source-files':
                number=x.get('generationConditions',{}).get('sourceFileNumber','')
                label=('Source file ' if en else '来源文件 ')+str(number) if number else ('Published output' if en else '公开输出')
            result += '<figure><a href="'+E(x['path'])+'"><img src="'+E(x['thumbnail'])+'" alt="'+E(x['model']+' · '+label)+'" loading="lazy"></a><figcaption>'+E(label)+'</figcaption></figure>'
        result += '</div></section>'
    comparison_html = result
    result = ''
    for key, zh, english in [('childIds','从原帖拆出的作品','Works from this source'),('linkedCaseIds','对应的独立作品','Individual works'),('relatedSourceIds','其他原始出处','Other original sources'),('variantIds','其它档位／同日输出（展开查看）','Other settings / same-day outputs'),('duplicateIds','同一作品的其他出处','Other archives of the same output')]:
        members = [by_id[x] for x in item.get(key,[]) if x in by_id]
        if members:
            result += '<details class="case-variants" data-case-relations><summary>'+E(english if en else zh)+' ('+str(len(members))+')</summary><ul>'+''.join('<li>'+link(x)+'</li>' for x in members)+'</ul></details>'
    return {'context':context,'comparison':comparison_html,'relations':result,'all':context+comparison_html+result}[section]
