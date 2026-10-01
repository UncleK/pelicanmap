"""Read-only public checks for the three approved early-history outputs."""
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup
import verify_user_history_live as shared

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'pelican-archive/research/2026-10-01-nile-early'
MANIFEST=json.loads((ARCHIVE/'approved-manifest.json').read_text(encoding='utf8'))


def main():
    stamp=hashlib.sha256((ROOT/'site/catalog.json').read_bytes()).hexdigest()[:12]
    remote=json.loads(shared.get('/data/catalog.json?nile='+stamp))
    assert remote==shared.LOCAL
    checked=[]
    for c in MANIFEST['cases']:
        checked.append(shared.check(c))
        x=shared.BY[c['id']]
        for lang,prefix in [('zh',''),('en','/en')]:
            soup=BeautifulSoup(shared.get(prefix+x['path']),'html.parser')
            if x.get('comparisonType')=='quantizations':
                section=soup.select_one('[data-setting-comparison]')
                assert len(section.select('figure'))==2
                assert section.h2.get_text()==('Same model · quantizations and runtimes' if lang=='en' else '同一模型 · 量化与运行环境对照')
                assert not x['timelineVisible']
            api=json.loads(shared.get('/api/v1/specimens/'+c['id']+'?lang='+lang))
            assert api['sourcePublicationDate']==c['date'] and api['caseVisible']
    for lang in ['zh','en']:
        works=json.loads(shared.get('/api/v1/specimens?lang='+lang+'&limit=1'))
        timeline=json.loads(shared.get('/api/v1/timeline?lang='+lang+'&limit=1'))
        assert works['total']==remote['counts']['cases']
        assert timeline['total']==remote['counts']['timeline']
        gemma=json.loads(shared.get('/api/v1/timeline?year=2025&family=Gemma&limit=50&lang='+lang))
        assert not {c['id'] for c in MANIFEST['cases'] if 'gemma3n' in c['id']} & {x['id'] for x in gemma['items']}
    result={'original_media_hashes':len(checked),'bilingual_details_and_api':2*len(checked),'cases':remote['counts']['cases'],'timeline':remote['counts']['timeline'],'gemma_representative':'not guessed','mistral_duplicate':'not imported'}
    (ARCHIVE/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
