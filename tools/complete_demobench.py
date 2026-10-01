from archive_io import ROOT, WEB, AUDIT, records, text_for, fetch_batch
from bs4 import BeautifulSoup
import json
import shutil

base = 'https://demobench.janekm.com/'
files = ['audio-player.js', 'audio-worklet.js', 'machine-worker.js', 'machine.wasm', 'gpu-webgpu.js', 'gpu-compiler.js', 'app.js', 'studio.html', 'previews/pelican.png', 'previews/pelican.gif', 'previews/src/pelican.asm', 'examples/pelican.asm']
rows = fetch_batch([base + f for f in files], kind='demobench')
folder = WEB / 'demos/demobench'
folder.mkdir(exist_ok=True)
for name in files:
    row = rows[base + name]
    if row.get('error'):
        raise RuntimeError(row)
    dest = folder / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / row['file'], dest)
demo_data = json.loads(text_for(base + 'previews/data.js').split('window.DEMOS =', 1)[1].strip().removesuffix(';'))
pelican = [x for x in demo_data if x['id'] == 'pelican']
(folder / 'previews/data.js').write_text('window.DEMOS = ' + json.dumps(pelican) + ';\n', encoding='utf-8')
for name in ['index.html', 'studio.html']:
    raw = text_for(base if name == 'index.html' else base + name)
    soup = BeautifulSoup(raw, 'html.parser')
    for link in soup.select('link[href]'):
        if 'fonts.google' in link['href']:
            link.decompose()
    if name == 'studio.html':
        select = soup.select_one('#example-select')
        for option in list(select.find_all('option')):
            if option.get('value') != 'examples/pelican.asm':
                option.decompose()
        select.find('option')['selected'] = ''
    note = soup.new_tag('p')
    note['style'] = 'padding:12px;color:inherit;border:1px solid #888;position:relative;z-index:10'
    note.string = 'Pelican 本地存档：已保存预览、汇编源码与 WASM 运行时。交互运行需要 HTTP 服务；直接打开文件时可观看本地 GIF。'
    anchor = soup.new_tag('a', href='previews/pelican.gif')
    anchor.string = ' 打开动画预览'
    note.append(anchor)
    soup.body.insert(0, note)
    (folder / name).write_text(str(soup), encoding='utf-8')
data = json.loads((WEB / 'data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
item = next(x for x in data['timeline'] if x['id'] == 'x-janek-db32-4kb-2026-09-26')
item.update(media='demos/demobench/previews/pelican.gif', mediaStatus='local', local=True, demo='demos/demobench/index.html', mediaItems=[dict(src='demos/demobench/previews/pelican.gif', source=base, caption='原站提供的 Pelican 动画预览')], mediaNote='交互运行需要 HTTP 服务；GIF 可直接打开。')
next(x for x in data['repos'] if x['id'] == 'site-demobench').update(demo='demos/demobench/index.html', demoLabel='本地演示（HTTP）', notes='Pelican 4KB 演示、GIF、汇编源码及 WASM 运行时已存档；交互运行需 HTTP 服务。')
(WEB / 'data.js').write_text('window.PELICAN = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
print('DB32 Pelican: saved runtime, sources, poster and GIF')
