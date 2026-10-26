import test from 'node:test';
import assert from 'node:assert/strict';
import {loadLiveStats} from '../docs/assets/live-stats.mjs';

function mockFetcher({mismatch=false, unavailable=false}={}) {
  const requests=[];
  const fetcher=async url=>{
    requests.push(url);
    assert.equal(url.pathname,'/api/v1/stats');
    assert.equal(url.search,'');
    return {ok:!unavailable,json:async()=>({works:10,timeline:6,derivatives:4,counts:{cases:10,timeline:6},updated:'2025-10-02',years:[{key:'2023',total:2},{key:'2024',total:3},{key:'2025',total:5}],sources:[{key:'origin',total:2},{key:'zoo',total:1},{key:'wtf',total:3},{key:'community',total:mismatch?5:4}]})};
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
  assert.equal(requests.length,1);
});

test('an inconsistent release is rejected instead of showing mixed statistics',async()=>{
  await assert.rejects(loadLiveStats(mockFetcher({mismatch:true}).fetcher),/release changed/);
});

test('an unavailable API leaves the caller able to retain its labelled snapshot',async()=>{
  await assert.rejects(loadLiveStats(mockFetcher({unavailable:true}).fetcher),/unavailable/);
});
