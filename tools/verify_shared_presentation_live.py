"""Shared inferred version positions, bilingual film hero and stable artwork facts."""
import csv
import hashlib
import io
import json
import urllib.parse
from bs4 import BeautifulSoup
from verify_model_chronology_live import get, data, ROOT, CAT
from model_chronology import ordered_timeline
from historical_context import HISTORY_ID, historical_sections

def main():
    checks=0
    for language,prefix in [('zh',''),('en','/en')]:
        localized=json.loads((ROOT/'public-site'/prefix.lstrip('/')/'data/catalog.json').read_text(encoding='utf8'))
        assert data(prefix+'/data/catalog.json?shared-position=20261002')==localized
        works=[x for x in localized['items'] if x.get('caseVisible') and not x.get('referenceOnly')]
        timeline=[x for x in works if x.get('timelineVisible')]
        for scope,rows in [('specimens',works),('timeline',timeline)]:
            for sort in ['newest','oldest']:
                for family in ['', 'Gemini','GPT','Claude']:
                    selected=[x for x in rows if not family or family in x['modelFamilies']]
                    for offset in [0,50]:
                        query=urllib.parse.urlencode(dict(lang=language,sort=sort,family=family,offset=offset,limit=50))
                        response=data('/api/v1/'+scope+'?'+query)
                        assert response['sortBasis']=='model-release'
                        assert response['total']==len(selected)
                        assert response['items']==ordered_timeline(selected,sort)[offset:offset+50]
                        checks+=1
            page=BeautifulSoup(get(prefix+'/'+scope+'/'),'html.parser')
            paths=[a['href'] for a in page.select('[data-results] .card-cover')]
            assert paths==[x['path'] for x in ordered_timeline(rows)[:24]]
            assert not page.select('[data-year="unknown"], [data-release-month="unknown"]')
            assert '发布时间待核' not in page.select_one('[data-browser]').get_text()
            assert 'Release date unverified' not in page.select_one('[data-browser]').get_text()
            checks+=1
        for row in csv.DictReader(io.StringIO(get(prefix+'/data/catalog.csv').decode())):
            info=next(x for x in localized['items'] if x['id']==row['id']).get('modelTimeline',{})
            assert row['modelSortDate']==info.get('sortDate','')
            assert row['modelReleaseDate']==info.get('releaseDate','')
        history=next(x for x in localized['items'] if x['id']==HISTORY_ID)
        assert history['date']=='1988' and not history['caseVisible'] and not history['timelineVisible'] and history['caseNumber'] is None
        home=BeautifulSoup(get(prefix+'/'),'html.parser')
        hero=home.select_one('[data-historical-hero]')
        assert hero.select_one('.hero-media')['href']==history['path']
        assert hero.select_one('video')['data-motion-src']==history['media'][0]['src']
        detail=BeautifulSoup(get(history['path']),'html.parser')
        markdown=get(history['markdown']).decode()
        for title,text,url,_ in historical_sections(language):
            assert text in detail.select_one('[data-historical-story]').get_text()
            assert detail.find('a',href=url) and text in markdown and url in markdown
        assert 'Dave Spafford' in detail.select_one('.facts').get_text()
        checks+=4
    history=next(x for x in CAT['items'] if x['id']==HISTORY_ID)
    film=history['media'][0]
    film_sha=history['recordRepair']['mediaSha256']
    assert hashlib.sha256(get(film['src'])).hexdigest()==film_sha
    assert data('/data/collecting-policy.json')==json.loads((ROOT/'site/collecting-policy.json').read_text(encoding='utf8'))
    inferred=[x for x in CAT['items'] if x.get('timelineVisible') and x.get('modelTimeline',{}).get('status')=='inferred-position']
    assert all('releaseDate' not in x['modelTimeline'] and x['modelTimeline']['estimatedFrom']['sourceUrl'] for x in inferred)
    print(json.dumps(dict(checks=checks+2,cases=CAT['counts']['cases'],timeline=CAT['counts']['timeline'],integrated_inferred_representatives=len(inferred),original_movie_sha256=film_sha,status='passed'),ensure_ascii=False))

if __name__=='__main__':main()
