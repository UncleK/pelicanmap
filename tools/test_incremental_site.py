from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock

from content_cache import cached_hashes
from incremental_site import SiteCache,inspect_file


class IncrementalSiteTests(unittest.TestCase):
    def test_media_inspection_is_reused_only_for_matching_bytes_and_code(self):
        with tempfile.TemporaryDirectory() as folder,cached_hashes(Path(folder)/'hashes.json'):
            root=Path(folder);path=root/'media.svg';path.write_text('<svg/>')
            cache=SiteCache(root,root,'2026-10-10','v1');inspect=Mock(return_value='static')
            with patch('incremental_site.CURRENT',cache):
                self.assertEqual(inspect_file(path,'type',inspect),'static')
                self.assertEqual(inspect_file(path,'type',inspect),'static')
                self.assertEqual(inspect.call_count,1)
                cache.code='v2';inspect_file(path,'type',inspect)
                self.assertEqual(inspect.call_count,2)
                path.write_text('<svg>new bytes</svg>');inspect_file(path,'type',inspect)
                self.assertEqual(inspect.call_count,3)

    def test_unchanged_date_is_reused_but_relations_numbers_and_media_invalidate(self):
        with tempfile.TemporaryDirectory() as folder, cached_hashes(Path(folder)/'hashes.json'):
            root = Path(folder);output = root/'site';output.mkdir()
            items = [dict(id=key, source='community', format='svg', caseVisible=True,
                path='/specimens/'+key+'/', markdown='/specimens/'+key+'/index.md',
                media=[{'src':'/media/'+key+'.png'}], thumbnail='/media/'+key+'.png',
                caseNumber=n) for n,key in enumerate(['a','b','c','d','e'],1)]
            for item in items:
                path=output/item['media'][0]['src'].lstrip('/');path.parent.mkdir(exist_ok=True);path.write_bytes(item['id'].encode())
            cache=SiteCache(root,output,'2026-10-10','code-v1');cache.prepare_details(items,'zh')
            self.assertFalse(cache.detail(items[4],'zh')[0])
            for name in ['index.html','index.md']:
                path=output/'specimens/e'/name;cache.write(path,'existing detail')
            cache.save()
            cache=SiteCache(root,output,'2026-10-11','code-v1');cache.prepare_details(items,'zh')
            self.assertEqual(cache.detail(items[4],'zh'),(True,'2026-10-10'))
            changed=deepcopy(items);changed[0]['title']='related work changed'
            cache.prepare_details(changed,'zh');self.assertFalse(cache.detail(changed[4],'zh')[0])
            cache.prepare_details(items,'zh');cache.detail(items[4],'zh')
            # A work beyond the first three recommendations has no dependency here.
            changed=deepcopy(items);changed[3]['title']='unrelated work changed'
            cache.prepare_details(changed,'zh');self.assertTrue(cache.detail(changed[4],'zh')[0])
            changed=deepcopy(items);changed[4]['caseNumber']=9
            cache.prepare_details(changed,'zh');self.assertFalse(cache.detail(changed[4],'zh')[0])
            cache.prepare_details(items,'zh');cache.detail(items[4],'zh')
            (output/'media/e.png').write_bytes(b'changed-media')
            self.assertFalse(cache.detail(items[4],'zh')[0])

    def test_modified_cached_output_is_repaired_and_schema_date_alone_does_not_render(self):
        with tempfile.TemporaryDirectory() as folder, cached_hashes(Path(folder)/'hashes.json'):
            root=Path(folder);output=root/'site';output.mkdir();target=output/'index.html'
            cache=SiteCache(root,output,'2026-10-10','v1')
            self.assertFalse(cache.page('/',{'content':'same'},[target])[0]);cache.write(target,'original');cache.save()
            cache=SiteCache(root,output,'2026-10-11','v1')
            self.assertEqual(cache.page('/',{'content':'same'},[target]),(True,'2026-10-10'))
            target.write_text('tampered')
            self.assertFalse(cache.page('/',{'content':'same'},[target])[0])


if __name__ == '__main__':unittest.main()
