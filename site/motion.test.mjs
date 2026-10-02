import test from 'node:test';
import assert from 'node:assert/strict';
import {motionAllowed,safeMotionSource} from './assets/motion.js';
import {renderCard} from './assets/browse.js';

test('motion is visible-only, background-safe and honours explicit pause and closed originals',()=>{
  const ready={enabled:true,visible:true,hidden:false};
  assert.equal(motionAllowed(ready),true);
  for(const override of [{enabled:false},{visible:false},{hidden:true},{closed:true},{manualPaused:true}])
    assert.equal(motionAllowed({...ready,...override}),false);
});

test('only archive assets and isolated local demos may play; external code never embeds',()=>{
  const origin='https://pelicanmap.aveniqa.com';
  assert.equal(safeMotionSource('/media/one.webm','video',origin),true);
  assert.equal(safeMotionSource('https://pelicanmap-demos.aveniqa.com/demos/one/','iframe',origin),true);
  for(const url of ['https://example.org/game','javascript:alert(1)','data:text/html,hi','https://user:pass@pelicanmap-demos.aveniqa.com/demos/x/','https://pelicanmap-demos.aveniqa.com.evil/demos/x/','https://pelicanmap-demos.aveniqa.com/admin'])
    assert.equal(safeMotionSource(url,'iframe',origin),false);
  assert.equal(safeMotionSource('/media/one.html','iframe',origin),false);
  assert.equal(safeMotionSource('https://x.com/video.mp4','video',origin),false);
});

test('all views retain a linked poster and actual lazy moving media; no format-only guesses',()=>{
  const item={id:'x',path:'/specimens/x/',thumbnail:'/media/poster.png',title:'Pelican',model:'Sol',modelNames:['Sol'],date:'2026-09-29',format:'animation',formatLabel:'Animation',caseNumber:8};
  for(const english of [false,true])for(const view of ['standard','compact','images'])for(const timeline of [false,true]) {
    const video=renderCard({...item,motionPreview:{type:'video',src:'/media/one.webm'}},{view,english,timeline});
    assert.ok(video.includes('href="/specimens/x/"'));
    assert.ok(video.includes('<img src="/media/poster.png"'));
    assert.ok(video.includes('data-motion-src="/media/one.webm"'));
    assert.ok(video.includes('autoplay muted loop playsinline preload="none"'));
    assert.ok(!video.includes('<video src='));
    const gif=renderCard({...item,motionPreview:{type:'image',src:'/media/one.gif'}},{view,english,timeline});
    assert.ok(gif.includes('data-motion-kind="image"'));
    const iframe=renderCard({...item,motionPreview:{type:'iframe',src:'https://pelicanmap-demos.aveniqa.com/demos/one/'}},{view,english,timeline});
    assert.ok(iframe.includes('sandbox="allow-scripts allow-same-origin"'));
    assert.ok(!iframe.includes('allow-top-navigation'));
    assert.ok(!renderCard(item,{view,english,timeline}).includes('data-motion-kind'));
  }
});
