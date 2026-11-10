// Browser-like smoke test of the *single* public application, using its actual datasets.
// Synthetic values are never substituted for the real hosted data.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html=readFileSync('site/index.html','utf8');
const script=readFileSync('site/assets/app.js','utf8');
const dom=new JSDOM(html,{url:'https://example.org/cricket-greatness-index/index.html#overview',runScripts:'outside-only'});
const {window:w}=dom;
w.scrollTo=()=>{};
w.DecompressionStream=globalThis.DecompressionStream;
w.Response=globalThis.Response;
w.fetch=async url=>{
  const path=String(url).split('?')[0].replace(/^\/+/,'');
  if(!/^data\/[a-z0-9_-]+\.(json|gz)$/.test(path))throw new Error('Unexpected fetch '+path);
  try{
    const bytes=readFileSync('site/'+path);
    if(path.endsWith('.gz'))return {ok:true,blob:async()=>new Blob([bytes])};
    return {ok:true,json:async()=>JSON.parse(bytes.toString('utf8'))};
  }catch(err){return {ok:false,status:404,json:async()=>{throw err}}}
};
w.eval(script);
async function settle(){await new Promise(r=>setTimeout(r,150))}
async function route(name){
 w.location.hash='#'+name;
 w.dispatchEvent(new w.Event('hashchange'));
 await settle();
 assert.equal(w.document.querySelector('#breadcrumb').textContent.trim().toLowerCase(),({'test_odi':'tests + odis','all_three':'all three formats'}[name]||name.replaceAll('_',' ')).toLowerCase());
 assert.ok(w.document.querySelector('#page-body').textContent.trim().length>100,'empty route '+name);
}
await settle();
assert.match(w.document.querySelector('#page-body').textContent,/Leading batters by format/);
assert.ok(w.document.querySelector('#research-notice').classList.contains('ready'),'canonical data not loaded');
for(const f of ['test','odi','t20i','test_odi','all_three']){
 await route(f);
 assert.ok(w.document.querySelector('.table-scroller tbody tr'),'missing data rows for '+f);
 assert.ok(w.document.querySelector('#rank-metric'),'missing metric selection for '+f);
 assert.ok(w.document.querySelector('#rank-search'),'missing search for '+f);
}
await route('compare');
assert.ok(w.document.querySelector('.player-grid .player-card'),'comparison is missing player cards');
await route('methodology');
assert.match(w.document.querySelector('#page-body').textContent,/JAWS-inspired career vs peak/);
await route('coverage');
assert.match(w.document.querySelector('#page-body').textContent,/Historical batting/i);
await route('matches');
await settle();
assert.ok(w.document.querySelector('#match-results').textContent.length>30,'modern explorer blank');
// No second app / old bootstrap data loaded.
assert.equal(w.document.querySelectorAll('script[src]').length,1);
assert.equal(w.document.querySelector('script[src]').getAttribute('src'),'assets/app.js');
console.log('PASS: one application, all ten routes, rankings, comparison, audit and modern explorer');
w.close();
