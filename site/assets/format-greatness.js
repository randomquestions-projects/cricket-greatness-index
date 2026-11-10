/* Cricket Greatness Lab v0.4: real scorecard-era derived model, no dummy figures. */
(()=>{'use strict';
const $=s=>document.querySelector(s);
const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=(v,d=1)=>v==null||!isFinite(Number(v))?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const titles={test:'Test',odi:'ODI',t20i:'T20I',test_odi:'Test + ODI',all_three:'All formats'};
const format=new URLSearchParams(location.search).get('format')||'test';
const valid=['test','odi','t20i','test_odi','all_three'];
let data=null,combined=null,players=[],a='',b='',metric='quality',search='',min=35;
const multi=['test_odi','all_three'].includes(format);
const indexMetric={quality:'overallQualityPercentile',teamCarry:'overallCarryPercentile',careerGreatness:'overallCareerPercentile',
 peakQuality:'overallPeakPercentile',jawsPercentile:'overallJawsPercentile',jawsStyleValue:'overallJawsPercentile'};
const get=(p,k)=>multi?p[indexMetric[k]]:k==='peakQuality'?p.peakQuality?.index:p[k];
const interval=(p,k)=>k==='quality'?p.qualityInterval90:k==='teamCarry'?p.teamCarryInterval90:null;
function pickerOptions(){return players.slice().sort((x,y)=>x.name.localeCompare(y.name)).map(p=>'<option value="'+escape(p.playerId)+'">'+escape(p.name)+' · '+escape(p.team)+'</option>').join('')}
function topTable(){
  const filtered=players.filter(p=>(multi||p.innings>=min)&&(p.name+' '+p.team).toLowerCase().includes(search));
  filtered.sort((x,y)=>(get(y,metric)??-1e8)-(get(x,metric)??-1e8));
  $('#g-count').textContent=n(filtered.length,0)+' eligible batters';
  let html='<table><thead><tr><th>#</th><th>Batter</th><th>Index</th><th>90% interval*</th><th>Innings</th><th>Runs</th><th>Era-relative quality</th><th>Carry</th><th>JAWS score / percentile</th></tr></thead><tbody>';
  for(const [i,p] of filtered.slice(0,250).entries()){
    const ci=!multi?interval(p,metric):null;
    html+='<tr data-player="'+escape(p.playerId)+'"><td>'+(i+1)+'</td><td><b>'+escape(p.name)+'</b><div class="g-note">'+escape(p.team)+(multi?' · multi-format':' · '+n(p.historicalInnings,0)+' historical innings')+'</div></td><td class="g-top">'+n(get(p,metric))+'</td><td>'+(ci?n(ci[0])+'–'+n(ci[1]):'—')+'</td><td>'+n(multi?p.totalInnings:p.innings,0)+'</td><td>'+(multi?'—':n(p.runs,0))+'</td><td>'+n(multi?p.overallQualityPercentile:p.quality)+'</td><td>'+n(multi?p.overallCarryPercentile:p.teamCarry)+'</td><td>'+n(multi?p.overallJawsPercentile:p.jawsStyleValue)+'</td></tr>';
  }
  html+='</tbody></table>';
  $('#g-ranking').innerHTML=html;
  $('#g-ranking').querySelectorAll('tr[data-player]').forEach(tr=>tr.addEventListener('click',()=>{
    a=tr.dataset.player;$('#g-a').value=a;showProfiles();$('#comparison').scrollIntoView({behavior:'smooth'});
  }));
}
function splits(rows,label,detail){
  if(!rows?.length)return '<tr><td colspan="3">Not enough eligible scorecard observations</td></tr>';
  return rows.slice(0,10).map(r=>'<tr><td>'+escape(r[label])+'</td><td>'+n(r.innings,0)+' innings</td><td>'+n(r.quality)+(detail&&r.average!=null?' · '+n(r.average,2)+' avg':'')+'</td></tr>').join('');
}
function profile(p){
  if(!p)return '<div class="g-panel">Player not found</div>';
  if(multi){
    let h='<article class="g-profile"><span class="k-label">'+escape(p.team)+'</span><h3>'+escape(p.name)+'</h3><div class="g-metrics"><div>OVERALL JAWS<b>'+n(p.overallJawsPercentile)+'</b></div><div>QUALITY %ILE<b>'+n(p.overallQualityPercentile)+'</b></div><div>TEAM CARRY %ILE<b>'+n(p.overallCarryPercentile)+'</b></div></div>';
    h+='<p class="g-note">Equal-weight format percentiles, not the sum of runs or an unadjusted comparison of batting averages. Eligibility requires minimum observed innings in every format.</p>';
    h+='<table class="g-mini"><thead><tr><th>Format</th><th>Innings</th><th>Quality / JAWS %ile</th></tr></thead><tbody>';
    Object.entries(p.formats).forEach(([fmt,d])=>{h+='<tr><td>'+escape(titles[fmt])+'</td><td>'+n(d.innings,0)+'</td><td>'+n(d.quality)+' / '+n(d.jawsPercentile)+'</td></tr>'});
    return h+'</tbody></table></article>';
  }
  const ci=p.qualityInterval90;
  let h='<article class="g-profile"><span class="k-label">'+escape(p.team)+' · '+n(p.innings,0)+' observed innings · '+escape(p.careerStart)+'–'+escape(p.careerEnd)+'</span><h3>'+escape(p.name)+'</h3><div class="g-metrics">';
  h+='<div>QUALITY<b>'+n(p.quality)+'</b><small>90% '+(ci?n(ci[0])+'–'+n(ci[1]):'—')+'</small></div>';
  h+='<div>TEAM CARRY<b>'+n(p.teamCarry)+'</b><small>'+n(p.teamCarryInnings,0)+' innings</small></div>';
  h+='<div>JAWS %ILE<b>'+n(p.jawsPercentile)+'</b><small>Within format</small></div></div>';
  h+='<p class="g-note">Career greatness '+n(p.careerGreatness)+' · Peak 25 innings '+n(p.peakQuality?.index)+' · JAWS-style contextual surplus '+n(p.jawsStyleValue)+' · Runs '+n(p.runs,0)+' / avg '+n(p.average,2)+'.</p>';
  h+='<p class="g-note"><b>Peak years:</b> '+escape((p.bestSevenSeasons||[]).join(', '))+' · Career contextual surplus '+n(p.careerValue)+' vs 7-season surplus '+n(p.bestSevenSeasonValue)+'. Both in the same arbitrary standardized units, not baseball WAR.</p>';
  if(p.careerCheck)h+='<p class="g-note"><b>Official reference checks:</b> runs '+(p.careerCheck.runsMatch?'matched':'MISMATCH')+'; innings '+(p.careerCheck.inningsMatch?'matched':'MISMATCH')+'. Does not prove every scorecard is accurate.</p>';
  h+='<h4>Opposition</h4><table class="g-mini"><thead><tr><th>Nation</th><th>Sample</th><th>Quality / average</th></tr></thead><tbody>'+splits(p.opponents,'opponent',true)+'</tbody></table>';
  h+='<h4>Home vs away</h4><table class="g-mini"><thead><tr><th>Classification</th><th>Sample</th><th>Quality</th></tr></thead><tbody>'+splits(p.venues,'venueClass',false)+'</tbody></table>';
  if(p.opponentAndVenue?.length)h+='<h4>Opponent × road context</h4><table class="g-mini"><tbody>'+p.opponentAndVenue.slice(0,12).map(r=>'<tr><td>'+escape(r.opponent)+' · '+escape(r.venueClass)+'</td><td>'+n(r.innings,0)+' inns</td><td>'+n(r.quality)+'</td></tr>').join('')+'</tbody></table>';
  h+='<h4>Adjustment sensitivity</h4><table class="g-mini"><tbody>';
  for(const [k,t] of [['quality','All context controls'],['withoutOpposition','Remove opponent'],['withoutVenue','Remove home/away'],['withoutMatchContext','Remove match difficulty']])
    h+='<tr><td>'+t+'</td><td>'+n(k==='quality'?p.quality:p.sensitivity?.[k])+'</td></tr>';
  h+='</tbody></table><p class="g-note">Known venue context '+n(p.venueKnownPct)+'% · Opposition evidence '+n(p.opponentEvidencePct)+'% · Peer-match evidence '+n(p.peerMatchEvidencePct)+'%. Missing source and historical model uncertainty not covered by displayed confidence intervals.</p></article>';
  return h;
}
function showProfiles(){ $('#g-profiles').innerHTML=profile(players.find(p=>p.playerId===a))+profile(players.find(p=>p.playerId===b)); }
function initControls(){
  if(multi){$('#g-min').parentNode.style.display='none';}
  else{$('#g-min').value=String(data.qualificationMinimumInnings??35);min=+(data.qualificationMinimumInnings??35);}
  $('#g-metric').value=multi?'jawsPercentile':'quality';
  metric=$('#g-metric').value;
  $('#g-metric').onchange=ev=>{metric=ev.target.value;topTable()};
  $('#g-search').oninput=ev=>{search=ev.target.value.toLowerCase().trim();topTable()};
  $('#g-min').onchange=ev=>{min=+ev.target.value;topTable()};
  $('#g-a').innerHTML=pickerOptions();$('#g-b').innerHTML=pickerOptions();
  a=players.find(p=>p.name==='Don Bradman')?.playerId||players.find(p=>p.name==='Sachin Tendulkar')?.playerId||players[0]?.playerId;
  b=players.find(p=>p.name==='Virat Kohli')?.playerId||players[1]?.playerId;
  $('#g-a').value=a;$('#g-b').value=b;
  $('#g-a').onchange=ev=>{a=ev.target.value;showProfiles()};
  $('#g-b').onchange=ev=>{b=ev.target.value;showProfiles()};
  topTable();showProfiles();
}
async function main(){
  if(!valid.includes(format)){location.href='?format=test';return}
  document.querySelectorAll('[data-tab]').forEach(el=>el.classList.toggle('active',el.dataset.tab===format));
  const side=$('#side-'+format);if(side)side.classList.add('selected');
  $('#g-title').innerHTML=escape(titles[format])+' Batting <em>Greatness</em>';
  document.title=titles[format]+' Batting Greatness · Cricket Greatness Lab';
  if(multi){
    $('#g-subtitle').textContent='Historically comparable, equal-format-percentile composite. A batter must qualify in every included format; this is not a ranking of players who never played that format.';
    $('#g-metric').querySelectorAll('option').forEach(opt=>{
      if(opt.value==='jawsStyleValue')opt.textContent='JAWS-inspired percentile';
      if(opt.value==='quality')opt.textContent='Era-adjusted quality percentile';
      if(opt.value==='teamCarry')opt.textContent='Team carry percentile';
      if(opt.value==='careerGreatness')opt.textContent='Career greatness percentile';
      if(opt.value==='peakQuality')opt.textContent='Best seven-season peak percentile';
    });
  }
  try{
    const endpoint=multi?'data/greatness-combined.json':'data/'+format+'-greatness.json';
    const response=await fetch(endpoint,{cache:'no-store'});
    if(!response.ok)throw Error('Production format model not yet published');
    const doc=await response.json();
    if(multi){combined=doc;players=doc.combined?.[format]||[];data={};}
    else{data=doc;players=doc.players||[];}
    if(!players.length)throw Error('No qualifying players in the available records');
    $('#g-status').innerHTML='<b>'+n(players.length,0)+' eligible batters</b> · '+(multi?'equal-weight percentiles of eligible formats':n(data.observedDistinctMatches,0)+' observed format matches · '+n(data.historicalTestInnings,0)+' historical-only innings')+' · Experimental model; all-time coverage and historical source rights are not certified. No fictional rankings.';
    $('#g-rank-title').textContent=titles[format]+' · Era-adjusted greatness rankings';
    initControls();
  }catch(err){$('#g-status').textContent='No published numerical results yet: '+err.message+'. The GitHub data workflow must complete.'}
}
main();
})();