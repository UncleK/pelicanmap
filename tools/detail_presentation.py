"""Shared bilingual detail layout. Presentation never changes archival media/order."""
import html
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit
from PIL import Image
from case_policy import relationship_html


def local_media(src, output):
    """Resolve only archived media, including assets on our isolated demo origin."""
    parsed = urlsplit(src)
    roots = [Path(output).resolve()]
    if parsed.netloc:
        if parsed.scheme != 'https' or parsed.netloc != 'pelicanmap-demos.aveniqa.com':
            return None
        roots = [Path(output).resolve().parent / 'demos', Path(__file__).resolve().parents[1] / 'public-demos']
    for root in roots:
        local = (root / unquote(parsed.path).lstrip('/')).resolve()
        if local.is_relative_to(root.resolve()) and local.is_file():
            return local
    return None


@lru_cache(maxsize=4096)
def motion_kind(src, output):
    """Inspect actual local files, not the catalogue's historical format label."""
    path = urlsplit(src).path
    suffix = Path(path).suffix.lower()
    if suffix in {'.mp4', '.webm'}:
        return 'video'
    if suffix in {'.mp3', '.m4a', '.wav', '.ogg', '.flac'}:
        return 'audio'
    local = local_media(src, output)
    if not local:
        return ''
    if suffix in {'.gif', '.webp', '.png'}:
        with Image.open(local) as image:
            return 'animation' if getattr(image, 'is_animated', False) else ''
    if suffix == '.svg':
        source = local.read_text(encoding='utf8', errors='replace')
        if re.search(r'<(?:\w+:)?(?:animate(?:Motion|Transform)?|set)\b|@(?:-webkit-)?keyframes\b', source):
            return 'animation'
    return ''


def media_groups(item, output):
    """Motion first; gallery of individual views; detail-only originals stay folded."""
    media = []
    seen = set()
    for m in item['media']:
        if m['src'] not in seen:
            seen.add(m['src'])
            media.append(m)
    moving = [m for m in media if not m.get('detailOnly') and motion_kind(m['src'], str(output))]
    stills = [m for m in media if not m.get('detailOnly') and not motion_kind(m['src'], str(output))]
    primary = next((m for m in stills if item['thumbnail'] in {m['src'], m.get('preview')}), None)
    primary = primary or next((m for m in stills if not m.get('detailOnly')), None) or (stills[0] if stills else None)
    main = ([primary] if primary else [])+[m for m in stills if m is not primary]
    return moving, main, [m for m in media if m not in moving and m not in main]


def local_demo(item):
    demo = item.get('demoUrl') or item.get('previewUrl') or ''
    parsed = urlsplit(demo)
    return demo if parsed.scheme == 'https' and parsed.netloc == 'pelicanmap-demos.aveniqa.com' and parsed.path.startswith('/demos/') else ''


def apply_motion_previews(items, output):
    """Derived presentation only: never infer motion from a format label or still."""
    for item in items:
        item.pop('motionPreview', None)
        if item.get('referenceOnly'):
            continue
        for media in item['media']:
            if media.get('detailOnly') or not local_media(media['src'], output):
                continue
            kind = motion_kind(media['src'], str(output))
            if kind in {'video', 'animation'}:
                item['motionPreview'] = {'type': 'video' if kind == 'video' else 'image', 'src': media['src']}
                break
        else:
            # Uncounted composite archives do not become animated main covers.
            # Existing demos have already passed the shared license/safety policy.
            demo = local_demo(item)
            if demo and item.get('caseVisible') is not False:
                item['motionPreview'] = {'type': 'iframe', 'src': demo}
    return items


def cover_media(item, alt=None):
    """Static crawlable fallback + lazy, visible-only motion; mirrors browse.js."""
    E = lambda value: html.escape(str(value or ''), quote=True)
    preview = item.get('motionPreview', {})
    src, kind = E(preview.get('src')), preview.get('type')
    attrs = (' data-motion-kind="image" data-motion-src="'+src+'" data-motion-poster="'+E(item['thumbnail'])+'"') if kind == 'image' else ''
    image = '<img src="'+E(item['thumbnail'])+'" alt="'+E(alt or item['title'])+'" width="640" height="420" loading="lazy"'+attrs+'>'
    if kind == 'video':
        image += '<video class="motion-layer" data-motion-kind="video" data-motion-src="'+src+'" autoplay muted loop playsinline preload="none" aria-hidden="true" tabindex="-1"></video>'
    elif kind == 'iframe':
        image += '<span class="motion-layer motion-frame"><iframe data-motion-kind="iframe" data-motion-src="'+src+'" title="'+E(item['title'])+'" loading="lazy" scrolling="no" sandbox="allow-scripts allow-same-origin" referrerpolicy="no-referrer" aria-hidden="true" tabindex="-1"></iframe></span>'
    return image


def record_content(item, items, output, facts, buttons, language='zh'):
    en = language == 'en'
    t = lambda zh, english: english if en else zh
    E = lambda value: html.escape(str(value or ''), quote=True)
    moving, main, attachments = media_groups(item, output)
    demo = local_demo(item)

    def figure(m):
        kind = motion_kind(m['src'], str(output))
        if kind == 'video':
            poster = ' poster="'+E(m['poster'])+'"' if m.get('poster') else ''
            tag = '<video controls autoplay muted loop playsinline preload="none" data-motion-kind="video" data-motion-src="'+E(m['src'])+'"'+poster+'>'+t('您的浏览器无法播放该视频。','Your browser cannot play this video.')+'</video><noscript><a href="'+E(m['src'])+'">'+t('打开原视频播放 ↗','Open the original video ↗')+'</a></noscript>'
        elif kind == 'audio':
            tag = '<audio controls preload="metadata" src="'+E(m['src'])+'">'+t('您的浏览器无法播放该音频。','Your browser cannot play this audio.')+'</audio>'
        else:
            # A static preview must not replace an actual archived animation.
            src = m['src'] if kind == 'animation' else m.get('preview') or m['src']
            attrs = ' data-motion-kind="image" data-motion-src="'+E(src)+'" data-motion-poster="'+E(m.get('preview') or item['thumbnail'])+'"' if kind == 'animation' else ''
            tag = '<img src="'+E(src)+'" alt="'+E(item['title']+' · '+(m.get('caption') or item['formatLabel']))+'" loading="lazy"'+attrs+'>'
        links = '<a href="'+E(m['src'])+'">'+t('原始文件 ↗','Original file ↗')+'</a>'
        if m.get('source') and m['source'] != m['src']:
            links += ' · <a href="'+E(m['source'])+'">'+t('附件原始来源 ↗','Original media source ↗')+'</a>'
        return '<figure data-media-src="'+E(m['src'])+'" data-media-kind="'+(kind or 'image')+'">'+tag+'<figcaption>'+E(m.get('caption'))+' <span>'+links+'</span></figcaption></figure>'

    body = ''
    if moving:
        body += '<section class="detail-motion detail-gallery" data-detail-primary="media"><h2>'+t('观看作品','Watch the work')+'</h2>'+''.join(figure(m) for m in moving)+'</section>'
    if demo:
        label = t('站内交互演示','Interactive demo') if item.get('interactive') else t('动画预览','Animation preview')
        controls = item.get('interactionControls', {}).get(language) or t('在本页观看；播放或暂停不代表可玩交互。','Watch on this page; playback or pause alone is not a playable interaction.')
        motion_attrs = ' data-motion-kind="iframe" data-motion-src="'+E(demo)+'"' if not item.get('interactive') else ''
        body += '<section id="demo" class="demo-section detail-primary" data-detail-primary="demo"><div class="section-head"><h2>'+label+'</h2><button type="button" class="browse-button" data-demo-fullscreen>'+t('全屏 ↗','Full screen ↗')+'</button></div><p class="small">'+E(controls)+'</p><iframe data-local-demo'+motion_attrs+' src="'+E(demo)+'" title="'+E(item['title']+' · '+label)+'" loading="lazy" sandbox="allow-scripts allow-same-origin allow-pointer-lock" allow="fullscreen" referrerpolicy="no-referrer"></iframe></section>'
    body += relationship_html(item, items, language, section='comparison')
    # Keep the comparison before the individual image, as required for grouped runs.
    frames = item.get('detailFrames') or []
    views = main + [{'src':f['src'],'source':f['sourceMedia'],
                      'caption':t('原始媒体真实帧 · ','Frame from original media · ')+(str(f['second'])+' s' if 'second' in f else t('帧 ','frame ')+str(f['frameIndex']))} for f in frames]
    # Only real archived previews are used when a demo has no video frames.
    if not views and (demo or moving) and local_media(item['thumbnail'],output) and not motion_kind(item['thumbnail'],str(output)):
        views=[{'src':item['thumbnail'],'source':item['sourceUrl'],'caption':t('已归档静态预览','Archived still preview')}]
    gallery = ''.join(figure(m) for m in views)
    if len(views)>1:
        gallery='<div data-detail-carousel><div class="detail-gallery-track" tabindex="0" aria-label="'+t('左右滑动查看同一作品的其它画面','Scroll horizontally to see other views of this work')+'">'+gallery+'</div><div class="gallery-controls"><button type="button" data-gallery-step="-1" aria-label="'+t('上一幅','Previous image')+'">←</button><span data-gallery-position>1 / '+str(len(views))+'</span><button type="button" data-gallery-step="1" aria-label="'+t('下一幅','Next image')+'">→</button></div></div>'
    if views:
        heading = t('不同时间帧','Frames at different times') if frames and not main else t('静态预览','Still preview') if demo or moving else t('本件作品','The work')
        if not demo and not moving and item['format'] in {'animation', 'game'}:
            body += '<p class="small" data-preview-only>'+t('本站仅归档了来源静态预览；原始动画或交互可通过明确的出处链接查看。','Only a source still preview is archived here. Use the labelled source links to view the original animation or interaction.')+'</p>'
        body += '<h2 class="detail-image-heading">'+heading+'</h2>'
    elif not demo and not moving:
        gallery = '<p class="callout">'+E(item.get('mediaNote') or t('请查看原始出处与资料。','See the original source and record.'))+'</p>'
    summary = [
        (t('记录日期','Recorded date'), item['date'] or t('未记录','Not recorded')),
        (t('模型（来源标注）','Model (source label)'), item['model'] or t('未标注；不推断','Not specified; not inferred')),
        (t('作者 / 发布者','Creator / publisher'), item['author'] or t('请见原始出处','See original source')),
        (t('形式','Format'), item['formatLabel']),
    ]
    summary_html = ''.join('<dt>'+key+'</dt><dd>'+E(value)+'</dd>' for key, value in summary)
    body += '<div class="detail-layout"><div class="detail-gallery">'+gallery+'</div><aside class="facts"><h2>'+t('作品信息','Work information')+'</h2><dl>'+summary_html+'</dl><p class="small">'+t('模型与署名按来源保留，未独立认证。','Model and attribution are source-reported, not independently authenticated.')+'</p><div class="actions">'+buttons+'</div><p class="rights">'+E(item['rights'])+'</p></aside></div>'
    if item.get('notes'):
        body += '<section class="detail-notes"><h2>'+t('作品说明','About this work')+'</h2><p>'+E(item['notes'])+'</p></section>'
    if attachments:
        body += '<details class="detail-attachments"><summary>'+t('原图与补充附件','Full originals & additional media')+' ('+str(len(attachments))+')</summary><div class="detail-gallery">'+''.join(figure(m) for m in attachments)+'</div></details>'
    body += relationship_html(item, items, language, section='relations')
    fact_html = ''.join('<dt>'+E(key)+'</dt><dd>'+E(value)+'</dd>' for key, value in facts)
    original_label = '<p class="small">'+t('原目录标签：','Original catalog label: ')+E(item['originalLevel'])+t('。这是整理标签，不能作为统一条件下的模型能力评分。','. A historical organizing label, not a score from a controlled benchmark.')+'</p>' if item.get('originalLevel') else ''
    body += '<details class="detail-provenance"><summary>'+t('日期依据、提示词与溯源记录','Date evidence, prompt & provenance')+'</summary>'+relationship_html(item, items, language, section='context')+'<dl>'+fact_html+'</dl>'+original_label+'</details>'
    return body
