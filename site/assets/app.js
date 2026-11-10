/* Cricket Greatness Lab · unified v0.4 scorecard-era application.
   Exactly one public primary methodology. Historical source innings are never exposed.
   Match explorer exclusively uses licensed modern Cricsheet-derived observations. */
(()=>{'use strict';
const FORMATS=['test','odi','t20i'],COMBOS=['test_odi','all_three'];
const LABEL={overview:'Overview',test:'Test Cricket',odi:'One-Day Internationals',t20i:'T20 Internationals',test_odi:'Tests + ODIs',all_three:'All Three Formats',compare:'Batter Comparison',matches:'Match Explorer',methodology:'Index Methodology',coverage:'Data & Coverage'};
const SHOW={quality:'Era-adjusted quality',teamCarry:'Team carry',careerGreatness:'Career greatness',peakQuality:'Peak (25 innings)',jawsPercentile:'JAWS-inspired percentile',jawsStyleValue:'JAWS-style value'};
const COMBO={quality:'overallQualityPercentile',teamCarry:'overallCarryPercentile',careerGreatness:'overallCareerPercentile',peakQuality:'overallPeakPercentile',jawsPercentile:'overallJawsPercentile',jawsStyleValue:'overallJawsPercentile'};
const $=s=>document.querySelector(s),E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const N=(v,d=1)=>v==null||!Number.isFinite(+v)?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const I=v=>N(v,0);
const docs={};
const state={view:'overview',metric:'quality',search:'',country:'All',minimum:35,compareFormat:'test',first:'',second:'',matchPlayer:'',matchFormat:'odi',matchOpposition:'',matchSearch:'',matchOrder:'date',matchPage:0,sortDesc:true};
const matchLimit=65;
let modernInnings=null,modernError=null;

function url(p){return 'data/'+p+'.json'}
async function fetchJSON(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error('Unable to load '+path+' ('+r.status+')');return r.json()}
const isCombined=f=>COMBOS.includes(f);
const current=f=>docs[f];
const players=f=>isCombined(f)?(docs.combined?.combined?.[f]||[]):(docs[f]?.players||[]);
const score=(p,m,f)=>isCombined(f)?p[COMBO[m]]:(m==='peakQuality'?p.peakQuality?.index:p[m]);
const scoreName=(m,f)=>isCombined(f)?SHOW[m]+' · within-format percentile':SHOW[m];
const modelReady=()=>FORMATS.every(f=>docs[f]?.scorecardCommonDenominator&&docs[f]?.modernOnlyFeaturesInPrimaryModel===false)&&docs.combined?.allTimeCertified===false;
function showNotice(){
 const notice=$('#research-notice');
 if(modelReady()){
  notice.className='research-notice ready';
  notice.innerHTML='<strong>One historically comparable batting framework.</strong> Tests, ODIs and T20Is use the same scorecard-level model; combined views use eligible format percentiles. <b>Research estimates, not certified all-time rankings.</b>';
  $('#sidebar-status').textContent='Data computed · '+(docs.test?.generatedUTC||'').slice(0,10);
 }else{notice.className='research-notice';notice.textContent='The research model is unavailable. Rankings will not be replaced by the old incompatible index.'}
}
function nav(f){if(!LABEL[f])f='overview';state.view=f;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===f));$('#breadcrumb').textContent=LABEL[f].toUpperCase();const side=$('#sidebar');side.classList.remove('open');$('#menu-button').setAttribute('aria-expanded','false')}
function go(f){location.hash='#'+f;if(state.view===f)render()}
const metricOptions=(f,selected)=>Object.keys(SHOW).map(m=>'<option value="'+m+'"'+(m===selected?' selected':'')+'>'+E(scoreName(m,f))+'</option>').join('');
function hero(title,desc,eyebrow='SOURCE-BACKED BATTING RESEARCH · EXPERIMENTAL'){
 $('#page-header').innerHTML='<div class="eyebrow">'+E(eyebrow)+'</div><h1>'+title+'</h1><p>'+E(desc)+'</p>';
}
function naviTiles(){
 return '<div class="view-grid">'+[['test','Test Cricket','From Bradman and Sobers to Tendulkar, Smith, Root and Kohli.'],['odi','One-Day Internationals','Richards, Tendulkar, Kohli and the greatest ODI careers.'],['t20i','T20 Internationals','Contextual T20 batting and teammate contributions.'],['test_odi','Tests + ODIs','Historically broad two-format greatness.'],['all_three','All Three Formats','Only those eligible in each format; never penalize pre-T20I generations.'],['compare','Batter Comparison','Compare any eligible batters and their opponent/venue splits.']].map(([f,t,d])=>'<a class="view-card" href="#'+f+'"><small>'+E(f.replaceAll('_',' ').toUpperCase())+'</small><strong>'+E(t)+'</strong><p>'+E(d)+'</p><span>View research →</span></a>').join('')+'</div>'
}
function rowsFmt(report,f){const arr=players(f);return arr.slice().sort((a,b)=>(score(b,'quality',f)??-1e12)-(score(a,'quality',f)??-1e12))}
function overview(){
 hero('Who was <em>truly</em> the greatest?','One analytical framework for batting greatness across international cricket history. Same scorecard fields in every era; detailed modern data never create an unfair historical bonus.');
 if(!modelReady())return '<div class="panel">The current-model datasets are not available. No legacy leaderboards are shown.</div>';
 const sample=FORMATS.map(f=>docs[f].qualifiedPlayers);
 const top=FORMATS.map(f=>({format:f,item:rowsFmt(docs[f],f)[0]}));
 const comboNames=[['test_odi','Tests + ODIs'],['all_three','All Three Formats']];
 return '<div class="stat-grid">'+[
  ['Tests analyzed',I(docs.test.observedDistinctMatches),'Observed historic + modern source matches'],
  ['ODIs analyzed',I(docs.odi.observedDistinctMatches),'Observed historic + modern source matches'],
  ['T20Is analyzed',I(docs.t20i.observedDistinctMatches),'Observed historic + modern source matches'],
  ['Eligible batters',sample.map(I).join(' / '),'Test / ODI / T20I samples']
 ].map(([a,b,c])=>'<div class="stat"><small>'+a+'</small><strong>'+b+'</strong><span>'+c+'</span></div>').join('')+'</div>'+
 '<section class="section"><div class="section-head"><h2>What we measure</h2><span>Separate answers, not one forced winner</span></div><div class="trio">'+[
 ['01 · QUALITY','Era-adjusted batting quality','Runs and dismissal survival relative to contemporaries, adjusted for opposing nation, home/away and same-match scoring context.'],
 ['02 · IMPACT','Team carry','Was an innings outstanding compared with the other players in the same batting lineup?'],
 ['03 · LEGACY','Peak & career greatness','Separate peak and career metrics, plus a JAWS-inspired career/7-best-season index.']
 ].map(([num,t,d])=>'<article class="panel"><small>'+num+'</small><h3>'+t+'</h3><p>'+d+'</p></article>').join('')+'</div></section>'+
 '<section class="section"><div class="section-head"><h2>Leading batters by format</h2><span>One shared v0.4 era-adjusted quality measure</span></div><div class="trio">'+top.map(({format:f,item:p})=>'<a class="leader" href="#'+f+'"><small>'+E(LABEL[f].toUpperCase())+'</small><h3>'+E(p?.name||'Not available')+'</h3><p>Era-adjusted quality <b>'+N(p?.quality)+'</b> · '+I(p?.innings)+' innings</p><span>Open '+E(LABEL[f])+' analysis →</span></a>').join('')+'</div><p class="note">These leaders are based on the new scorecard-era model, not the previously published modern-only ranking. Minimum eligible innings and source coverage still matter.</p></section>'+
 '<section class="section"><div class="section-head"><h2>Cross-format greatness</h2><span>Format-normalized JAWS-inspired percentiles</span></div><div class="two">'+comboNames.map(([f,t])=>{let p=players(f)[0];return '<a class="leader" href="#'+f+'"><small>'+E(t.toUpperCase())+'</small><h3>'+E(p?.name||'Not available')+'</h3><p>Composite percentile '+N(p?.overallJawsPercentile)+' · '+I(players(f).length)+' eligible players</p><span>Compare across formats →</span></a>'}).join('')+'</div><p class="note">The three-format ranking includes only players who participated and qualified in each format. Earlier generations are excluded by eligibility, never assigned zero.</p></section>'+
 '<section class="section"><div class="section-head"><h2>Explore the research</h2></div>'+naviTiles()+'</section>'+
 '<section class="section"><div class="section-head"><h2>How the adjustments work</h2><a href="#methodology">Full methodology →</a></div>'+adjustmentContent(false)+'</section>';
}
function adjustmentContent(full){
 const points=[
 ['Era','Reference each batter against nearby-year peers, leaving the evaluated batter out of their own baseline.'],
 ['Opponent quality','Score how other batters fared against the opposing nation. Historical individual bowlers faced are not consistently recorded.'],
 ['Home / away','Distinguish home, away and neutral conditions when the host is known; unknown venues stay unadjusted.'],
 ['Match difficulty','Use other batters in the same Test, ODI or T20I as a shrunken proxy for scoring conditions, not a physical pitch rating.'],
 ['Team carry','Compare a score with teammates in the same innings; a 70 amid a collapse gets more carry credit than a 70 in an easy high-scoring game.'],
 ['Peak and longevity','Show best 25-innings quality, career quality and a JAWS-inspired average of career and seven strongest calendar-season contextual surplus.']
 ];
 return '<div class="adjustments">'+points.map(([t,d])=>'<div class="adjustment"><b>'+E(t)+'</b><p>'+E(d)+'</p></div>').join('')+'</div>'+(full?'<p class="note">Each adjustment is observational and conservative, with missing data disclosed. The same input fields are used for both historical and modern batters; no historic player is penalized for missing deliveries.</p>':'');
}
function tableData(f){
 const multi=isCombined(f),list=players(f);
 const choices=[...new Set(list.map(p=>p.team))].sort((a,b)=>a.localeCompare(b));
 const minimum=docs[f]?.qualificationMinimumInnings||35;
 let ms=multi?'jawsPercentile':'quality';
 if(!SHOW[state.metric])state.metric=ms;
 if(multi&&state.metric==='jawsStyleValue')state.metric='jawsPercentile';
 if(!multi&&state.metric==='jawsPercentile')state.metric='quality';
 state.minimum=multi?0:(state.minimum||minimum);
 const val=p=>score(p,state.metric,f);
 const filtered=list.filter(p=>(multi||p.innings>=state.minimum)&&(state.country==='All'||p.team===state.country)&&((p.name+' '+p.team).toLowerCase().includes(state.search.toLowerCase())));
 filtered.sort((a,b)=>(val(b)??-1e15)-(val(a)??-1e15));
 return {filtered,multi,minimum,choices};
}
function perFormat(f){
 hero(E(LABEL[f])+' <em>Batting Greatness</em>',isCombined(f)?'Equal-weight percentile comparisons among batters qualifying in every required format. Missing formats are not treated as poor performance.':'Historical and modern batting evaluated using identical scorecard-based era, opponent, venue and match-context controls.');
 if(!current(f)&&!isCombined(f))return '<div class="panel">No validated '+E(LABEL[f])+' model output available.</div>';
 const {filtered,multi,minimum,choices}=tableData(f);
 const options=metricOptions(f,state.metric);
 const metricTitle=isCombined(f)?'Format-normalized percentile':'Research index';
 const rows=filtered.slice(0,300).map((p,i)=>{
  const raw=score(p,state.metric,f),ci=multi?null:(state.metric==='quality'?p.qualityInterval90:state.metric==='teamCarry'?p.teamCarryInterval90:null);
  return '<tr><td>'+(i+1)+'</td><td><button class="text-link" data-profile="'+E(p.playerId)+'" data-profile-format="'+f+'"><b>'+E(p.name)+'</b></button><span class="team">'+E(p.team)+'</span></td>'+
   '<td class="figure">'+N(raw)+'</td><td>'+(ci?N(ci[0])+'–'+N(ci[1]):'—')+'</td>'+
   '<td>'+I(multi?p.totalInnings:p.innings)+'</td><td>'+(multi?'—':I(p.runs))+'</td>'+
   '<td>'+N(multi?p.overallQualityPercentile:p.quality)+'</td>'+
   '<td>'+N(multi?p.overallCarryPercentile:p.teamCarry)+'</td>'+
   '<td>'+N(multi?p.overallJawsPercentile:p.jawsPercentile)+'</td></tr>';
 }).join('');
 const list='<div class="table-scroller"><table><thead><tr><th>Rank</th><th>Batter / country</th><th>'+E(metricTitle)+'</th><th>90% interval*</th><th>Innings</th><th>Runs</th><th>Quality</th><th>Carry</th><th>JAWS %ile</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
 const metrics=multi?'<div class="callout">These values are within-format percentile combinations, not raw Test/ODI/T20I score sums. '+(f==='all_three'?'Players who retired before international T20 are not eligible.':'Players must qualify in both Tests and ODIs.')+'</div>':
 '<div class="mini-stats">'+[['Observed innings',I(docs[f].observedTestInnings)],['Historic batting innings',I(docs[f].historicalTestInnings)],['Eligible batters',I(docs[f].qualifiedPlayers)],['Career peak','Seven best seasons + 25-innings peak']].map(([t,v])=>'<div><small>'+t+'</small><strong>'+v+'</strong></div>').join('')+'</div>';
 return metrics+'<section class="section"><div class="section-head"><h2>'+E(LABEL[f])+' rankings</h2><span>'+I(filtered.length)+' eligible batters · 100 = contextual parity for quality</span></div>'+
 '<div class="controls"><label>Rank by<select id="rank-metric">'+options+'</select></label><label>Search batter<input id="rank-search" value="'+E(state.search)+'" placeholder="Search by name or country"></label><label>Country<select id="rank-country"><option>All</option>'+choices.map(c=>'<option'+(c===state.country?' selected':'')+'>'+E(c)+'</option>').join('')+'</select></label>'+
 (multi?'':'<label>Minimum innings<select id="rank-min">'+[minimum,70,120,180].filter((v,i,a)=>v>=minimum&&a.indexOf(v)===i).map(v=>'<option value="'+v+'"'+(state.minimum===v?' selected':'')+'>'+v+'+</option>').join('')+'</select></label>')+'</div>'+list+
 '<p class="note">*Only quality and carry have conditional match-block bootstrap intervals; model and historical-source uncertainty are not included. Click a name for detailed opponent, home/away and peak comparisons.</p></section>'+
 '<section class="section"><div class="section-head"><h2>Make a comparison</h2></div><p class="note">Compare players using the same metric and the same eligible format. <a href="#compare">Open full player comparison →</a></p></section>'+
 '<section class="section"><div class="section-head"><h2>Methodological controls</h2></div>'+adjustmentContent(false)+'</section>';
}
function playerOptions(f){
 return players(f).slice().sort((a,b)=>a.name.localeCompare(b.name)).map(p=>'<option value="'+E(p.playerId)+'">'+E(p.name)+' · '+E(p.team)+'</option>').join('');
}
function lookup(f,id){return players(f).find(p=>p.playerId===id)||null}
function splits(rows,attr,detail){
 if(!rows?.length)return '<tr><td colspan="3">Insufficient observations for this split</td></tr>';
 return rows.slice(0,12).map(r=>'<tr><td>'+E(r[attr])+'</td><td>'+I(r.innings)+'</td><td>'+N(r.quality)+(detail&&r.average!=null?' · '+N(r.average,2)+' avg':'')+'</td></tr>').join('');
}
function playerCard(p,f){
 if(!p)return '<article class="panel">Select an eligible batter</article>';
 if(isCombined(f)){
  return '<article class="player-card"><small>'+E(p.team)+'</small><h3>'+E(p.name)+'</h3>'+
   '<div class="inline-metrics">'+[['Overall JAWS %ile',p.overallJawsPercentile],['Quality %ile',p.overallQualityPercentile],['Carry %ile',p.overallCarryPercentile]].map(([t,v])=>'<div><small>'+t+'</small><b>'+N(v)+'</b></div>').join('')+'</div>'+
   '<table><thead><tr><th>Format</th><th>Innings</th><th>Quality</th><th>JAWS %ile</th></tr></thead><tbody>'+
   Object.entries(p.formats).map(([fmt,d])=>'<tr><td>'+E(LABEL[fmt])+'</td><td>'+I(d.innings)+'</td><td>'+N(d.quality)+'</td><td>'+N(d.jawsPercentile)+'</td></tr>').join('')+'</tbody></table>'+
   '<p class="note">The composite is the equal-weight mean of eligible within-format percentile measures, not a directly interpretable batting average.</p></article>';
 }
 const ci=p.qualityInterval90;
 const pct=p.jawsPercentile;
 return '<article class="player-card"><small>'+E(p.team)+' · '+I(p.innings)+' innings · '+E(p.careerStart)+'–'+E(p.careerEnd)+'</small><h3>'+E(p.name)+'</h3>'+
  '<div class="inline-metrics">'+[['Quality',p.quality],['Team carry',p.teamCarry],['JAWS %ile',pct]].map(([t,v])=>'<div><small>'+t+'</small><b>'+N(v)+'</b></div>').join('')+'</div>'+
  '<p class="note">Runs '+I(p.runs)+' · Average '+N(p.average,2)+' · Quality 90% conditional interval '+(ci?N(ci[0])+'–'+N(ci[1]):'unavailable')+' · Historical batting innings '+I(p.historicalInnings)+'.</p>'+
  '<div class="value-pair"><span>Career greatness <b>'+N(p.careerGreatness)+'</b></span><span>Peak 25-innings quality <b>'+N(p.peakQuality?.index)+'</b></span></div>'+
  '<p class="note">JAWS-inspired same-units value: career surplus '+N(p.careerValue)+'; seven best calendar seasons '+N(p.bestSevenSeasonValue)+'; blended value '+N(p.jawsStyleValue)+'. Peak seasons: '+E((p.bestSevenSeasons||[]).join(', '))+'. These are not baseball WAR.</p>'+
  (p.careerCheck?'<div class="callout">Reference career check: runs '+(p.careerCheck.runsMatch?'MATCH':'MISMATCH')+', innings '+(p.careerCheck.inningsMatch?'MATCH':'MISMATCH')+'. Totals alone do not certify all scorecards.</div>':'')+
  '<h4>Against opposing nations</h4><table><tbody>'+splits(p.opponents,'opponent',true)+'</tbody></table>'+
  '<h4>Home, away and neutral</h4><table><tbody>'+splits(p.venues,'venueClass',false)+'</tbody></table>'+
  '<h4>Opponent × venue</h4><table><tbody>'+(p.opponentAndVenue||[]).slice(0,10).map(r=>'<tr><td>'+E(r.opponent)+' · '+E(r.venueClass)+'</td><td>'+I(r.innings)+'</td><td>'+N(r.quality)+'</td></tr>').join('')+'</tbody></table>'+
  '<h4>Remove a model adjustment</h4><table><tbody>'+[['All adjustments',p.quality],['Without opposition',p.sensitivity?.withoutOpposition],['Without venue',p.sensitivity?.withoutVenue],['Without match difficulty',p.sensitivity?.withoutMatchContext]].map(([k,v])=>'<tr><td>'+k+'</td><td>'+N(v)+'</td></tr>').join('')+'</tbody></table>'+
  '<p class="note">Known venue '+N(p.venueKnownPct)+'% · Opposition evidence '+N(p.opponentEvidencePct)+'% · Same-match evidence '+N(p.peerMatchEvidencePct)+'%. Opposing nation difficulty and match scoring are proxies; historical bowlers and measured pitches cannot be reconstructed.</p></article>';
}
function compare(){
 hero('Batter <em>Comparison Lab</em>','Compare historical and modern batters under identical format-specific scorecard definitions. Opponent, away, team carry, peak and career context are visible on both sides.');
 const f=state.compareFormat;
 const options=playerOptions(f);
 const ps=players(f);
 if(!ps.length)return '<div class="panel">Comparison data unavailable.</div>';
 if(!lookup(f,state.first))state.first=(ps.find(p=>p.name==='Don Bradman')||ps.find(p=>p.name==='Sachin Tendulkar')||ps[0]).playerId;
 if(!lookup(f,state.second))state.second=(ps.find(p=>p.name==='Virat Kohli')||ps[1]||ps[0]).playerId;
 return '<div class="controls"><label>Format<select id="compare-format">'+[...FORMATS,...COMBOS].map(x=>'<option value="'+x+'"'+(x===f?' selected':'')+'>'+E(LABEL[x])+'</option>').join('')+'</select></label>'+
 '<label>First batter<select id="compare-first">'+options+'</select></label><label>Second batter<select id="compare-second">'+options+'</select></label></div>'+
 '<div class="player-grid" id="comparison-profiles">'+playerCard(lookup(f,state.first),f)+playerCard(lookup(f,state.second),f)+'</div>'+
 '<p class="note">Comparison scores are the same values used in the format rankings. We do not substitute the former modern-only model or imply unknown historical pitch and individual-bowler information.</p>';
}
async function loadModern(){
 if(modernInnings)return modernInnings;
 if(modernError)throw modernError;
 try{
  if(!('DecompressionStream' in window))throw new Error('Your browser cannot decompress the published modern ledger.');
  const r=await fetch('data/innings.json.gz',{cache:'no-store'});
  if(!r.ok)throw new Error('Modern licensed match ledger not available ('+r.status+')');
  let blob=await r.blob();
  const stream=blob.stream().pipeThrough(new DecompressionStream('gzip'));
  const text=await new Response(stream).text();
  modernInnings=JSON.parse(text);
  if(!Array.isArray(modernInnings))throw new Error('Unexpected modern match data structure');
  return modernInnings;
 }catch(err){modernError=err;throw err}
}
function matchExplorer(){
 hero('Match <em>Explorer</em>','Explore actual licensed modern Cricsheet batting appearances. Historical third-party scorecards are deliberately excluded because redistribution permission remains unverified.');
 return '<div class="callout">Modern-only detailed match explorer. It is not the source for the all-era rankings displayed elsewhere. Older batter performances remain represented through aggregate scorecard-era ratings.</div>'+
 '<div class="controls"><label>Format<select id="match-format">'+FORMATS.map(f=>'<option value="'+f+'"'+(state.matchFormat===f?' selected':'')+'>'+E(LABEL[f])+'</option>').join('')+'</select></label>'+
 '<label>Search batter<input id="match-search" placeholder="Player name" value="'+E(state.matchSearch)+'"></label>'+
 '<label>Opposition<input id="match-opponent" placeholder="Any opponent" value="'+E(state.matchOpposition)+'"></label>'+
 '<label>Sort<select id="match-sort"><option value="date"'+(state.matchOrder==='date'?' selected':'')+'>Most recent</option><option value="runs"'+(state.matchOrder==='runs'?' selected':'')+'>Most runs</option></select></label></div><div id="match-results" class="section"><div class="panel">Loading licensed modern records…</div></div>';
}
function renderMatches(){
 const holder=$('#match-results');if(!holder)return;
 if(!modernInnings){holder.innerHTML='<div class="panel">Loading licensed source ledger…</div>';return}
 let results=modernInnings.filter(r=>r.f===state.matchFormat&&(!state.matchSearch||(r.n||'').toLowerCase().includes(state.matchSearch.toLowerCase()))&&(!state.matchOpposition||(r.o||'').toLowerCase().includes(state.matchOpposition.toLowerCase())));
 results.sort((a,b)=>state.matchOrder==='runs'?b.r-a.r:b.d.localeCompare(a.d));
 const total=results.length,paged=results.slice(state.matchPage*matchLimit,(state.matchPage+1)*matchLimit);
 const table='<div class="table-scroller"><table><thead><tr><th>Date</th><th>Batter</th><th>Opposition</th><th>Runs</th><th>Balls</th><th>Team</th><th>Data tier</th></tr></thead><tbody>'+paged.map(r=>'<tr><td>'+E(r.d)+'</td><td>'+E(r.n)+'</td><td>'+E(r.o)+'</td><td>'+I(r.r)+'</td><td>'+I(r.b)+'</td><td>'+E(r.t)+'</td><td>Cricsheet modern</td></tr>').join('')+'</tbody></table></div>';
 holder.innerHTML='<div class="section-head"><h2>'+I(total)+' observed batting records</h2><span>Licensed modern-only source events; not a historical scorecard census</span></div>'+table+
 '<div class="pager"><button type="button" data-match-page="-1"'+(state.matchPage===0?' disabled':'')+'>← Previous</button><span>Page '+(state.matchPage+1)+' of '+Math.max(1,Math.ceil(total/matchLimit))+'</span><button type="button" data-match-page="1"'+((state.matchPage+1)*matchLimit>=total?' disabled':'')+'>Next →</button></div>';
}
function methodology(){
 hero('How the <em>adjustments work</em>','One scorecard-era model, consistent across historical and modern players. We disclose every proxy, eligibility rule and uncertainty limitation.');
 return '<section class="section"><div class="section-head"><h2>Core batting adjustments</h2></div>'+adjustmentContent(true)+'</section>'+
 '<section class="section"><div class="section-head"><h2>Three headline measurements</h2></div><div class="trio">'+[
 ['01 · QUALITY','Era-adjusted batting quality','Contextual run production and wicket survival compared with nearby-year peers. The index uses a shrunken 72% run / 28% survival log-ratio blend; 100 is contextual parity.'],
 ['02 · CARRY','Team carry','Within each actual team innings, compare runs with the average of other batters, adding 10 runs to stabilize very low totals. Shrink small samples toward 100.'],
 ['03 · GREATNESS','Career and peak','Career greatness rewards cumulative contextual surplus plus quality. A 25-innings peak is reported separately from JAWS-inspired career and seven strongest annual surplus totals.']
 ].map(([k,h,t])=>'<div class="panel"><small>'+k+'</small><h3>'+h+'</h3><p>'+t+'</p></div>').join('')+'</div></section>'+
 '<section class="section"><div class="section-head"><h2>JAWS-inspired career vs peak</h2></div><div class="panel prose">'+
 '<p>Baseball JAWS averages career WAR and the WAR accumulated in a player’s seven best seasons. Our <b>cricket analogue is not WAR</b> and must not imply a causal value in runs or wins.</p>'+
 '<p><b>Per-innings contextual surplus</b> = (runs − expected runs) / max(10, expected runs) + 0.35 × (expected outs − actual outs).</p>'+
 '<p><b>Career value</b> = sum of contextual surplus over all observed innings.</p>'+
 '<p><b>Peak value</b> = sum of contextual surplus in the seven best observed calendar seasons (not necessarily consecutive).</p>'+
 '<p><b>JAWS-style value</b> = (career value + peak value) / 2, with both quantities in the same units.</p>'+
 '<p><b>Combined rankings</b> average within-format percentiles after requiring minimum observed innings in every included format. No raw Test, ODI and T20I surplus is added directly. Players who did not play T20Is are not assigned zero.</p>'+
 '<div class="callout"><b>Known limitation:</b> annual international match opportunities differ substantially across eras and countries. This first JAWS adaptation still carries opportunity bias and is experimental.</div></div></section>'+
 '<section class="section"><div class="section-head"><h2>Validation and transparency</h2></div><div class="panel prose"><p>Conditional match-level bootstrap 90% intervals are calculated for quality and team carry. They do not cover model-weight sensitivity, incomplete historical matches, or source-rights uncertainty.</p><p>Pitch difficulty is approximated using other batters’ same-match scores, not an actual pitch assessment. Opposition quality is a nation-level run-concession proxy, not measured performance against each historical bowler. Playing conditions and rules, batting positions and series context are not always available.</p><p><a href="https://github.com/randomquestions-projects/cricket-greatness-index/blob/main/docs/format-greatness-methodology.md" target="_blank" rel="noreferrer">Read full formula documentation →</a></p></div></section>';
}
function coverage(){
 hero('Data, coverage & <em>limitations</em>','Observed match data is not automatically the same as a complete, independently verified official scorecard census.');
 const c=docs.coverage,stats=FORMATS.map(f=>{
  const x=c?.formats?.[f]||{},d=docs[f]||{};
  return '<tr><td>'+E(LABEL[f])+'</td><td>'+I(x.observedMatches)+'</td><td>'+I(x.deliveryMatches)+'</td><td>'+I(x.historicalScorecardMatches)+'</td><td>'+I(d.qualifiedPlayers)+'</td></tr>';
 }).join('');
 const career=docs.careers||{};
 return '<section class="section"><div class="section-head"><h2>Observed source coverage</h2></div><div class="table-scroller"><table><thead><tr><th>Format</th><th>Combined observed matches</th><th>Modern delivery matches</th><th>Historic batting-only matches</th><th>Qualified players</th></tr></thead><tbody>'+stats+'</tbody></table></div>'+
 '<div class="callout"><b>Not certified:</b> Independently complete all-time official match coverage, historical fielding and bowling cards, full player-identification reconciliation, and direct pitch quality. 2017 historical records are batting-innings observations, not complete scorecards.</div></section>'+
 '<section class="section"><div class="section-head"><h2>Reference career checks</h2></div><div class="panel">Matched run totals in the limited reference careers: <b>'+I(career.passingCareers)+' / '+I(career.checkedCareers)+'</b>. Matching a career total does not prove every match/innings record is correct.</div>'+
 '<div class="table-scroller"><table><thead><tr><th>Batter</th><th>Format</th><th>Recorded runs</th><th>Reference runs</th><th>Result</th></tr></thead><tbody>'+
 (career.checks||[]).map(x=>'<tr><td>'+E(x.player)+'</td><td>'+E(x.format.toUpperCase())+'</td><td>'+I(x.observedRuns)+'</td><td>'+I(x.referenceRuns)+'</td><td>'+(x.careerRunsReconciled?'Matched':'Review')+'</td></tr>').join('')+'</tbody></table></div></section>'+
 '<section class="section"><div class="section-head"><h2>Licensed sources and boundaries</h2></div><div class="panel prose"><p><b>Cricsheet:</b> modern events and derived scorecards from the openly licensed ODC-BY archive. The match explorer uses these records only.</p><p><b>Historical research:</b> a separate 2017 ESPN-derived batting-innings source, provisionally deduplicated with modern matches. Its redistribution rights are not established. New public rankings contain aggregated player/model findings, not raw historical scorecards.</p><p><b>Master warehouse:</b> the independently reusable open source database is separate from these research-only historical inputs. New model data refreshes weekly but do not certify complete historical coverage.</p><p><a href="https://github.com/randomquestions-projects/cricket-greatness-index/blob/main/warehouse/SCORECARD_STATUS.md">Source audits and limitations →</a></p></div></section>';
}
async function render(){
 const raw=location.hash.replace(/^#/,'').split('/')[0],f=LABEL[raw]?raw:'overview';state.view=f;state.search=f===state._lastFormat?state.search:'';state.country=f===state._lastFormat?state.country:'All';state._lastFormat=f;
 nav(f);
 const block=$('#page-body');
 if(f==='overview')block.innerHTML=overview();
 else if([...FORMATS,...COMBOS].includes(f))block.innerHTML=perFormat(f);
 else if(f==='compare')block.innerHTML=compare();
 else if(f==='matches'){
  block.innerHTML=matchExplorer();
  loadModern().then(()=>{if(state.view==='matches')renderMatches()}).catch(err=>{if(state.view==='matches')$('#match-results').innerHTML='<div class="callout">Could not load licensed modern match data: '+E(err.message)+'</div>'});
 }
 else if(f==='methodology')block.innerHTML=methodology();
 else if(f==='coverage')block.innerHTML=coverage();
 bindSelectValues();
 window.scrollTo({top:0,behavior:'instant'});
}
function bindSelectValues(){
 const f=state.view;
 if(f==='compare'){$('#compare-first').value=state.first;$('#compare-second').value=state.second}
}
document.addEventListener('input',event=>{
 if(event.target.id==='rank-search'){state.search=event.target.value;const ss=event.target.selectionStart;perFormatPartial();$('#rank-search')?.focus();$('#rank-search')?.setSelectionRange(ss,ss)}
 if(event.target.id==='match-search'){state.matchSearch=event.target.value;state.matchPage=0;renderMatches()}
 if(event.target.id==='match-opponent'){state.matchOpposition=event.target.value;state.matchPage=0;renderMatches()}
});
function perFormatPartial(){const f=state.view;if(![...FORMATS,...COMBOS].includes(f))return;const body=$('#page-body');body.innerHTML=perFormat(f)}
document.addEventListener('change',event=>{
 const id=event.target.id,v=event.target.value;
 if(['rank-metric','rank-country','rank-min'].includes(id)){
  if(id==='rank-metric')state.metric=v;
  if(id==='rank-country')state.country=v;
  if(id==='rank-min')state.minimum=+v;
  perFormatPartial();
 }
 if(id==='compare-format'){state.compareFormat=v;state.first='';state.second='';$('#page-body').innerHTML=compare();bindSelectValues()}
 if(id==='compare-first'){state.first=v;$('#comparison-profiles').innerHTML=playerCard(lookup(state.compareFormat,state.first),state.compareFormat)+playerCard(lookup(state.compareFormat,state.second),state.compareFormat)}
 if(id==='compare-second'){state.second=v;$('#comparison-profiles').innerHTML=playerCard(lookup(state.compareFormat,state.first),state.compareFormat)+playerCard(lookup(state.compareFormat,state.second),state.compareFormat)}
 if(id==='match-format'){state.matchFormat=v;state.matchPage=0;renderMatches()}
 if(id==='match-sort'){state.matchOrder=v;state.matchPage=0;renderMatches()}
});
document.addEventListener('click',event=>{
 const el=event.target.closest('[data-profile]');
 if(el){const f=el.dataset.profileFormat;state.compareFormat=f;state.first=el.dataset.profile;state.second='';go('compare');return}
 const pg=event.target.closest('[data-match-page]');
 if(pg){state.matchPage=Math.max(0,state.matchPage+Number(pg.dataset.matchPage));renderMatches();return}
});
$('#menu-button').addEventListener('click',()=>{const isOpen=$('#sidebar').classList.toggle('open');$('#menu-button').setAttribute('aria-expanded',String(isOpen))});
window.addEventListener('hashchange',render);
async function init(){
 if(location.pathname.endsWith('format-greatness.html')){
  const q=new URLSearchParams(location.search).get('format');
  if(LABEL[q])location.replace('index.html#'+q);
 }
 if(!location.hash)location.hash='#overview';
 try{
  const loaded=await Promise.allSettled([
   ...FORMATS.map(f=>fetchJSON(url(f+'-greatness'))),
   fetchJSON(url('greatness-combined')),fetchJSON(url('coverage-status')),fetchJSON(url('career-reconciliation'))
  ]);
  FORMATS.forEach((f,i)=>{if(loaded[i].status==='fulfilled')docs[f]=loaded[i].value});
  const labels=['combined','coverage','careers'];
  for(let i=3;i<6;i++)if(loaded[i].status==='fulfilled')docs[labels[i-3]]=loaded[i].value;
  const failed=loaded.filter(x=>x.status==='rejected');
  if(failed.length)console.warn('Some research datasets could not be loaded',failed.map(x=>x.reason?.message));
  showNotice();render();
 }catch(err){$('#research-notice').textContent='Unable to load study data: '+err.message}
}
init();
})();