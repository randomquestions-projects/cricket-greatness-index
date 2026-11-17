/* Source-free cricket viewer. All records arrive only as bounded server-derived results.
   The browser NEVER downloads the raw innings file, rankings database or source records. */
(()=>{'use strict';
const $=q=>document.querySelector(q);
const FORMATS=['test','odi','t20i'], COMBOS=['test_odi','all_three'], ALL=[...FORMATS,...COMBOS];
const LABEL={overview:'Overview',test:'Test Cricket',odi:'One-Day Internationals',
 t20i:'T20 Internationals',test_odi:'Tests + ODIs',all_three:'All Three Formats',
 compare:'Batter Comparison',matches:'Match Explorer',
 methodology:'Index Methodology',coverage:'Data & Coverage'};
const METRICS={jawsPercentile:'JAWS-inspired percentile',quality:'Era-adjusted quality',
 teamCarry:'Team carry',careerGreatness:'Career greatness',peakQuality:'Peak quality'};
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const N=(v,d=1)=>v==null||!Number.isFinite(+v)?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:d});
const I=v=>N(v,0);
const state={view:'overview',format:'test',metric:'jawsPercentile',search:'',country:'',
 page:0,matchFormat:'odi',matchPage:0,matchSearch:'',matchOpposition:'',
 first:null,second:null,compareFormat:'test',compareSearch:'',activeCompareSide:'first'};
let meta=null,requestSerial=0,searchTimer;
function apiURL(path,params={}){
 const base=String(window.CRICKET_OUTPUTS_API_BASE||'');
 let u;try{u=new URL(base)}catch{throw new Error('Results API is not configured')}
 if(u.protocol!=='https:'||!/(^|\.)execute-api\.[a-z0-9-]+\.amazonaws\.com$/.test(u.hostname)
    ||u.username||u.password||u.search||u.hash||u.pathname!=='/')
  throw new Error('Unapproved results API endpoint');
 let target=new URL('/v1/cricket/'+path,u);
 for(const [k,v] of Object.entries(params))if(v!==''&&v!=null)target.searchParams.set(k,String(v));
 return target.toString();
}
async function get(path,params={}){
 const res=await fetch(apiURL(path,params),{cache:'no-store',headers:{Accept:'application/json'}});
 if(!res.ok)throw new Error('Results service unavailable ('+res.status+')');
 const data=await res.json();
 return data;
}
function hero(title,desc){
 $('#page-header').innerHTML='<div class="eyebrow">INDEPENDENT CRICKET RESEARCH · OUTPUTS ONLY</div>'+
 '<h1>'+title+'</h1><p>'+E(desc)+'</p>';
}
function showError(area,err){if(area)area.innerHTML='<div class="callout">'+E(err.message||err)+'</div>'}
function currentRoute(){
 const r=location.hash.replace(/^#/,'').split('/')[0];
 return LABEL[r]?r:'overview';
}
function navigation(v){
 $('#breadcrumb').textContent=LABEL[v].toUpperCase();
 document.querySelectorAll('[data-view]').forEach(a=>a.classList.toggle('active',a.dataset.view===v));
 $('#sidebar').classList.remove('open');$('#menu-button').setAttribute('aria-expanded','false');
}
function panel(title,body){return '<section class="section"><div class="section-head"><h2>'+E(title)+'</h2></div>'+body+'</section>'}
function table(head,rows){
 return '<div class="table-scroller"><table><thead><tr>'+head.map(s=>'<th>'+E(s)+'</th>').join('')+
 '</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
}
function overview(){
 hero('Who was <em>truly</em> the greatest?',
   'Explore era-adjusted Test, ODI and T20I batting research. No downloadable historical scorecards or raw match database.');
 const formats=FORMATS.map(f=>meta.formats[f]||{});
 const blocks=[
 ['Tests analyzed',formats[0].observedDistinctMatches],['ODIs analyzed',formats[1].observedDistinctMatches],
 ['T20Is analyzed',formats[2].observedDistinctMatches],
 ['Eligible batters',formats.map(f=>I(f.qualifiedPlayers)).join(' / ')]
 ].map(([label,value])=>'<div class="stat"><small>'+label+'</small><strong>'+E(typeof value==='string'?value:I(value))+'</strong></div>').join('');
 const leaders=FORMATS.map(f=>{
  const p=(meta.leaders[f]||[])[0];
  return '<a class="leader" href="#'+f+'"><small>'+E(LABEL[f])+'</small><h3>'+
  E(p?.name||'Unavailable')+'</h3><p>JAWS percentile '+N(p?.jawsPercentile)+
  ' · '+I(p?.innings)+' innings</p><span>Open ranking →</span></a>';
 }).join('');
 const tiles=ALL.map(f=>'<a class="view-card" href="#'+f+'"><small>ANALYSIS</small>'+
 '<strong>'+E(LABEL[f])+'</strong><p>View validated research results and compare historic greats.</p>'+
 '<span>Explore →</span></a>').join('');
 $('#page-body').innerHTML='<div class="stat-grid">'+blocks+'</div>'+
 panel('Leading batters by format','<div class="trio">'+leaders+'</div>')+
 panel('Explore the research','<div class="view-grid">'+tiles+'</div>')+
 '<p class="note">The source data and models are private; the displayed rankings are experimental analytical outputs, not certified all-time records.</p>';
}
async function ranking(fmt){
 hero(E(LABEL[fmt])+' <em>Batting Greatness</em>',
 'Search, filter and rank model-derived player summaries; raw batting and bowling records remain in private storage.');
 const serial=++requestSerial;
 const focused=document.activeElement?.id||'';
 const caret=(focused==='output-search'||focused==='output-country')?
    document.activeElement.selectionStart:null;
 const m=state.metric;
 const options=Object.entries(METRICS).map(([k,label])=>'<option value="'+k+'"'+
  (k===m?' selected':'')+'>'+E(label)+'</option>').join('');
 $('#page-body').innerHTML='<section class="section"><div class="controls">'+
 '<label>Rank by<select id="output-metric">'+options+'</select></label>'+
 '<label>Search batter<input id="output-search" placeholder="Name or country" value="'+E(state.search)+'"></label>'+
 '<label>Country<input id="output-country" placeholder="Filter country" value="'+E(state.country)+'"></label>'+
 '</div><div id="output-results" class="panel">Loading ranking results…</div></section>'+
 '<section class="section"><div id="output-profile"></div></section>';
 if(caret!==null){
  const field=$('#'+focused);
  if(field){field.focus();field.setSelectionRange(caret,caret)}
 }
 try{
  const result=await get('rankings',{format:fmt,metric:m,search:state.search,
        country:state.country,page:state.page});
  if(serial!==requestSerial||state.view!==fmt)return;
  const trs=result.items.map((p,i)=>'<tr><td>'+I(result.page*40+i+1)+'</td>'+
  '<td><button class="text-link" data-player="'+E(p.playerId)+'"><b>'+E(p.name)+
  '</b></button><span class="team">'+E(p.team)+'</span></td>'+
  '<td class="figure">'+N(p[m==='peakQuality'?'peakQuality':m])+'</td>'+
  '<td>'+I(p.innings)+'</td><td>'+I(p.runs)+'</td><td>'+N(p.quality)+'</td>'+
  '<td>'+N(p.teamCarry)+'</td><td>'+N(p.jawsPercentile)+'</td></tr>');
  const pageInfo='<div class="pager"><button data-rankpage="-1"'+
     (result.page===0?' disabled':'')+'>← Previous</button><span>Page '+(result.page+1)+
     ' · '+I(result.total)+' eligible results</span><button data-rankpage="1"'+
     ((result.page+1)*result.pageSize>=result.total?' disabled':'')+'>Next →</button></div>';
  $('#output-results').innerHTML=table(['Rank','Batter / country',METRICS[m],
            'Innings','Runs','Quality','Carry','JAWS %ile'],trs)+pageInfo+
            '<p class="note">Results are paginated. Click a name for model-derived context and sensitivity analysis.</p>';
 }catch(e){if(serial===requestSerial)showError($('#output-results'),e)}
}
function splits(rows,key){
 if(!Array.isArray(rows)||!rows.length)return '<p class="note">Not available</p>';
 return table(['Context','Innings','Relative quality'],rows.slice(0,12).map(x=>
 '<tr><td>'+E(x[key])+'</td><td>'+I(x.innings)+'</td><td>'+N(x.quality)+'</td></tr>'));
}
function profileCard(p,fmt){
 if(!p)return '<div class="panel">Player result not available.</div>';
 const combo=COMBOS.includes(fmt);
 return '<article class="player-card"><small>'+E(p.team)+' · '+I(p.innings??p.totalInnings)+
 ' observed innings</small><h3>'+E(p.name)+'</h3>'+
 '<div class="inline-metrics">'+[
 ['Quality',p.quality??p.overallQualityPercentile],
 ['Team carry',p.teamCarry??p.overallCarryPercentile],
 ['JAWS percentile',p.jawsPercentile??p.overallJawsPercentile]
 ].map(([label,val])=>'<div><small>'+label+'</small><b>'+N(val)+'</b></div>').join('')+
 '</div><p class="note">Runs: '+I(p.runs)+' · Career: '+E(p.careerStart||'—')+
 '–'+E(p.careerEnd||'—')+' · Peak: '+N(p.peakQuality?.index??p.overallPeakPercentile)+
 '</p>'+(combo?'':panel('Opponent quality',splits(p.opponents,'opponent'))+
 panel('Home, away and neutral',splits(p.venues,'venueClass')))+
 '<p class="note">Only model-derived summaries are displayed. Source-level bowling or batting records are not available through this page.</p></article>';
}
async function showProfile(fmt,id,selector='#output-profile'){
 const area=$(selector);if(!area)return;
 area.innerHTML='<div class="panel">Loading player analysis…</div>';
 try{const data=await get('player',{format:fmt,playerId:id});
      if(area.isConnected)area.innerHTML=profileCard(data.player,fmt);
 }catch(e){if(area.isConnected)showError(area,e)}
}
async function compare(){
 hero('Batter <em>Comparison Lab</em>',
 'Compare model-derived cricket research across eras without accessing the underlying source database.');
 const fmt=state.compareFormat;
 $('#page-body').innerHTML='<section class="section"><div class="controls">'+
 '<label>Format<select id="compare-format">'+ALL.map(f=>'<option value="'+f+'"'+
 (fmt===f?' selected':'')+'>'+E(LABEL[f])+'</option>').join('')+'</select></label>'+
 '<label>Find a batter<input id="compare-search" value="'+E(state.compareSearch)+
 '" placeholder="Search players…"></label></div><div id="compare-hits" class="panel">'+
 'Search by player name to choose a comparison.</div>'+
 '<div class="controls"><button id="compare-side-first" type="button">Select first</button>'+
 '<button id="compare-side-second" type="button">Select second</button></div>'+
 '<div class="player-grid"><div id="compare-first-result"></div>'+
 '<div id="compare-second-result"></div></div></section>';
 if(state.first)showProfile(fmt,state.first,'#compare-first-result');
 if(state.second)showProfile(fmt,state.second,'#compare-second-result');
 if(!state.compareSearch){
   state.compareSearch=(meta.leaders[fmt]||[])[0]?.name||'';
 }
 searchComparison();
}
async function searchComparison(){
 const area=$('#compare-hits');if(!area)return;
 try{
  const d=await get('rankings',{format:state.compareFormat,
         search:state.compareSearch,page:0});
  if(!area.isConnected)return;
  area.innerHTML=(d.items.length?d.items.map(p=>'<button class="text-link" type="button" '+
  'data-compare-id="'+E(p.playerId)+'">'+E(p.name)+' · '+E(p.team)+'</button>').join(' · '):
  'No matching batters')+'<p class="note">Choose first or second, then select a player.</p>';
 }catch(e){showError(area,e)}
}
async function matches(){
 hero('Match <em>Explorer</em>',
 'Bounded Cricsheet-derived batting displays through the private-backed API, never a bulk source file.');
 $('#page-body').innerHTML='<section class="section"><div class="controls">'+
 '<label>Format<select id="match-format">'+FORMATS.map(f=>'<option value="'+f+'"'+
 (f===state.matchFormat?' selected':'')+'>'+E(LABEL[f])+'</option>').join('')+'</select></label>'+
 '<label>Batter<input id="match-search" value="'+E(state.matchSearch)+'" placeholder="Search…"></label>'+
 '<label>Opposition<input id="match-opposition" value="'+E(state.matchOpposition)+
 '" placeholder="Opposition…"></label></div><div id="match-results" class="panel">Loading…</div>'+
 '<div id="match-detail"></div></section>';
 await fetchMatches();
}
async function fetchMatches(){
 const area=$('#match-results');if(!area)return;
 const serial=++requestSerial;
 try{
  const d=await get('matches',{format:state.matchFormat,
      search:state.matchSearch,opposition:state.matchOpposition,page:state.matchPage,sort:'date'});
  if(serial!==requestSerial||!area.isConnected)return;
  const rows=(d.items||[]).map(r=>'<tr><td>'+E(r.d)+'</td><td>'+E(r.n)+
   '</td><td>'+E(r.o)+'</td><td>'+I(r.r)+'</td><td>'+I(r.b)+
   '</td><td><button class="text-link" data-match-innings="'+E(r.i)+
   '" data-match-player="'+E(r.p)+'">View innings</button></td></tr>');
  area.innerHTML=table(['Date','Batter','Opposition','Runs','Balls','Detail'],rows)+
  '<div class="pager"><button data-matchpage="-1"'+(state.matchPage===0?' disabled':'')+
  '>← Previous</button><span>Page '+(state.matchPage+1)+' · '+I(d.total)+' results</span>'+
  '<button data-matchpage="1"'+((state.matchPage+1)*65>=d.total?' disabled':'')+
  '>Next →</button></div>';
 }catch(e){if(serial===requestSerial)showError(area,e)}
}
async function matchDetail(inningsId,playerId){
 const area=$('#match-detail');area.innerHTML='<div class="panel">Loading…</div>';
 try{const d=await get('innings',{inningsId,playerId});const p=d.selected;
      if(!p)throw new Error('Selected innings unavailable');
      area.innerHTML=panel('Selected innings: '+p.n,
       '<p>'+E(p.d)+' · '+E(p.o)+' · '+I(p.r)+' runs from '+I(p.b)+' balls</p>'+
       table(['Teammate','Runs','Balls'],(d.teammates||[]).map(t=>
       '<tr><td>'+E(t.n)+'</td><td>'+I(t.r)+'</td><td>'+I(t.b)+'</td></tr>')));
 }catch(e){showError(area,e)}
}
function coverage(){
 hero('Data, coverage & <em>limitations</em>',
  'Source-coverage limitations and player-level model output, not independently certified all-time scorecards.');
 const c=meta.coverage||{};
 const rows=FORMATS.map(f=>{
  const x=c.formats?.[f]||{};
  return '<tr><td>'+E(LABEL[f])+'</td><td>'+I(x.observedMatches)+
   '</td><td>'+I(x.deliveryMatches)+'</td><td>'+
   I(x.historicalScorecardMatches)+'</td></tr>';
 });
 $('#page-body').innerHTML=panel('Observed international match coverage',
    table(['Format','Observed matches','Modern delivery matches','Historic batting-only matches'],rows))+
 '<div class="callout">Historical batting and bowling source records are not available for download. '+ 
 'Official match-level completeness and all-time greatness rankings remain unverified.</div>'+
 panel('Reference career checks','<div class="panel">Validated career run totals: '+
 I(c.passingCareers)+' / '+I(c.checkedCareers)+
 '. Matching career totals does not certify all innings or player identities.</div>');
}
function methodology(){
 hero('How the <em>index works</em>',
  'A plain-language explanation of derived measurements; raw data, code and model fitting remain private.');
 const items=[
 ['Era adjusted quality','Compare player performance with peers in the same era and format.'],
 ['Opposition','Adjust using opponent strength proxies where available.'],
 ['Team carry','Estimate contribution relative to the observed teammates.'],
 ['Home and away','Account for known host conditions, leaving uncertain venues unknown.'],
 ['Peak and longevity','Show career, best seasons, short-term peak and JAWS-style indices.']];
 $('#page-body').innerHTML=panel('Model overview','<div class="trio">'+items.map(([a,b])=>
 '<article class="panel"><h3>'+E(a)+'</h3><p>'+E(b)+'</p></article>').join('')+
 '</div><p class="note">Scores are experimental research outputs, not official all-time certifications.</p>');
}
async function render(){
 const route=currentRoute();
 state.view=route;navigation(route);
 if(!meta){try{meta=await get('bootstrap')}catch(e){showError($('#page-body'),e);return}}
 if(route==='overview')overview();
 else if(ALL.includes(route)){state.format=route;await ranking(route)}
 else if(route==='compare')await compare();
 else if(route==='matches')await matches();
 else if(route==='methodology')methodology();
 else if(route==='coverage')coverage();
 $('#sidebar-status').textContent='Private-backed research results';
}
function delayed(callback){clearTimeout(searchTimer);searchTimer=setTimeout(callback,280)}
document.addEventListener('input',ev=>{
 if(ev.target.id==='output-search'){state.search=ev.target.value;state.page=0;delayed(()=>ranking(state.format))}
 if(ev.target.id==='output-country'){state.country=ev.target.value;state.page=0;delayed(()=>ranking(state.format))}
 if(ev.target.id==='compare-search'){state.compareSearch=ev.target.value;delayed(searchComparison)}
 if(ev.target.id==='match-search'){state.matchSearch=ev.target.value;state.matchPage=0;delayed(fetchMatches)}
 if(ev.target.id==='match-opposition'){state.matchOpposition=ev.target.value;state.matchPage=0;delayed(fetchMatches)}
});
document.addEventListener('change',ev=>{
 if(ev.target.id==='output-metric'){state.metric=ev.target.value;state.page=0;ranking(state.format)}
 if(ev.target.id==='compare-format'){state.compareFormat=ev.target.value;state.first=null;state.second=null;state.compareSearch='';compare()}
 if(ev.target.id==='match-format'){state.matchFormat=ev.target.value;state.matchPage=0;matches()}
});
document.addEventListener('click',ev=>{
 const p=ev.target.closest('[data-player]');if(p){showProfile(state.format,p.dataset.player);return}
 const rp=ev.target.closest('[data-rankpage]');if(rp){state.page=Math.max(0,Math.min(49,state.page+Number(rp.dataset.rankpage)));ranking(state.format);return}
 const mp=ev.target.closest('[data-matchpage]');if(mp){state.matchPage=Math.max(0,Math.min(99,state.matchPage+Number(mp.dataset.matchpage)));fetchMatches();return}
 const detail=ev.target.closest('[data-match-innings]');if(detail){matchDetail(detail.dataset.matchInnings,detail.dataset.matchPlayer);return}
 const side=ev.target.closest('[id^=compare-side-]');if(side){state.activeCompareSide=side.id.slice('compare-side-'.length);return}
 const chosen=ev.target.closest('[data-compare-id]');if(chosen){
  const side=state.activeCompareSide;
  state[side]=chosen.dataset.compareId;
  showProfile(state.compareFormat,chosen.dataset.compareId,'#compare-'+side+'-result');
 }
});
$('#menu-button').addEventListener('click',()=>{const on=$('#sidebar').classList.toggle('open');$('#menu-button').setAttribute('aria-expanded',String(on))});
window.addEventListener('hashchange',()=>{state.page=0;render()});
render();
})();