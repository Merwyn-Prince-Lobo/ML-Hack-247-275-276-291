'use strict';
const $ = id => document.getElementById(id);
const state = { connected:false, busy:false, connecting:false, trips:[], selected:null, result:null, endpoint:null, zoom:1, pan:[0,0], completed:new Set() };
const canvas=$('map'), ctx=canvas.getContext('2d');
let frame=null, timer=null, drag=null;
const icon=name=>`<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
try{$('api').value=localStorage.getItem('pathsnapApi')||'http://localhost:8000';}catch{$('api').value='http://localhost:8000';}

function endpoint(){const u=new URL($('api').value.trim());if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash||!['','/'].includes(u.pathname))throw Error('Enter a server address such as http://192.168.1.10:8000, without a path or credentials.');return u.origin;}
function status(message,error=false){$('status-text').textContent=message;$('status').classList.toggle('error',error);}
function connection(ok,label){state.connected=ok;$('server-dot').className=`status-dot ${ok?'online':''}`;$('server-label').textContent=label;$('run').disabled=!ok||!state.selected||state.busy||state.connecting;}
async function request(base,path,options={},timeout=120000){
  const abort=new AbortController(),clock=setTimeout(()=>abort.abort(),timeout);
  try{const r=await fetch(base+path,{...options,signal:abort.signal});let data;try{data=await r.json();}catch{throw Error('The server returned an unreadable response. Check the API address.');}if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:`Server request failed (HTTP ${r.status}).`);return data;}
  catch(e){if(e.name==='AbortError')throw Error('The server took too long to respond. Check Laptop 1 and try again.');if(e instanceof TypeError)throw Error('Cannot reach the API. Check its address, the running backend, and your network connection.');throw e;}
  finally{clearTimeout(clock);}
}
function clearResult(){
  state.result=null;state.completed.clear();state.zoom=1;state.pan=[0,0];
  for(const id of ['accuracy','f1','count','latency','arc-count','break-count','gap-count','precision','recall'])$(id).textContent='—';
  $('map-empty').hidden=false;$('map-trip-badge').hidden=true;$('map-scale').hidden=true;$('export').disabled=true;$('download-json').disabled=true;
  $('route-title').textContent='Your route, reconstructed';$('route-subtitle').textContent='Select a trip from the library to get started.';$('insights-badge').textContent='Awaiting route';
  $('coordinates').textContent='Offline geometry · no tile connection needed';$('observation-foot').textContent='Points in the selected journey';
  $('evaluation-note').textContent='Reference routes stay on the model server. The interface receives predictions and aggregate evaluation metrics.';
  $('response').textContent='Run a reconstruction to inspect its request and response summary.';$('session-label').textContent='Ready when you are';$('session-dot').className='status-dot';scheduleDraw();
}
function renderTrips(){
  const visible=state.trips.filter(t=>t.trip_id.includes($('search').value.trim()));$('trip-list').replaceChildren();
  for(const trip of visible){const id=trip.trip_id,b=document.createElement('button');b.type='button';b.className=`trip-button ${state.selected===id?'active':''}`;b.setAttribute('aria-label',`Select trip ${id}`);b.setAttribute('aria-pressed',String(state.selected===id));b.disabled=state.busy||state.connecting;
    b.innerHTML=`<span class="trip-symbol">${icon('route')}</span><span class="trip-meta"><strong></strong><small></small></span><span class="trip-state"></span>`;
    b.querySelector('strong').textContent=id;b.querySelector('small').textContent=state.completed.has(id)?'Reconstruction ready':'Ready to reconstruct';b.querySelector('.trip-state').textContent=state.completed.has(id)?'✓':state.selected===id?'›':'';b.addEventListener('click',()=>selectTrip(id));$('trip-list').append(b);}
  if(!visible.length){const p=document.createElement('p');p.className='list-placeholder';p.textContent=state.trips.length?'No trips match your search.':state.connected?'No complete trip inputs were found on the server.':'Connect your API to load trips.';$('trip-list').append(p);}
}
function selectTrip(id){if(state.busy||state.connecting)return;state.selected=id;$('selected-trip').textContent=`Trip ${id}`;$('run-hint').textContent=state.result?.trip_id===id?'Run again with the current model.':'Ready for reconstruction.';$('run').disabled=!state.connected;renderTrips();if(state.result&&state.result.trip_id!==id)status(`Trip ${id} selected. The map still shows the last completed result, trip ${state.result.trip_id}. Reconstruct to update.`);else if(state.connected)status(`Trip ${id} selected. Reconstruct its route to view the prediction and server-side evaluation.`);}
async function connect(){
  if(state.busy||state.connecting)return;state.connecting=true;$('connect').disabled=true;$('api').disabled=true;connection(false,'Connecting…');renderTrips();$('connection-message').textContent='Checking the model server…';
  try{const base=endpoint(),health=await request(base,'/health',{},15000),data=await request(base,'/trips',{},15000);
    if(!Array.isArray(data.trips)||!data.trips.every(t=>typeof t.trip_id==='string'&&/^\d{8}$/.test(t.trip_id)))throw Error('The API returned an invalid trip list.');
    clearResult();state.endpoint=base;state.trips=data.trips;state.selected=data.trips[0]?.trip_id||null;$('search').value='';
    $('trip-count').textContent=data.trips.length;$('nav-count').textContent=data.trips.length;
    const reserved=data.mode==='reserved-evaluator';$('mode').textContent=reserved?'Evaluator dataset':'Student-test · Development';$('footer-mode').textContent=reserved?'Reserved evaluator inputs · predictions computed on request':'Student-test development data · reserved evaluator trips not loaded';
    $('model-name').textContent=health.model||'Model connected';$('docs').href=base+'/docs';$('docs').hidden=false;connection(true,'Model server connected');$('connection-message').textContent=`${data.trips.length} trips available. Reference data stays on this server.`;
    try{localStorage.setItem('pathsnapApi',base);}catch{/* Optional persistence. */}
    status(state.selected?`Connected. Select a trip and reconstruct its route.`:'Connected, but no complete trip inputs are available. Check the dataset directory on Laptop 1.');
  }catch(e){connection(false,'Connection unavailable');$('server-dot').classList.add('error');$('connection-message').textContent=e.message;$('docs').hidden=true;status(e.message,true);}
  finally{state.connecting=false;$('connect').disabled=false;$('api').disabled=false;renderTrips();if(state.connected&&state.selected)selectTrip(state.selected);else{$('run').disabled=true;$('selected-trip').textContent=state.selected?`Trip ${state.selected}`:'Select a trip';}}
}
function validResult(r,id){
  const points=a=>Array.isArray(a)&&a.every(p=>Array.isArray(p)&&p.length>=2&&Number.isFinite(p[0])&&Number.isFinite(p[1]));
  return r.trip_id===id&&Number.isInteger(r.observations)&&r.observations>=2&&points(r.gps)&&points(r.snapped)&&r.gps.length===r.observations&&r.snapped.length===r.observations&&Array.isArray(r.predicted_arc_ids)&&r.predicted_arc_ids.length===r.observations&&['road_segments','route_segments'].every(k=>Array.isArray(r[k])&&r[k].every(s=>points(s)&&s.length===2))&&['route_arc_ids','route_break_indices','gap_reset_indices'].every(k=>Array.isArray(r[k]))&&Number.isFinite(r.inference_seconds);
}
const ratio=v=>Number.isFinite(v)?(v*100).toFixed(1)+'%':'N/A';
async function reconstruct(){
  if(!state.connected||!state.selected||state.busy)return;
  const id=state.selected,base=state.endpoint,started=performance.now();state.busy=true;$('run').disabled=true;$('connect').disabled=true;$('api').disabled=true;$('run-text').textContent='Reconstructing…';$('map-loading').hidden=false;$('session-label').textContent='Reconstruction in progress';$('elapsed').textContent='0.0s elapsed';renderTrips();
  timer=setInterval(()=>{$('elapsed').textContent=((performance.now()-started)/1000).toFixed(1)+'s elapsed';},100);status(`Processing trip ${id} on the model server. Large road networks can take a little longer.`);
  try{const r=await request(base,'/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({trip_id:id,evaluate:true})});if(!validResult(r,id))throw Error('The API result is incomplete or does not match the requested trip.');
    state.result=r;state.completed.add(id);state.zoom=1;state.pan=[0,0];$('accuracy').textContent=ratio(r.metrics?.top1_accuracy);$('f1').textContent=Number.isFinite(r.metrics?.macro_f1)?r.metrics.macro_f1.toFixed(3):'N/A';$('count').textContent=r.observations.toLocaleString();$('latency').textContent=r.inference_seconds.toFixed(2)+'s';$('observation-foot').textContent=`Matched points · Trip ${id}`;
    $('arc-count').textContent=new Set(r.predicted_arc_ids).size;$('break-count').textContent=r.route_break_indices.length;$('gap-count').textContent=r.gap_reset_indices.length;$('precision').textContent=ratio(r.metrics?.macro_precision);$('recall').textContent=ratio(r.metrics?.macro_recall);$('model-name').textContent=r.model;
    $('route-title').textContent=`Trip ${id}`;$('route-subtitle').textContent=`${r.observations.toLocaleString()} observations · road sequence reconstructed on the server`;$('insights-badge').textContent='Reconstruction complete';$('session-label').textContent='Journey reconstructed';$('session-dot').className='status-dot online';$('map-empty').hidden=true;$('map-trip-badge').hidden=false;$('map-trip-label').textContent=`Trip ${id} · prediction`;
    $('evaluation-note').textContent=r.metrics?(r.evaluation_note||'Metrics calculated by the server using its internal reference data.'):'Reference data is unavailable for this trip. The prediction is displayed; evaluation metrics are N/A.';
    $('export').disabled=false;$('download-json').disabled=false;$('run-hint').textContent='Ready to explore or export.';
    $('response').textContent=JSON.stringify({request:{trip_id:id,evaluate:true},trip_id:id,observations:r.observations,model:r.model,inference_seconds:r.inference_seconds,round_trip_seconds:Number(((performance.now()-started)/1000).toFixed(3)),metrics:r.metrics,gap_resets:r.gap_reset_indices.length,route_breaks:r.route_break_indices.length,evaluation_note:r.evaluation_note||'Reference metrics unavailable.'},null,2);
    status(`Trip ${id} reconstructed. ${r.route_break_indices.length} route breaks and ${r.gap_reset_indices.length} GPS gap resets. Drag to pan, scroll to zoom, or toggle a layer.`);
  }catch(e){status(`Trip ${id}: ${e.message}${state.result?` The map retains the last completed trip (${state.result.trip_id}).`:''}`,true);$('session-label').textContent='Reconstruction failed';$('session-dot').className='status-dot error';}
  finally{clearInterval(timer);state.busy=false;$('map-loading').hidden=true;$('run-text').textContent='Reconstruct route';$('connect').disabled=false;$('api').disabled=false;$('run').disabled=!state.connected||!state.selected;renderTrips();scheduleDraw();}
}

function scheduleDraw(){if(!frame)frame=requestAnimationFrame(()=>{frame=null;draw();});}
function draw(){
  const box=canvas.getBoundingClientRect(),w=box.width,h=box.height,dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#f0f3ee';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#e7ece3';ctx.lineWidth=1;ctx.beginPath();
  for(let x=(state.pan[0]%42+42)%42;x<w;x+=42){ctx.moveTo(x,0);ctx.lineTo(x,h);}for(let y=(state.pan[1]%42+42)%42;y<h;y+=42){ctx.moveTo(0,y);ctx.lineTo(w,y);}ctx.stroke();if(!state.result)return;
  const r=state.result;let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
  function extend(p){minX=Math.min(minX,p[0]);maxX=Math.max(maxX,p[0]);minY=Math.min(minY,p[1]);maxY=Math.max(maxY,p[1]);}
  r.gps.forEach(extend);for(const segment of r.route_segments)segment.forEach(extend);
  const cos=Math.max(.01,Math.cos((minY+maxY)/2*Math.PI/180)),cx=(minX+maxX)/2,cy=(minY+maxY)/2,scale=Math.min(Math.max(60,w-130)/Math.max((maxX-minX)*cos,1e-6),Math.max(60,h-100)/Math.max(maxY-minY,1e-6))*state.zoom;
  const project=p=>[(p[0]-cx)*cos*scale+w/2+state.pan[0],(cy-p[1])*scale+h/2+state.pan[1]];
  function lines(segments,color,lineWidth){ctx.strokeStyle=color;ctx.lineWidth=lineWidth;ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();for(const segment of segments){const a=project(segment[0]),b=project(segment[1]);if(Math.max(a[0],b[0])<0||Math.min(a[0],b[0])>w||Math.max(a[1],b[1])<0||Math.min(a[1],b[1])>h)continue;ctx.moveTo(...a);ctx.lineTo(...b);}ctx.stroke();}
  if($('layer-road').checked){lines(r.road_segments,'#d7dfd2',3);lines(r.road_segments,'#fbfcf8',1.5);}if($('layer-route').checked){lines(r.route_segments,'#bfd6b2',8);lines(r.route_segments,'#287655',3);}
  if($('layer-gps').checked){ctx.fillStyle='#648fc3';ctx.globalAlpha=.7;ctx.beginPath();for(const p of r.gps){const q=project(p);if(q[0]<0||q[0]>w||q[1]<0||q[1]>h)continue;ctx.moveTo(q[0]+1.7,q[1]);ctx.arc(q[0],q[1],1.7,0,Math.PI*2);}ctx.fill();ctx.globalAlpha=1;}
  function marker(p,label,color){const[x,y]=project(p);ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.font='600 9px Segoe UI';const size=ctx.measureText(label).width+14;ctx.fillStyle='#ffffffee';ctx.fillRect(x+11,y-10,size,20);ctx.fillStyle='#56724d';ctx.fillText(label,x+18,y+3);}
  marker(r.gps[0],'START','#2a805a');marker(r.gps[r.gps.length-1],'END','#5d85b7');
  $('coordinates').textContent=`${Math.abs(cy).toFixed(4)}° ${cy>=0?'N':'S'} · ${Math.abs(cx).toFixed(4)}° ${cx>=0?'E':'W'} · ${state.zoom.toFixed(1)}×`;
  const metresPerPixel=111195/scale,target=70*metresPerPixel,magnitude=10**Math.floor(Math.log10(target)),distance=[1,2,5,10].map(v=>v*magnitude).reduce((a,b)=>Math.abs(a-target)<Math.abs(b-target)?a:b);
  $('scale-label').textContent=distance>=1000?(distance/1000).toLocaleString()+' km':distance.toLocaleString()+' m';$('map-scale').style.width=(distance/metresPerPixel)+'px';$('map-scale').hidden=false;
}
function zoomBy(factor){state.zoom=Math.min(40,Math.max(.25,state.zoom*factor));scheduleDraw();}
function fit(){state.zoom=1;state.pan=[0,0];scheduleDraw();}
function download(value,name,type){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type})),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('export').addEventListener('click',()=>{const r=state.result;if(r)download({type:'FeatureCollection',features:[{type:'Feature',properties:{trip_id:r.trip_id,model:r.model,route_breaks:r.route_break_indices.length,gap_resets:r.gap_reset_indices.length,source:'PathSnap prediction'},geometry:{type:'MultiLineString',coordinates:r.route_segments}}]},`pathsnap-${r.trip_id}.geojson`,'application/geo+json');});
$('download-json').addEventListener('click',()=>{const r=state.result;if(!r)return;const{trip_id,observations,model,gps,predicted_arc_ids,route_arc_ids,route_segments,snapped,gap_reset_indices,route_break_indices,inference_seconds,metrics,evaluation_note}=r;download({trip_id,observations,model,gps,predicted_arc_ids,route_arc_ids,route_segments,snapped,gap_reset_indices,route_break_indices,inference_seconds,metrics,evaluation_note},`pathsnap-${r.trip_id}.json`,'application/json');});
$('connect').addEventListener('click',connect);$('run').addEventListener('click',reconstruct);$('search').addEventListener('input',renderTrips);
$('api').addEventListener('input',()=>{connection(false,'Address changed · reconnect');$('connection-message').textContent='Connect to load trips from this server.';$('docs').hidden=true;});$('api').addEventListener('keydown',e=>{if(e.key==='Enter')connect();});
for(const id of ['layer-road','layer-gps','layer-route'])$(id).addEventListener('change',scheduleDraw);
$('zoom-in').addEventListener('click',()=>zoomBy(1.3));$('zoom-out').addEventListener('click',()=>zoomBy(1/1.3));$('fit').addEventListener('click',fit);
canvas.addEventListener('wheel',e=>{e.preventDefault();zoomBy(Math.exp(-e.deltaY*.001));},{passive:false});
canvas.addEventListener('pointerdown',e=>{if(!state.result)return;drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(drag){state.pan[0]+=e.clientX-drag[0];state.pan[1]+=e.clientY-drag[1];drag=[e.clientX,e.clientY];scheduleDraw();}});
for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,()=>{drag=null;});canvas.addEventListener('dblclick',fit);
canvas.addEventListener('keydown',e=>{if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();if(['+','='].includes(e.key))zoomBy(1.3);else if(e.key==='-')zoomBy(1/1.3);else if(e.key==='0')fit();else{state.pan[0]+={ArrowLeft:30,ArrowRight:-30}[e.key]||0;state.pan[1]+={ArrowUp:30,ArrowDown:-30}[e.key]||0;scheduleDraw();}}});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('search').focus();}});new ResizeObserver(scheduleDraw).observe($('map-stage'));scheduleDraw();connect();
