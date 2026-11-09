"""Historical men's Test/ODI/T20I scorecard innings backfill.

Source: Duncan Golicher's publicly posted 2017 ESPNcricinfo *innings-wise*
archive. This is *not* a certified complete or public-domain dataset; download
for private research, cite provenance, and do not re-publish the raw archive.
Historical batting-order and per-bowler faced deliveries are NOT inferred.

Use `python -m pipeline.historical --download`. `--source-dir` allows lawful,
independently obtained CSV files to be supplied without downloading.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,pathlib,re,urllib.request,unicodedata
from collections import Counter,defaultdict
from datetime import datetime,date
from .ingest import ROOT,FIELDS,CITY_COUNTRY,SENA

SOURCE_BASE='https://raw.githubusercontent.com/dgolicher/cricket/master/'
SOURCE_FILES={'batting':'all-innings.csv','team':'all-match_innings.csv'}
HISTORY_FIELDS=FIELDS+['scorecard_innings_position_known','scorecard_match_order_known']
COUNTRIES={
 'AUS':'Australia','AUSTRALIA':'Australia','IND':'India','INDIA':'India',
 'ENG':'England','ENGLAND':'England','NZ':'New Zealand','NEW ZEALAND':'New Zealand',
 'SL':'Sri Lanka','SRI LANKA':'Sri Lanka','SA':'South Africa','RSA':'South Africa','SOUTH AFRICA':'South Africa',
 'WI':'West Indies','WEST INDIES':'West Indies','PAK':'Pakistan','PAKISTAN':'Pakistan',
 'BDESH':'Bangladesh','BAN':'Bangladesh','BANGLADESH':'Bangladesh',
 'ZIM':'Zimbabwe','ZIMBABWE':'Zimbabwe','AFG':'Afghanistan','AFGHANISTAN':'Afghanistan',
 'IRE':'Ireland','IRELAND':'Ireland','SCOT':'Scotland','SCOTLAND':'Scotland',
 'KENYA':'Kenya','KEN':'Kenya','UAE':'United Arab Emirates','UNITED ARAB EMIRATES':'United Arab Emirates',
 'NED':'Netherlands','NETHERLANDS':'Netherlands','NEP':'Nepal','NEPAL':'Nepal',
 'CAN':'Canada','CANADA':'Canada','USA':'United States','US':'United States',
 'NAM':'Namibia','NAMIBIA':'Namibia','HKG':'Hong Kong','HONG KONG':'Hong Kong',
 'PNG':'Papua New Guinea','OMAN':'Oman','OMN':'Oman','BER':'Bermuda','BERMUDA':'Bermuda'
}
VENUES={
 'Lord\'s':'England','The Oval':'England','Old Trafford':'England','Headingley':'England',
 'Trent Bridge':'England','Edgbaston':'England','Rose Bowl':'England','Sophia Gardens':'England',
 'MCG':'Australia','SCG':'Australia','WACA':'Australia','Gabba':'Australia',
 'Adelaide Oval':'Australia','Bellerive Oval':'Australia',
 'Basin Reserve':'New Zealand','Eden Park':'New Zealand','Hagley Oval':'New Zealand',
 'Newlands':'South Africa','Wanderers':'South Africa','Kingsmead':'South Africa',
 'SuperSport Park':'South Africa','Queen\'s Park Oval':'West Indies','Kensington Oval':'West Indies',
 'Sabina Park':'West Indies','National Stadium, Karachi':'Pakistan',
 'R Premadasa Stadium':'Sri Lanka','Eden Gardens':'India','Wankhede Stadium':'India',
 'M Chinnaswamy Stadium':'India'
}
HISTORICAL_ALIASES={
 'DG Bradman':'Don Bradman','Sir Donald Bradman':'Don Bradman','IVA Richards':'Viv Richards',
 'SR Tendulkar':'Sachin Tendulkar','V Kohli':'Virat Kohli','R Dravid':'Rahul Dravid',
 'RT Ponting':'Ricky Ponting','SPD Smith':'Steve Smith','JH Kallis':'Jacques Kallis',
 'BC Lara':'Brian Lara','KC Sangakkara':'Kumar Sangakkara','MS Dhoni':'MS Dhoni',
 'RG Sharma':'Rohit Sharma','JE Root':'Joe Root','KS Williamson':'Kane Williamson',
 'CH Gayle':'Chris Gayle','AC Gilchrist':'Adam Gilchrist','ST Jayasuriya':'Sanath Jayasuriya',
 'V Sehwag':'Virender Sehwag','AB de Villiers':'AB de Villiers','GC Smith':'Graeme Smith',
 'HM Amla':'Hashim Amla','DA Warner':'David Warner','MJ Clarke':'Michael Clarke',
 'Younis Khan':'Younis Khan','Inzamam-ul-Haq':'Inzamam-ul-Haq',
 'Mohammad Yousuf':'Mohammad Yousuf','M Yousuf':'Mohammad Yousuf',
 'S Gill':'Shubman Gill','Shubman Gill':'Shubman Gill',
 'YBK Jaiswal':'Yashasvi Jaiswal','Babar Azam':'Babar Azam',
 'TT Samaraweera':'Thilan Samaraweera'
}


def norm(v):
    value=unicodedata.normalize('NFKD',str(v or ''))
    return re.sub(r'[^a-z0-9]+','',value.encode('ascii','ignore').decode().lower())


def country(x):
    token=re.sub(r'\s+',' ',str(x or '').strip()).upper()
    return COUNTRIES.get(token,token.title())


def parse_day(raw):
    s=str(raw or '').strip()
    for pattern in ('%Y-%m-%d','%d %b %Y','%d %B %Y','%m/%d/%Y','%Y/%m/%d'):
        try:return datetime.strptime(s,pattern).date().isoformat()
        except ValueError:pass
    return None


def fmt_name(raw):
    s=str(raw or '').strip().lower().split(' v ')[0]
    if s in ('test','tests','test match'):return 'test'
    if s in ('odi','odis','one day international','one-day international'):return 'odi'
    if s in ('t20i','t20','t20 international','it20','twenty20 international'):return 't20i'
    return None


def batsman(raw):
    p=re.sub(r'\s*\([^)]*\)\s*$','',str(raw or '')).strip()
    return HISTORICAL_ALIASES.get(p,p)


def ground_host(g):
    g=str(g or '').strip()
    if g in VENUES:return VENUES[g]
    for city,host in CITY_COUNTRY.items():
        if norm(g)==norm(city) or g.endswith(', '+city):return host
    return ''


def key_match(day,fmt,team,opp):
    return (day,fmt,*sorted((team,opp)))


def checksum(path):
    with open(path,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def download(directory):
    """Use upstream raw URLs; never package or commit the downloaded raw records."""
    directory.mkdir(parents=True,exist_ok=True)
    for basename in SOURCE_FILES.values():
        target=directory/basename
        if target.exists() and target.stat().st_size>500:continue
        url=SOURCE_BASE+basename
        print('Fetching historical source:',url,flush=True)
        request=urllib.request.Request(url,headers={'User-Agent':'CricketGreatnessLab/1.1 (historical research; cites source)'})
        with urllib.request.urlopen(request,timeout=240) as response:
            with target.open('wb') as stream:
                while True:
                    block=response.read(1024*1024)
                    if not block:break
                    stream.write(block)
        with open(target,'rb') as handle:header=handle.readline(1000).lower()
        if target.stat().st_size<500 or b'player' not in header and basename=='all-innings.csv':
            raise ValueError('Historical download lacks recognizable CSV batting header: '+str(target))


def records(path):
    with open(path,'rt',encoding='utf-8-sig',newline='') as fp:
        reader=csv.DictReader(fp)
        for r in reader:yield {str(k).strip():v for k,v in r.items() if k is not None}


def match_totals(path):
    totals={};order={};collision=Counter()
    if not path.exists():return totals,order
    for row in records(path):
        f=fmt_name(row.get('type') or row.get('Format'))
        d=parse_day(row.get('Date') or row.get('Start Date'))
        t=country(row.get('Team'));o=country((row.get('Opposition') or '').removeprefix('v ').removeprefix('v'))
        if not f or not d or not t or not o:continue
        label=str(row.get('Inns') or '').strip();label=str(label).removesuffix('.0')
        try:n=int(label)
        except ValueError:continue
        k=key_match(d,f,t,o)+(t,n)
        value=str(row.get('Total') or row.get('Score') or '').strip()
        try:run=int(re.search(r'\d+',value).group())
        except (ValueError,AttributeError):continue
        if k in totals and totals[k]!=run:collision[k]+=1
        else:totals[k]=run
        # For ODI, 'Inns' from team scorecard is global innings ordinal.
        # For Tests this is also a match-innings ordinal; no global ordering is
        # otherwise inferred from the batter 'Inns' column.
        order[k]=n
    return totals,order


def load_batting(path,team_file=None):
    """Convert historic innings into same columns as modern match ledger.

    `position=0` and `role=unknown` are *intentional*: the scraped innings table
    is score-ordered, not batting-ordered. Team innings are reconstructed
    independently of source ordering.
    """
    totals,match_order=match_totals(team_file) if team_file else ({},{})
    groups=defaultdict(list);skipped=Counter();dup=0;seen={}
    for raw in records(path):
        f=fmt_name(raw.get('type') or raw.get('Format'))
        if f not in ('test','odi','t20i'):skipped['unrecognized_format']+=1;continue
        day=parse_day(raw.get('Date') or raw.get('Start Date'))
        raw_name=str(raw.get('Player') or '').strip()
        parenthesized=re.search(r'\(([^)]+)\)\s*$',raw_name)
        team=country(raw.get('Country') or (parenthesized.group(1) if parenthesized else ''))
        # Never guess the player's country from a name without an explicit tag.
        opponent=(raw.get('Opposition') or '').strip()
        opponent=re.sub(r'^v\s+','',opponent,flags=re.I)
        opp=country(opponent)
        if not day or not raw_name or not team or not opp:skipped['missing_identity_or_date']+=1;continue
        runs_s=str(raw.get('Runs') or '').strip()
        if not re.fullmatch(r'\d+\*?',runs_s):skipped['no_numeric_batting_innings']+=1;continue
        runs=int(runs_s.rstrip('*'))
        team_inn=str(raw.get('Inns') or '1').strip().removesuffix('.0')
        try:team_inn=int(team_inn)
        except ValueError:skipped['bad_innings_number']+=1;continue
        if team_inn not in (1,2,3,4):skipped['bad_innings_number']+=1;continue
        name=batsman(raw_name)
        # Never count not-out as dismissal. Legacy files encode true, T, or
        # literal star in either Runs or Notout.
        notout=str(raw.get('Notout') or '').strip().lower() in ('true','t','yes','1','*') or runs_s.endswith('*')
        balls_s=str(raw.get('BF') or raw.get('Balls') or '').strip()
        balls=int(balls_s) if re.fullmatch(r'\d+',balls_s) else 0
        fours_s=str(raw.get('Fours') or raw.get('4s') or '').strip()
        sixes_s=str(raw.get('Sixs') or raw.get('6s') or '').strip()
        source_key=(day,f,team,opp,team_inn,norm(raw_name))
        old=seen.get(source_key)
        if old is not None:
            if old==(runs,notout,balls):dup+=1;continue
            raise ValueError('Conflicting batting innings in historical source: '+str(source_key))
        seen[source_key]=(runs,notout,balls)
        ground=(raw.get('Ground') or '').strip()
        # Explicit team-inning grouping; pair sorted so both teams share one match.
        match_key=key_match(day,f,team,opp)
        groups[(match_key,team,team_inn)].append({'date':day,'format':f,'team':team,'opposition':opp,
            'name':name,'sourceName':raw_name,'runs':runs,'balls':balls,'fours':int(fours_s) if fours_s.isdigit() else 0,
            'sixes':int(sixes_s) if sixes_s.isdigit() else 0,'dismissed':0 if notout else 1,
            'ground':ground,'team_innings_number':team_inn})
    output=[];matches=set();yearfmt=Counter();quality=Counter()
    for (key,team,team_inn),rs in sorted(groups.items()):
        day,f,t1,t2=key
        gid='hist:'+f+':'+day+':'+norm(t1)+':'+norm(t2)
        iid=gid+':'+norm(team)+':'+str(team_inn)
        hosts={ground_host(x['ground']) for x in rs};hosts.discard('')
        host=next(iter(hosts)) if len(hosts)==1 else ''
        team_batter_runs=sum(x['runs'] for x in rs)
        team_batter_balls=sum(x['balls'] for x in rs)
        outs=sum(x['dismissed'] for x in rs)
        # When team-innings source is not safely matchable, gross innings total
        # remains unknown. We label this using team *batter* runs, not a total.
        official_total=totals.get(key+(team,team_inn))
        # Historical match innings source can number both teams globally (1..4)
        # while batters use each team's 1st/2nd. Never manufacture a total.
        if official_total is not None and official_total<team_batter_runs:
            official_total=None;quality['invalid_team_total']+=1
        # Match-end totals are not required for the era-parity model.
        for x in rs:
            player_id='hist:'+hashlib.sha1((norm(x['name'])+'|'+norm(team)).encode()).hexdigest()[:16]
            region='SENA' if host in SENA else 'India' if host=='India' else 'Other' if host else 'Unknown'
            row={'match_id':gid,'innings_id':iid,'date':day,'year':int(day[:4]),'format':f,
                'source':'Duncan Golicher / historical ESPNcricinfo innings snapshot (2017)',
                'source_match_file':path.name,'player_id':player_id,'name':x['name'],'team':team,'opposition':x['opposition'],
                'innings_number':team_inn,'venue':x['ground'],'city':'','host':host,'region':region,
                'home':int(host==team) if host else '', 'match_result':'','event':'','event_stage':'',
                'role':'unknown','position':0,'runs':x['runs'],'balls':x['balls'],'fours':x['fours'],'sixes':x['sixes'],
                'dismissed':x['dismissed'],'dismissal':'not out' if x['dismissed']==0 else 'dismissed',
                'team_total':official_total if official_total is not None else 0,
                'team_batter_runs':team_batter_runs,'team_wickets':outs,'team_balls':0,
                'teammate_runs':team_batter_runs-x['runs'],'teammate_balls':team_batter_balls-x['balls'],
                'teammate_dismissals':outs-x['dismissed'],
                'team_run_share':round(x['runs']/official_total,6) if official_total else 0,
                'bowler_exposures':'{}','phase_runs':'{}',
                'quality_flag':'historical-innings-no-batting-position-or-bowler-exposure',
                'scorecard_innings_position_known':0,'scorecard_match_order_known':0}
            output.append(row)
        matches.add(key)
    yearfmt=Counter((k[1],int(k[0][:4])) for k in matches)
    result={'source':SOURCE_BASE,'sourceLicense':'Unknown — original Cricinfo-derived scores; no raw archive redistributed',
        'sourceSHA256':checksum(path),'teamSourceSHA256':checksum(team_file) if team_file and team_file.exists() else None,
        'historicalMatchCount':len(matches),'historicalInnings':len(output),
        'byFormat':dict(Counter(k[1] for k in matches)),
        'firstDate':min((r['date'] for r in output),default=None),
        'lastDate':max((r['date'] for r in output),default=None),
        'skipped':dict(skipped),'duplicateSourceRows':dup,'qualityAlerts':dict(quality),
        'scorecardPositionKnown':False,'observedMatchTotalsPossiblyIncomplete':True,
        'yearCounts':{f'{fmt}:{y}':n for (fmt,y),n in sorted(yearfmt.items())}}
    return output,result


def ingest_historical(source_dir,output_dir):
    file=source_dir/SOURCE_FILES['batting']
    if not file.exists():raise FileNotFoundError(f'Historical innings source missing: {file}')
    rows,manifest=load_batting(file,source_dir/SOURCE_FILES['team'])
    if not rows:raise ValueError('Zero valid historical scorecard innings')
    output_dir.mkdir(parents=True,exist_ok=True)
    with gzip.open(output_dir/'historical-innings.csv.gz','wt',encoding='utf-8',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=HISTORY_FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    (output_dir/'historical-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Imported',len(rows),'historical player innings in',manifest['historicalMatchCount'],'matches',flush=True)
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=pathlib.Path,default=ROOT/'data'/'raw'/'historical')
    p.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'data'/'generated');p.add_argument('--download',action='store_true')
    args=p.parse_args()
    if args.download:download(args.source_dir)
    manifest=ingest_historical(args.source_dir,args.output_dir)
    print(json.dumps({k:v for k,v in manifest.items() if k!='yearCounts'},indent=2))

if __name__=='__main__':main()
