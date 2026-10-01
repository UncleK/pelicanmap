"""Inventory every archived record before source-reviewed case-unit migration.

Read-only with respect to the collection. Reports/contact sheets go to deploy-build.
No semantic/model attribution is inferred from image similarity.
"""
import collections
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def audit():
    items = json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))['items']
    hashes = collections.defaultdict(list)
    rows, candidates = [], []
    for item in items:
        if item.get('referenceOnly'):
            continue
        media = []
        for m in item['media']:
            path = ROOT/'pelican-web'/m['src'].lstrip('/')
            if not path.is_file():
                path = ROOT/'public-site'/m['src'].lstrip('/')
            if path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                media.append({'src': m['src'], 'sha256': digest})
                hashes[digest].append(item['id'])
        candidate = len(item.get('modelNames', [])) != 1 or len(item['media']) > 1 or 'ai-worlds-fair' in item['id'] or 'grid' in item['id']
        row = {k: item.get(k) for k in ['id','originalId','source','date','author','model','modelNames','format','sourceUrl','thumbnail','promptCategory','notes']}
        row['media'] = media
        row['reviewCandidate'] = candidate
        rows.append(row)
        if candidate and item['format'] in ('svg', 'text'):
            candidates.append(item)
    report = {'recordsReviewed': len(rows), 'records': rows,
              'exactMediaDuplicates': {h: sorted(set(v)) for h,v in hashes.items() if len(set(v)) > 1}}
    out = ROOT/'deploy-build'
    out.mkdir(exist_ok=True)
    (out/'case-unit-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 13)
    for start in range(0,len(candidates),12):
        sheet = Image.new('RGB',(1200,1080),'#f4f2e8')
        draw = ImageDraw.Draw(sheet)
        for index,item in enumerate(candidates[start:start+12]):
            x,y = index%3*400,index//3*270
            path = ROOT/'public-site'/item['thumbnail'].lstrip('/')
            if path.suffix.lower() != '.svg' and path.is_file():
                with Image.open(path) as im:
                    preview = ImageOps.contain(im.convert('RGB'),(390,185))
                    sheet.paste(preview,(x+(400-preview.width)//2,y+5))
            else:
                draw.text((x+10,y+70),'SVG: source file, no raster preview',font=font,fill='black')
            draw.text((x+5,y+191),item['id'][:48],font=font,fill='black')
            draw.text((x+5,y+212),item['model'][:51],font=font,fill='black')
            draw.text((x+5,y+234),item['date']+' / '+str(len(item['media']))+' media',font=font,fill='black')
        sheet.save(out/f'case-unit-sheet-{start//12+1:02}.jpg',quality=92)
    selected = [x for x in candidates if x['source']=='community' and len(x['media'])>1 and len(x.get('modelNames',[]))>1 and 'elo-' not in x['id'] and 'qwen36-beats' not in x['id'] and 'origin' not in x['id']]
    for item in selected:
        sheet = Image.new('RGB',(400*len(item['media']),420),'#f4f2e8')
        draw = ImageDraw.Draw(sheet)
        for i,m in enumerate(item['media']):
            path=ROOT/'pelican-web'/m['src'].lstrip('/')
            if path.suffix.lower() in {'.png','.webp','.jpg','.jpeg'}:
                with Image.open(path) as im:
                    preview=ImageOps.contain(im.convert('RGB'),(390,330));sheet.paste(preview,(i*400,0))
                draw.text((i*400+5,335),str(i)+' '+m['src'].rsplit('/',1)[-1],font=font,fill='black')
        sheet.save(out/('attachments-'+item['originalId']+'.jpg'),quality=94)
    print(json.dumps({'reviewed':len(rows),'staticReviewCandidates':len(candidates),'exactHashGroups':len(report['exactMediaDuplicates']),'sheets':(len(candidates)+11)//12}))


if __name__ == '__main__':
    audit()
