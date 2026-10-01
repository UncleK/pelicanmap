import http from 'node:http';
import {Readable} from 'node:stream';
import fs from 'node:fs';
import path from 'node:path';
import worker from './worker.mjs';
let loadedCatalogs,loadedVersion;
function liveCatalogs(){
  const root=process.env.PELICAN_CATALOG_ROOT;
  if(!root)return undefined;
  const real=fs.realpathSync(root),file=path.join(real,'data/catalog.json');
  const version=real+':'+fs.statSync(file).mtimeMs;
  if(version!==loadedVersion){
    const zh=JSON.parse(fs.readFileSync(file,'utf8'));
    const en=JSON.parse(fs.readFileSync(path.join(real,'en/data/catalog.json'),'utf8'));
    if(zh.items.length!==en.items.length)throw Error('Catalog editions do not match');
    loadedCatalogs={zh,en};loadedVersion=version;
  }
  return loadedCatalogs;
}

// Only Nginx can reach this loopback service; never derive canonical URLs from Host.
export function createArchiveServer(){
  return http.createServer({requestTimeout:15000,headersTimeout:10000},async(req,res)=>{
    try {
      if(!req.url.startsWith('/api/')&&req.url.split('?')[0]!=='/mcp'){
        res.writeHead(404);res.end();return;
      }
      const chunks=[];let size=0;
      for await(const chunk of req){
        size+=chunk.length;
        if(size>32768){res.writeHead(413,{'Connection':'close'});res.end('Request too large');return;}
        chunks.push(chunk);
      }
      const method=req.method||'GET';
      const request=new Request('https://pelicanmap.aveniqa.com'+req.url,{
        method,headers:req.headers,
        ...(['GET','HEAD'].includes(method)?{}:{body:Buffer.concat(chunks)})
      });
      const response=await worker.fetch(request,{CATALOGS:liveCatalogs(),ASSETS:{fetch:()=>new Response(null,{status:404})}});
      res.writeHead(response.status,Object.fromEntries(response.headers));
      if(!response.body||method==='HEAD'){res.end();return;}
      Readable.fromWeb(response.body).on('error',()=>res.destroy()).pipe(res);
    } catch(err){
      console.error(JSON.stringify({event:'request_error',message:err.message}));
      if(!res.headersSent)res.writeHead(500,{'Content-Type':'application/json'});
      res.end('{"error":"Internal error"}');
    }
  });
}
