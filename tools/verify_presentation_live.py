"""Verify the deployed bilingual media-first details and browse control layout."""
import concurrent.futures
import json
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
from detail_presentation import media_groups, local_demo

ROOT=Path(__file__).resolve().parents[1]
BASE='https://pelicanmap.aveniqa.com'
LOCAL=json.loads((ROOT/'public-site/data/catalog.json').read_text(encoding='utf8'))


def get(path):
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'PelicanMap-Presentation-Verifier/1.0'})
    with urllib.request.urlopen(request,timeout=40) as response:
        assert response.status==200
        return response.read()


def verify_detail(task):
    prefix,item=task
    page=BeautifulSoup(get(prefix+item['path']),'html.parser')
    moving,main,attachments=media_groups(item,ROOT/'public-site')
    text=str(page)
    primary=page.select('[data-detail-primary]')
    assert len(primary)==bool(moving)+bool(local_demo(item)),(prefix,item['id'])
    if primary:assert text.index('data-detail-primary')<text.index('class="detail-layout"')
    for media in item['media']:
        assert page.find('a',href=media['src']),(item['id'],media['src'])
    if moving:
        assert len(page.select('.detail-motion figure'))==len(moving)
    if local_demo(item):
        assert page.select_one('iframe[data-local-demo]')['src']==local_demo(item)
    if main:
        assert page.select_one('h2.detail-image-heading')
        assert not page.select_one('.detail-layout .detail-gallery h2')
    if attachments:assert page.select_one('.detail-attachments:not([open])')
    assert page.select_one('.detail-provenance:not([open])')
    assert page.find('a',href=item['sourceUrl'])
    if item.get('comparisonIds') and len(item['comparisonIds'])>1:
        assert text.index('data-setting-comparison')<text.index('class="detail-layout"')
    return item['id']


def main():
    live=json.loads(get('/data/catalog.json'))
    assert live['items']==LOCAL['items'] and live['counts']==LOCAL['counts']
    for prefix in ['', '/en']:
        for route in ['/specimens/','/timeline/','/timeline/2025/','/play/']:
            page=BeautifulSoup(get(prefix+route),'html.parser')
            assert page.select_one('.browse-family-row .family-links')
            assert page.select_one('.browse-family-row .browse-buttons')
            assert not page.select_one('.browse-family-row [data-result-count]')
            assert len(page.select('.year-links'))==1
            assert page.select_one('.browse-toolbar .year-links')
            assert page.select_one('.browse-toolbar [data-result-count]')
            for card in page.select('[data-results] .card'):
                row=card.select_one('.timeline-meta' if route.startswith('/timeline/') else '.card-foot')
                expected=['case-number','timeline-model','timeline-date'] if route.startswith('/timeline/') else ['case-number','card-models','card-date']
                assert [x['class'][0] for x in row.find_all(recursive=False)]==expected
                assert row.select_one('time[datetime]')
                if not route.startswith('/timeline/') and not card.get('data-batch-card'):
                    assert card.select_one('.card-cover .source-label')
                    assert not card.select_one('.card-body .card-meta')
            assert page.select_one('[data-density-toggle] span').get_text()==('Standard view' if prefix else '标准视图')
            assert page.select_one('.browse-footer > [data-pagination]')
            if route=='/specimens/':assert page.select_one('.browse-footer > .archive-link')
            if route=='/timeline/2025/':assert page.select_one('[data-browser]')['data-base']==prefix+'/timeline/'
    selected=[x for x in LOCAL['items'] if media_groups(x,ROOT/'public-site')[0] or local_demo(x) or (x['format'] in {'animation','game'}) or x.get('comparisonIds') or x.get('cropProvenance')]
    tasks=[(prefix,item) for prefix in ['', '/en'] for item in selected]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(verify_detail,tasks))
    print(json.dumps({'bilingual_details_checked':len(tasks),'bilingual_browse_routes':8,'catalogue_unchanged':True,'counts':LOCAL['counts'],'dynamic_first_and_archives_retained':True}))


if __name__=='__main__':main()
