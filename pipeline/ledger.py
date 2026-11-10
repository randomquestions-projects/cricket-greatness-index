"""Shared raw innings ledger normalization used by the SINGLE v0.4 model.

Reads Cricsheet source innings and pre-2017 historical research innings, dedups
overlapping full matches, reconciles names, preserves source flags. It does NOT
create legacy rankings or publish historical source rows.
"""
from __future__ import annotations
import csv, gzip
from collections import defaultdict
from datetime import date
from .ingest import ROOT, FILES, SENA, role
from .historical import norm, country

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


