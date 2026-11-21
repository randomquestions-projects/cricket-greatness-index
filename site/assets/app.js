/* Source-free cricket viewer. All records arrive only as bounded server-derived results.
   The browser NEVER downloads the raw innings file, rankings database or source records. */
(()=>{'use strict';
const $=q=>document.querySelector(q);
const FORMATS=['test','odi','t20i'], COMBOS=['test_odi','all_three'], ALL=[...FORMATS,...COMBOS];
const LABEL={overview:'Overview',test:'Test Cricket',odi:'One-Day Internationals',
 t20i:'T20 Internationals',test_odi:'Tests + ODIs',all_three:'All Three Formats',
 bowling:'Bowling Rankings',allrounder:'All-Rounder Rankings',
 compare:'Player Comparison',matches:'Match Explorer',
 methodology:'Index Methodology',coverage:'Data & Coverage'};
const METRICS={careerGreatness:'Career greatness',jawsPercentile:'JAWS-inspired percentile',
 quality:'Era-adjusted quality',teamCarry:'Team carry',peakQuality:'Peak quality'};
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const N=(v,d=1)=>v==null||!Number.isFinite(+v)?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:d});
const I=v=>N(v,0);
const state={discipline:'batting',view:'overview',format:'test',metric:'careerGreatness',search:'',country:'',
 page:0,matchFormat:'odi',matchPage:0,matchSearch:'',matchOpposition:'',
 first:null,second:null,firstSearch:'',secondSearch:'',compareFormat:'test',
 disciplineFormat:'test',disciplineMetric:'career',disciplineSearch:'',disciplineCountry:'',disciplinePage:0,fullMember:'all',inningsMin:'',inningsMax:'',inningsBound:null,inningsContext:''};
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
 const target=apiURL(path,params);
 let res;
 for(let attempt=0;attempt<4;attempt++){
  res=await fetch(target,{cache:'no-store',headers:{Accept:'application/json'}});
  if(res.status!==429)break;
  await new Promise(resolve=>setTimeout(resolve,450*(attempt+1)));
 }
 if(!res.ok)throw new Error('Results service unavailable ('+res.status+')');
 return res.json();
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
 $('#global-discipline').value=state.discipline;
 document.querySelectorAll('[data-view]').forEach(a=>a.classList.toggle('active',a.dataset.view===v));
 $('#sidebar').classList.remove('open');$('#menu-button').setAttribute('aria-expanded','false');
}
function panel(title,body){return '<section class="section"><div class="section-head"><h2>'+E(title)+'</h2></div>'+body+'</section>'}
function table(head,rows){
 return '<div class="table-scroller"><table><thead><tr>'+head.map(s=>'<th>'+E(s)+'</th>').join('')+
 '</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
}

/* ICC membership is based on present-day Full Member teams, not historic
   membership when a particular innings was played. All filters execute on
   bounded server-side ranking queries and are applied before pagination. */
function ensureRankingRange(fmt){
 const context=state.discipline+':'+fmt;
 if(state.inningsContext!==context){
  state.inningsContext=context;
  state.inningsMin='';state.inningsMax='';state.inningsBound=null;
 }
}
function rankingFiltersParams(){
 return {fullMember:state.fullMember,minInnings:state.inningsMin,maxInnings:state.inningsMax};
}
function sharedRankingFilters(){
 return '<label>ICC Full Members<select id="full-member-filter" aria-label="ICC Full Members">'+
 ['all','yes','no'].map(x=>'<option value="'+x+'"'+(state.fullMember===x?' selected':'')+'>'+
  ({all:'All teams',yes:'Yes — Full Members',no:'No — Other teams'}[x])+'</option>').join('')+
 '</select></label><div class="innings-filter" id="innings-range-host" aria-label="Number of innings range">'+
 (state.inningsBound==null?'<span class="range-placeholder">Loading innings range…</span>':inningsRangeHTML())+
 '</div>';
}
function inningsRangeHTML(){
 const cap=Math.max(0,Number(state.inningsBound)||0);
 const low=Math.min(cap,Math.max(0,state.inningsMin===''?0:Number(state.inningsMin)));
 const high=Math.max(low,Math.min(cap,state.inningsMax===''?cap:Number(state.inningsMax)));
 const lowPct=cap?Math.round(low*100/cap):0;
 const highPct=cap?Math.round(high*100/cap):100;
 return '<fieldset class="innings-fieldset"><legend>Number of innings</legend>'+
 '<div class="innings-number-row"><label>Minimum<input id="innings-min" inputmode="numeric" type="number" min="0" max="'+cap+
 '" step="1" value="'+low+'" aria-label="Minimum innings"></label>'+
 '<span aria-hidden="true">–</span>'+
 '<label>Maximum<input id="innings-max" inputmode="numeric" type="number" min="0" max="'+cap+
 '" step="1" value="'+high+'" aria-label="Maximum innings"></label></div>'+
 '<div class="innings-dual" style="--range-low:'+lowPct+'%;--range-high:'+highPct+'%">'+
 '<input type="range" id="innings-low" min="0" max="'+cap+'" value="'+low+
 '" step="1" aria-label="Minimum innings slider"'+(cap===0?' disabled':'')+'>'+
 '<input type="range" id="innings-high" min="0" max="'+cap+'" value="'+high+
 '" step="1" aria-label="Maximum innings slider"'+(cap===0?' disabled':'')+'>'+
 '</div><div class="innings-range-hint">Inclusive · '+I(low)+'–'+I(high)+' innings'+
 (state.discipline==='allrounder'?' (batting innings)':'')+'</div></fieldset>';
}
function paintInningsFilter(bounds){
 if(!bounds||typeof bounds.max!=='number')throw new Error('Rankings API lacks innings-range support');
 const cap=Math.max(0,Math.min(10000,Math.floor(bounds.max)));
 state.inningsBound=cap;
 const node=$('#innings-range-host');
 if(node)node.innerHTML=inningsRangeHTML();
}
function changeInningsSelection(changed){
 if(state.inningsBound==null)return;
 const cap=state.inningsBound;
 const lower=$('#innings-min'),upper=$('#innings-max'),lowSlider=$('#innings-low'),highSlider=$('#innings-high');
 if(!lower||!upper||!lowSlider||!highSlider)return;
 let lo=Number((changed==='innings-low'?lowSlider:lower).value);
 let hi=Number((changed==='innings-high'?highSlider:upper).value);
 if(!Number.isFinite(lo)||!Number.isFinite(hi))return;
 lo=Math.round(Math.max(0,Math.min(cap,lo)));
 hi=Math.round(Math.max(0,Math.min(cap,hi)));
 if(lo>hi){if(changed==='innings-low'||changed==='innings-min')hi=lo;else lo=hi}
 state.inningsMin=lo===0?'':String(lo);
 state.inningsMax=hi===cap?'':String(hi);
 for(const [el,value] of [[lower,lo],[lowSlider,lo],[upper,hi],[highSlider,hi]])el.value=value;
 const wrap=$('.innings-dual');
 if(wrap){wrap.style.setProperty('--range-low',(cap?lo*100/cap:0)+'%');
          wrap.style.setProperty('--range-high',(cap?hi*100/cap:100)+'%')}
 const hint=$('.innings-range-hint');
 if(hint)hint.textContent='Inclusive · '+I(lo)+'–'+I(hi)+' innings'+
       (state.discipline==='allrounder'?' (batting innings)':'');
}

async function overview(){
 const current=state.discipline,serial=++requestSerial;
 const name={batting:'Batting',bowling:'Bowling',allrounder:'All-Rounder'}[current];
 hero('Cricket <em>'+E(name)+' Greatness</em>',
  'Explore independent Test, ODI and T20I research using available derived statistics; rankings remain provisional, with different historical coverage by discipline.');
 $('#page-body').innerHTML='<div class="panel">Loading '+E(name.toLowerCase())+' research overview…</div>';
 try{
  let formats=[],leaders={},numbers=[],integratedHistory=false;
  if(current==='batting'){
   formats=FORMATS.map(f=>meta.formats[f]||{});
   // The homepage has its own consistent leaderboard definition:
   // career greatness, current ICC Full Member teams, unfiltered innings.
   numbers=[
    ['Tests observed',formats[0].observedDistinctMatches],
    ['ODIs observed',formats[1].observedDistinctMatches],
    ['T20Is observed',formats[2].observedDistinctMatches],
    ['Eligible batters',formats.map(f=>I(f.qualifiedPlayers)).join(' / ')]];
  }else{
   const d=await get('disciplines');
   integratedHistory=d.historicalRestrictedSourcesIncluded===true;
   formats=FORMATS.map(f=>d.formats?.[current]?.[f]||{});
   numbers=FORMATS.map((f,i)=>[LABEL[f]+' qualified players',formats[i].qualifiedPlayers]);
   numbers.push(['Live source coverage',integratedHistory?'Integrated observed historical + modern (provisional)':'Licensed modern Cricsheet only']);
  }
  // Do not choose the first member of a globally ranked bootstrap top-three:
  // that misses qualified Full Members below the first few positions. Ask the
  // bounded ranking API to filter before sorting/paginating for each format.
  const endpoint=current==='batting'?'rankings':'discipline-rankings';
  const metric=current==='batting'?'careerGreatness':'career';
  for(const fmt of ALL){
   if(serial!==requestSerial||state.view!=='overview'||state.discipline!==current)return;
   const params={format:fmt,metric,fullMember:'yes',page:0};
   if(current!=='batting')params.discipline=current;
   try{
    const response=await get(endpoint,params);
    if(!Array.isArray(response.items))throw new Error('Invalid homepage rankings');
    leaders[fmt]=response.items.slice(0,1);
   }catch(error){
    // Degraded combined-format queries must not hide the single-format leaders.
    if(!COMBOS.includes(fmt))throw error;
    leaders[fmt]=[];
   }
  }
  if(serial!==requestSerial||state.view!=='overview'||state.discipline!==current)return;
  const statCards=numbers.map(([label,value])=>'<div class="stat"><small>'+E(label)+'</small><strong>'+
    E(typeof value==='string'?value:I(value))+'</strong></div>').join('');
  const leaderCard=f=>{
   const p=(leaders[f]||[])[0];
   return '<a class="leader" href="#'+f+'"><small>'+E(LABEL[f])+'</small><h3>'+
    E(p?.name||'Not yet available')+'</h3><p>'+(
    p ? E(p.team||'')+' · Career greatness '+N(current==='batting'?
       p.careerGreatness:p.career)+' · '+I(p.innings)+' innings' :
       'No qualified or verified combined-format leader available')+'</p>'+
    '<span>Open '+E(name.toLowerCase())+' ranking →</span></a>';
  };
  const top=FORMATS.map(leaderCard).join('');
  const combined=COMBOS.map(leaderCard).join('');
  const tiles=ALL.map(f=>'<a class="view-card" href="#'+f+'"><small>'+E(name.toUpperCase())+' ANALYSIS</small>'+
   '<strong>'+E(LABEL[f])+'</strong><p>Explore '+E(name.toLowerCase())+
   ' results for this format.</p><span>Explore →</span></a>').join('');
  $('#page-body').innerHTML='<div class="stat-grid">'+statCards+'</div>'+
    panel('Single-format GOATs · Career Greatness · ICC Full Members',
      '<p class="note">Current ICC Full Member national teams only · Career Greatness, ranked separately for Tests, ODIs and T20Is.</p><div class="trio">'+top+'</div>')+
    panel('Multi-format GOATs · Career Greatness · ICC Full Members',
      '<p class="note">Tests + ODIs and All Three Formats. Players must qualify in every included format. Modern careers use verified provider IDs; historical cross-format identities are evidence-labeled candidates. Scores use within-format percentiles, not raw totals, and all-era completeness remains unverified.</p><div class="two">'+combined+'</div>')+
    panel('Explore '+E(name.toLowerCase())+' research','<div class="view-grid">'+tiles+'</div>')+
    '<p class="note">'+(current==='batting'?
      'Published batting remains the previously validated derived snapshot; new historical rebuild comparisons are under review.':
      (integratedHistory?'The live API includes historical and modern observed-career research candidates. Cross-source identities and comprehensive historical coverage are not independently certified.':'The live bowling and all-rounder rankings use licensed modern Cricsheet records. Full-source historical research is retained privately and is not yet shown as live rankings.'))+
    '</p>';
 }catch(e){if(serial===requestSerial)showError($('#page-body'),e)}
}
const D_METRICS={
 bowling:{greatness:'Greatness index',quality:'Era & opponent peer quality',
          career:'Career greatness',peak:'Peak quality',wickets:'Wickets'},
 allrounder:{career:'Career greatness',greatness:'All-rounder JAWS index',batting:'Batting percentile',
             bowling:'Bowling percentile',runs:'Runs',wickets:'Wickets'}
};
async function disciplineRanking(fmt){
 const discipline=state.discipline;
 if(!D_METRICS[discipline])return;
 if(!D_METRICS[discipline][state.disciplineMetric])state.disciplineMetric='career';
 ensureRankingRange(fmt);
 const serial=++requestSerial,metric=state.disciplineMetric;
 const active=document.activeElement?.id||'';
 const caret=(active==='discipline-search'||active==='discipline-country')?
    document.activeElement.selectionStart:null;
 const name=discipline==='bowling'?'Bowling':'All-Rounder';
 hero(E(LABEL[fmt])+' <em>'+name+' Greatness</em>',
  'Rank, search and inspect source-approved player summaries; never raw batting or bowling archives.');
 const metricOptions=Object.entries(D_METRICS[discipline]).map(([key,label])=>
   '<option value="'+E(key)+'"'+(key===metric?' selected':'')+'>'+E(label)+'</option>').join('');
 $('#page-body').innerHTML='<div class="callout">Provisional '+E(name.toLowerCase())+
   ' research · Source scope verified from the rankings API; historical identities, when present, remain provisional.'+
   (COMBOS.includes(fmt)?' Combined rankings require the same verified provider ID in every selected format and average within-format metric percentiles.':'')+
   '</div><section class="section"><div class="controls">'+
   '<label>Rank by<select id="discipline-metric">'+metricOptions+'</select></label>'+
   '<label>Search player<input id="discipline-search" placeholder="Name or country" value="'+E(state.disciplineSearch)+'"></label>'+
   '<label>Country<input id="discipline-country" placeholder="Filter country" value="'+E(state.disciplineCountry)+'"></label>'+sharedRankingFilters()+
   '</div><div id="discipline-results" class="panel">Loading ranking results…</div></section>'+
   '<section class="section"><div id="discipline-profile"></div></section>';
 if(caret!==null){const el=$('#'+active);if(el){el.focus();el.setSelectionRange(caret,caret)}}
 try{
  const result=await get('discipline-rankings',{discipline,format:fmt,metric,
      search:state.disciplineSearch,country:state.disciplineCountry,
      page:state.disciplinePage,...rankingFiltersParams()});
  if(serial!==requestSerial||state.view!==fmt||state.discipline!==discipline)return;
  if(result.schemaVersion!=='cricket-discipline-projection-v1')
      throw new Error('Unexpected research schema');
   const historical=result.historicalRestrictedSourcesIncluded===true;
   const intro=document.querySelector('#page-body > .callout');
   if(intro)intro.textContent=(historical?'Integrated historical + modern observed-career ranking (provisional). Historical cross-source identities and full career coverage are not certified.':'Licensed modern Cricsheet-only ranking; historical research remains private and is not used by this live view.')+
     (COMBOS.includes(fmt)?' Two/three-format scores require evidence-supported player matches across included formats.':'');
   paintInningsFilter(result.inningsBounds);
  const head=discipline==='bowling'?
    ['Rank','Bowler / country',D_METRICS[discipline][metric],
     'Innings','Wickets','Quality','Career','Peak']:
    ['Rank','All-rounder / country',D_METRICS[discipline][metric],
     'Batting innings','Runs','Wickets','Career','Batting %ile','Bowling %ile'];
  const rows=(result.items||[]).map((p,i)=>{
   const cols=discipline==='bowling'?
      [I(p.innings),I(p.wickets),N(p.quality),N(p.career),N(p.peak)]:
      [I(p.innings),I(p.runs),I(p.wickets),N(p.career),N(p.batting),N(p.bowling)];
   return '<tr><td>'+I(result.page*result.pageSize+i+1)+'</td><td>'+
     '<button class="text-link" data-discipline-player="'+E(p.playerId)+'">'+E(p.name)+
     '</button><span class="team">'+E(p.team)+'</span></td><td class="figure">'+
     N(p[metric])+'</td>'+cols.map(x=>'<td>'+E(x)+'</td>').join('')+'</tr>';
  });
  const paging='<div class="pager"><button data-discipline-page="-1"'+
    (result.page===0?' disabled':'')+'>← Previous</button><span>Page '+
    (result.page+1)+' · '+I(result.total)+' eligible players</span>'+
    '<button data-discipline-page="1"'+
    ((result.page+1)*result.pageSize>=result.total?' disabled':'')+'>Next →</button></div>';
  $('#discipline-results').innerHTML=(rows.length?table(head,rows):
    '<p>No qualified players match these filters.</p>')+paging+
    '<p class="note">Selected player names open limited derived statistics. Rankings are provisional.'+
    (COMBOS.includes(fmt)?' Combined score columns are normalized percentiles, not raw-format values.':'')+'</p>';
 }catch(err){if(serial===requestSerial)showError($('#discipline-results'),err)}
}

function disciplineCard(p,fmt,discipline){
 if(!p)return '<div class="panel">Player not available in this discipline and format.</div>';
 const columns=discipline==='bowling'?
   [['Career greatness',p.career],['JAWS-inspired greatness',p.greatness],['Quality',p.quality],
    ['Peak',p.peak],['Wickets',p.wickets],['Innings',p.innings],
    ['Bowling average',p.bowlingAverage],['Strike rate',p.strikeRate]]:
   [['Career greatness',p.career],['All-rounder JAWS',p.greatness],['Batting percentile',p.batting],
    ['Bowling percentile',p.bowling],['Runs',p.runs],['Wickets',p.wickets],
    ['Batting innings',p.battingInnings??p.innings],['Bowling innings',p.bowlingInnings]];
 return '<article class="player-card"><small>'+E(p.team)+' · '+E(LABEL[fmt])+
   '</small><h3>'+E(p.name)+'</h3><div class="research-metric-grid">'+
   columns.map(([k,v])=>'<div><small>'+E(k)+'</small><b>'+N(v)+'</b></div>').join('')+
   '</div><p class="note">Provisional '+E(discipline==='bowling'?'bowling':'all-rounder')+
   ' research from source-qualified observed data; historical source scope and identity uncertainty are shown in Data & Coverage.'+
   (COMBOS.includes(fmt)?' Combined scores are within-format normalized percentiles.':'')+
   '</p></article>';
}
async function disciplineProfile(discipline,fmt,id,selector='#discipline-profile'){
 const area=$(selector);if(!area)return;
 area.innerHTML='<div class="panel">Loading player summary…</div>';
 try{
  const payload=await get('discipline-player',{discipline,format:fmt,playerId:id});
  if(area.isConnected&&state.discipline===discipline)
    area.innerHTML=disciplineCard(payload.player,fmt,discipline);
 }catch(err){if(area.isConnected)showError(area,err)}
}

async function ranking(fmt){
 if(state.discipline!=='batting')return disciplineRanking(fmt);
 ensureRankingRange(fmt);
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
 '<label>Country<input id="output-country" placeholder="Filter country" value="'+E(state.country)+'"></label>'+sharedRankingFilters()+
 '</div><div id="output-results" class="panel">Loading ranking results…</div></section>'+
 '<section class="section"><div id="output-profile"></div></section>';
 if(caret!==null){
  const field=$('#'+focused);
  if(field){field.focus();field.setSelectionRange(caret,caret)}
 }
 try{
  const result=await get('rankings',{format:fmt,metric:m,search:state.search,
        country:state.country,page:state.page,...rankingFiltersParams()});
  if(serial!==requestSerial||state.view!==fmt)return;
  paintInningsFilter(result.inningsBounds);
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
 ['Career greatness',p.careerGreatness??p.overallCareerPercentile],
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
 const discipline=state.discipline,fmt=state.compareFormat,serial=++requestSerial;
 hero('Player <em>Comparison Lab</em>',
   'Compare two '+E({batting:'batters',bowling:'bowlers',allrounder:'all-rounders'}[discipline])+
   ' using the same format, source scope and model.');
 const slots=['first','second'].map(side=>{
  const label=side==='first'?'Player 1':'Player 2';
  return '<div class="comparison-slot"><label>'+label+' search'+
     '<input id="compare-search-'+side+'" placeholder="Search by player or country…" value="'+
     E(state[side+'Search']||'')+'"></label><label>'+label+
     '<select id="compare-player-'+side+'"><option value="">Choose a player…</option></select></label>'+
     '<p class="hint">Search and select a player to compare their available derived statistics.</p>'+
     '<div id="compare-'+side+'-result"></div></div>';
 }).join('');
 $('#page-body').innerHTML='<section class="section"><div class="controls">'+
  '<label>Format<select id="compare-format">'+ALL.map(f=>'<option value="'+f+'"'+
  (fmt===f?' selected':'')+'>'+E(LABEL[f])+'</option>').join('')+'</select></label>'+
  '</div><div class="comparison-selects">'+slots+'</div>'+
  '<p class="note">'+(discipline==='batting'?
     'Published batting summaries use the historical derived batting model.':
     'Comparisons use the source scope of the selected live ranking API; historic profiles, when present, remain provisional.')+
     ' Players can only be compared within the chosen discipline and format.</p></section>';
 await Promise.all(['first','second'].map(side=>searchComparison(side,serial)));
}
async function searchComparison(side,renderSerial=requestSerial){
 const discipline=state.discipline,fmt=state.compareFormat;
 const select=$('#compare-player-'+side);
 if(!select)return;
 select.innerHTML='<option value="">Searching…</option>';
 try{
  const query=state[side+'Search']||'';
  const params={format:fmt,search:query,page:0};
  if(discipline!=='batting')params.discipline=discipline;
  const data=await get(discipline==='batting'?'rankings':'discipline-rankings',params);
  if(renderSerial!==requestSerial||!select.isConnected||state.discipline!==discipline)return;
  const selected=state[side];
  const list=data.items||[];
  const available=list.some(p=>p.playerId===selected);
  select.innerHTML='<option value="">Choose '+(side==='first'?'Player 1':'Player 2')+'…</option>'+
    (selected&&!available?'<option selected value="'+E(selected)+'">Selected player (outside current search)</option>':'')+
    list.map(p=>'<option value="'+E(p.playerId)+'"'+(p.playerId===selected?' selected':'')+'>'+
       E(p.name)+' · '+E(p.team)+'</option>').join('');
  if(selected)showComparisonPlayer(side);
 }catch(e){if(select.isConnected){select.innerHTML='<option value="">Rankings unavailable</option>';
   showError($('#compare-'+side+'-result'),e)}}
}
function showComparisonPlayer(side){
 const id=state[side],selector='#compare-'+side+'-result',fmt=state.compareFormat;
 const area=$(selector);if(!area)return;
 if(!id){area.innerHTML='<div class="panel">Choose a player above.</div>';return}
 if(state.discipline==='batting')showProfile(fmt,id,selector);
 else disciplineProfile(state.discipline,fmt,id,selector);
}

async function matches(){
 const discipline=state.discipline;
 hero('Match <em>Explorer</em>',
  discipline==='batting'?
    'Explore bounded modern innings and their teammates, without downloading raw match archives.':
    'Explore source-approved, bounded modern '+(discipline==='bowling'?'bowling':'all-rounder')+
    ' player-match summaries; this is not a complete historical scorecard database.');
 $('#page-body').innerHTML='<section class="section">'+
  (discipline==='batting'?'':'<div class="callout">Modern Cricsheet-derived match summaries only. Older bowling and all-rounder scorecards remain outside the public API.</div>')+
  '<div class="controls"><label>Format<select id="match-format">'+FORMATS.map(f=>
    '<option value="'+f+'"'+(f===state.matchFormat?' selected':'')+'>'+
    E(LABEL[f])+'</option>').join('')+'</select></label>'+
  '<label>Player<input id="match-search" value="'+E(state.matchSearch)+
  '" placeholder="Search player or country…"></label>'+
  '<label>Opposition<input id="match-opposition" value="'+E(state.matchOpposition)+
  '" placeholder="Opposition…"></label></div>'+
  '<div id="match-results" class="panel">Loading…</div>'+
  '<div id="match-detail"></div></section>';
 await fetchMatches();
}
async function fetchMatches(){
 const area=$('#match-results');if(!area)return;
 const serial=++requestSerial,discipline=state.discipline,fmt=state.matchFormat;
 const modern=discipline!=='batting';
 try{
  const endpoint=modern?'discipline-matches':'matches';
  const params={format:fmt,search:state.matchSearch,
               opposition:state.matchOpposition,page:state.matchPage};
  if(modern)params.discipline=discipline;else params.sort='date';
  const data=await get(endpoint,params);
  if(serial!==requestSerial||!area.isConnected||state.discipline!==discipline)return;
  if(modern&&data.schemaVersion!=='cricket-discipline-matches-v1')
    throw new Error('Unapproved match summary format');
  const rows=(data.items||[]).map(p=>{
   if(!modern)return '<tr><td>'+E(p.d)+'</td><td>'+E(p.n)+
     '</td><td>'+E(p.o)+'</td><td>'+I(p.r)+'</td><td>'+I(p.b)+
     '</td><td><button class="text-link" data-match-innings="'+E(p.i)+
     '" data-match-player="'+E(p.p)+'">View innings</button></td></tr>';
   const cells=discipline==='bowling'?
     [E(p.date),E(p.name),E(p.opposition),I(p.wickets),
      I(p.bowlingBalls),I(p.runsConceded)]:
     [E(p.date),E(p.name),E(p.opposition),I(p.runs),
      I(p.wickets),I(p.bowlingBalls)];
   return '<tr>'+cells.map(v=>'<td>'+v+'</td>').join('')+
     '<td><button class="text-link" data-discipline-match="'+E(p.matchId)+
     '">View summary</button></td></tr>';
  });
  const headings=discipline==='batting'?
    ['Date','Batter','Opposition','Runs','Balls','Detail']:
    discipline==='bowling'?
    ['Date','Bowler','Opposition','Wickets','Balls bowled','Runs conceded','Detail']:
    ['Date','All-rounder','Opposition','Runs','Wickets','Balls bowled','Detail'];
  area.innerHTML=(rows.length?table(headings,rows):
     '<p>No approved match summaries match these filters.</p>')+
   '<div class="pager"><button data-matchpage="-1"'+(state.matchPage===0?' disabled':'')+
   '>← Previous</button><span>Page '+(state.matchPage+1)+' · '+I(data.total)+
   ' results</span><button data-matchpage="1"'+
   ((state.matchPage+1)*(data.pageSize||65)>=data.total?' disabled':'')+
   '>Next →</button></div>';
 }catch(e){
  if(serial!==requestSerial)return;
  if(discipline!=='batting'&&/404|503/.test(e.message||'')){
   area.innerHTML='<div class="callout">The modern '+E(discipline)+
   ' match-summary API is still being staged. Rankings and player comparisons remain available; no match-level records are invented.</div>';
  }else showError(area,e);
 }
}
async function matchDetail(inningsId,playerId){
 const area=$('#match-detail');if(!area)return;
 area.innerHTML='<div class="panel">Loading…</div>';
 try{
  const data=await get('innings',{inningsId,playerId});
  const p=data.selected;if(!p)throw new Error('Selected innings unavailable');
  area.innerHTML=panel('Selected innings: '+p.n,
    '<p>'+E(p.d)+' · '+E(p.o)+' · '+I(p.r)+' runs from '+I(p.b)+' balls</p>'+
    table(['Teammate','Runs','Balls'],(data.teammates||[]).map(t=>
    '<tr><td>'+E(t.n)+'</td><td>'+I(t.r)+'</td><td>'+I(t.b)+'</td></tr>')));
 }catch(e){showError(area,e)}
}
async function disciplineMatchDetail(matchId){
 const area=$('#match-detail');if(!area)return;
 area.innerHTML='<div class="panel">Loading match summary…</div>';
 try{
  const discipline=state.discipline;
  const data=await get('discipline-innings',{
    discipline,format:state.matchFormat,matchId});
  if(!area.isConnected||state.discipline!==discipline)return;
  const p=data.selected;if(!p)throw new Error('Match summary unavailable');
  const vals=[['Date',p.date],['Opposition',p.opposition],['Runs',p.runs],
              ['Balls faced',p.balls],['Wickets',p.wickets],
              ['Balls bowled',p.bowlingBalls],['Runs conceded',p.runsConceded]];
  area.innerHTML='<article class="player-card"><h3>'+E(p.name)+'</h3><small>'+E(p.team)+
    ' · '+E(LABEL[state.matchFormat])+'</small><div class="research-metric-grid">'+
    vals.map(([key,val])=>'<div><small>'+E(key)+'</small><b>'+
      (typeof val==='string'?E(val):I(val))+'</b></div>').join('')+
    '</div><p class="note">Derived modern Cricsheet match summary only; restricted source records are not available.</p></article>';
 }catch(e){showError(area,e)}
}

async function coverage(){
 const selected=state.discipline,serial=++requestSerial;
 hero('Data, coverage & <em>limitations</em>',
  'Understand which evidence supports the selected player discipline and where historical coverage remains incomplete.');
 const c=meta.coverage||{};
 if(selected==='batting'){
  const rows=FORMATS.map(f=>{
   const x=c.formats?.[f]||{};
   return '<tr><td>'+E(LABEL[f])+'</td><td>'+I(x.observedMatches)+
    '</td><td>'+I(x.deliveryMatches)+'</td><td>'+
    I(x.historicalScorecardMatches)+'</td></tr>';
  });
  $('#page-body').innerHTML=panel('Observed batting match coverage',
     table(['Format','Observed matches','Modern delivery matches','Historic batting-only matches'],rows))+
  '<div class="callout">Historical batting source records are private. Official match-level completeness and all-time identity reconciliation remain unverified.</div>'+
  panel('Reference career checks','<div class="panel">Validated career run totals: '+
  I(c.passingCareers)+' / '+I(c.checkedCareers)+
  '. Passing career-total checks does not certify every innings or historical player identity.</div>');
  return;
 }
 $('#page-body').innerHTML='<div class="panel">Loading '+E(selected)+' coverage…</div>';
 try{
  const d=await get('disciplines');
  if(serial!==requestSerial||state.view!=='coverage'||state.discipline!==selected)return;
  const historical=d.historicalRestrictedSourcesIncluded===true;
  const rows=FORMATS.map(f=>{
   const x=d.formats?.[selected]?.[f]||{};
   return '<tr><td>'+E(LABEL[f])+'</td><td>'+I(x.qualifiedPlayers)+'</td>'+
    '<td>'+E(x.coverage||'Modern-only Cricsheet')+'</td></tr>';
  });
  $('#page-body').innerHTML=panel('Live public '+E(selected)+' player coverage',
    table(['Format','Qualified public profiles','Live data scope'],rows))+
    historicalAudit(selected)+
   '<div class="callout">'+(historical?'This API currently serves integrated historical and modern observed-career summaries. Historical player/match identity and source-coverage claims remain provisional; no scorecards or raw archives are available.':'This API currently serves licensed modern Cricsheet-only rankings. The private historical research counts above are not live player profiles.')+' Publication rights for the underlying historical source archives remain unresolved. Combined-format players must qualify separately in each format.</div>';
 }catch(e){if(serial===requestSerial)showError($('#page-body'),e)}
}
/* Source coverage counts below refer to the completed, verified private S3
   research build of November 21, 2026, NOT to an approved public ranking.
   They are aggregate diagnostics, not a hidden player dataset. */
const HISTORICAL_RESEARCH_AUDIT={
 bowling:{test:375,odi:483,t20i:508,test_odi:167,all_three:56},
 allrounder:{test:329,odi:342,t20i:281,test_odi:137,all_three:27}
};
function historicalAudit(discipline){
 const counts=HISTORICAL_RESEARCH_AUDIT[discipline];
 if(!counts)return '';
 const rows=ALL.map(fmt=>'<tr><td>'+E(LABEL[fmt])+'</td><td>'+I(counts[fmt])+
   '</td></tr>');
 return panel('Private all-era research · Nov 21, 2026',
    '<p class="note">Historical and modern source observations were used to build a separate, integrated research ranking for all five formats. These are qualified <strong>research source groups/candidates</strong>, not necessarily unique, independently verified complete careers. These counts describe research cohorts; Data & Coverage shows the number of profiles actually served by the live ranking API.</p>'+
    table(['Format','Private ranked research records'],rows)+
    '<p class="note">Private build: 195,226 canonical historical bowling observations, 158,191 historical batting innings, and 7,165 modern matches. Nine of nine selected retired Test wicket aggregates reconcile; that does not certify every scorecard, identity, or era model.</p>');
}
function methodology(){
 const type=state.discipline, title={batting:'Batting',bowling:'Bowling',allrounder:'All-Rounder'}[type];
 hero(E(title)+' <em>index methodology</em>',
  'How career scores, peak scores and cross-era adjustments are calculated; what has been validated and what remains provisional.');
 if(type==='batting'){
   const items=[
     ['Era-adjusted quality','Compare batting performances against source-era and format peers, preserving uncertain history as missing rather than inventing innings.'],
     ['Opposition and context','Use peer-supported opposition quality, team-relative performance and available venue context; explicitly flag low-evidence adjustments.'],
     ['Career greatness','Reward accumulated adjusted career contribution, with qualification and sample-size safeguards.'],
     ['Peak and JAWS','Report peak separately and a JAWS-inspired career-plus-peak comparison. Do not interpret those as official ratings.'],
     ['Combined formats','Normalize rankings within each eligible format, then combine percentiles only for suitably linked players.']
   ];
   $('#page-body').innerHTML=panel('How batting greatness is calculated',
      '<div class="trio">'+items.map(([a,b])=>'<article class="panel"><h3>'+E(a)+'</h3><p>'+E(b)+'</p></article>').join('')+'</div>'+
      '<p class="note">Batting currently uses the already published derived ranking snapshot. A separate full-source model rebuild is under review; historical completeness is not certified.</p>');
   return;
 }
 const qualifier='<p class="note">Qualification minima: Test batting 35 innings / bowling 40 innings; ODI 35 / 35; T20I 25 / 25. A bowler only needs the bowling minimum, while an all-rounder must pass both within the same format. These are analytical thresholds, not official career eligibility rules.</p>';
 const bowling=[
  ['1. Build a valid historical record','Use the canonical deduplicated historic bowling warehouse together with modern Cricsheet matches. Exclude conflicting duplicates and missing bowling figures. Source-qualified fragments are merged only with corroborating evidence; uncertain careers remain separately identified research candidates.'],
  ['2. Set a fair peer expectation','Estimate wicket-taking and run-concession rates using leave-bowler-out, same-format, same-source-tier peers within ±3 years. Where there is sufficient evidence, partially condition on opposition. Modern venue information may help when known; historical pitch conditions are not fabricated.'],
  ['3. Measure impact, not raw wickets alone','Expected wickets = legal balls × peer wickets per ball. Expected runs = legal balls × peer conceded runs per ball. Wicket surplus = actual wickets − expected wickets. Runs prevented = expected runs − actual conceded runs. Convert runs prevented to contemporary wicket equivalents using the peer runs-per-wicket ratio.'],
  ['4. Calculate Career Greatness','Career bowling value is the sum of wicket surplus plus run-prevention wicket equivalents across observed qualified innings. Negative performances reduce the score; consistent success and longevity are rewarded. The research Career Index is its tie-aware percentile within format among qualified observed career groups.'],
  ['5. Distinguish peak from career','A separately standardized peak model evaluates the strongest eligible seven seasons. The JAWS-style Greatness Index averages career and peak percentiles, not incomparable raw runs/wickets. Era-adjusted quality remains distinct from both longevity and peak.'],
  ['6. Validate and flag incomplete careers','Selected retired Test career wicket aggregates reconcile 9/9, including Warne, Muralitharan, McGrath, Kumble and others. Aggregate agreement is not evidence that every innings has an authoritative player/match crosswalk. The rank sensitivity audit varies the run-prevention weight from 0.5× to 1.5×.']
 ];
 const allrounder=[
  ['1. Require both disciplines','A player must have enough observed batting innings and bowling innings in the same format to qualify for both underlying models. Do not classify a batting-only or bowling-only specialist as an eligible all-rounder.'],
  ['2. Build independent batting and bowling strength','Evaluate era-adjusted batting Career Greatness and bowling Career Value independently, using peers within their format/source context. Their raw model units cannot be added directly.'],
  ['3. Reward balanced careers','Convert both disciplines to within-cohort percentiles, then combine using the harmonic mean: 2 × batting percentile × bowling percentile ÷ (batting percentile + bowling percentile). This penalizes a weak second discipline instead of allowing one elite skill to dominate.'],
  ['4. Normalize Career and JAWS separately','The Career Index ranks the harmonic career balance against other qualified candidate all-rounders. The JAWS-style score separately combines the two disciplines’ career-plus-peak percentiles, then reranks that result. Missing peak evidence is not invented.'],
  ['5. Reconcile historical player identities','Modern batting and bowling are joined by the same Cricsheet provider ID. Historical candidates must have a unique name/initial/team candidate plus at least three matching dated format/team/opponent fixture observations. These remain evidence-labeled proposals, not official identity matches.'],
  ['6. Calculate two-format and all-format rankings','Tests + ODIs requires both eligible formats; All Three requires Test, ODI and T20I. Average within-format career percentiles for qualified candidate identities; uncertain historical cross-format matches remain explicitly flagged.']
 ];
 const items=type==='bowling'?bowling:allrounder;
 const headline=type==='bowling'?'Wickets above expectation + runs prevented':'Balanced batting + bowling contribution';
 const intro=type==='bowling'?
  'The model values dismissals AND containment in era-adjusted wicket-equivalent units. Separate Career, Quality, Peak and JAWS-style scores prevent raw wicket totals or a single short peak from defining the ranking.':
  'Batting and bowling are scored independently, then balanced using a harmonic mean of their model percentiles. Career Greatness is the default ranking; peak-balanced JAWS remains a separate view.';
 $('#page-body').innerHTML=panel(headline,
    '<p>'+E(intro)+'</p><div class="trio">'+items.map(([a,b])=>
       '<article class="panel"><h3>'+E(a)+'</h3><p>'+E(b)+'</p></article>').join('')+
    '</div>'+qualifier)+
    historicalAudit(type)+
    '<div class="callout"><strong>Publication status:</strong> The actual live source scope is reported in Data & Coverage and the ranking banners. Modern-only public results and private full-source historical candidate rankings are distinct; an integrated live API must label its unverified historical player identities and incomplete coverage. Historical archive publication rights and the full identity crosswalk remain unresolved. No raw databases, deliveries, restricted scorecards or provider IDs are published.</div>';
}

async function render(){
 let route=currentRoute();
 if(route==='bowling'||route==='allrounder'){
   state.discipline=route;
   location.hash='#test';
   return;
 }
 state.view=route;navigation(route);
 if(!meta){try{meta=await get('bootstrap')}catch(e){showError($('#page-body'),e);return}}
 if(route==='overview')await overview();
 else if(ALL.includes(route)){state.format=route;await ranking(route)}
 else if(route==='compare')await compare();
 else if(route==='matches')await matches();
 else if(route==='methodology')methodology();
 else if(route==='coverage')await coverage();
 $('#sidebar-status').textContent='Private-backed '+state.discipline+' research';
}
function delayed(callback){clearTimeout(searchTimer);searchTimer=setTimeout(callback,280)}
document.addEventListener('input',ev=>{
 if(['innings-low','innings-high','innings-min','innings-max'].includes(ev.target.id)){
   if(ev.target.value!=='')changeInningsSelection(ev.target.id);
   return;
 }
 if(ev.target.id==='output-search'){state.search=ev.target.value;state.page=0;delayed(()=>ranking(state.format))}
 if(ev.target.id==='output-country'){state.country=ev.target.value;state.page=0;delayed(()=>ranking(state.format))}
 if(ev.target.id==='discipline-search'){state.disciplineSearch=ev.target.value;state.disciplinePage=0;delayed(()=>disciplineRanking(state.format))}
 if(ev.target.id==='discipline-country'){state.disciplineCountry=ev.target.value;state.disciplinePage=0;delayed(()=>disciplineRanking(state.format))}
 if(ev.target.id==='match-search'){state.matchSearch=ev.target.value;state.matchPage=0;delayed(fetchMatches)}
 if(ev.target.id==='match-opposition'){state.matchOpposition=ev.target.value;state.matchPage=0;delayed(fetchMatches)}
 for(const side of ['first','second'])if(ev.target.id==='compare-search-'+side){
   state[side+'Search']=ev.target.value;
   const serial=++requestSerial;
   delayed(()=>searchComparison(side,serial));
 }
});
document.addEventListener('change',ev=>{

 if(ev.target.id==='full-member-filter'){
  state.fullMember=ev.target.value;state.page=0;state.disciplinePage=0;ranking(state.format);
 }
 if(['innings-low','innings-high','innings-min','innings-max'].includes(ev.target.id)){
  changeInningsSelection(ev.target.id);
  state.page=0;state.disciplinePage=0;ranking(state.format);
 }
 if(ev.target.id==='global-discipline'){
   if(!['batting','bowling','allrounder'].includes(ev.target.value))return;
   state.discipline=ev.target.value;
   state.page=0;state.disciplinePage=0;state.disciplineMetric='career';state.inningsContext='';
   state.first=null;state.second=null;state.firstSearch='';state.secondSearch='';
   render();
 }
 if(ev.target.id==='output-metric'){state.metric=ev.target.value;state.page=0;ranking(state.format)}
 if(ev.target.id==='discipline-metric'){state.disciplineMetric=ev.target.value;state.disciplinePage=0;ranking(state.format)}
 if(ev.target.id==='compare-format'){state.compareFormat=ev.target.value;state.first=null;state.second=null;compare()}
 for(const side of ['first','second'])if(ev.target.id==='compare-player-'+side){
   state[side]=ev.target.value;showComparisonPlayer(side);
 }
 if(ev.target.id==='match-format'){state.matchFormat=ev.target.value;state.matchPage=0;matches()}
});
document.addEventListener('click',ev=>{
 const dp=ev.target.closest('[data-discipline-player]');
 if(dp){disciplineProfile(state.discipline,state.format,dp.dataset.disciplinePlayer);return}
 const p=ev.target.closest('[data-player]');if(p){showProfile(state.format,p.dataset.player);return}
 const rp=ev.target.closest('[data-rankpage]');if(rp){state.page=Math.max(0,Math.min(49,state.page+Number(rp.dataset.rankpage)));ranking(state.format);return}
 const drp=ev.target.closest('[data-discipline-page]');if(drp){state.disciplinePage=Math.max(0,Math.min(49,state.disciplinePage+Number(drp.dataset.disciplinePage)));ranking(state.format);return}
 const mp=ev.target.closest('[data-matchpage]');if(mp){state.matchPage=Math.max(0,Math.min(99,state.matchPage+Number(mp.dataset.matchpage)));fetchMatches();return}
 const detail=ev.target.closest('[data-match-innings]');if(detail){matchDetail(detail.dataset.matchInnings,detail.dataset.matchPlayer);return}
 const dm=ev.target.closest('[data-discipline-match]');if(dm){disciplineMatchDetail(dm.dataset.disciplineMatch);return}
});

$('#menu-button').addEventListener('click',()=>{const on=$('#sidebar').classList.toggle('open');$('#menu-button').setAttribute('aria-expanded',String(on))});
window.addEventListener('hashchange',()=>{state.page=0;state.disciplinePage=0;render()});
render();
})();