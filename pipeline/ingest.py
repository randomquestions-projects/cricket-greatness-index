"""Ingest actual Cricsheet men's international match JSON into an auditable innings ledger.

Run python -m pipeline.ingest --download, or pass --archives DIR containing
 tests_male_json.zip, odis_male_json.zip, t20s_male_json.zip.
Every output record carries its original archive filename; no hand-typed player totals.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, io, json, pathlib, urllib.request
from collections import Counter, defaultdict
from datetime import date
from zipfile import ZipFile

ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES={'test':'tests_male_json.zip','odi':'odis_male_json.zip','t20i':'t20s_male_json.zip'}
NOT_OUT={'retired hurt','absent hurt','retired not out'}
NOT_BOWLER={'run out','retired out','obstructing the field','retired hurt','absent hurt','retired not out'}
# Country may be unknown. Never silently guess a venue's geography.
CITIES={
 'India':'Mumbai|Bengaluru|Bangalore|Chennai|Delhi|New Delhi|Kolkata|Ahmedabad|Pune|Hyderabad|Nagpur|Kanpur|Indore|Jaipur|Dharamsala|Dharamshala|Ranchi|Lucknow|Rajkot|Mohali|Visakhapatnam|Thiruvananthapuram|Guwahati|Cuttack|Vadodara',
 'Australia':'Sydney|Melbourne|Perth|Adelaide|Brisbane|Hobart|Canberra|Darwin|Geelong|Cairns|Gold Coast|Launceston',
 'England':'London|Leeds|Manchester|Birmingham|Southampton|Nottingham|Bristol|Chester-le-Street|Derby|Chelmsford|Leicester|Taunton|Cardiff|Canterbury|Durham',
 'South Africa':'Cape Town|Johannesburg|Centurion|Durban|Gqeberha|Port Elizabeth|Paarl|Bloemfontein|Potchefstroom|East London|Benoni',
 'New Zealand':'Auckland|Wellington|Christchurch|Hamilton|Dunedin|Napier|Nelson|Tauranga|Queenstown|Mount Maunganui|Whangarei|New Plymouth',
 'Sri Lanka':'Colombo|Galle|Kandy|Pallekele|Dambulla|Hambantota|Moratuwa',
 'Pakistan':'Lahore|Karachi|Rawalpindi|Multan|Faisalabad|Peshawar',
 'Bangladesh':'Dhaka|Chattogram|Chittagong|Sylhet',
 'Zimbabwe':'Harare|Bulawayo',
 'United Arab Emirates':'Dubai|Abu Dhabi|Sharjah',
 'West Indies':'Kingston|Bridgetown|Georgetown|Port of Spain|Gros Islet|Basseterre|St George\'s|Roseau|Providence|North Sound|St Lucia',
 'Ireland':'Dublin|Malahide|Belfast', 'Scotland':'Edinburgh|Glasgow|Aberdeen',
 'United States':'New York|Lauderhill|Dallas', 'Kenya':'Nairobi','Namibia':'Windhoek','Nepal':'Kathmandu'
}
CITY_COUNTRY={c:country for country, cities in CITIES.items() for c in cities.split('|')}
SENA={'South Africa','England','New Zealand','Australia'}
FIELDS=['match_id','innings_id','date','year','format','source','source_match_file','player_id','name','team','opposition','innings_number','venue','city','host','region','home','match_result','event','event_stage','role','position','runs','balls','fours','sixes','dismissed','dismissal','team_total','team_batter_runs','team_wickets','team_balls','teammate_runs','teammate_balls','teammate_dismissals','team_run_share','bowler_exposures','phase_runs','quality_flag']


def find_host(info):
    city=info.get('city') or ''
    if city in CITY_COUNTRY:return CITY_COUNTRY[city]
    venue=info.get('venue') or ''
    for item,country in CITY_COUNTRY.items():
        if len(item)>4 and (venue.endswith(', '+item) or venue.endswith(' '+item)):
            return country
    return None


def role(position):
    return 'opening' if position<=2 else 'top' if position<=4 else 'middle' if position<=7 else 'lower'


def phase(fmt,over):
    if fmt=='test':return 'new-ball' if over<20 else 'old-ball' if over<80 else 'second-new-ball'
    if fmt=='odi':return 'powerplay' if over<10 else 'middle' if over<40 else 'death'
    return 'powerplay' if over<6 else 'middle' if over<15 else 'death'


def parse_match(doc,archive_name,format_key):
    """Return (batting rows, bowling rows, per-delivery rows, match detail).
    Deliveries are process-local; downstream does not have to persist 5m JSON rows.
    """
    info=doc.get('info',{})
    if info.get('gender')!='male' or info.get('team_type','international')!='international':return [],[],[],None
    if info.get('match_type') not in ('Test','ODI','T20','IT20'):return [],[],[],None
    if format_key=='test' and info['match_type']!='Test':return [],[],[],None
    if format_key=='odi' and info['match_type']!='ODI':return [],[],[],None
    if format_key=='t20i' and info['match_type'] not in ('T20','IT20'):return [],[],[],None
    dates=info.get('dates',[])
    if not dates:return [],[],[],None
    try:day=date.fromisoformat(dates[0]);when=day.isoformat()
    except (TypeError,ValueError):return [],[],[],None
    teams=info.get('teams') or []
    if len(teams)!=2:return [],[],[],None
    rid=info.get('registry',{}).get('people') or {}
    match_id=format_key+':'+pathlib.Path(archive_name).stem
    host=find_host(info)
    outcome=info.get('outcome') or {}
    winner=outcome.get('winner')
    result='draw' if 'result' in outcome and outcome['result']=='draw' else ('tie' if outcome.get('result')=='tie' else 'no result' if outcome.get('result')=='no result' else winner or 'unknown')
    game={'id':match_id,'date':when,'year':day.year,'format':format_key,'teams':teams,'host':host,'venue':info.get('venue',''),'city':info.get('city',''),'result':result,'winner':winner,'event':(info.get('event') or {}).get('name',''),'eventStage':(info.get('event') or {}).get('stage',''),'sourceFile':archive_name,'source':'Cricsheet ODC-BY 1.0','scorecardType':'delivery','matchTypeNumber':info.get('match_type_number')}
    batting=[];bowling=[];deliveries=[]
    for innings_no,inn in enumerate(doc.get('innings',[]),1):
        if inn.get('super_over') or inn.get('forfeited') or not inn.get('overs'):continue
        team=inn.get('team');opp=next((t for t in teams if t!=team),None)
        if not team or not opp:continue
        people={};order=[];bowler_stats={};wickets=0
        team_runs=int((inn.get('penalty_runs') or {}).get('pre',0))+int((inn.get('penalty_runs') or {}).get('post',0));team_balls=0
        inn_id=f'{match_id}:{innings_no}'
        for over in inn.get('overs',[]):
            ov=int(over.get('over',0))
            for b in over.get('deliveries',[]):
                batter=b.get('batter');partner=b.get('non_striker');bowler=b.get('bowler')
                if not batter or not bowler:continue
                for p in (batter,partner):
                    if p and p not in people:
                        people[p]={'runs':0,'balls':0,'fours':0,'sixes':0,'dismissed':0,'dismissal':'not out','phase_runs':Counter(),'bowler_exposures':Counter()}
                        order.append(p)
                extra=b.get('extras') or {};r=b.get('runs') or {}
                batruns=int(r.get('batter',r.get('batsman',0)));total=int(r.get('total',0))
                legal=not ('wides' in extra or 'noballs' in extra)
                faced=not ('wides' in extra)
                team_runs+=total
                if legal:team_balls+=1
                batter_out=0;credit_wickets=0
                for wicket in b.get('wickets') or []:
                    victim=wicket.get('player_out');kind=wicket.get('kind','unknown')
                    if kind not in NOT_OUT:wickets+=1
                    if not victim or kind in NOT_OUT:continue
                    if victim not in people:
                        people[victim]={'runs':0,'balls':0,'fours':0,'sixes':0,'dismissed':0,'dismissal':'not out','phase_runs':Counter(),'bowler_exposures':Counter()};order.append(victim)
                    people[victim]['dismissed']=1;people[victim]['dismissal']=kind
                    if victim==batter:batter_out=1
                    if kind not in NOT_BOWLER:credit_wickets+=1
                s=people[batter]
                s['runs']+=batruns
                s['phase_runs'][phase(format_key,ov)]+=batruns
                s['bowler_exposures'][rid.get(bowler,bowler)]+=1 if faced else 0
                if faced:
                    s['balls']+=1
                    s['fours']+=int(batruns==4 and ('non_boundary' not in r))
                    s['sixes']+=int(batruns==6 and ('non_boundary' not in r))
                    deliveries.append({'id':inn_id,'match_id':match_id,'fmt':format_key,'year':day.year,'phase':phase(format_key,ov),'wicket_group':min(2,wickets//3),'position_role':role(order.index(batter)+1),'batter_id':rid.get(batter,batter),'bowler_id':rid.get(bowler,bowler),'runs':batruns,'dismissed':batter_out,'innings_number':innings_no,'host':host,'team':team,'opposition':opp})
                bs=bowler_stats.setdefault(bowler,{'bowled':0,'runs':0,'wickets':0})
                bs['bowled']+=int(legal);bs['runs']+=batruns+int(extra.get('wides',0))+int(extra.get('noballs',0));bs['wickets']+=credit_wickets
        if not order:continue
        total_batter_runs=sum(p['runs'] for p in people.values())
        total_batter_balls=sum(p['balls'] for p in people.values())
        total_dismissals=sum(p['dismissed'] for p in people.values())
        for pos,p in enumerate(order,1):
            stat=people[p]
            batting.append({'match_id':match_id,'innings_id':inn_id,'date':when,'year':day.year,'format':format_key,
                'source':'Cricsheet ODC-BY 1.0','source_match_file':archive_name,'player_id':rid.get(p,p),'name':p,'team':team,'opposition':opp,'innings_number':innings_no,
                'venue':info.get('venue',''),'city':info.get('city',''),'host':host or '',
                'region':'SENA' if host in SENA else 'India' if host=='India' else 'Other' if host else 'Unknown','home':int(host==team) if host else '',
                'match_result':result,'event':(info.get('event') or {}).get('name',''),'event_stage':(info.get('event') or {}).get('stage',''), 'role':role(pos),'position':pos,
                'runs':stat['runs'],'balls':stat['balls'],'fours':stat['fours'],'sixes':stat['sixes'],'dismissed':stat['dismissed'],'dismissal':stat['dismissal'],
                'team_total':team_runs,'team_batter_runs':total_batter_runs,'team_wickets':wickets,'team_balls':team_balls,
                'teammate_runs':total_batter_runs-stat['runs'],'teammate_balls':total_batter_balls-stat['balls'],
                'teammate_dismissals':total_dismissals-stat['dismissed'],
                'team_run_share':round(stat['runs']/team_runs,6) if team_runs else 0,
                'bowler_exposures':json.dumps(stat['bowler_exposures'],separators=(',',':')),'phase_runs':json.dumps(stat['phase_runs'],separators=(',',':')),
                'quality_flag':'observed-deliveries' if not info.get('missing') else 'source-notes:'+str(info['missing'])[:150]})
        for bowler,bs in bowler_stats.items():
            bowling.append({'match_id':match_id,'date':when,'year':day.year,'format':format_key,'bowler_id':rid.get(bowler,bowler),'name':bowler,
                            'team':opp,'opposition':team,'innings_id':inn_id,**bs})
    return batting,bowling,deliveries,game


def download_archives(directory):
    directory.mkdir(parents=True,exist_ok=True)
    for file in FILES.values():
        path=directory/file
        if path.exists() and path.stat().st_size>1000:continue
        url='https://cricsheet.org/downloads/'+file
        req=urllib.request.Request(url,headers={'User-Agent':'CricketGreatnessLab/1.0 (Research; cricsheet.org attribution)'})
        print('Downloading',url,flush=True)
        with urllib.request.urlopen(req,timeout=180) as res:
            content=res.read()
        if not content.startswith(b'PK') or len(content)<5000:raise RuntimeError('Invalid ZIP from '+url)
        path.write_bytes(content)


def ingest(archives,output,limit=0):
    output.mkdir(parents=True,exist_ok=True)
    path=output/'innings.csv.gz'; bowling_path=output/'bowling.csv.gz'
    matches=[];all_bowlers=[];sampled=[];sha={};match_counts=Counter();innings_counts=Counter();players=defaultdict(dict)
    with gzip.open(path,'wt',encoding='utf-8',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader()
        for fmt,file in FILES.items():
            archive=archives/file
            if not archive.exists():raise FileNotFoundError(str(archive))
            with archive.open('rb') as stream:sha[file]=hashlib.file_digest(stream,'sha256').hexdigest()
            with ZipFile(archive) as z:
                seen=set()
                for filename in sorted(x for x in z.namelist() if x.endswith('.json') and not x.startswith('__MACOSX/')):
                    if limit and match_counts[fmt]>=limit:break
                    stem=pathlib.Path(filename).stem
                    if stem in seen:raise ValueError('Duplicate archive id '+stem)
                    seen.add(stem)
                    with z.open(filename) as f: doc=json.load(f)
                    batting,bowling,balls,match=parse_match(doc,filename,fmt)
                    if match is None or not batting:continue
                    match_counts[fmt]+=1;innings_counts[fmt]+=len(set(b['innings_id'] for b in batting));matches.append(match)
                    for row in batting:
                        writer.writerow(row)
                        players[row['player_id']].update({'id':row['player_id'],'name':row['name'],'team':row['team']})
                    all_bowlers.extend(bowling)
    if all_bowlers:
        with gzip.open(bowling_path,'wt',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(all_bowlers[0]));writer.writeheader();writer.writerows(all_bowlers)
    (output/'matches.json').write_text(json.dumps(matches,separators=(',',':')))
    (output/'players.json').write_text(json.dumps(list(players.values()),separators=(',',':')))
    manifest={'source':'Cricsheet (ODC-BY 1.0)','url':'https://cricsheet.org/downloads/','matchCount':sum(match_counts.values()),'byFormat':dict(match_counts),'inningsByFormat':dict(innings_counts),
              'playerCount':len(players),'earliestDate':min((x['date'] for x in matches),default=None),'latestDate':max((x['date'] for x in matches),default=None),
              'sha256':sha,'coverageScope':'Available men’s international ball-by-ball matches, not complete historical scorecards','rawArchivesBundled':False,
              'withheldNotice':'Cricsheet states some international matches are withheld; see source coverage page'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--archives',type=pathlib.Path,default=ROOT/'data'/'raw');p.add_argument('--output',type=pathlib.Path,default=ROOT/'data'/'generated');p.add_argument('--download',action='store_true');p.add_argument('--limit',type=int,default=0)
    a=p.parse_args()
    if a.download:download_archives(a.archives)
    print(json.dumps(ingest(a.archives,a.output,a.limit),indent=2))

if __name__=='__main__':main()
