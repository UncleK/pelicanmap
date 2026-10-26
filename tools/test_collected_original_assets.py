"""Reviewed large media must reach the public archive with their pinned bytes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from PIL import Image

import build_public_site as build


class CollectedOriginalTests(unittest.TestCase):
    def test_reviewed_display_repair_keeps_pinned_large_video_bytes(self):
        with tempfile.TemporaryDirectory(prefix='pelican-repaired-assets-') as directory:
            root=Path(directory);source=root/'source';out=root/'out';demos=root/'demos'
            (root/'site/assets').mkdir(parents=True)
            Image.new('RGB',(64,64),'white').save(root/'site/assets/logo-a.png')
            (root/'site/additions.json').write_text('[]',encoding='utf8')
            (source/'demos').mkdir(parents=True)
            video=source/'media/collected/repair/segment.mp4';video.parent.mkdir(parents=True)
            video.write_bytes(b'reviewed source packets\0'*(1200000))
            self.assertGreater(video.stat().st_size,24*1024*1024)
            (root/'site/record-overrides.json').write_text(json.dumps({'work':{'fields':{'media':[{
                'src':'/media/collected/repair/segment.mp4','sha256':hashlib.sha256(video.read_bytes()).hexdigest()}]}}}),encoding='utf8')
            public=out/'media/collected/repair/segment.mp4';public.parent.mkdir(parents=True);public.write_bytes(b'old transcode')
            branding=Mock();branding.asset_group.return_value=True
            with patch.multiple(build,ROOT=root,SOURCE=source,OUT=out,DEMOS=demos,BUILD_CACHE=branding),patch.object(build.subprocess,'run') as transcode:
                build.prepare_assets()
                self.assertEqual(public.read_bytes(),video.read_bytes())
                transcode.assert_not_called()

    def test_large_reviewed_video_is_copied_even_when_an_old_derivative_exists(self):
        with tempfile.TemporaryDirectory(prefix='pelican-original-assets-') as directory:
            root=Path(directory)
            source=root/'source';out=root/'out';demos=root/'public-demos'
            (root/'site/assets').mkdir(parents=True)
            Image.new('RGB',(64,64),'white').save(root/'site/assets/logo-a.png')
            (source/'demos').mkdir(parents=True)
            video=source/'media/collected/reviewed/original.mp4'
            video.parent.mkdir(parents=True)
            video.write_bytes(b'pinned original\0'*(2*1024*1024))
            self.assertGreater(video.stat().st_size,24*1024*1024)
            public=out/'media/collected/reviewed/original.mp4'
            public.parent.mkdir(parents=True)
            public.write_bytes(b'old reduced-resolution derivative')
            expected=hashlib.sha256(video.read_bytes()).hexdigest()
            record={'generationMethod':'code-generated','media':[{'src':'/media/collected/reviewed/original.mp4','sha256':expected}]}
            (root/'site/additions.json').write_text(json.dumps([record]),encoding='utf-8')
            legacy=source/'media/collected/reviewed/legacy-unreferenced.mp4'
            legacy.write_bytes(video.read_bytes())
            legacy_public=out/'media/collected/reviewed/legacy-unreferenced.mp4'
            legacy_public.write_bytes(b'unchanged legacy delivery copy')
            # Branding reuse is unrelated to the original-media copy contract.
            branding=Mock();branding.asset_group.return_value=True
            with patch.multiple(build,ROOT=root,SOURCE=source,OUT=out,DEMOS=demos,BUILD_CACHE=branding),patch.object(build.subprocess,'run') as transcode:
                build.prepare_assets()
                self.assertEqual(hashlib.sha256(public.read_bytes()).hexdigest(),expected)
                self.assertEqual(legacy_public.read_bytes(),b'unchanged legacy delivery copy')
                transcode.assert_not_called()
                # A later source-byte update cannot leave the earlier public copy.
                with video.open('ab') as file:file.write(b'reviewed update')
                record['media'][0]['sha256']=hashlib.sha256(video.read_bytes()).hexdigest()
                (root/'site/additions.json').write_text(json.dumps([record]),encoding='utf-8')
                build.prepare_assets()
                self.assertEqual(public.read_bytes(),video.read_bytes())
                transcode.assert_not_called()


if __name__=='__main__':unittest.main()
