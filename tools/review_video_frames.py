"""Extract authentic source-video frames for manual thumbnail selection."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def binaries():
    candidates = list(Path(os.environ['LOCALAPPDATA']).glob('Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/bin/ffmpeg.exe'))
    if candidates:
        return str(candidates[0]), str(candidates[0].with_name('ffprobe.exe'))
    return shutil.which('ffmpeg'), shutil.which('ffprobe')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='+')
    parser.add_argument('--select', type=float, help='Archive one manually reviewed timestamp as a poster')
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'public-site/data/catalog.json').read_text(encoding='utf8'))
    ffmpeg, ffprobe = binaries()
    for item in catalog['items']:
        if item['id'] not in args.ids:
            continue
        media = next(m for m in item['media'] if m['src'].endswith(('.mp4', '.webm')))
        source = ROOT / 'pelican-web' / media['src'].lstrip('/')
        assert source.is_file()
        probe = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-show_entries',
            'format=duration', '-of', 'json', str(source)]))
        duration = float(probe['format']['duration'])
        if args.select is not None:
            assert len(args.ids) == 1, 'Select one record at a time'
            assert 0 <= args.select < duration
            poster_dir = ROOT / 'pelican-web/media/posters/2026-10-01'
            poster_dir.mkdir(parents=True, exist_ok=True)
            target = poster_dir / f'{item["originalId"]}-{args.select:.2f}s.jpg'
            assert not target.exists(), 'Preserve already archived poster'
            subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-ss', str(args.select),
                '-i', str(source), '-frames:v', '1', '-q:v', '2', str(target)], check=True)
            manifest = ROOT / 'site/thumbnail-overrides.json'
            overrides = json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else {}
            overrides[item['originalId']] = {
                'poster': '/' + target.relative_to(ROOT / 'pelican-web').as_posix(),
                'video': media['src'], 'source': media['source'], 'timestampSeconds': args.select,
                'durationSeconds': duration, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                'caption': f'原视频真实帧 · {args.select:.2f} 秒；替换片头/空白封面，原视频未改动',
                'captionEn': f'Authentic source-video frame at {args.select:.2f}s; original video unchanged',
                'reviewed': '2026-10-01',
            }
            manifest.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding='utf8')
            print('Selected:', target)
            continue
        times = sorted({round(duration * fraction, 2) for fraction in (0, .05, .1, .2, .35, .5, .65, .8, .9)})
        folder = ROOT / 'deploy-build/thumbnail-frame-review' / item['id']
        folder.mkdir(parents=True, exist_ok=True)
        sheet = Image.new('RGB', (1080, 3 * 220), '#dddace')
        draw = ImageDraw.Draw(sheet)
        for index, time in enumerate(times):
            target = folder / f'{time:.2f}s.jpg'
            subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(time),
                '-i', str(source), '-frames:v', '1', '-q:v', '2', str(target)], check=True)
            with Image.open(target) as image:
                image = ImageOps.contain(image.convert('RGB'), (350, 192))
                x, y = index % 3 * 360, index // 3 * 220
                sheet.paste(image, (x + (360 - image.width) // 2, y))
                draw.text((x + 10, y + 197), f'{time:.2f}s / {duration:.2f}s', fill='black')
        sheet.save(folder / 'contact.jpg')
        (folder / 'source.json').write_text(json.dumps({'id': item['id'], 'originalId': item['originalId'],
            'video': media['src'], 'source': media['source'], 'duration': duration, 'times': times}, indent=2), encoding='utf8')
        print(item['id'], duration, folder / 'contact.jpg')


if __name__ == '__main__':
    main()
