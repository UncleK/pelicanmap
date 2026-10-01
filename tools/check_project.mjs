/** Check the public checkout's paths and bilingual catalog semantics. */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {isCase,inTimeline} from '../site/assets/browse.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const zh=JSON.parse(read('site/catalog.json'));
const en=JSON.parse(read('site/catalog.en.json'));
assert.deepEqual(zh.counts,en.counts);
assert.deepEqual(zh.items.map(x=>x.id).sort(),en.items.map(x=>x.id).sort());
assert.equal(zh.items.filter(isCase).length,zh.counts.cases);
assert.equal(zh.items.filter(inTimeline).length,zh.counts.timeline);
assert.equal(new Set(zh.items.map(x=>x.id)).size,zh.items.length);
let links=0;
for(const file of ['docs/index.html','docs/en/index.html']){
  const doc=read(file);
  assert.match(doc,/<html lang="(?:zh-CN|en)"/);
  assert.match(doc,/name="viewport"/);
  for(const match of doc.matchAll(/(?:href|src)="([^"#]+)"/g)){
    const target=match[1];
    if(/^(?:https?:|data:|mailto:)/.test(target))continue;
    assert.ok(!target.startsWith('/'),'Pages assets must support the repository subpath: '+target);
    let local=path.resolve(root,path.dirname(file),target.split('?')[0]);
    if(fs.existsSync(local)&&fs.statSync(local).isDirectory())local=path.join(local,'index.html');
    assert.ok(fs.existsSync(local),file+' → '+target);
    links++;
  }
  for(const key of ['cases','timeline','sourceIndex','benchmarkCollections'])assert.ok(doc.includes('>'+zh.counts[key].toLocaleString('en-US')+'</strong>'));
}
for(const p of ['README.md','README.en.md','NOTICE.md','CONTRIBUTING.md','LICENSE','docs/assets/github-cover.svg','docs/assets/social-preview.png'])assert.ok(fs.existsSync(path.join(root,p)),p);
assert.match(read('NOTICE.md'),/does not relicense/);
console.log(JSON.stringify({editions:2,works:zh.counts.cases,timeline:zh.counts.timeline,records:zh.items.length,localPageLinks:links}));
