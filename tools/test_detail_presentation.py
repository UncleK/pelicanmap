"""Whole-catalogue layout and preservation checks for the shared detail template."""
import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from detail_presentation import media_groups, local_demo, record_content

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'public-site'
CAT = json.loads((OUT/'data/catalog.json').read_text(encoding='utf8'))


class DetailPresentationTests(unittest.TestCase):
    def test_all_detail_media_and_sources_retained_bilingually(self):
        for prefix in ['', 'en/']:
            for item in CAT['items']:
                page = BeautifulSoup((OUT/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertTrue(page.select_one('.detail-provenance:not([open])'), item['id'])
                self.assertTrue(page.find('a',href=item['sourceUrl']), item['id'])
                for m in item['media']:
                    self.assertTrue(page.select_one('figure[data-media-src="'+m['src']+'"]'), (prefix,item['id'],m['src']))
                    self.assertTrue(page.find('a',href=m['src']), m['src'])
                    if m.get('source'):
                        self.assertTrue(page.find('a',href=m['source']), m['source'])
                attachments = page.select_one('.detail-attachments')
                if attachments:self.assertFalse(attachments.has_attr('open'))
                self.assertFalse(page.select_one('.page-top p:not(.batch-parent)'), item['id'])

    def test_actual_moving_media_and_demos_precede_stills_and_provenance(self):
        for item in CAT['items']:
            moving,main,_ = media_groups(item,OUT)
            for prefix in ['', 'en/']:
                text = (OUT/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8')
                page = BeautifulSoup(text,'html.parser')
                primary = page.select('[data-detail-primary]')
                self.assertEqual(len(primary),bool(local_demo(item))+bool(moving),item['id'])
                if primary:
                    self.assertLess(text.index('data-detail-primary'),text.index('class="detail-layout"'))
                for m in moving:
                    self.assertTrue(page.select_one('.detail-motion [data-media-src="'+m['src']+'"]'),item['id'])
                if local_demo(item):
                    self.assertEqual(page.select_one('iframe[data-local-demo]')['src'],local_demo(item))
                    self.assertTrue(page.select_one('iframe')['sandbox'])
                if main:
                    self.assertEqual(page.select_one('.detail-layout .detail-gallery figure')['data-media-src'],main[0]['src'])
                self.assertLess(text.index('class="detail-layout"'),text.index('class="detail-provenance"'))

    def test_nonlocal_demo_is_not_embedded_and_media_order_is_unchanged(self):
        item = next(x for x in CAT['items'] if x.get('previewUrl'))
        original = json.dumps(item,sort_keys=True)
        html = record_content(item,CAT['items'],OUT,[], '', 'en')
        self.assertIn('Animation preview',html)
        self.assertEqual(json.dumps(item,sort_keys=True),original)
        self.assertEqual(local_demo({**item,'demoUrl':'https://example.com/unsafe'}),'')

    def test_shared_browse_rows_and_bottom_archive_link(self):
        for prefix in ['', 'en/']:
            for path in ['specimens/', 'timeline/', 'timeline/2025/', 'play/']:
                page = BeautifulSoup((OUT/prefix/path/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertTrue(page.select_one('.browse-family-row .family-links'))
                self.assertTrue(page.select_one('.browse-family-row .browse-buttons'))
                self.assertFalse(page.select_one('.browse-family-row [data-result-count]'))
                self.assertEqual(len(page.select('.year-links')),1)
                self.assertTrue(page.select_one('.browse-toolbar .year-links'))
                self.assertTrue(page.select_one('.browse-toolbar [data-result-count]'))
                self.assertFalse(page.select_one('.browse-toolbar .browse-buttons'))
                self.assertEqual(page.select_one('[data-density-toggle] span').get_text(),'Standard view' if prefix else '标准视图')
                if path=='specimens/':
                    self.assertEqual(len(page.select('.archive-link')),1)
                    self.assertTrue(page.select_one('.browse-footer > .archive-link'))
                    self.assertTrue(page.select_one('.browse-footer > [data-pagination]'))
                if path=='timeline/2025/':
                    root=page.select_one('[data-browser]')
                    self.assertEqual(root['data-base'],'/'+prefix+'timeline/')
                    self.assertEqual(page.select_one('[data-year="2025"]')['aria-current'],'true')

    def test_card_footers_have_number_model_date_in_order(self):
        for prefix in ['', 'en/']:
            for path in ['specimens/','timeline/','timeline/2025/']:
                page=BeautifulSoup((OUT/prefix/path/'index.html').read_text(encoding='utf8'),'html.parser')
                for card in page.select('[data-results] .card'):
                    row=card.select_one('.timeline-meta' if path.startswith('timeline/') else '.card-foot')
                    expected=['case-number','timeline-model','timeline-date'] if path.startswith('timeline/') else ['case-number','card-models','card-date']
                    self.assertEqual([x['class'][0] for x in row.find_all(recursive=False)],expected)
                    self.assertTrue(row.select_one('time[datetime]'))
                    self.assertTrue(row.select_one('.case-number').get_text().startswith('#'))
                    if path=='specimens/':
                        self.assertTrue(card.select_one('.card-cover .source-label'))
                        self.assertFalse(row.select_one('.source-label'))
                        self.assertFalse(card.select_one('.card-body .card-meta'))

    def test_detail_only_comparison_movie_remains_folded(self):
        item={'thumbnail':'/media/one-poster.png','media':[
            {'src':'/media/one.webm','poster':'/media/one-poster.png'},
            {'src':'/media/complete-comparison.mp4','detailOnly':True},
        ]}
        moving,main,attachments=media_groups(item,OUT)
        self.assertEqual([m['src'] for m in moving],['/media/one.webm'])
        self.assertEqual(main,[])
        self.assertEqual([m['src'] for m in attachments],['/media/complete-comparison.mp4'])

    def test_main_image_heading_is_outside_aligned_frame_grid(self):
        for prefix in ['', 'en/']:
            for item in CAT['items']:
                _, main, _=media_groups(item,OUT)
                if not main:continue
                page=BeautifulSoup((OUT/prefix/item['path'].lstrip('/')/'index.html').read_text(encoding='utf8'),'html.parser')
                self.assertTrue(page.select_one('h2.detail-image-heading'))
                self.assertFalse(page.select_one('.detail-layout .detail-gallery h2'))
                self.assertTrue(page.select_one('.detail-layout > .facts'))


if __name__=='__main__':unittest.main()
