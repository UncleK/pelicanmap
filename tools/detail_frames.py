"""Faithful video frames for detail galleries, never additional archival works."""
import hashlib
from content_cache import sha256_file
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def apply_detail_frames(items, output):
    manifest = json.loads((ROOT/'site/detail-frames.json').read_text(encoding='utf8'))
    for item in items:
        item.pop('detailFrames', None)
        if item.get('referenceOnly'):
            continue
        frames = []
        for media in item['media']:
            row = manifest['videos'].get(media['src']) or manifest.get('animations',{}).get(media['src'])
            if media.get('detailOnly') or not row:
                continue
            for frame in row['frames']:
                local = Path(output)/frame['src'].lstrip('/')
                assert local.is_file(), frame['src']
                assert sha256_file(local) == frame['sha256'], frame['src']
                frames.append({**frame,'sourceMedia':media['src'],'sourceType':'video' if media['src'] in manifest['videos'] else 'animation','sourceSha256':row['sourceSha256'],
                               'sourceUrl':media.get('source') or item['sourceUrl']})
        if frames:
            item['detailFrames'] = frames
    return items

def generate():
    """Run explicitly on reviewed local archives, not during server builds."""
    import os
    import shutil
    import subprocess
    from PIL import Image, ImageStat
    ffmpeg = next((str(p) for p in Path(os.environ.get('LOCALAPPDATA','')).glob('Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/ffmpeg.exe')),None) or shutil.which('ffmpeg')
    ffprobe = str(Path(ffmpeg).with_name('ffprobe.exe')) if ffmpeg and Path(ffmpeg).suffix=='.exe' else shutil.which('ffprobe')
    assert ffmpeg and ffprobe
    catalog=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))
    videos={m['src'] for x in catalog['items'] if not x.get('referenceOnly') and x.get('caseVisible') is not False
            for m in x['media'] if not m.get('detailOnly') and Path(m['src']).suffix.lower() in {'.mp4','.webm'} and m['src'].startswith('/media/')}
    dest=ROOT/'pelican-web/media/derived/detail-frames'
    dest.mkdir(parents=True,exist_ok=True)
    result={'version':'2026-10-02','method':'Original decoded pixels at 20/40/60/80 percent duration or original animation frame indexes, no resize or redraw; supplemental views, not new works.','videos':{},'animations':{}}
    for src in sorted(videos):
        local=ROOT/'pelican-web'/src.lstrip('/')
        raw_hash=sha256_file(local)
        probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_format','-show_streams','-of','json',str(local)]))
        duration=float(probe['format']['duration'])
        stream=next(s for s in probe['streams'] if s['codec_type']=='video')
        row={'sourceSha256':raw_hash,'duration':duration,'width':stream['width'],'height':stream['height'],'frames':[],'skipped':[]}
        seen=set()
        for fraction in [.2,.4,.6,.8]:
            second=round(duration*fraction,3)
            target=dest/(raw_hash[:20]+'-'+str(round(second*1000))+'.png')
            if not target.exists():
                subprocess.run([ffmpeg,'-v','error','-nostdin','-i',str(local),'-ss',str(second),'-frames:v','1','-compression_level','9',str(target)],check=True,capture_output=True)
            with Image.open(target) as im:
                im.load()
                assert im.size==(stream['width'],stream['height']),src
                pixels=hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
                reason='duplicate frame' if pixels in seen else 'near-uniform frame' if max(ImageStat.Stat(im.convert('RGB')).stddev)<2 else ''
                if reason:
                    row['skipped'].append({'second':second,'reason':reason});continue
                seen.add(pixels)
            row['frames'].append({'src':'/'+target.relative_to(ROOT/'pelican-web').as_posix(), 'second':second,
                                  'sha256':sha256_file(target),'pixelSha256':pixels})
        result['videos'][src]=row
    animations={m['src'] for x in catalog['items'] if not x.get('referenceOnly') and x.get('caseVisible') is not False
                for m in x['media'] if not m.get('detailOnly') and Path(m['src']).suffix.lower() in {'.gif','.webp','.png'} and m['src'].startswith('/media/')}
    for src in sorted(animations):
        local=ROOT/'pelican-web'/src.lstrip('/')
        with Image.open(local) as im:
            if not getattr(im,'is_animated',False):continue
            raw_hash=sha256_file(local)
            durations=[]
            for n in range(im.n_frames):
                im.seek(n);durations.append(im.info.get('duration',0))
            row={'sourceSha256':raw_hash,'width':im.width,'height':im.height,'frameCount':im.n_frames,'frames':[]}
            elapsed=[sum(durations[:n])/1000 for n in range(im.n_frames)]
            valid_time=all(d>0 for d in durations)
            seen=set()
            for n in sorted({min(im.n_frames-1,int(im.n_frames*f)) for f in [.2,.4,.6,.8]}):
                im.seek(n);frame=im.convert('RGBA')
                pixel_hash=hashlib.sha256(frame.convert('RGB').tobytes()).hexdigest()
                if pixel_hash in seen:continue
                seen.add(pixel_hash)
                target=dest/(raw_hash[:20]+'-frame-'+str(n)+'.png')
                frame.save(target,optimize=True)
                data={'src':'/'+target.relative_to(ROOT/'pelican-web').as_posix(),'frameIndex':n,'sha256':sha256_file(target),'pixelSha256':pixel_hash}
                if valid_time:data['second']=round(elapsed[n],3)
                row['frames'].append(data)
            if row['frames']:result['animations'][src]=row
    (ROOT/'site/detail-frames.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'videos':len(videos),'animations':len(result['animations']),'frames':sum(len(x['frames']) for key in ['videos','animations'] for x in result[key].values()),'bytes':sum(x.stat().st_size for x in dest.glob('*.png'))}))

if __name__=='__main__':generate()
