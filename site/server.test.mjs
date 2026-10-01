import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createArchiveServer} from './server.mjs';

test('Node transport serves API, MCP, HEAD and bounds request size',async()=>{
  const server=createArchiveServer();
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  try {
    const response=await fetch(base+'/api/v1/specimens?limit=1');
    assert.equal(response.status,200);
    assert.equal((await response.json()).items.length,1);
    assert.equal(await (await fetch(base+'/api/v1/specimens',{method:'HEAD'})).text(),'');
    const mcp=await fetch(base+'/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream',Origin:'https://pelicanmap.aveniqa.com'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'transport-test',version:'1'}}})});
    assert.equal(mcp.status,200);
    assert.equal((await mcp.json()).result.serverInfo.name,'pelican-map');
    assert.equal((await fetch(base+'/mcp',{method:'POST',body:'x'.repeat(32769)})).status,413);
    assert.equal((await fetch(base+'/private')).status,404);
  } finally {await new Promise(resolve=>server.close(resolve));}
});
