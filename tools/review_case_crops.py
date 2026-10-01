"""Generated visual proof for source-reviewed panel extraction; no collection edits."""
import json
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
items=json.loads((ROOT/'site/catalog.json').read_text(encoding='utf8'))['items']
items=[x for x in items if x.get('cropProvenance')]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
for start in range(0,len(items),20):
    sheet=Image.new('RGB',(1400,1100),'#f6f2e9');draw=ImageDraw.Draw(sheet)
    for i,x in enumerate(items[start:start+20]):
        left,top=i%5*280,i//5*275
        with Image.open(ROOT/'public-site'/x['thumbnail'].lstrip('/')) as im:
            image=ImageOps.contain(im.convert('RGB'),(270,218));sheet.paste(image,(left+(280-image.width)//2,top))
        draw.text((left+5,top+221),x['model'][:33],font=font,fill='black')
        draw.text((left+5,top+242),x['date']+' '+str(x.get('originalLevel','')),font=font,fill='black')
    sheet.save(ROOT/f'deploy-build/crop-review-{start//20+1:02}.jpg',quality=94)
print('Crops:',len(items),'Sheets:',(len(items)+19)//20)
