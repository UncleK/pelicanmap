// Presentation only. Never execute source text or guess motion from a format label.
export function motionAllowed({enabled, visible, hidden, closed=false, manualPaused=false}) {
  return enabled && visible && !hidden && !closed && !manualPaused;
}

export function safeMotionSource(src, kind, origin) {
  try {
    const url=new URL(src,origin);
    if(url.username || url.password)return false;
    const demo=url.origin==='https://pelicanmap-demos.aveniqa.com' && url.pathname.startsWith('/demos/');
    return kind==='iframe'?demo:(url.origin===origin || demo) && ['http:','https:'].includes(url.protocol);
  } catch {return false;}
}

export function bootMotion(main) {
  const english=document.documentElement.lang==='en';
  const t=(zh,en)=>english?en:zh;
  const preference=matchMedia('(prefers-reduced-motion: reduce)');
  let saved=null;
  try {saved=localStorage.getItem('pelican-autoplay');} catch {}
  let enabled=saved===null?!preference.matches:saved==='on';
  const managed=new Map(), targets=new Map();
  const toggle=document.createElement('button');
  toggle.type='button';toggle.className='floating-motion';toggle.dataset.motionToggle='';
  toggle.hidden=true;document.body.append(toggle);
  function label() {
    toggle.hidden=!managed.size;
    toggle.textContent=enabled?t('Ⅱ 暂停动态预览','Ⅱ Pause motion'):t('▶ 播放动态预览','▶ Play motion');
    toggle.setAttribute('aria-pressed',String(enabled));
    toggle.setAttribute('aria-label',enabled?t('自动播放已开启；暂停本页动态媒体','Autoplay is on; pause moving media on this page'):t('自动播放已暂停；播放本页动态媒体','Autoplay is paused; play moving media on this page'));
  }
  function layer(node,active) {
    const parent=node.closest('.motion-layer') || (node.classList.contains('motion-layer')?node:null);
    parent?.classList.toggle('motion-active',active);
  }
  function freezeImage(node,state) {
    const poster=node.dataset.motionPoster;
    if(poster && poster!==node.dataset.motionSrc) {
      if(node.getAttribute('src')!==poster)node.src=poster;
      return;
    }
    if(!node.complete || !node.naturalWidth)return;
    if(!state.canvas) {
      state.canvas=document.createElement('canvas');
      state.canvas.className='motion-freeze';state.canvas.setAttribute('role','img');state.canvas.setAttribute('aria-label',node.alt);
      node.after(state.canvas);
    }
    const scale=Math.min(1,1280/node.naturalWidth,960/node.naturalHeight);
    state.canvas.width=Math.round(node.naturalWidth*scale);state.canvas.height=Math.round(node.naturalHeight*scale);
    try {state.canvas.getContext('2d').drawImage(node,0,0,state.canvas.width,state.canvas.height);} catch {return;}
    state.canvas.hidden=false;node.classList.add('motion-frozen');node.removeAttribute('src');
  }
  function pause(node,state) {
    if(state.kind==='video') {
      if(!node.paused){state.internalPauses++;node.pause();}
    } else if(state.kind==='image')freezeImage(node,state);
    else {
      // Cross-origin source code is left byte-identical. Blank inactive previews
      // rather than trying to inject code into them. Playable detail frames are
      // intentionally not managed, so a user's game progress is not reset.
      if(node.getAttribute('src') && node.getAttribute('src')!=='about:blank')node.src='about:blank';
      layer(node,false);
    }
    state.active=false;
  }
  function update(node,state) {
    const closed=!!node.closest('details:not([open])');
    const active=motionAllowed({enabled,visible:state.visible,hidden:document.hidden,closed,manualPaused:state.manualPaused});
    if(active===state.active)return;
    if(!active){pause(node,state);return;}
    state.active=true;
    const src=node.dataset.motionSrc;
    if(state.kind==='video') {
      node.muted=true;node.loop=true;node.playsInline=true;
      if(node.getAttribute('src')!==src)node.src=src;
      node.play().catch(()=>{
        if(!state.active)return;
        node.dataset.motionBlocked='true';
        const card=node.closest('.card');
        if(card && !state.startButton) {
          state.startButton=document.createElement('button');
          state.startButton.type='button';state.startButton.className='motion-start';
          state.startButton.textContent=t('▶ 播放','▶ Play');
          state.startButton.addEventListener('click',()=>{
            enabled=true;state.manualPaused=false;state.active=false;label();update(node,state);
          });
          card.append(state.startButton);
        }
      });
    } else if(state.kind==='image') {
      if(state.canvas)state.canvas.hidden=true;
      node.classList.remove('motion-frozen');
      if(node.getAttribute('src')!==src)node.src=src;
    } else if(node.getAttribute('src')!==src)node.src=src;
  }
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries)for(const node of targets.get(entry.target)||[]) {
      const state=managed.get(node);
      if(!state)continue;
      state.visible=entry.isIntersecting && entry.intersectionRect.width>8 && entry.intersectionRect.height>8;
      update(node,state);
    }
  },{threshold:[0,0.01]});
  const size=new ResizeObserver(entries=>{
    for(const {target} of entries) {
      const rect=target.getBoundingClientRect();
      for(const node of targets.get(target)||[])if(node.dataset.motionKind==='iframe' && node.closest('.card-cover')) {
        const scale=Math.min(rect.width/1000,rect.height/760);
        node.style.transform=`translate(-50%,-50%) scale(${scale})`;
      }
    }
  });
  function watch() {
    for(const [node,state] of managed)if(!node.isConnected) {
      pause(node,state);managed.delete(node);
      const members=targets.get(state.target);members?.delete(node);
      if(!members?.size){observer.unobserve(state.target);size.unobserve(state.target);targets.delete(state.target);}
    }
    for(const node of main.querySelectorAll('[data-motion-kind]')) {
      if(managed.has(node) || !safeMotionSource(node.dataset.motionSrc,node.dataset.motionKind,location.origin))continue;
      // A paused GIF/SVG may be replaced by a frozen canvas. Observe its stable
      // figure, not the hidden image, otherwise a detail animation never resumes.
      const target=node.closest('.card-cover')||(node.dataset.motionKind==='image'?node.closest('figure'):null)||node;
      const state={kind:node.dataset.motionKind,target,active:false,visible:false,internalPauses:0,manualPaused:false};
      managed.set(node,state);
      if(!targets.has(target)){targets.set(target,new Set());observer.observe(target);size.observe(target);}
      targets.get(target).add(node);
      if(state.kind==='video') {
        node.addEventListener('pause',()=>{
          if(state.internalPauses){state.internalPauses--;return;}
          if(state.active){state.manualPaused=true;state.active=false;}
        });
        node.addEventListener('playing',()=>{
          state.manualPaused=false;state.active=true;layer(node,true);
          delete node.dataset.motionBlocked;state.startButton?.remove();state.startButton=null;
        });
        node.addEventListener('error',()=>layer(node,false));
      } else if(state.kind==='image')node.addEventListener('load',()=>{if(!state.active)freezeImage(node,state);});
      else node.addEventListener('load',()=>layer(node,state.active));
      // Close attachments, background tabs and reduced-motion pages never begin
      // playing merely because their original HTML has an autoplay attribute.
      pause(node,state);
    }
    label();
  }
  const refresh=()=>{for(const [node,state] of managed)update(node,state);};
  toggle.addEventListener('click',()=>{
    enabled=!enabled;
    for(const state of managed.values())state.manualPaused=false;
    try {localStorage.setItem('pelican-autoplay',enabled?'on':'off');} catch {}
    label();refresh();
  });
  preference.addEventListener('change',()=>{
    let explicit=null;try {explicit=localStorage.getItem('pelican-autoplay');} catch {}
    if(explicit===null){enabled=!preference.matches;label();refresh();}
  });
  document.addEventListener('visibilitychange',refresh);
  window.addEventListener('pagehide',()=>{for(const [node,state] of managed)pause(node,state);});
  window.addEventListener('pageshow',refresh);
  main.addEventListener('toggle',refresh,true);
  let pending=false;
  new MutationObserver(()=>{
    if(pending)return;pending=true;
    requestAnimationFrame(()=>{pending=false;watch();});
  }).observe(main,{childList:true,subtree:true});
  watch();
}

if(typeof document!=='undefined')bootMotion(document.querySelector('main'));
