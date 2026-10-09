// Reviewed public X fMP4 VOD only. URLs/hashes are evidence, never commands.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';

const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const limit = 100 * 1024 * 1024;
function videoId(value) {
  const u = new URL(value);
  const match = u.pathname.match(/^\/amplify_video\/(\d+)\/(?:pl|vid|aud)\//);
  if (u.protocol !== 'https:' || u.hostname !== 'video.twimg.com' || u.port || u.username || u.password || u.hash || !match)
    throw Error('HLS requires a public HTTPS X video URL');
  return match[1];
}
function checkedPart(part, id, extension) {
  if (!part || videoId(part.url) !== id || !extension.test(new URL(part.url).pathname) || !/^[a-f0-9]{64}$/.test(part.sha256 || ''))
    throw Error('HLS requires matching video identity, original paths and pinned hashes');
}
export function validateHlsSpec(media, evidence) {
  const hls = media.hls;
  if (!hls || !/^[a-zA-Z0-9][a-zA-Z0-9._-]*\.mp4$/.test(media.filename || '') || media.url !== hls.master?.url || !/^[a-f0-9]{64}$/.test(media.sha256 || '') || media.svgFromTranscript || media.svgFromHardPrompts)
    throw Error('Reviewed HLS requires an MP4 assembly hash and original master URL');
  const id = videoId(media.url);
  checkedPart(hls.master, id, /\.m3u8$/);
  if (!hls.video) throw Error('HLS needs a complete video track');
  for (const [name, track] of Object.entries({video:hls.video, ...(hls.audio ? {audio:hls.audio} : {})})) {
    checkedPart(track.playlist, id, /\.m3u8$/);
    checkedPart(track.init, id, /\.mp4$/);
    if (!Array.isArray(track.segments) || !track.segments.length || track.segments.length > 2000)
      throw Error('HLS cannot import an initialization-only or unbounded track');
    for (const part of track.segments) checkedPart(part, id, /\.m4s$/);
    if (new Set(track.segments.map(x=>x.url)).size !== track.segments.length)
      throw Error('HLS fragments must be unique and ordered');
    const all = [track.playlist, track.init, ...track.segments];
    if (all.some(x=>!evidence.includes(x.url)) || !evidence.includes(hls.master.url))
      throw Error('Every HLS source must occur in reviewed public evidence');
    if (!track.init.url.includes(name==='video'?'/vid/':'/aud/')) throw Error('HLS track kind mismatch');
  }
}

const attributes = text => Object.fromEntries([...text.matchAll(/([A-Z0-9-]+)=(?:"([^"]*)"|([^,]*))/g)].map(x=>[x[1],x[2]??x[3]]));
function resolvePublic(uri, playlist) {
  const resolved = new URL(uri, playlist).href;
  if (videoId(resolved)!==videoId(playlist)) throw Error('HLS playlist crosses video identity');
  return resolved;
}
export function verifyHlsMaster(bytes, hls) {
  const lines=bytes.toString('utf8').trim().split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  if (lines[0]!=='#EXTM3U') throw Error('Invalid HLS master');
  const index=lines.findIndex((x,i)=>x.startsWith('#EXT-X-STREAM-INF:') && lines[i+1] && resolvePublic(lines[i+1],hls.master.url)===hls.video.playlist.url);
  if (index<0) throw Error('Selected video is absent from original master');
  const audioGroup=attributes(lines[index]).AUDIO;
  if (audioGroup) {
    const audio=lines.filter(x=>x.startsWith('#EXT-X-MEDIA:')).map(attributes).filter(x=>x.TYPE==='AUDIO' && x['GROUP-ID']===audioGroup);
    if (!hls.audio || !audio.some(x=>x.URI && resolvePublic(x.URI,hls.master.url)===hls.audio.playlist.url))
      throw Error('Selected original audio track is required');
  } else if (hls.audio) throw Error('Audio is not associated with the selected video');
}
export function verifyHlsTrack(bytes, track) {
  const lines=bytes.toString('utf8').trim().split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  if (lines[0]!=='#EXTM3U' || lines.at(-1)!=='#EXT-X-ENDLIST' || lines.filter(x=>x==='#EXT-X-ENDLIST').length!==1 || lines.some(x=>x.startsWith('#EXT-X-PLAYLIST-TYPE:') && x!=='#EXT-X-PLAYLIST-TYPE:VOD')) throw Error('Only complete ENDLIST VOD is supported');
  const allowed=/^#(?:EXTM3U|EXT-X-(?:VERSION|MEDIA-SEQUENCE|TARGETDURATION|PLAYLIST-TYPE|INDEPENDENT-SEGMENTS|MAP|ENDLIST)|EXTINF)(?::|$)/;
  if (lines.some(x=>x.startsWith('#') && !allowed.test(x))) throw Error('Unsupported encrypted, ranged, discontinuous or incomplete HLS');
  const maps=lines.filter(x=>x.startsWith('#EXT-X-MAP:')).map(attributes);
  if (maps.length!==1 || Object.keys(maps[0]).some(k=>k!=='URI') || resolvePublic(maps[0].URI,track.playlist.url)!==track.init.url)
    throw Error('Reviewed HLS initialization does not match playlist');
  const segments=[];
  let duration=0, pending=false;
  for (const line of lines.slice(1)) {
    if (line.startsWith('#EXTINF:')) {
      const seconds=Number(line.slice(8).split(',')[0]);
      if (pending || !Number.isFinite(seconds) || seconds<=0) throw Error('Invalid HLS segment duration');
      duration+=seconds; pending=true;
    } else if (!line.startsWith('#')) {
      if (!pending) throw Error('HLS segment lacks duration');
      segments.push(resolvePublic(line,track.playlist.url)); pending=false;
    }
  }
  if (pending || !segments.length || JSON.stringify(segments)!==JSON.stringify(track.segments.map(x=>x.url)))
    throw Error('Reviewed HLS fragments are missing, reordered or incomplete');
  return {duration, segments:segments.length};
}

async function download(part) {
  const response=await fetch(part.url,{redirect:'error',headers:{'User-Agent':'PelicanMap-Collector/1.0'},signal:AbortSignal.timeout(60000)});
  if (!response.ok) throw Error('HLS HTTP '+response.status+'; use authorized Chrome public read-only fallback for restricted access');
  if (Number(response.headers.get('content-length'))>limit) throw Error('Oversize HLS source');
  let size=0; const chunks=[];
  for await (const chunk of response.body) {
    size+=chunk.length;
    if (size>limit) throw Error('Oversize HLS source');
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}
async function preserve(file,bytes) {
  try {await fs.writeFile(file,bytes,{flag:'wx'});}
  catch(e) {if(e.code!=='EEXIST')throw e; if(hash(await fs.readFile(file))!==hash(bytes))throw Error('Refusing to replace HLS original');}
}
export async function assembleReviewedHls(media, evidence, directory, {getPart=download, ffmpeg=process.env.PELICAN_FFMPEG || 'ffmpeg'}={}) {
  validateHlsSpec(media,evidence);
  await fs.mkdir(directory,{recursive:true});
  const sources=[]; let size=0;
  async function read(part, filename) {
    const bytes=await getPart(part);
    size+=bytes.length;
    if (!bytes.length || size>limit || hash(bytes)!==part.sha256) throw Error('HLS source hash or total size mismatch');
    await preserve(path.join(directory,filename),bytes);
    sources.push({url:part.url,sha256:part.sha256,filename,bytes:bytes.length});
    return bytes;
  }
  const master=await read(media.hls.master,'master.m3u8');
  verifyHlsMaster(master,media.hls);
  const tracks={};
  for (const name of ['video','audio']) {
    const track=media.hls[name]; if(!track)continue;
    const playlist=await read(track.playlist,name+'.m3u8');
    const summary=verifyHlsTrack(playlist,track);
    const parts=[await read(track.init,name+'-init.mp4')];
    for(const [index,part] of track.segments.entries())parts.push(await read(part,name+'-'+index+'.m4s'));
    const bytes=Buffer.concat(parts), file=path.join(directory,name+'-original.mp4');
    await preserve(file,bytes);
    tracks[name]={...summary,sha256:hash(bytes),file};
  }
  const output=path.join(directory,'assembled.mp4');
  try {await fs.access(output);} catch(e) {
    if(e.code!=='ENOENT')throw e;
    const args=['-v','error','-n','-i',tracks.video.file];
    if(tracks.audio)args.push('-i',tracks.audio.file);
    args.push('-map','0:v:0'); if(tracks.audio)args.push('-map','1:a:0');
    args.push('-c','copy',output);
    const result=spawnSync(ffmpeg,args,{encoding:'utf8',windowsHide:true,timeout:120000});
    if(result.status!==0)throw Error('HLS stream-copy assembly failed '+(result.error?.message || result.stderr));
  }
  const bytes=await fs.readFile(output);
  if(hash(bytes)!==media.sha256)throw Error('Reviewed HLS assembly hash mismatch');
  const decode=spawnSync(ffmpeg,['-v','error','-xerror','-i',output,'-f','null','-'],{encoding:'utf8',windowsHide:true,timeout:120000});
  if(decode.status!==0)throw Error('Incomplete or invalid HLS decode '+(decode.error?.message || decode.stderr));
  return {bytes,extraction:{kind:'reviewed-hls-stream-copy',masterUrl:media.url,masterSha256:media.hls.master.sha256,
    sources,tracks:Object.fromEntries(Object.entries(tracks).map(([k,{file,...v}])=>[k,v])),assemblySha256:hash(bytes),fullDecodeVerified:true}};
}
