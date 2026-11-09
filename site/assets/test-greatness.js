/* Test Greatness — common scorecard standard for historic and modern Test batters. */
(function(){
'use strict';
const $=s=>document.querySelector(s);
const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const n=(v,d=1)=>v==null||!Number.isFinite(+v)?'—':Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
let report=null,sort='quality',min=35,query='',first=null,second=null;
const v=(p,k)=>k==='peakQuality'?p.peakQuality?.index:p[k];
function ranking(){
let rows=report.players.filter(p=>p.innings>=min&&(p.name+' '+p.team).toLowerCase().includes(query));
rows.sort((a,b)=>(v(b,sort)??-1)-(v(a,sort)??-1));
$('#test-count').textContent=n(rows.length,0)+' qualified batters';
let html='<table><thead><tr><th>#</th><th>Batter / source mix</th><th>Index</th><th>90% interval</th><th>Inns</th><th>Runs</th><th>Average</th><th>Older inns</th><th>Above expected</th></tr></thead><tbody>';
rows.slice(0,200).forEach((p,i)=>{
let ci=sort==='quality'&&p.qualityInterval90?p.qualityInterval90:sort==='teamCarry'&&p.teamCarryInterval90?p.teamCarryInterval90:null;
html+='<tr data-p="'+e(p.playerId)+'"><td>'+(i+1)+'</td><td><b>'+e(p.name)+'</b><div style="font-size:9px;color:#849b91">'+e(p.team)+' · '+(p.historicalInnings?'Historic + modern':'Modern only')+'</div></td><td><strong>'+n(v(p,sort))+'</strong></td><td>'+(ci?n(ci[0])+'–'+n(ci[1]):'—')+'</td><td>'+n(p.innings,0)+'</td><td>'+n(p.runs,0)+'</td><td>'+n(p.average,2)+'</td><td>'+n(p.historicalInnings,0)+'</td><td>'+n(p.runsAboveExpected)+'</td></tr>';
});
html+='</tbody></table>';
$('#test-ranking').innerHTML=html;
$('#test-ranking').querySelectorAll('tr[data-p]').forEach(tr=>tr.addEventListener('click',()=>{
first=tr.dataset.p;$('#test-first').value=first;comparison();$('#test-compare').scrollIntoView({behavior:'smooth',block:'start'});
}));
}
function splits(rows,field,avg){
if(!rows||!rows.length)return '<tr><td colspan="3">No split with at least five innings</td></tr>';
return rows.slice(0,9).map(r=>'<tr><td>'+e(r.opponent||r.venueClass)+'</td><td>'+n(r.innings,0)+' inns</td><td>'+n(r.quality)+(avg&&r.average!=null?' · '+n(r.average,2)+' avg':'')+'</td></tr>').join('');
}
function card(p){
if(!p)return '<article class="test-profile">No eligible player</article>';
const qi=p.qualityInterval90,ti=p.teamCarryInterval90,check=p.careerCheck;
let html='<article class="test-profile"><span class="k-label">'+e(p.team)+' · '+n(p.innings,0)+' Test innings · '+e(p.careerStart)+'–'+e(p.careerEnd)+'</span><h3>'+e(p.name)+'</h3><div class="triple">';
html+='<div>QUALITY<b>'+n(p.quality)+'</b><span>90% '+(qi?n(qi[0])+'–'+n(qi[1]):'—')+'</span></div>';
html+='<div>TEAM CARRY<b>'+n(p.teamCarry)+'</b><span>90% '+(ti?n(ti[0])+'–'+n(ti[1]):'—')+'</span></div>';
html+='<div>CAREER<b>'+n(p.careerGreatness)+'</b><span>Peak '+(p.peakQuality?n(p.peakQuality.index):'—')+'</span></div></div>';
html+='<p class="test-note">Runs '+n(p.runs,0)+' · Test average '+n(p.average,2)+' · Above era/context expectation '+n(p.runsAboveExpected)+' · '+n(p.historicalInnings,0)+' historical-only innings</p>';
if(check)html+='<p class="test-note"><strong>Career audit:</strong> reference runs '+n(check.referenceRuns,0)+' ('+(check.runsMatch?'matched':'MISMATCH')+'); innings '+n(check.referenceInnings,0)+' ('+(check.inningsMatch?'matched':'MISMATCH')+'). Totals alone cannot certify match coverage.</p>';
html+='<h4>Performance against opposing nations</h4><table class="test-mini-table"><thead><tr><th>Opponent</th><th>Sample</th><th>Adjusted quality · avg</th></tr></thead><tbody>'+splits(p.opponents,true,true)+'</tbody></table>';
html+='<h4>Home / away / neutral</h4><table class="test-mini-table"><thead><tr><th>Ground type</th><th>Sample</th><th>Adjusted quality</th></tr></thead><tbody>'+splits(p.venues,false,false)+'</tbody></table>';
html+='<p class="test-note">Venue classification known for '+n(p.venueKnownPct)+'% of innings. Opposition proxy supported for '+n(p.opponentEvidencePct)+'%; same-match proxy supported for '+n(p.peerMatchEvidencePct)+'%; team-carry observations '+n(p.teamCarryInnings,0)+'.</p>';
html+='<h4>Index sensitivity: remove each context adjustment</h4><table class="test-mini-table"><tbody><tr><td>All controls</td><td>'+n(p.quality)+'</td></tr><tr><td>Without opponent</td><td>'+n(p.sensitivity?.withoutOpposition)+'</td></tr><tr><td>Without home/away</td><td>'+n(p.sensitivity?.withoutVenue)+'</td></tr><tr><td>Without match difficulty</td><td>'+n(p.sensitivity?.withoutMatchContext)+'</td></tr></tbody></table>';
if(p.peakQuality)html+='<p class="test-note"><b>Best 25-innings window</b> '+n(p.peakQuality.index)+' · '+e(p.peakQuality.start)+' to '+e(p.peakQuality.end)+' (selected maximum, subject to selection bias).</p>';
return html+'</article>';
}
function comparison(){
$('#test-compare').innerHTML=card(report.players.find(p=>p.playerId===first))+card(report.players.find(p=>p.playerId===second));
}
function options(){
return report.players.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(p=>'<option value="'+e(p.playerId)+'">'+e(p.name)+' · '+e(p.team)+'</option>').join('');
}
async function init(){
$('#test-metric').onchange=ev=>{sort=ev.target.value;if(report)ranking()};
$('#test-search').oninput=ev=>{query=ev.target.value.toLowerCase().trim();if(report)ranking()};
$('#test-min').onchange=ev=>{min=+ev.target.value;if(report)ranking()};
$('#test-first').onchange=ev=>{first=ev.target.value;if(report)comparison()};
$('#test-second').onchange=ev=>{second=ev.target.value;if(report)comparison()};
try{
const response=await fetch('data/test-greatness.json',{cache:'no-store'});
if(!response.ok)throw Error('Model data not published yet');
report=await response.json();
if(!Array.isArray(report.players)||!report.players.length)throw Error('No eligible players');
$('#test-status').innerHTML='<strong>'+n(report.qualifiedPlayers,0)+' qualified batters</strong> · '+n(report.observedDistinctMatches,0)+' observed Test matches · '+n(report.historicalTestInnings,0)+' historical-only batting innings · '+e(report.modelVersion)+'. <b>Experimental</b>: historical scorecard completeness and research-data rights remain unverified; no definitive all-time verdict.';
const opts=options();
$('#test-first').innerHTML=opts;$('#test-second').innerHTML=opts;
first=report.players.find(p=>p.name==='Don Bradman')?.playerId||report.players[0]?.playerId;
second=report.players.find(p=>p.name==='Virat Kohli')?.playerId||report.players[1]?.playerId;
$('#test-first').value=first;$('#test-second').value=second;
ranking();comparison();
}catch(err){$('#test-status').textContent='Test analysis not available yet: '+err.message+'. The data workflow must complete successfully.'}
}
init();
})();