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
const METRICS={jawsPercentile:'JAWS-inspired percentile',quality:'Era-adjusted quality',
 teamCarry:'Team carry',careerGreatness:'Career greatness',peakQuality:'Peak quality'};
const DISCIPLINES={batting:'Batting',bowling:'Bowling',allrounder:'All-Rounders'};
function storedDiscipline(){
 try{const value=localStorage.getItem('cricket-discipline');
     return DISCIPLINES[value]?value:'batting'}catch{return 'batting'}
}
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const N=(v,d=1)=>v==null||!Number.isFinite(+v)?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:d});
const I=v=>N(v,0);
const state={view:'overview',discipline:storedDiscipline(),format:'test',metric:'jawsPercentile',search:'',country:'',
 page:0,matchFormat:'odi',matchPage:0,matchSearch:'',matchOpposition:'',
 first:null,second:null,compareFormat:'test',compareSearch:'',compareCandidates:[],comparePicked:{first:null,second:null},activeCompareSide:'first',
 disciplineFormat:'test',disciplineMetric:'greatness',disciplineSearch:'',disciplineCountry:'',disciplinePage:0};
let meta=null,disciplineMeta=null,requestSerial=0,compareSearchSerial=0,searchTimer;
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
 const selector=$('#discipline-selector');if(selector)selector.value=state.discipline;
 $('#sidebar').classList.remove('open');$('#menu-button').setAttribute('aria-expanded','false');
}
function panel(title,body){return '<section class="section"><div class="section-head"><h2>'+E(title)+'</h2></div>'+body+'</section>'}
function table(head,rows){
 return '<div class="table-scroller"><table><thead><tr>'+head.map(s=>'<th>'+E(s)+'</th>').join('')+
 '</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
}
async function loadDisciplineMeta(){
 if(!disciplineMeta)disciplineMeta=await get('disciplines');
 if(disciplineMeta.schemaVersion!=='cricket-discipline-projection-v1')
   throw new Error('Discipline API schema not approved');
 return disciplineMeta;
}
function formatOptions(current){
 return ALL.map(f=>'<option value="'+E(f)+'"'+(f===current?' selected':'')+'>'+E(LABEL[f])+'</option>').join('');
}
async function overview(){
 const discipline=state.discipline,modern=discipline!=='batting';
 hero('Who was <em>truly</em> the greatest?',
  (modern?'Explore provisional '+DISCIPLINES[discipline].toLowerCase()+
   ' scores using modern Cricsheet-qualified player identities.':
   'Explore batting greatness across Tests, ODIs and T20Is, with independent era-normalized research.'));
 let leaders={},formats={};
 if(modern){
   try{const source=await loadDisciplineMeta();leaders=source.leaders[discipline]||{};
       formats=source.formats[discipline]||{}}
   catch(e){showError($('#page-body'),e);return}
 }else{leaders=meta.leaders||{};formats=meta.formats||{}}
 const blocks=FORMATS.map(fmt=>['Eligible '+(fmt==='test'?'Test':fmt==='odi'?'ODI':'T20I')+' players',
   formats[fmt]?.qualifiedPlayers]);
 blocks.push([modern?'Research scope':'Observed Test matches',
   modern?'Modern Cricsheet only':meta.formats?.test?.observedDistinctMatches]);
 const tiles=blocks.map(([label,value])=>'<div class="stat"><small>'+E(label)+'</small><strong>'+
    E(typeof value==='string'?value:I(value))+'</strong></div>').join('');
 const leaderCards=FORMATS.map(fmt=>{
   const p=(leaders[fmt]||[])[0];
   const mainScore=modern?N(p?.greatness):N(p?.jawsPercentile);
   return '<a class="leader" href="#'+fmt+'"><small>'+E(LABEL[fmt])+'</small>'+
   '<h3>'+E(p?.name||'Unavailable')+'</h3><p>'+E(modern?'Greatness index':'JAWS percentile')+
   ' '+mainScore+' · '+I(p?.innings)+' innings</p><span>View ranking →</span></a>';
 }).join('');
 const cards=ALL.map(fmt=>'<a class="view-card" href="#'+fmt+'"><small>'+
   E(DISCIPLINES[discipline].toUpperCase())+'</small><strong>'+E(LABEL[fmt])+'</strong>'+
   '<p>'+E(COMBOS.includes(fmt)?'Cross-format comparisons for players eligible in every selected format.':
      'Explore ranked player summaries, profiles and model evidence.')+'</p>'+
   '<span>Explore →</span></a>').join('');
 $('#page-body').innerHTML='<div class="stat-grid">'+tiles+'</div>'+
   panel('Leaders by format · '+DISCIPLINES[discipline],'<div class="trio">'+leaderCards+'</div>')+
   panel('Explore '+DISCIPLINES[discipline].toLowerCase()+' rankings',
     '<div class="view-grid">'+cards+'</div>')+
   '<p class="note">'+(modern?
      'Bowling and all-rounder rankings are modern Cricsheet-only provisional outputs. Combined formats require the same verified provider ID in each constituent format. Historical all-era certification is incomplete.':
      'Batting rankings use the preserved, previously validated model outputs. Historic source data stays private; historical all-era completeness is not certified.')+
   '</p>';
}
const D_METRICS={
 bowling:{greatness:'Greatness index',quality:'Era & opponent peer quality',
          career:'Career value',peak:'Peak quality',wickets:'Wickets'},
 allrounder:{greatness:'All-rounder index',batting:'Batting percentile',
             bowling:'Bowling percentile',runs:'Runs',wickets:'Wickets'}
};
function disciplineForm(discipline){
 const options=Object.entries(D_METRICS[discipline]).map(([key,label])=>
   '<option value="'+E(key)+'"'+(key===state.disciplineMetric?' selected':'')+'>'+E(label)+'</option>').join('');
 return '<div class="controls">'+
 '<label>Rank by<select id="discipline-metric">'+options+'</select></label>'+
 '<label>Search player<input id="discipline-search" placeholder="Player or country" value="'+E(state.disciplineSearch)+'"></label>'+
 '<label>Country<input id="discipline-country" placeholder="Country" value="'+E(state.disciplineCountry)+'"></label></div>';
}
async function disciplineRanking(discipline,fmt){
 if(!D_METRICS[discipline])return;
 if(!D_METRICS[discipline][state.disciplineMetric])state.disciplineMetric='greatness';
 const serial=++requestSerial;
 const active=document.activeElement?.id||'';
 const caret=(active==='discipline-search'||active==='discipline-country')?
    document.activeElement.selectionStart:null;
 const heading=DISCIPLINES[discipline];
 hero(E(LABEL[fmt])+' <em>'+heading+' Greatness</em>',
  'Experimental '+heading.toLowerCase()+' rankings from modern Cricsheet-only qualified records.');
 $('#page-body').innerHTML=
 '<div class="callout">Research preview · Modern Cricsheet only. '+
 (COMBOS.includes(fmt)?'Combined scores average normalized within-format scores for players with verified matching IDs in every selected format.':
 'Historic bowling archives and unverified cross-source player identity merges are excluded.')+
 '</div>'+
 panel('Explore '+heading.toLowerCase()+' rankings',disciplineForm(discipline)+
    '<div id="discipline-results" class="panel">Loading bounded player results…</div>'+
    '<div id="discipline-profile"></div>');
 if(caret!==null){const field=$('#'+active);if(field){
    field.focus();field.setSelectionRange(caret,caret)}}
 try{
  const result=await get('discipline-rankings',{discipline,format:fmt,
     metric:state.disciplineMetric,search:state.disciplineSearch,
     country:state.disciplineCountry,page:state.disciplinePage});
  if(serial!==requestSerial||state.view!==fmt||state.discipline!==discipline)return;
  if(result.schemaVersion!=='cricket-discipline-projection-v1')
    throw new Error('Research result schema not approved');
  const headers=discipline==='bowling'?
    ['Rank','Bowler / country',D_METRICS[discipline][state.disciplineMetric],
     'Innings','Wickets','Quality','Career','Peak']:
    ['Rank','All-rounder / country',D_METRICS[discipline][state.disciplineMetric],
     'Batting innings','Runs','Wickets','Batting %ile','Bowling %ile'];
  const key=state.disciplineMetric;
  const rows=(result.items||[]).map((p,i)=>{
    const cols=discipline==='bowling'?
      [I(p.innings),I(p.wickets),N(p.quality),N(p.career),N(p.peak)]:
      [I(p.innings),I(p.runs),I(p.wickets),N(p.batting),N(p.bowling)];
    return '<tr><td>'+I(result.page*result.pageSize+i+1)+'</td><td>'+
     '<button class="text-link" data-discipline-player="'+E(p.playerId)+'">'+E(p.name)+
     '</button><span class="team">'+E(p.team)+'</span></td><td class="figure">'+
     N(p[key])+'</td>'+cols.map(v=>'<td>'+E(v)+'</td>').join('')+'</tr>';
  });
  const paging='<div class="pager"><button data-discipline-page="-1"'+
    (result.page===0?' disabled':'')+'>← Previous</button><span>Page '+
    (result.page+1)+' · '+I(result.total)+' players</span>'+
    '<button data-discipline-page="1"'+
    ((result.page+1)*result.pageSize>=result.total?' disabled':'')+'>Next →</button></div>';
  $('#discipline-results').innerHTML=
    (rows.length?table(headers,rows):'<p>No eligible players in this filter.</p>')+paging+
    '<p class="note">'+(COMBOS.includes(fmt)?
      'Combined scores are percentile-normalized within each format. Raw Test and limited-overs scores are not added.':
      'Provisional within-format model ranking.')+
    ' Click a player to review permitted summary metrics; raw source archives remain private.</p>';
 }catch(err){
  if(serial!==requestSerial)return;
  showError($('#discipline-results'),err);
 }
}
function disciplineProfileCard(p,discipline,fmt){
 if(!p)return '<div class="panel">Player profile unavailable.</div>';
 const fields=discipline==='bowling'?
  [['Greatness',p.greatness],['Quality',p.quality],
   ['Career',p.career],['Peak',p.peak],['Wickets',p.wickets],
   ['Bowling average',p.bowlingAverage],['Strike rate',p.strikeRate],
   ['Opponent peer evidence %',p.opponentEvidencePct]]:
  [['All-rounder index',p.greatness],['Batting percentile',p.batting],
   ['Bowling percentile',p.bowling],['Runs',p.runs],
   ['Wickets',p.wickets],['Batting innings',p.battingInnings??p.innings],
   ['Bowling innings',p.bowlingInnings]];
 const breakdown=Array.isArray(p.formatBreakdown)?
   panel('Format-by-format context',
     table(['Format','Within-format score','Format percentile','Innings','Wickets','Runs'],
     p.formatBreakdown.map(r=>'<tr><td>'+E(LABEL[r.format]||r.format)+'</td>'+
      '<td>'+N(r.greatness)+'</td><td>'+N(r.formatGreatnessPercentile)+'</td>'+
      '<td>'+I(r.innings)+'</td><td>'+I(r.wickets)+'</td><td>'+I(r.runs)+'</td></tr>'))):'';
 return '<article class="player-card"><small>'+E(p.team)+' · '+
    E(LABEL[fmt])+'</small><h3>'+E(p.name)+'</h3>'+
    '<div class="research-metric-grid">'+fields.map(([key,value])=>
    '<div><small>'+E(key)+'</small><b>'+N(value)+'</b></div>').join('')+'</div>'+
    breakdown+
    '<p class="note">Provisional modern-only Cricsheet research. Unverified historical identities and raw source records are not published.</p></article>';
}
async function disciplineProfile(discipline,id,fmt=state.format,selector='#discipline-profile'){
 const area=$(selector);if(!area)return;
 area.innerHTML='<div class="panel">Loading player summary…</div>';
 try{
  const payload=await get('discipline-player',{discipline,format:fmt,playerId:id});
  if(area.isConnected)area.innerHTML=disciplineProfileCard(payload.player,discipline,fmt);
 }catch(err){if(area.isConnected)showError(area,err)}
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
function comparisonQuery(){
 const params={format:state.compareFormat,search:state.compareSearch,page:0};
 if(state.discipline==='batting')return get('rankings',params);
 return get('discipline-rankings',{...params,discipline:state.discipline});
}
function comparisonOptions(side){
 const entries=[...state.compareCandidates];
 const chosen=state.comparePicked[side];
 if(chosen&&!entries.some(p=>p.playerId===chosen.playerId))entries.unshift(chosen);
 const current=state[side]||'';
 return '<option value="">Select '+(side==='first'?'first':'second')+' player</option>'+
 entries.map(p=>'<option value="'+E(p.playerId)+'"'+
  (p.playerId===current?' selected':'')+'>'+E(p.name)+' · '+E(p.team)+'</option>').join('');
}
function updateComparisonSelects(){
 for(const side of ('first,second').split(',')){
   const field=$('#compare-'+side+'-select');
   if(field)field.innerHTML=comparisonOptions(side);
 }
}
async function comparisonProfiles(){
 const discipline=state.discipline,fmt=state.compareFormat;
 for(const side of ('first,second').split(',')){
   const area=$('#compare-'+side+'-result');
   if(!area)continue;
   const pid=state[side];
   if(!pid){area.innerHTML='<div class="panel empty-compare">Choose a player above to compare.</div>';continue}
   if(discipline==='batting')showProfile(fmt,pid,'#compare-'+side+'-result');
   else disciplineProfile(discipline,pid,fmt,'#compare-'+side+'-result');
 }
}
function chooseComparison(side,id){
 if(!['first','second'].includes(side))return;
 state[side]=id||null;
 const selected=state.compareCandidates.find(p=>p.playerId===id);
 if(selected)state.comparePicked[side]=selected;
 if(!id)state.comparePicked[side]=null;
 updateComparisonSelects();
 comparisonProfiles();
}
async function compare(){
 hero('Player <em>Comparison Lab</em>',
  'Compare two players using consistent '+DISCIPLINES[state.discipline].toLowerCase()+
  ' scores for the selected format and model. Cross-format scores use normalized percentiles.');
 const fmt=state.compareFormat;
 $('#page-body').innerHTML='<section class="section"><div class="controls">'+
 '<label>Ranking type<select id="compare-discipline">'+
 Object.entries(DISCIPLINES).map(([key,label])=>'<option value="'+E(key)+'"'+
  (state.discipline===key?' selected':'')+'>'+E(label)+'</option>').join('')+
 '</select></label>'+
 '<label>Format<select id="compare-format">'+formatOptions(fmt)+'</select></label>'+
 '<label>Find players<input id="compare-search" value="'+E(state.compareSearch)+
 '" placeholder="Search names or countries…"></label></div>'+
 '<div class="comparison-selects">'+
 '<label>First player<select id="compare-first-select">'+comparisonOptions('first')+'</select></label>'+
 '<label>Second player<select id="compare-second-select">'+comparisonOptions('second')+'</select></label>'+
 '</div><div id="compare-hits" class="panel">Searching eligible player summaries…</div>'+
 '<div class="controls comparison-side-buttons"><span>Assign a search result to:</span>'+
 '<button id="compare-side-first" type="button"'+(state.activeCompareSide==='first'?' class="selected"':'')+'>First player</button>'+
 '<button id="compare-side-second" type="button"'+(state.activeCompareSide==='second'?' class="selected"':'')+'>Second player</button></div>'+
 '<div class="player-grid"><div id="compare-first-result"></div>'+
 '<div id="compare-second-result"></div></div></section>';
 await comparisonProfiles();
 if(!state.compareSearch){
   try{
     const leaders=state.discipline==='batting'?meta.leaders:
       (await loadDisciplineMeta()).leaders[state.discipline];
     state.compareSearch=(leaders[fmt]||[])[0]?.name||'';
     const input=$('#compare-search');
     if(input)input.value=state.compareSearch;
   }catch(e){showError($('#compare-hits'),e);return}
 }
 searchComparison();
}
async function searchComparison(){
 const area=$('#compare-hits');if(!area)return;
 const serial=++compareSearchSerial,discipline=state.discipline,fmt=state.compareFormat;
 try{
   const d=await comparisonQuery();
   if(serial!==compareSearchSerial||!area.isConnected||state.discipline!==discipline||
      state.compareFormat!==fmt)return;
   const items=d.items||[];
   state.compareCandidates=items;
   updateComparisonSelects();
   area.innerHTML=(items.length?items.map(p=>'<button class="text-link comparison-hit" type="button" '+
   'data-compare-id="'+E(p.playerId)+'">'+E(p.name)+' · '+E(p.team)+'</button>').join(''):
   '<p>No eligible players found for this search and format.</p>')+
   '<p class="note">Choose a player in each dropdown, or assign a search result to the highlighted side.</p>';
 }catch(e){
   if(serial===compareSearchSerial)showError(area,e);
 }
}
async function matches(){
 if(state.discipline!=='batting'){
   hero('Match <em>Explorer</em>',
     'Explore international cricket with source-backed match evidence.');
   $('#page-body').innerHTML='<div class="callout">The existing bounded Match Explorer contains batting innings only. '+
      'Verified per-match '+E(DISCIPLINES[state.discipline].toLowerCase())+
      ' figures are not yet available in the public API, so batting innings will not be mislabeled as bowling or all-rounder match analysis.</div>'+
      panel('Research available now','<p>Player-level '+E(DISCIPLINES[state.discipline].toLowerCase())+
       ' rankings and profiles are available by international format.</p>'+
       '<div class="view-grid">'+FORMATS.map(fmt=>'<a class="view-card" href="#'+fmt+'"><strong>'+
         E(LABEL[fmt])+'</strong><span>View player rankings →</span></a>').join('')+'</div>');
   return;
 }
 hero('Match <em>Explorer</em>',
 'Bounded Cricsheet-derived batting innings through the private-backed API, never a bulk source file.');
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
async function coverage(){
 hero('Data, coverage & <em>limitations</em>',
   'An account of the evidence supporting '+DISCIPLINES[state.discipline].toLowerCase()+
   ' models, not official complete all-time scorecards.');
 if(state.discipline!=='batting'){
   let data;
   try{data=await loadDisciplineMeta()}catch(err){showError($('#page-body'),err);return}
   const formats=data.formats[state.discipline]||{};
   const rows=ALL.map(fmt=>{
     const record=formats[fmt]||{};
     return '<tr><td>'+E(LABEL[fmt])+'</td><td>'+I(record.qualifiedPlayers)+'</td>'+
       '<td>'+E(COMBOS.includes(fmt)?'Shared eligible provider IDs':'Modern Cricsheet only')+'</td></tr>';
   });
   $('#page-body').innerHTML=panel('Eligible '+DISCIPLINES[state.discipline].toLowerCase()+' by format',
       table(['Format','Qualified players','Coverage basis'],rows))+
       '<div class="callout">Older restricted historical source data is not released into these public rankings. '+
       'Cross-era player identities, an official match-level census and historical completeness remain uncertified. '+
       'For combined formats, each player must be independently qualified in every constituent format.</div>';
   return;
 }
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
 const discipline=state.discipline;
 hero('How the <em>index works</em>',
   'A plain-language explanation of '+DISCIPLINES[discipline].toLowerCase()+
   ' scores. The data and research models remain private.');
 const items=discipline==='bowling'?[
  ['Era and opposition peers','Compare wickets per legal ball and runs conceded to bowlers from the same source tier within a ±3-year window, excluding the player. Opponent-specific peer evidence is used only when sufficiently supported.'],
  ['Bowling quality','Combine observed wicket-rate advantage (70%) and runs-conceded advantage (30%) with bounded log-ratio adjustments and evidence shrinkage.'],
  ['Career and peak','Score the whole observed career and the best seven seasons; report a JAWS-inspired average of career and peak.'],
  ['Evidence limitations','Opposition conditioning is a peer-outcome proxy, not independently certified opponent batting strength, pitch or venue adjustment.']
 ]:discipline==='allrounder'?[
  ['Batting contribution','Within each format, percentile-rank batting greatness among qualified batters.'],
  ['Bowling contribution','Within the same format, percentile-rank bowling greatness among qualified bowlers.'],
  ['Two-way index','Combine batting and bowling percentiles with their harmonic mean; both disciplines must be present, which penalizes one-sided specialists.'],
  ['Verified identity','Automatically join only the same immutable Cricsheet player ID and compatible team. Historical name-based matching is excluded.'],
  ['Multiple formats','For Tests + ODIs and All Three Formats, average separately normalized format percentiles only for players qualified in every selected format.']
 ]:[
  ['Era-adjusted quality','Compare player performance with peers in the same era and format.'],
  ['Opposition','Adjust using opponent strength proxies where available.'],
  ['Team carry','Estimate contribution relative to the observed teammates.'],
  ['Home and away','Account for known host conditions, leaving uncertain venues unknown.'],
  ['Peak and longevity','Show career, best seasons, short-term peak and JAWS-inspired indices.']
 ];
 if(discipline==='bowling'){
  items.push(['Multiple formats','For combined formats, aggregate within-format greatness percentiles across verified provider IDs, not incompatible raw scores.']);
 }
 $('#page-body').innerHTML=panel(DISCIPLINES[discipline]+' model overview',
  '<div class="trio">'+items.map(([a,b])=>
  '<article class="panel"><h3>'+E(a)+'</h3><p>'+E(b)+'</p></article>').join('')+
  '</div><p class="note">Scores are provisional research outputs, not official all-time certifications.</p>');
}
function setDiscipline(discipline){
 if(!DISCIPLINES[discipline]||state.discipline===discipline)return;
 state.discipline=discipline;
 try{localStorage.setItem('cricket-discipline',discipline)}catch{}
 state.page=0;state.disciplinePage=0;state.disciplineMetric='greatness';
 state.disciplineCountry='';state.disciplineSearch='';
 state.first=null;state.second=null;state.comparePicked={first:null,second:null};
 state.compareCandidates=[];state.compareSearch='';state.activeCompareSide='first';
 compareSearchSerial++;
 render();
}
async function render(){
 let route=currentRoute();
 if(route==='bowling'||route==='allrounder'){
   // Existing shared links now use the same Test/ODI/T20I routes.
   state.discipline=route;
   try{localStorage.setItem('cricket-discipline',route)}catch{}
   location.hash='#test';
   return;
 }
 state.view=route;navigation(route);
 if(!meta){try{meta=await get('bootstrap')}catch(e){showError($('#page-body'),e);return}}
 const notice=$('#research-notice');
 if(notice)notice.textContent=state.discipline==='batting'?
   'Batting: preserved historical derived model. Completeness is provisional; original source data remains private.':
   DISCIPLINES[state.discipline]+': verified modern Cricsheet-only display outputs; historical cross-era completeness unverified.';
 if(route==='overview')await overview();
 else if(ALL.includes(route)){
    state.format=route;
    if(state.discipline==='batting')await ranking(route);
    else await disciplineRanking(state.discipline,route);
 }
 else if(route==='compare')await compare();
 else if(route==='matches')await matches();
 else if(route==='methodology')methodology();
 else if(route==='coverage')await coverage();
 $('#sidebar-status').textContent=DISCIPLINES[state.discipline]+' · Private-backed research';
}
function delayed(callback){clearTimeout(searchTimer);searchTimer=setTimeout(callback,280)}
document.addEventListener('input',ev=>{
 if(ev.target.id==='output-search'){
   state.search=ev.target.value;state.page=0;
   delayed(()=>{if(state.discipline==='batting'&&ALL.includes(state.view))ranking(state.format)});
 }
 if(ev.target.id==='output-country'){
   state.country=ev.target.value;state.page=0;
   delayed(()=>{if(state.discipline==='batting'&&ALL.includes(state.view))ranking(state.format)});
 }
 if(ev.target.id==='discipline-search'){
   state.disciplineSearch=ev.target.value;state.disciplinePage=0;
   delayed(()=>{if(state.discipline!=='batting'&&ALL.includes(state.view))
      disciplineRanking(state.discipline,state.format)});
 }
 if(ev.target.id==='discipline-country'){
   state.disciplineCountry=ev.target.value;state.disciplinePage=0;
   delayed(()=>{if(state.discipline!=='batting'&&ALL.includes(state.view))
      disciplineRanking(state.discipline,state.format)});
 }
 if(ev.target.id==='compare-search'){
   state.compareSearch=ev.target.value;
   delayed(()=>{if(state.view==='compare')searchComparison()});
 }
 if(ev.target.id==='match-search'){state.matchSearch=ev.target.value;state.matchPage=0;delayed(fetchMatches)}
 if(ev.target.id==='match-opposition'){state.matchOpposition=ev.target.value;state.matchPage=0;delayed(fetchMatches)}
});
document.addEventListener('change',ev=>{
 if(ev.target.id==='discipline-selector'||ev.target.id==='compare-discipline'){
   setDiscipline(ev.target.value);
   return;
 }
 if(ev.target.id==='output-metric'){state.metric=ev.target.value;state.page=0;ranking(state.format)}
 if(ev.target.id==='discipline-metric'){
   state.disciplineMetric=ev.target.value;state.disciplinePage=0;
   disciplineRanking(state.discipline,state.format);
 }
 if(ev.target.id==='compare-format'){
   state.compareFormat=ev.target.value;state.first=null;state.second=null;
   state.comparePicked={first:null,second:null};
   state.compareCandidates=[];state.compareSearch='';compare();
 }
 if(ev.target.id==='compare-first-select')chooseComparison('first',ev.target.value);
 if(ev.target.id==='compare-second-select')chooseComparison('second',ev.target.value);
 if(ev.target.id==='match-format'){state.matchFormat=ev.target.value;state.matchPage=0;matches()}
});
document.addEventListener('click',ev=>{
 const dp=ev.target.closest('[data-discipline-player]');
 if(dp){disciplineProfile(state.discipline,dp.dataset.disciplinePlayer,state.format);return}
 const rp2=ev.target.closest('[data-discipline-page]');
 if(rp2){state.disciplinePage=Math.max(0,Math.min(49,
    state.disciplinePage+Number(rp2.dataset.disciplinePage)));
    disciplineRanking(state.discipline,state.format);return}
 const p=ev.target.closest('[data-player]');if(p){showProfile(state.format,p.dataset.player);return}
 const rp=ev.target.closest('[data-rankpage]');
 if(rp){state.page=Math.max(0,Math.min(49,state.page+Number(rp.dataset.rankpage)));ranking(state.format);return}
 const mp=ev.target.closest('[data-matchpage]');
 if(mp){state.matchPage=Math.max(0,Math.min(99,state.matchPage+Number(mp.dataset.matchpage)));fetchMatches();return}
 const detail=ev.target.closest('[data-match-innings]');
 if(detail){matchDetail(detail.dataset.matchInnings,detail.dataset.matchPlayer);return}
 const side=ev.target.closest('[id^=compare-side-]');
 if(side){
   state.activeCompareSide=side.id.slice('compare-side-'.length);
   document.querySelectorAll('.comparison-side-buttons button').forEach(
     button=>button.classList.toggle('selected',button.id===side.id));
   return;
 }
 const chosen=ev.target.closest('[data-compare-id]');
 if(chosen)chooseComparison(state.activeCompareSide,chosen.dataset.compareId);
});
$('#menu-button').addEventListener('click',()=>{const on=$('#sidebar').classList.toggle('open');$('#menu-button').setAttribute('aria-expanded',String(on))});
window.addEventListener('hashchange',()=>{state.page=0;state.disciplinePage=0;render()});
render();
})();