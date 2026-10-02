import test from 'node:test';
import assert from 'node:assert/strict';
import {loadLiveStats} from '../docs/assets/live-stats.mjs';

function mockFetcher({mismatch=false, unavailable=false}={}) {
  const requests=[];
  const fetcher=async url=>{
    requests.push(url);
    const p=url.searchParams;
    assert.equal(p.get('limit'),'1');
    let total=10;
    if(url.pathname.endsWith('timeline'))total=6;
    if(p.has('year'))total={'2023':2,'2024':3,'2025':5}[p.get('year')];
    if(p.has('source'))total={origin:2,zoo:1,wtf:3,community:4}[p.get('source')];
    if(mismatch&&p.get('source')==='community')total++;
    return {ok:!unavailable,json:async()=>({total,updated:'2025-10-02',items:[{date:'2023-06'}]})};
  };
  return {fetcher,requests};
}

test('live summary uses actual work totals, timeline subset and source/year partitions',async()=>{
  const {fetcher,requests}=mockFetcher();
  const result=await loadLiveStats(fetcher);
  assert.equal(result.works,10);
  assert.equal(result.timeline,6);
  assert.deepEqual(result.years.map(row=>row.key),['2023','2024','2025']);
  assert.equal(result.sources.reduce((sum,row)=>sum+row.total,0),10);
  assert.equal(requests.length,9);
});

test('an inconsistent release is rejected instead of showing mixed statistics',async()=>{
  await assert.rejects(loadLiveStats(mockFetcher({mismatch:true}).fetcher),/release changed/);
});

test('an unavailable API leaves the caller able to retain its labelled snapshot',async()=>{
  await assert.rejects(loadLiveStats(mockFetcher({unavailable:true}).fetcher),/unavailable/);
});
