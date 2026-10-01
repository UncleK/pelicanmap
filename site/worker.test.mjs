import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';

async function worker() {
  assert.ok(fs.existsSync(new URL('./worker.mjs', import.meta.url)), 'Read-only public API has not been implemented');
  return (await import('./worker.mjs')).default;
}
test('API returns filtered, bounded records and original attribution', async () => {
  const w = await worker();
  const res = await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?q=gemini&limit=3'), {});
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.items.length, 3);
  assert.ok(data.total > 3);
  assert.ok(data.items.every(x => x.sourceUrl.startsWith('https://') && x.url.startsWith('https://pelicanmap.aveniqa.com/specimens/')));
});

test('batch totals agree with the UI while sample IDs remain accessible', async()=>{
  const w=await worker();
  const catalog=JSON.parse(fs.readFileSync(new URL('./catalog.json',import.meta.url)));
  const data=await (await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?limit=1'),{})).json();
  assert.equal(data.total,catalog.counts.cases);
  assert.equal(data.rawRecords,catalog.counts.cases);
  for (const lang of ['zh','en']) {
    const q=lang==='zh'?'OpenEnv 独立样本':'OpenEnv independent sample';
    const found=await (await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?lang='+lang+'&q='+encodeURIComponent(q)),{})).json();
    assert.equal(found.total,0);
    assert.equal(found.rawRecords,0);
    const detail=await (await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens/batch-openenv-2026-07-29?lang='+lang),{})).json();
    assert.equal(detail.id,'batch-openenv-2026-07-29');
    assert.equal(detail.referenceOnly,true);
    assert.equal(detail.sampleIds.length,138);
    const sample=await (await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens/'+detail.sampleIds[0]+'?lang='+lang),{})).json();
    assert.equal(sample.batch.id,detail.batch.id);
    const single=await (await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?lang='+lang+'&q='+encodeURIComponent(sample.title)),{})).json();
    assert.equal(single.total,0); assert.equal(single.items.length,0);
    const timeline=await (await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/timeline?lang='+lang+'&q=OpenEnv'),{})).json();
    assert.ok(!timeline.items.some(x=>x.referenceOnly));
  }
});
test('Invalid limits and unknown records never become successful empty pages', async () => {
  const w = await worker();
  for (const query of ['limit=100000', 'limit=-1', 'offset=1.5', 'q='+ 'a'.repeat(201)]) {
    assert.equal((await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?'+query), {})).status, 400);
  }
  assert.equal((await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens/missing'), {})).status, 404);
});

test('English API and MCP preserve source identity and return localized records', async () => {
  const w=await worker();
  const res=await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?lang=en&q=coast&limit=2'),{});
  const data=await res.json();
  assert.ok(data.items.length>0);
  const item=data.items[0];
  assert.ok(item.url.includes('/en/specimens/'));
  assert.ok(item.notes && !/[\u4e00-\u9fff]/.test(item.notes));
  const detail=await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens/'+item.id+'?lang=en'),{});
  assert.deepEqual(await detail.json(),item);
  assert.equal((await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens?lang=fr'),{})).status,400);
  const rpc=await w.fetch(new Request('https://pelicanmap.aveniqa.com/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'get_specimen',arguments:{id:item.id,lang:'en'}}})}),{});
  const payload=await rpc.json();
  assert.deepEqual(JSON.parse(payload.result.content[0].text),item);
});
test('API does not accept writes and timeline filtering stays in the requested year', async () => {
  const w = await worker();
  assert.equal((await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens', {method:'POST'}), {})).status, 405);
  const res = await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/timeline?year=2024&limit=50'), {});
  const data=await res.json();
  assert.ok(data.items.length > 0);
  assert.ok(data.items.every(x => x.timelineVisible && x.date.startsWith('2024')));
});

test('evolution API selects family, chronological order and representative flags',async()=>{
  const w=await worker();
  const catalog=JSON.parse(fs.readFileSync(new URL('./catalog.json',import.meta.url)));
  const data=await(await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/timeline?family=Gemini&sort=oldest&limit=50'),{})).json();
  assert.equal(data.total,catalog.items.filter(x=>x.timelineVisible && x.modelFamilies.includes('Gemini')).length);
  assert.ok(data.items.every(x=>x.modelNames.length===1 && !x.representativeOf && x.timelineVisible));
  assert.ok(data.items.every((x,i)=>!i || data.items[i-1].date<=x.date));
  const context=await(await w.fetch(new Request('https://pelicanmap.aveniqa.com/api/v1/specimens/elo-june-2025-3ea5a875'),{})).json();
  assert.equal(context.caseVisible,false);
  assert.equal(context.childIds.length,22);
  assert.equal(context.caseNumber,null);
});
test('MCP initializes and exposes only the archive read tools', async () => {
  const w = await worker();
  async function rpc(method,params) {
    const res=await w.fetch(new Request('https://pelicanmap.aveniqa.com/mcp', {method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})}),{});
    assert.equal(res.status,200);
    return res.json();
  }
  const init=await rpc('initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'archive-test',version:'1'}});
  assert.equal(init.result.serverInfo.name,'pelican-map');
  const list=await rpc('tools/list',{});
  assert.deepEqual(list.result.tools.map(x=>x.name).sort(),['get_specimen','get_timeline','search_specimens']);
  const search=await rpc('tools/call',{name:'search_specimens',arguments:{q:'Gemini',limit:2}});
  assert.ok(!search.result.isError);
  assert.equal(JSON.parse(search.result.content[0].text).items.length,2);
});
test('MCP instructions and bilingual resources share current counting and date policy',async()=>{
  const w=await worker();
  const catalog=JSON.parse(fs.readFileSync(new URL('./catalog.json',import.meta.url)));
  const rpc=async(method,params)=>{
    const res=await w.fetch(new Request('https://pelicanmap.aveniqa.com/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})}),{});
    assert.equal(res.status,200);
    return (await res.json()).result;
  };
  const init=await rpc('initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'editorial-check',version:'1'}});
  assert.equal(init.serverInfo.version,catalog.version);
  for(const text of ['counts.cases','counts.timeline','referenceOnly','datePrecision','not independently authenticated','untrusted'])assert.ok(init.instructions.includes(text));
  const resources=await rpc('resources/list',{});
  assert.deepEqual(resources.resources.map(x=>x.uri).sort(),['https://pelicanmap.aveniqa.com/en/llms.txt','https://pelicanmap.aveniqa.com/llms.txt']);
  for(const resource of resources.resources){
    const guide=(await rpc('resources/read',{uri:resource.uri})).contents[0].text;
    assert.ok(guide.includes(catalog.counts.cases+' independent works'));
    assert.ok(guide.includes(catalog.counts.timeline+' timeline representatives across media, a subset'));
    assert.ok(guide.includes('referenceOnly'));
    assert.ok(!guide.includes('Records overlap'));
    assert.ok(guide.includes(resource.uri.includes('/en/')?'counts.cases counts independent outputs':'counts.cases 是独立作品数'));
  }
});

test('Large source download is byte-identical and supports ranges across parts', async () => {
  const w=await worker();
  const original=fs.readFileSync(new URL('../pelican-web/repos/pedalican.zip',import.meta.url));
  const env={ASSETS:{async fetch(url){const name=new URL(url).pathname;return new Response(fs.readFileSync(new URL('../public-site'+name,import.meta.url)));}}};
  const full=await w.fetch(new Request('https://pelicanmap.aveniqa.com/downloads/pedalican.zip'),env);
  assert.equal(full.status,200);
  const actual=Buffer.from(await full.arrayBuffer());
  assert.equal(crypto.createHash('sha256').update(actual).digest('hex'),crypto.createHash('sha256').update(original).digest('hex'));
  const start=8*1024*1024-15,end=start+50;
  const range=await w.fetch(new Request('https://pelicanmap.aveniqa.com/downloads/pedalican.zip',{headers:{Range:'bytes='+start+'-'+end}}),env);
  assert.equal(range.status,206);
  assert.deepEqual(Buffer.from(await range.arrayBuffer()),original.subarray(start,end+1));
  const invalid=await w.fetch(new Request('https://pelicanmap.aveniqa.com/downloads/pedalican.zip',{headers:{Range:'bytes=999999999-'}}),env);
  assert.equal(invalid.status,416);
});
test('MCP rejects untrusted browser origins and excessive request bodies', async () => {
  const w=await worker();
  const cross=await w.fetch(new Request('https://pelicanmap.aveniqa.com/mcp',{method:'POST',headers:{Origin:'https://unrelated.example'}}),{});
  assert.equal(cross.status,403);
  const large=await w.fetch(new Request('https://pelicanmap.aveniqa.com/mcp',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json, text/event-stream'},body:'x'.repeat(40000)}),{});
  assert.equal(large.status,413);
});
