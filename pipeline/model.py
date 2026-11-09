"""Independently calculated, auditable *provisional* cricket batting research indices.

Not a causal estimator. Scorecard-parity index is available across eras only when
licensed historical innings are provided; the modern index further adjusts for
bowling exposure and same-match scoring environment. Never blend these indices.
"""
from __future__ import annotations
import argparse, csv, gzip, json, math, pathlib, random, statistics, hashlib
from collections import defaultdict, Counter
from datetime import date
from .ingest import ROOT, FILES, SENA, role
from .historical import norm, country

WEIGHTS={'test':(0.32,0.68),'odi':(0.58,0.42),'t20i':(0.78,0.22)}
MIN_N={'test':25,'odi':25,'t20i':20}
MIN_REF_BALLS=240
BIRTHS={
'Virat Kohli':'1988-11-05','Shubman Gill':'1999-09-08','Sachin Tendulkar':'1973-04-24',
'Rahul Dravid':'1973-01-11','Ricky Ponting':'1974-12-19','Steve Smith':'1989-06-02',
'Viv Richards':'1952-03-07','MS Dhoni':'1981-07-07','Jacques Kallis':'1975-10-16',
'Brian Lara':'1969-05-02','AB de Villiers':'1984-02-17','Joe Root':'1990-12-30',
'Suryakumar Yadav':'1990-09-14','Kumar Sangakkara':'1977-10-27','Yashasvi Jaiswal':'2001-12-28',
'Babar Azam':'1994-10-15','Rohit Sharma':'1987-04-30','Don Bradman':'1908-08-27',
'Kane Williamson':'1990-08-08','Jos Buttler':'1990-09-08','Glenn Maxwell':'1988-10-14',
'David Warner':'1986-10-27','Mohammad Rizwan':'1992-06-01','Sanath Jayasuriya':'1969-06-30',
'Adam Gilchrist':'1971-11-14','Hashim Amla':'1983-03-31','Chris Gayle':'1979-09-21'
}
ALIAS={
'V Kohli':'Virat Kohli','Shubman Gill':'Shubman Gill','Shubman Gill (IND)':'Shubman Gill',
'SR Tendulkar':'Sachin Tendulkar','R Dravid':'Rahul Dravid','RT Ponting':'Ricky Ponting',
'SPD Smith':'Steve Smith','RG Sharma':'Rohit Sharma','SA Yadav':'Suryakumar Yadav',
'MS Dhoni':'MS Dhoni','AB de Villiers':'AB de Villiers','JE Root':'Joe Root',
'KS Williamson':'Kane Williamson','KC Sangakkara':'Kumar Sangakkara','JH Kallis':'Jacques Kallis',
'BC Lara':'Brian Lara','CH Gayle':'Chris Gayle','JC Buttler':'Jos Buttler',
'AC Gilchrist':'Adam Gilchrist','ST Jayasuriya':'Sanath Jayasuriya',
'HM Amla':'Hashim Amla','DA Warner':'David Warner','GJ Maxwell':'Glenn Maxwell',
'YBK Jaiswal':'Yashasvi Jaiswal','DJG Sammy':'Daren Sammy','GS Sobers':'Garfield Sobers','JB Hobbs':'Jack Hobbs'
}

def numeral(v,default=0):
    try:return float(v) if v not in ('',None) else float(default)
    except (TypeError,ValueError):return float(default)

def reading(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8',newline='') as f:
        yield from csv.DictReader(f)

def lookup_name(row):return ALIAS.get(row['name'],row['name'])

def read_innings(folder, historical=None):
    """Load BOTH archives, match-link identities and de-duplicate at MATCH level.

    Modern deliveries win for any match covered by Cricsheet. Historical
    scorecards are used only for OTHER matches, avoiding mixed-source partial
    scorecards or inflated innings counts. This is conservative, and the
    coverage audit reports unmatched/missing seasons separately.
    """
    rows=[]
    for raw in reading(folder/'innings.csv.gz'):
        r=dict(raw);r.update({col:numeral(raw.get(col)) for col in ('runs','balls','fours','sixes','dismissed','position','team_total','team_batter_runs','teammate_runs','teammate_balls','team_wickets')})
        r['year']=int(numeral(raw['year']));r['name']=lookup_name(r);r['scorecardOnly']=False
        r['fullAge']=None
        if r['name'] in BIRTHS:
            r['fullAge']=(date.fromisoformat(r['date'])-date.fromisoformat(BIRTHS[r['name']])).days/365.2425
        rows.append(r)
    modern_match_keys={(r['date'],r['format'],*sorted((country(r['team']),country(r['opposition'])))) for r in rows}
    name_ids=defaultdict(set)
    for r in rows:
        name_ids[(norm(r['name']),country(r['team']))].add(r['player_id'])
    historical_sources=[]
    automatic=folder/'historical-innings.csv.gz'
    if automatic.exists() and automatic.stat().st_size>128:historical_sources.append(automatic)
    if historical and historical.exists() and historical.stat().st_size>32:historical_sources.append(historical)
    seen_legacy=set();skipped_overlap=0;ambiguous_identity=0
    required={'match_id','date','format','player_id','name','team','opposition','innings_number','position','runs','balls','dismissed','team_total','source'}
    for source in historical_sources:
        for raw in reading(source):
            if not required.issubset(raw):raise ValueError('Historical CSV missing '+str(required-set(raw)))
            if raw['format'] not in ('test','odi','t20i'):continue
            # All innings of an overlap match come from the single authoritative
            # delivery source: never try to match by abbreviated batter name.
            match_key=(raw['date'],raw['format'],*sorted((country(raw['team']),country(raw['opposition']))))
            if match_key in modern_match_keys:
                skipped_overlap+=1;continue
            uid=(match_key,raw['team'],raw['player_id'],int(float(raw['innings_number'])))
            if uid in seen_legacy:continue
            seen_legacy.add(uid)
            r=dict(raw)
            r.update({col:numeral(raw.get(col)) for col in ('runs','balls','dismissed','position','team_total','team_batter_runs','teammate_runs','teammate_balls')})
            r['year']=date.fromisoformat(r['date']).year;r['name']=lookup_name(r)
            r['role']=raw.get('role') or ('unknown' if not r['position'] else role(int(r['position'])))
            r['region']=raw.get('region') or 'Unknown';r['host']=raw.get('host','');r['home']=raw.get('home','')
            r['scorecardOnly']=True;r['match_result']=raw.get('match_result','');r['event']=raw.get('event','');r['event_stage']=raw.get('event_stage','')
            r['innings_id']=raw.get('innings_id') or raw['match_id']+':'+str(raw['innings_number'])
            r['bowler_exposures']='{}';r['fullAge']=None
            if r['name'] in BIRTHS:r['fullAge']=(date.fromisoformat(r['date'])-date.fromisoformat(BIRTHS[r['name']])).days/365.2425
            modern_ids=name_ids.get((norm(r['name']),country(r['team'])),set())
            if len(modern_ids)==1:r['player_id']=next(iter(modern_ids))
            elif len(modern_ids)>1:ambiguous_identity+=1
            rows.append(r)
    # Publication uses this log for reconciliation; the per-player scores are
    # not allowed to hide historical name or match-resolution limitations.
    read_innings.last_audit={'duplicateHistoricalMatchInningsSuppressed':skipped_overlap,
                             'ambiguousIdentityCount':ambiguous_identity,
                             'historicalSources':[str(x) for x in historical_sources]}
    return rows


def reference_tables(rows):
    # Compare against other roles in nearby years; more granular cells require more balls.
    # Note: not independent validation or a causal pitch effect.
    role_bucket=defaultdict(lambda:[0.,0.,0.,0.]);all_bucket=defaultdict(lambda:[0.,0.,0.,0.])
    for r in rows:
        x=(r['runs'],r['balls'],r['dismissed'],1)
        k=(r['format'],r['year'],r['role']);g=(r['format'],r['year'])
        for arr in (role_bucket[k],all_bucket[g]):
            for i in range(4):arr[i]+=x[i]
    return role_bucket,all_bucket


def aggregate_reference(buckets, key, minimum=MIN_REF_BALLS, fallback=None):
    fmt,yr=key[0],key[1];tail=key[2:]
    for year_span in (1,2,4,7,12):
        total=[0.,0.,0.,0.]
        for y in range(yr-year_span,yr+year_span+1):
            coef=1.0/(1+abs(y-yr))
            v=buckets[(fmt,y,*tail)]
            for i in range(4):total[i]+=v[i]*coef
        if total[1]>=minimum and total[3]>=15:return total
    if fallback is not None:return aggregate_reference(fallback,(fmt,yr),minimum=minimum)
    return [0,0,0,0]


def bowling_strength(folder):
    file=folder/'bowling.csv.gz'
    if not file.exists():return {}
    stats=defaultdict(lambda:[0.,0.,0.]);lg=defaultdict(lambda:[0.,0.,0.])
    for r in reading(file):
        x=(numeral(r['bowled']),numeral(r['runs']),numeral(r['wickets']))
        key=(r['format'],int(r['year']),r['bowler_id'])
        for dst in (stats[key],lg[(r['format'],int(r['year']))]):
            for j in range(3):dst[j]+=x[j]
    result={}
    for key in list(stats):
        fmt,yr,bid=key
        p=[0.,0.,0.];q=[0.,0.,0.]
        for y in range(yr-2,yr+3):
            w=1/(1+abs(y-yr))
            for a,b in ((p,stats[(fmt,y,bid)]),(q,lg[(fmt,y)])):
                for j in range(3):a[j]+=b[j]*w
        if p[0]<60 or q[0]<10000:continue
        rpb=(p[1]+0.1)/(p[0]+0.1);ref_rpb=(q[1]+0.1)/(q[0]+0.1)
        p_w=(p[2]+0.3)/(p[0]+1);q_w=(q[2]+0.3)/(q[0]+1)
        raw=0.6*math.log(ref_rpb/rpb)+0.4*math.log(p_w/q_w)
        result[key]=round(max(-0.6,min(0.6,raw))*p[0]/(p[0]+600),5)
    return result


def model(rows,bowl_quality):
    bucket,fb=reference_tables(rows)
    ref_cache={}
    for r in rows:
        k=(r['format'],r['year'],r['role'])
        if k not in ref_cache:ref_cache[k]=aggregate_reference(bucket,k,fallback=fb)
        r_ref=ref_cache[k]
        rpb=(r_ref[0]+0.1)/(r_ref[1]+0.1) if r_ref[1] else 0
        opb=(r_ref[2]+0.5)/(r_ref[1]+1) if r_ref[1] else 0
        r['baseRuns']=rpb*r['balls'];r['baseOuts']=opb*r['balls']
        exposures=json.loads(r.get('bowler_exposures') or '{}')
        exp_sum=sum(numeral(v) for v in exposures.values())
        strength=sum(bowl_quality.get((r['format'],r['year'],p),0)*numeral(b) for p,b in exposures.items())/(exp_sum or 1)
        r['attackDifficulty']=strength if not r['scorecardOnly'] else None
        # A strong bowling opponent lowers ordinary expected runs; positive residual gets credit.
        r['expectedRuns']=max(0.01,r['baseRuns']*math.exp(-0.35*strength))
        r['expectedOuts']=max(0,r['baseOuts']*math.exp(+0.25*strength))
    # Same-match scoring environment. We use BOTH sides as peers when present,
    # exclude the evaluated innings, and partially pool the residual toward neutral.
    # This is a descriptive match fixed-effect proxy, not a measured pitch rating.
    match_rows=defaultdict(list)
    for r in rows:match_rows[r['match_id']].append(r)
    for rs in match_rows.values():
        total_r=sum(r['runs'] for r in rs);total_e=sum(r['expectedRuns'] for r in rs)
        total_b=sum(r['balls'] for r in rs)
        for r in rs:
            other_b=total_b-r['balls']
            other_r=total_r-r['runs'];other_e=total_e-r['expectedRuns']
            has_opposition=any(q['team']!=r['team'] for q in rs)
            if other_b<100 or not has_opposition or other_e<10:
                r['matchScoringFactor']=1.0
                continue
            raw=(other_r+100)/(other_e+100)
            factor=max(0.82,min(1.22,raw**0.45))
            r['matchScoringFactor']=factor
            r['expectedRuns']*=factor
            r['expectedOuts']*=factor**(-0.25)
    groups=defaultdict(lambda:[0.,0.,0.,0.])
    for r in rows:
        arr=groups[r['innings_id']]
        arr[0]+=r['runs'];arr[1]+=r['expectedRuns'];arr[2]+=r['balls'];arr[3]+=1
    for r in rows:
        group=groups[r['innings_id']]
        peer_r=group[0]-r['runs'];peer_e=group[1]-r['expectedRuns']
        # Teammate comparison: leave the subject out; shrink away tiny denominators.
        r['peerAdjustedRate']=(peer_r+25)/(peer_e+25) if peer_e>=0 else 1
        r['matchPeerLift']=(r['runs']-r['expectedRuns']*r['peerAdjustedRate'])
    return rows


def interval_from_matches(rs, fmt, draws=180):
    """Conditional match-block bootstrap of the batting-quality score.

    Resamples whole observed matches and holds the fitted benchmark fixed. This
    interval does NOT capture uncertainty in era, pitch or bowler coefficients.
    """
    match_groups=defaultdict(list)
    for r in rs:match_groups[r['match_id']].append(r)
    blocks=list(match_groups.values())
    if len(blocks)<15:return None
    w,_=WEIGHTS[fmt]
    seed=int.from_bytes(hashlib.sha256((rs[0]['player_id']+'|'+fmt).encode()).digest()[:8],'little')
    rand=random.Random(seed)
    estimates=[]
    for _ in range(draws):
        run=expected=dismissed=expouts=0.;n=0
        for __ in range(len(blocks)):
            for r in blocks[rand.randrange(len(blocks))]:
                n+=1;run+=r['runs'];expected+=r['expectedRuns'];dismissed+=r['dismissed'];expouts+=r['expectedOuts']
        rr=(run+25)/(expected+25)
        survival=(expouts+3)/(dismissed+3)
        estimates.append(100*math.exp((w*math.log(max(.05,rr))+(1-w)*math.log(max(.05,survival)))*n/(n+28)))
    estimates.sort()
    return [round(estimates[int(draws*.05)],1),round(estimates[min(draws-1,int(draws*.95))],1)]


def pct(num,den):return round(num/den*100,2) if den else None

def summarize(rows, bootstrap=False):
    grouped=defaultdict(list)
    for r in rows:grouped[(r['player_id'],r['format'])].append(r)
    standings={};career={};hist=Counter()
    for (pid,fmt),rs in grouped.items():
        runs=sum(r['runs'] for r in rs);balls=sum(r['balls'] for r in rs);outs=sum(r['dismissed'] for r in rs)
        expected=sum(r['expectedRuns'] for r in rs);exp_out=sum(r['expectedOuts'] for r in rs)
        nr=len(rs);matches=len({r['match_id'] for r in rs});w_run,w_sur=WEIGHTS[fmt]
        efficiency=(runs+25)/(expected+25) if expected else None
        survival=(exp_out+3)/(outs+3) if outs or exp_out else 1
        index=100*math.exp((w_run*math.log(max(.05,efficiency or 1))+w_sur*math.log(max(.05,survival)))*nr/(nr+28))
        weighted_peer=sum(r['peerAdjustedRate']*r['expectedRuns'] for r in rs)/max(expected,.001)
        carry=100*(runs+25)/(expected*weighted_peer+25) if expected else None
        ages=[r['fullAge'] for r in rs if r['fullAge'] is not None]
        first,last=min(r['date'] for r in rs),max(r['date'] for r in rs)
        by_site={}
        for area in ('India','SENA','Other','Unknown'):
            sr=[r for r in rs if r['region']==area]
            by_site[area]={'inns':len(sr),'runs':int(sum(r['runs'] for r in sr)),'index':round(100*(sum(r['runs'] for r in sr)+25)/(sum(r['expectedRuns'] for r in sr)+25),1) if sr else None}
        away=[r for r in rs if r['home']==0 or r['home']=='0']
        home=[r for r in rs if r['home']==1 or r['home']=='1']
        chasing=[r for r in rs if fmt!='test' and int(r['innings_number'])%2==0]
        world_cup=[r for r in rs if 'world cup' in r.get('event','').lower()]
        knockout=[r for r in world_cup if any(s in r.get('event_stage','').lower() for s in ('final','semi','quarter'))]
        def split(sub):
            e=sum(r['expectedRuns'] for r in sub)
            return {'inns':len(sub),'runs':int(sum(r['runs'] for r in sub)),
                    'index':round(100*(sum(r['runs'] for r in sub)+12)/(e+12),1) if len(sub)>3 else None}
        points=round(index,2)
        item={'playerId':pid,'name':rs[-1]['name'],'team':Counter(r['team'] for r in rs).most_common(1)[0][0],
              'format':fmt,'index':points,'ci90':interval_from_matches(rs,fmt),'greatnessIndex':round(100+(index-100)*math.sqrt(min(1,nr/140))+10*math.asinh((runs-expected)/1250),2),'runIndex':round(100*efficiency,1) if efficiency else None,
              'survivalIndex':round(100*survival,1),'carryIndex':round(carry,1) if carry else None,
              'innings':nr,'matches':matches,'runs':int(runs),'balls':int(balls),'dismissals':int(outs),
              'average':round(runs/outs,2) if outs else None,'strikeRate':round(100*runs/balls,2) if balls else None,
              'expectedRuns':round(expected,1),'runsAboveExpected':round(runs-expected,1),
              'teamRunShare':round(sum(r['runs'] for r in rs)/sum(r['team_total'] for r in rs)*100,2) if sum(r['team_total'] for r in rs) else None,
              'matchPeerLift':round(sum(r['matchPeerLift'] for r in rs),1),'matchScoringAdjustment':round(sum(r['matchScoringFactor']*r['balls'] for r in rs)/(balls or 1),3),
              'sourceTier':'scorecard+delivery' if any(r['scorecardOnly'] for r in rs) else 'delivery-only',
              'bowlerCoveragePct':round(100*sum(r['balls'] for r in rs if not r['scorecardOnly'])/(balls or 1),1),
              'avgBowlerDifficulty':round(sum((r['attackDifficulty'] or 0)*r['balls'] for r in rs)/max(1,balls),4),
              'range':[first,last],'firstAge':round(min(ages),2) if ages else None,'lastAge':round(max(ages),2) if ages else None,
              'conditions':by_site,'away':split(away),'home':split(home),'chasing':split(chasing),
              'worldCup':split(world_cup),'knockouts':split(knockout),
              'eligible':nr>=MIN_N[fmt] and matches>=int(MIN_N[fmt]*.67),
              'warnings':(['Historical innings incomplete unless historical source imported'] if first<'2001-01-01' or (fmt in ('test','odi') and first<'2007-01-01') else [])}
        standings[pid+':'+fmt]=item
        career.setdefault(pid,{'playerId':pid,'name':item['name'],'team':item['team'],'formats':{}})['formats'][fmt]=item
    lists={fmt:sorted([x for x in standings.values() if x['format']==fmt and x['eligible']],key=lambda x:-x['index']) for fmt in FILES}
    combos={}
    for label,need in [('test_odi',('test','odi')),('all_three',('test','odi','t20i'))]:
        ranked=[]
        for c in career.values():
            fmts=c['formats']
            if not all(f in fmts and fmts[f]['eligible'] for f in need):continue
            weighted=statistics.geometric_mean(fmts[f]['index'] for f in need)
            nr=sum(fmts[f]['innings'] for f in need)
            peak=sum(math.sqrt(max(1,fmts[f]['innings']))*fmts[f]['index'] for f in need)/sum(math.sqrt(max(1,fmts[f]['innings'])) for f in need)
            ranked.append({'playerId':c['playerId'],'name':c['name'],'team':c['team'],'index':round(weighted,2),'greatnessIndex':round(statistics.geometric_mean(fmts[f]['greatnessIndex'] for f in need),2),
                           'totalInnings':nr,'formats':{f:fmts[f]['index'] for f in need}})
        combos[label]=sorted(ranked,key=lambda x:-x['index'])
    return lists,combos,career


def scorecard_parity(rows):
    """A *common-denominator* model across all recorded eras.

    Historical files do not contain ordered batting position, so comparing
    historical unknown positions against modern top-order positions would be a
    structural error. The benchmark therefore deliberately uses ONLY fields
    observable for all eras: runs, wickets, date, format, team and opponents.
    It pools nearby years, leaves the scored player out of their own reference,
    uses shrinkage, and separately measures same-innings teammate burden.

    No claims of full opponent-bowler, match-phase or strike-rate adjustment.
    """
    historical=[r for r in rows if r['scorecardOnly']]
    if not historical:return {'hasHistorical':False,'rankings':{},'combined':{},'caution':'Historical archive has not been imported.'}
    grouped=defaultdict(list);annual=defaultdict(lambda:[0.,0.,0.]);self_annual=defaultdict(lambda:[0.,0.,0.])
    peers=defaultdict(list)
    for r in rows:
        pid,fmt=r['player_id'],r['format'];yr=r['year']
        grouped[(pid,fmt)].append(r)
        annual[(fmt,yr)][0]+=r['runs'];annual[(fmt,yr)][1]+=r['dismissed'];annual[(fmt,yr)][2]+=1
        self_annual[(fmt,yr,pid)][0]+=r['runs'];self_annual[(fmt,yr,pid)][1]+=r['dismissed'];self_annual[(fmt,yr,pid)][2]+=1
        peers[r['innings_id']].append(r)
    # Leave-one-player-out nearby-year expected batting, with sensible pooling
    # when the historical sample is sparse. The baseline is NEVER just the
    # unadjusted mean over both centuries.
    def baseline(fmt,yr,pid):
        for radius in (2,5,10,20,35):
            runs=outs=inn=0.
            for y in range(yr-radius,yr+radius+1):
                w=1/(1+abs(y-yr))
                a=annual[(fmt,y)];s=self_annual[(fmt,y,pid)]
                runs+=max(0,a[0]-s[0])*w
                outs+=max(0,a[1]-s[1])*w
                inn+=max(0,a[2]-s[2])*w
            if inn>=50 or radius==35:
                return (runs/inn if inn else 0.,outs/inn if inn else 0.,inn)
    out=defaultdict(list)
    min_year=min(r['year'] for r in historical)
    years=defaultdict(set)
    match_counts=defaultdict(set)
    for r in rows:
        years[r['format']].add(r['year']);match_counts[r['format']].add(r['match_id'])
    for (pid,fmt),rs in grouped.items():
        if len(rs)<MIN_N.get(fmt,25):continue
        obs=sum(r['runs'] for r in rs);dism=sum(r['dismissed'] for r in rs)
        exp_runs=exp_dism=0.;supported=0
        for r in rs:
            er,ed,n=baseline(fmt,r['year'],pid)
            exp_runs+=er;exp_dism+=ed
            supported+=int(n>=50)
        if exp_runs<=0:continue
        rate=(obs+25)/(exp_runs+25);survival=(exp_dism+3)/(dism+3)
        # A common scorecard proxy cannot put a strike-rate weight on ODIs
        # when balls faced were not recorded early in the 1970s and 1980s.
        # We use the same runs/survival weighting for everyone, independent
        # of what delivery-level features happen to exist for their era.
        n=len(rs);weight=0.50
        index=100*math.exp((weight*math.log(max(.05,rate))+(1-weight)*math.log(max(.05,survival)))*n/(n+35))
        # Runs vs same-innings *other* batting runs. This is DESCRIPTIVE,
        # not an additional independently estimated pitch skill component.
        peer_expected=0.;observed_share=0.;carry_observations=0
        for r in rs:
            teammates=peers[r['innings_id']]
            if len(teammates)<3:continue
            others=sum(t['runs'] for t in teammates if t is not r)
            peer_expected+=others/max(1,len(teammates)-1)
            observed_share+=r['runs']/max(1,sum(t['runs'] for t in teammates))
            carry_observations+=1
        carry=100*(obs+25)/(peer_expected+25) if carry_observations else None
        out[fmt].append({'playerId':pid,'name':rs[-1]['name'],'team':Counter(r['team'] for r in rs).most_common(1)[0][0],
                         'innings':n,'runs':int(obs),'dismissals':int(dism),'average':round(obs/dism,2) if dism else None,
                         'index':round(index,2),'eraNormalizedRuns':round(rate*100,1),
                         'eraNormalizedSurvival':round(survival*100,1),'teamCarryIndex':round(carry,1) if carry is not None else None,
                         'averageBattingRunSharePct':round(100*observed_share/carry_observations,2) if carry_observations else None,
                         'carryMatchedInnings':carry_observations,'period':[min(r['date'] for r in rs),max(r['date'] for r in rs)],
                         'historicInnings':sum(r['scorecardOnly'] for r in rs),
                         'historicStart':min((r['date'] for r in rs if r['scorecardOnly']),default=None),
                         'historicEnd':max((r['date'] for r in rs if r['scorecardOnly']),default=None),
                         'referenceSupportedPct':round(100*supported/n,1),
                         'minHistoricalCoverageUnknown':True})
    lists={f:sorted(ls,key=lambda x:-x['index']) for f,ls in out.items()}
    by_id=defaultdict(dict)
    for fmt,ls in lists.items():
        for p in ls:by_id[p['playerId']][fmt]=p
    combined={}
    for label,formats in [('test_odi',('test','odi')),('all_three',('test','odi','t20i'))]:
        ensemble=[]
        for pid,d in by_id.items():
            if not all(f in d for f in formats):continue
            ensemble.append({'playerId':pid,'name':d[formats[0]]['name'],'team':d[formats[0]]['team'],
                   'index':round(statistics.geometric_mean(d[f]['index'] for f in formats),2),
                   'formats':{f:d[f]['index'] for f in formats}})
        combined[label]=sorted(ensemble,key=lambda x:-x['index'])
    dates=[r['date'] for r in historical]
    return {'hasHistorical':True,'historicalInnings':len(historical),
            'historicalPlayerCount':len({r['player_id'] for r in historical}),
            'firstHistoricalDate':min(dates),'lastHistoricalDate':max(dates),
            'rankings':lists,'combined':combined,
            'historicalFormatCounts':dict(Counter(r['format'] for r in historical)),
            'matchSourceCoverageByFormat':{fmt:len(ids) for fmt,ids in match_counts.items()},
            'caution':'Exploratory scorecard-common-denominator index. It controls for broad era and same-innings teammate scoring, NOT historical bowler-by-bowler exposure, batting position, rules, or complete match coverage. Peer carry is descriptive; the source archive requires reconciliation before all-time claims.'}


def public_innings(rows):
    """Compact, auditable innings table for client-side matched-career and same-match analysis."""
    output=[]
    for r in rows:
        output.append({'m':r['match_id'],'i':r['innings_id'],'d':r['date'],'f':r['format'],'p':r['player_id'],'n':r['name'],'t':r['team'],'o':r['opposition'],
                       'r':int(r['runs']),'b':int(r['balls']),'x':int(r['dismissed']),'pos':int(r['position']),'er':round(r['expectedRuns'],2),
                       'eo':round(r['expectedOuts'],3),'pr':round(r['peerAdjustedRate'],3),'h':r.get('host'), 'reg':r.get('region'),'age':round(r['fullAge'],3) if r['fullAge'] is not None else None,
                       's':1 if r['scorecardOnly'] else 0,'e':r.get('event',''),'stage':r.get('event_stage',''),'home':r.get('home')})
    return output


def build(input_dir,output_dir,historical_path=None):
    output_dir.mkdir(parents=True,exist_ok=True)
    source_rows=read_innings(input_dir,historical_path)
    if not source_rows:raise ValueError('No observed innings found; cannot calculate rankings')
    historical=scorecard_parity(source_rows)
    rows=[r for r in source_rows if not r['scorecardOnly']]
    if not rows:raise ValueError('Modern delivery dataset absent; use separate historical model only')
    bowl=bowling_strength(input_dir)
    rows=model(rows,bowl)
    rankings,overall,players=summarize(rows)
    # Entirely source-derived context, NOT a constant rating or hypothetical sample.
    yearly=defaultdict(lambda:[0.,0.,0.,0])
    for r in rows:
        arr=yearly[(r['format'],r['year'])]
        arr[0]+=r['runs'];arr[1]+=r['balls'];arr[2]+=r['dismissed'];arr[3]+=1
    era_trends={f:[{'year':yr,'innings':n,'runs':int(run),'balls':int(ball),
                    'runsPer100Balls':round(100*run/ball,2) if ball else None,
                    'runsPerDismissal':round(run/out,2) if out else None,
                    'odiRuleRegime':('Before two-ball rule' if yr<2011 else 'Two balls + Powerplay' if yr<2015 else 'Post-2015 fielding changes' if yr<2025 else '2025+ ball-use regime') if f=='odi' else None}
                   for (fmt,yr),(run,ball,out,n) in sorted(yearly.items()) if fmt==f and n>=30]
                for f in FILES}
    # Historical source counts below are AFTER match-level Cricsheet deduplication.
    historic_matches={(r['match_id'],r['format'],r['year']) for r in source_rows if r['scorecardOnly']}
    historic_years=Counter((f,y) for _,f,y in historic_matches)
    manifest=json.loads((input_dir/'manifest.json').read_text())
    historical_manifest_file=input_dir/'historical-manifest.json'
    historical_manifest=json.loads(historical_manifest_file.read_text()) if historical_manifest_file.exists() else None
    if historical_manifest:
        manifest['historical']= {k:v for k,v in historical_manifest.items() if k!='yearCounts'}
        manifest['coverageScope']='Modern deliveries plus source-backed historical batting innings; historical completeness NOT certified'
    report={'metadata':{'modelVersion':'0.2-research','computedFrom':'Cricsheet original deliveries',
                        'hasHistoricalScorecards':historical['hasHistorical'],'historicalObservedInnings':historical.get('historicalInnings',0),
                        'historicalEraCoverageStarts':historical.get('firstHistoricalDate'),
                        'historicalSource':historical_manifest.get('source') if historical_manifest else None,
                        'historicalOverlapSuppressed':read_innings.last_audit.get('duplicateHistoricalMatchInningsSuppressed',0),
                        'historicalIdentityAmbiguities':read_innings.last_audit.get('ambiguousIdentityCount',0),
                        'historicalDistinctMatchesAfterDedup':len(historic_matches),
                        'mergedDistinctMatches':manifest['matchCount']+len(historic_matches),
                        'historicalMatchesByYear':{f'{f}:{y}':n for (f,y),n in sorted(historic_years.items())},
                        'dataThrough':manifest['latestDate'],
                        'scope':'Observed available match records only','isAllTimeEligible':False,
                        'rankingCaution':'Provisional index. Historical scorecard-parity comparisons are separately computed, but cannot yet be called complete all-time rankings without official-match reconciliation and source rights verification.',
                        'reference':'https://cricsheet.org/downloads/','license':'ODC-BY 1.0'},
            'manifest':manifest,'rankings':{f:ls for f,ls in rankings.items()},'combined':overall,
            'players':list(players.values()),
            'historicalPlayers':[{'playerId':pid,'name':p['name'],'team':p['team']} for pid,p in
                {x['playerId']:x for ls in historical.get('rankings',{}).values() for x in ls}.items()],
            'eraTrends':era_trends,'scorecardParity':historical}
    # Historical 2017 player-level innings are third-party-derived with unclear
    # bulk republication rights. Do not publish even selected per-match extracts.
    # Shared-era comparisons are available only through research score aggregates.
    report['historicalFocus']=[]
    report['metadata']['historicalFocusDisclaimer']='No individual ESPN-derived historical innings reproduced; model-derived aggregates only.'
    report_text=json.dumps(report,separators=(',',':'))
    (output_dir/'report.json').write_text(report_text)
    (output_dir/'bootstrap.js').write_text('window.CGL_REPORT='+report_text.replace('</','<\\/')+';\n')
    # Publish readable human-auditable per-innings data for browser-side comparisons.
    with gzip.open(output_dir/'innings.json.gz','wt',encoding='utf-8') as f:json.dump(public_innings(rows),f,separators=(',',':'))
    # Site also uses a compressed/offline-friendly CSV; GitHub Pages can stream it with browser DecompressionStream.
    with gzip.open(output_dir/'innings.csv.gz','wt',newline='',encoding='utf-8') as f:
        fields=['date','format','player_id','name','team','opposition','runs','balls','dismissed','expected_runs','peer_relative','match_id','region','age','source_tier']
        wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader()
        for r in rows:
            wr.writerow(dict(zip(fields,[r['date'],r['format'],r['player_id'],r['name'],r['team'],r['opposition'],int(r['runs']),int(r['balls']),int(r['dismissed']),round(r['expectedRuns'],2),round(r['peerAdjustedRate'],3),r['match_id'],r['region'],round(r['fullAge'],2) if r['fullAge'] is not None else '',r['source']])))
    # JSON JS module includes a restricted sample for instant comparisons, full ledger in gz.
    important={'Virat Kohli','Shubman Gill','Sachin Tendulkar','Rahul Dravid','Ricky Ponting','Viv Richards','Steve Smith','Suryakumar Yadav','AB de Villiers','MS Dhoni','Babar Azam','Rohit Sharma','Jacques Kallis','Joe Root','Kumar Sangakkara'}
    highlights=[x for x in public_innings(rows) if x['n'] in important]
    focus_text=json.dumps(highlights,separators=(',',':'))
    (output_dir/'focus-innings.json').write_text(focus_text)
    (output_dir/'focus.js').write_text('window.CGL_FOCUS='+focus_text.replace('</','<\\/')+';\n')
    print('Calculated',len(rows),'batting innings across',manifest['matchCount'],'ingested source matches,',len(players),'players')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=pathlib.Path,default=ROOT/'data'/'generated');p.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'site'/'data');p.add_argument('--historical',type=pathlib.Path,default=ROOT/'data'/'historical'/'innings.csv');args=p.parse_args()
    build(args.input_dir,args.output_dir,args.historical)

if __name__=='__main__':main()
