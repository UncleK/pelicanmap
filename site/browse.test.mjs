import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { selectRecords, paginate, pageHref } from './assets/browse.js';
import * as browse from './assets/browse.js';

const records = Array.from({length: 75}, (_, i) => ({
  id: `case-${i}`, date: `2026-09-${String(i % 30 + 1).padStart(2, '0')}`,
  kind: 'timeline', title: `Pelican ${i}`, model: 'Sol', author: 'Author',
  modelTimeline:{key:'sol',releaseDate:'2026-09-22',status:'verified-release'},
  notes: '', promptCategory: '', source: 'community', format: 'animation',
  interactive: i < 4, demoUrl: i < 4 ? `https://pelicanmap-demos.aveniqa.com/demos/${i}/` : '',
}));

test('timeline defaults to newest and supports old-to-new and year filtering', () => {
  const latest = selectRecords(records, {scope: 'timeline'});
  assert.equal(latest[0].date, '2026-09-30');
  assert.equal(selectRecords(records, {scope: 'timeline', sort: 'oldest'})[0].date, '2026-09-01');
  assert.equal(selectRecords(records, {scope: 'timeline', year: '2025'}).length, 0);
});
test('late artwork stays with its model release; unknowns last and folding exact versions only',()=>{
  const old={...records[0],id:'late-old',date:'2026-10-02',model:'Gemini 3.8 Flash',modelTimeline:{key:'gemini38',releaseDate:'2026-09-02'}};
  const newer={...records[0],id:'early-new',date:'2026-09-29',model:'GPT-6.1 Sol',modelTimeline:{key:'sol61',releaseDate:'2026-09-29'}};
  const another={...old,id:'earlier-old',date:'2026-09-03'};
  const unknown={...old,id:'unknown',model:'Gemini mystery',modelTimeline:{key:'unknown',status:'release-unverified'}};
  const rows=[old,unknown,newer,another];
  assert.deepEqual(selectRecords(rows,{scope:'timeline'}).map(x=>x.id),['early-new','late-old','earlier-old','unknown']);
  assert.deepEqual(selectRecords(rows,{scope:'timeline',sort:'oldest'}).map(x=>x.id),['earlier-old','late-old','early-new','unknown']);
  for(const sort of ['newest','oldest']) {
    assert.deepEqual(selectRecords(rows,{sort}).map(x=>x.id),selectRecords(rows,{scope:'timeline',sort}).map(x=>x.id));
    assert.deepEqual(selectRecords(rows,{scope:'gallery',sort}).map(x=>x.id),[]);
  }
  assert.equal(selectRecords(rows,{year:'2026'}).length,4);
  assert.deepEqual(selectRecords(rows,{scope:'timeline',year:'unknown'}).map(x=>x.id),['unknown']);
  const grouped=browse.groupModelRecords(selectRecords(rows,{scope:'timeline'}));
  assert.equal(grouped.length,3);
  assert.equal(grouped.reduce((n,x)=>n+x.modelMembers.length,0),4);
  assert.equal(rows[0].date,'2026-10-02');
});
test('all works includes non-representatives on the shared release axis but retains artwork-year filters',()=>{
  const rows=[
    {...records[0],id:'old',date:'2026-10-02',modelTimeline:{key:'old',releaseDate:'2025-09-01'}},
    {...records[0],id:'new',date:'2026-09-29',modelTimeline:{key:'new',releaseDate:'2026-09-29'}},
    {...records[0],id:'extra',date:'2026-09-20',kind:'gallery',timelineVisible:false,modelTimeline:{key:'old',releaseDate:'2025-09-01'}}
  ];
  assert.deepEqual(selectRecords(rows).map(x=>x.id),['new','old','extra']);
  assert.deepEqual(selectRecords(rows,{sort:'oldest'}).map(x=>x.id),['extra','old','new']);
  assert.deepEqual(selectRecords(rows,{scope:'gallery'}).map(x=>x.id),['extra']);
  assert.equal(selectRecords(rows,{year:'2026'}).length,3);
  assert.deepEqual(selectRecords(rows,{scope:'timeline',year:'2025'}).map(x=>x.id),['old']);
  assert.equal(selectRecords(rows,{year:'2025'}).length,0);
});

test('estimated positions join both browsing axes without fabricating a release date',()=>{
  const verified={...records[0],id:'sol61',date:'2026-09-29',modelTimeline:{key:'sol61',releaseDate:'2026-09-29',sortDate:'2026-09-29'}};
  const inferred={...records[0],id:'fable',date:'2026-10-02',modelTimeline:{key:'fable',status:'inferred-position',sortDate:'2026-10',sortBasis:'earliest-source-work'}};
  for(const scope of ['', 'timeline']) {
    assert.deepEqual(selectRecords([verified,inferred],{scope}).map(x=>x.id),['fable','sol61']);
    assert.deepEqual(selectRecords([verified,inferred],{scope,sort:'oldest'}).map(x=>x.id),['sol61','fable']);
  }
  assert.equal(browse.timelineMonth(inferred),'2026-10');
  assert.equal(inferred.modelTimeline.releaseDate,undefined);
  assert.deepEqual(selectRecords([verified,inferred],{scope:'timeline',year:'unknown'}).map(x=>x.id),['fable']);
});
test('play selects only verified local interactions and collapses shared demos', () => {
  const mixed = [...records, {...records[0], id: 'duplicate'}, {...records[1], id: 'remote', demoUrl: 'https://example.com/game'}];
  assert.equal(selectRecords(mixed, {scope: 'play'}).length, 4);
});

test('legacy play remains accessible independently of the single-model artwork count', () => {
  const game={...records[0],id:'legacy',caseVisible:false,caseNumber:null};
  const normal={...records[1],id:'canonical'};
  const duplicate={...normal,id:'repost',caseVisible:false,canonicalId:'canonical'};
  const selected=selectRecords([game,normal,duplicate],{scope:'play'});
  assert.deepEqual(new Set(selected.map(x=>x.id)),new Set(['legacy','canonical']));
  assert.equal(browse.groupRecords(selected,true).length,2);
  assert.ok(!browse.renderCard({...game,modelNames:[],path:'/specimens/legacy/',thumbnail:'/media/test.png'},{view:'standard'}).includes('#null'));
  assert.equal(selectRecords([game],{}).length,0);
});
test('filtering stays paged and compact view shows more records', () => {
  const selected = selectRecords(records, {q: 'pelican'});
  assert.equal(paginate(selected, 2, false).items.length, 24);
  assert.equal(paginate(selected, 1, true).items.length, 48);
  assert.equal(paginate(selected, 99, false).page, 4);
  assert.equal(paginate([], 99, false).page, 1);
});
test('page links retain year, order and compact preferences', () => {
  const href = pageHref('/timeline/', 3, {year: '2026', sort: 'oldest', view: 'compact', q: 'Sol'});
  const url = new URL(href, 'https://pelicanmap.aveniqa.com');
  assert.equal(url.searchParams.get('page'), '3');
  assert.equal(url.searchParams.get('year'), '2026');
  assert.equal(url.searchParams.get('sort'), 'oldest');
  assert.equal(url.searchParams.get('view'), 'compact');
});

test('view button cycles standard, compact, images, then standard', () => {
  assert.equal(typeof browse.nextView, 'function');
  assert.equal(browse.nextView('standard'), 'compact');
  assert.equal(browse.nextView('compact'), 'images');
  assert.equal(browse.nextView('images'), 'standard');
  assert.equal(browse.nextView('unknown'), 'compact');
});
test('view label describes the current view in both languages, not the next view',()=>{
  for(const [view,zh,en] of [['standard','标准视图','Standard view'],['compact','紧凑视图','Compact view'],['images','纯图片','Images only']]) {
    assert.equal(browse.viewLabel(view),zh);
    assert.equal(browse.viewLabel(view,true),en);
    assert.notEqual(browse.viewLabel(view),browse.viewLabel(browse.nextView(view)));
  }
  assert.equal(browse.viewLabel('unknown'),'标准视图');
});

test('desktop image-only pages match compact row count and clamp the last page', () => {
  assert.equal(paginate(records, 1, 'standard').size, 24);
  assert.equal(paginate(records, 1, 'compact').size, 48);
  assert.equal(paginate(records, 1, 'images').items.length, 60);
  assert.equal(paginate(records, 99, 'images').page, 2);
  assert.equal(paginate(records, 99, 'images').items.length, 15);
  assert.equal(new URL(pageHref('/specimens/',2,{view:'images',year:'2026'}),'https://pelicanmap.aveniqa.com').searchParams.get('view'),'images');
});

test('image pagination keeps the compact row budget at each responsive density', () => {
  const many=Array.from({length:251},(_,i)=>({...records[0],id:String(i)}));
  for(const [width,compactColumns,imageColumns] of [[320,2,4],[390,2,4],[400,2,5],[430,2,5],[720,2,5],[800,3,3],[900,3,3],[1280,4,5]]) {
    const compact=paginate(many,1,'compact',width), images=paginate(many,1,'images',width);
    assert.equal(images.size/imageColumns,compact.size/compactColumns,width);
    const pages=Array.from({length:images.pages},(_,i)=>paginate(many,i+1,'images',width).items).flat();
    assert.deepEqual(pages.map(x=>x.id),many.map(x=>x.id));
    assert.equal(paginate(many,999,'images',width).page,images.pages);
  }
});

test('image-only cards retain the accessible image link without metadata', () => {
  assert.equal(typeof browse.renderCard, 'function');
  const item={...records[0],path:'/specimens/example/',thumbnail:'/media/example.webp',formatLabel:'Animation'};
  const html=browse.renderCard(item,{view:'images'});
  assert.ok(html.includes('href="/specimens/example/"'));
  assert.ok(html.includes('alt="Pelican 0"'));
  assert.ok(html.includes('loading="lazy"'));
  assert.ok(!html.includes('card-body'));
  assert.ok(!html.includes('media-label'));
  assert.ok(!html.includes('2026-09-01'));
  assert.ok(browse.renderCard(item,{view:'standard'}).includes('card-body'));
  assert.ok(browse.renderCard(item,{view:'compact'}).includes('media-label'));
});

test('explicit batches count once, preserve single sample hits and never merge by model', () => {
  const batch={id:'experiment',title:'A batch',description:'Reviewed runs',sourceUrl:'https://example.com/dataset',path:'/collections/experiment/',total:3,models:1,modelLabels:['Sol']};
  const members=records.slice(0,3).map(x=>({...x,batch,media:[{src:'/media/test.png'}],thumbnail:'/media/test.png'}));
  const grouped=browse.groupRecords([...members,records[5]]);
  assert.equal(grouped.length,2);
  assert.equal(grouped[0].id,'batch-experiment');
  assert.equal(grouped[0].matchingSamples,3);
  assert.equal(grouped[0].path,batch.path);
  assert.equal(grouped[0].sampleIds.length,3);
  assert.equal(browse.groupRecords([members[1]])[0].id,members[1].id);
  assert.equal(browse.groupRecords(records).length,75);
  const partial=browse.groupRecords(members.slice(0,2))[0];
  assert.equal(partial.matchingSamples,2);
  assert.equal(partial.batch.total,3);
  for (const view of ['standard','compact','images']) {
    const html=browse.renderCard(grouped[0],{view});
    assert.ok(html.includes('href="/collections/experiment/"'));
    assert.ok(html.includes('batch-badge'));
    assert.ok(view==='images'?!html.includes('card-body'):html.includes('1 个案例'));
  }
});

test('card footer shows global number and every model, never the old record labels', () => {
  const item={...records[0],caseNumber:674,model:'Sol / Astra (author-reported)',modelNames:['Sol','Astra'],path:'/specimens/test/',thumbnail:'/media/test.webp'};
  for (const english of [false,true]) for (const view of ['standard','compact']) {
    const html=browse.renderCard(item,{view,english});
    assert.ok(html.includes('specimen-card'));
    assert.ok(html.includes('>#674</span>'));
    assert.ok(html.includes('class="model-name">Sol</span>'));
    assert.ok(html.includes('class="model-name">Astra</span>'));
    assert.ok(!html.includes('View record'));
    assert.ok(!html.includes('查看标本'));
    assert.ok(!html.includes('Timeline record'));
    assert.ok(html.includes('class="card-body" tabindex="0"'));
    assert.ok(html.includes('</p></div><div class="card-foot">'));
  }
  const image=browse.renderCard(item,{view:'images'});
  assert.ok(!image.includes('card-foot'));
  assert.ok(!image.includes('#674'));
  assert.ok(browse.renderCard({...item,modelNames:[]},{english:true}).includes('Model not specified'));
});

test('benchmark references never enter main browsing, grouping or counts',()=>{
  const reference={...records[0],id:'reference',kind:'reference',referenceOnly:true};
  assert.deepEqual(selectRecords([reference,...records]),selectRecords(records));
  assert.equal(selectRecords([reference],{scope:'timeline'}).length,0);
  assert.equal(browse.groupRecords([reference,...records]).length,records.length);
  assert.equal(browse.groupRecords([reference],true).length,1);
});

test('real collage outputs count individually but show seven timeline cards',()=>{
  const catalog=JSON.parse(fs.readFileSync(new URL('./catalog.json',import.meta.url),'utf8'));
  const members=catalog.items.filter(x=>x.parentId==='reddit-emu001-codex-pelican-matrix-2026-09-26');
  assert.equal(selectRecords(members).length,35);
  assert.equal(selectRecords(members,{scope:'timeline'}).length,7);
  assert.ok(selectRecords(members,{scope:'timeline'}).every(x=>x.originalLevel==='medium'));
  assert.equal(selectRecords(catalog.items).length,catalog.counts.cases);
  assert.equal(selectRecords(catalog.items,{scope:'timeline'}).length,catalog.counts.timeline);
  const gemini=selectRecords(catalog.items,{scope:'timeline',family:'Gemini',sort:'oldest'});
  assert.ok(gemini.length>10);
  assert.ok(gemini.every(x=>x.modelFamilies.includes('Gemini')));
  assert.ok(gemini.every((x,i)=>!i || browse.compareTimeline(gemini[i-1],x,'oldest')<=0));
  const html=browse.renderCard(gemini[0],{timeline:true});
  assert.ok(html.includes('timeline-card'));
  assert.ok(html.includes('class="timeline-meta"'));
  assert.ok(html.indexOf('class="timeline-model"')<html.indexOf('class="timeline-date"'));
  assert.ok(html.includes('<time class="timeline-date"'));
  assert.ok(!html.includes('card-body'));
  assert.ok(!html.includes('card-foot'));
});

test('both card types share number/model/date footer; source sits at image right',()=>{
  const item={...records[0],caseNumber:819,modelNames:['Claude Opus 5.5'],model:'Claude Opus 5.5',sourceLabel:'社区记录',path:'/specimens/test/',thumbnail:'/media/test.webp'};
  for(const english of [false,true])for(const timeline of [false,true]){
    const html=browse.renderCard(item,{english,timeline});
    const number=html.indexOf('class="case-number"'),model=html.indexOf(timeline?'class="timeline-model"':'class="card-models"'),date=html.indexOf(timeline?'class="timeline-date"':'class="card-date"');
    assert.ok(number<model && model<date);
    assert.ok(html.includes('>#819</span>'));
    assert.ok(html.includes('datetime="2026-09-01"'));
    assert.ok(!html.includes('class="card-meta"'));
    if(!timeline){
      assert.ok(html.indexOf('class="source-label"')<number);
      assert.ok(!html.slice(number).includes('社区记录'));
    }
  }
});

test('text regions share their row maximum and keep long descriptions scrollable',()=>{
  assert.equal(browse.rowTextHeight([86,110,95]),110);
  assert.equal(browse.rowTextHeight([88,92]),92);
  assert.equal(browse.rowTextHeight([80,400,96]),190);
  assert.equal(browse.rowTextHeight([80,400,96],140),140);
  assert.equal(browse.rowTextHeight([15,NaN]),72);
  assert.equal(browse.rowTextHeight([86.2,105.4]),106);
});
