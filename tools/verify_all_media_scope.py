"""Scope migration audit: preserved works/assets, all-media timeline and live API."""
import argparse
import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'pelican-archive/research/2026-10-01-all-media-scope'
BASE='https://pelicanmap.aveniqa.com'


def request(path):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-ScopeAudit/1.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=45) as response:return response.read()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--before',action='store_true');args=parser.parse_args()
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    before_path=ARCHIVE/'before-catalog.json'
    if args.before:
        data=request('/data/catalog.json?scope-audit=before')
        if not before_path.exists():before_path.write_bytes(data)
    before=json.loads(before_path.read_bytes())
    local=json.loads((ROOT/'public-site/data/catalog.json').read_bytes())
    old={x['id']:x for x in before['items']};new={x['id']:x for x in local['items']}
    assert set(old)==set(new),'Scope change must not create/remove archival rows'
    assert before['counts']['cases']==local['counts']['cases']
    for key in old:
        for field in ['sourceUrl','model','author','date','media','caseVisible','referenceOnly','thumbnail']:
            assert old[key].get(field)==new[key].get(field),(key,field)
    promoted=[key for key in new if new[key]['timelineVisible'] and not old[key]['timelineVisible']]
    excluded=[key for key in old if old[key]['timelineVisible'] and not new[key]['timelineVisible']]
    assert not excluded,('Existing representatives removed',excluded)
    assert all(not x.get('referenceOnly') and x['caseVisible'] and len(x['modelNames'])==1 for x in new.values() if x['timelineVisible'])
    assert any(x['timelineVisible'] and x['format']=='video' for x in new.values())
    result={'cases':local['counts']['cases'],'timelineBefore':before['counts']['timeline'],'timeline':local['counts']['timeline'],
            'promoted':promoted,'removedRepresentatives':excluded,'timelineFormats':dict(Counter(x['format'] for x in new.values() if x['timelineVisible'])),
            'originalIdsDatesMediaUnchanged':True,'benchmarkReferenceCount':local['counts']['referenceRecords']}
    if not args.before:
        for lang in ['zh','en']:
            prefix='/en' if lang=='en' else ''
            live=json.loads(request(prefix+'/data/catalog.json?scope-audit=live'))
            expected=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_bytes())
            assert live==expected,lang
            for medium in ['svg','image','animation','3d','game','video','audio','other']:
                data=json.loads(request('/api/v1/timeline?lang='+lang+'&format='+medium+'&limit=1'))
                assert data['total']==sum(x['timelineVisible'] and x['format']==medium for x in expected['items']),(lang,medium)
                assert all(x['timelineVisible'] and not x.get('referenceOnly') for x in data['items'])
            for route in ['/timeline/','/about/','/play/','/sources/','/llms.txt']:
                text=request(prefix+route).decode()
                assert 'outside the static timeline' not in text and '普通新增仅限' not in text,(lang,route)
        for key in promoted:
            item=new[key];relative=item['thumbnail']
            assert hashlib.sha256(request(relative)).digest()==hashlib.sha256((ROOT/'public-site'/relative.lstrip('/')).read_bytes()).digest(),key
        policy=json.loads(request('/data/collecting-policy.json'))
        assert policy['allMediaTypes'] is True and policy['timelineMediaTypes'].startswith('all')
        result['liveBilingualApiAndCovers']=True
    target=ARCHIVE/('migration-audit.json' if args.before else 'publication-audit.json')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:value for key,value in result.items() if key!='promoted'},ensure_ascii=False))


if __name__=='__main__':main()
