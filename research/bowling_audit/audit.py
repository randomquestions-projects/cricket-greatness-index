"""Read-only bowling coverage audit; Cricsheet ODC-BY source only.

This module is isolated under research/, not imported by the batting app.
It NEVER downloads or processes rights-uncertain historical scorecards.
"""
import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

FORMATS = ("test","odi","t20i")
ALIASES = {
 "Sydney Barnes":["SF Barnes","Sydney Barnes"],
 "Jim Laker":["JC Laker","Jim Laker"],
 "Clarrie Grimmett":["CV Grimmett","Clarrie Grimmett"],
 "Malcolm Marshall":["MD Marshall","Malcolm Marshall"],
 "Richard Hadlee":["RJ Hadlee","Sir RJ Hadlee","Richard Hadlee"],
 "Wasim Akram":["Wasim Akram"],
 "Waqar Younis":["Waqar Younis"],
 "Shane Warne":["SK Warne","Shane Warne"],
 "Muttiah Muralitharan":["M Muralitharan","Muttiah Muralitharan"],
 "Glenn McGrath":["GD McGrath","Glenn McGrath"],
 "Anil Kumble":["A Kumble","Anil Kumble"],
 "James Anderson":["JM Anderson","James Anderson"],
 "Dale Steyn":["DW Steyn","Dale Steyn"],
 "Ravichandran Ashwin":["R Ashwin","Ravichandran Ashwin"],
 "Mitchell Starc":["MA Starc","Mitchell Starc"],
 "Pat Cummins":["PJ Cummins","Pat Cummins"],
 "Jasprit Bumrah":["JJ Bumrah","Jasprit Bumrah"]
}
def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def run(shards,output):
    source=[];data=defaultdict(lambda:defaultdict(int));identity=defaultdict(list)
    with tempfile.TemporaryDirectory(prefix="bowling-audit-") as temporary:
        for shard in shards:
            shard=Path(shard)
            disk=Path(temporary)/shard.name[:-3]
            with gzip.open(shard,"rb") as s,disk.open("wb") as d:shutil.copyfileobj(s,d)
            db=sqlite3.connect(f"file:{disk}?mode=ro",uri=True)
            db.row_factory=sqlite3.Row
            try:
                tables={x["name"] for x in db.execute("select name from sqlite_master where type='table'")}
                assert {"matches","innings","bowling","quality_flags"}<=tables
                source.append({"file":shard.name,"sha256":sha256(shard),
                      "sourceMatches":db.execute("select count(*) from matches").fetchone()[0]})
                for x in db.execute("""
                    SELECT m.category AS fmt,substr(m.start_date,1,4) AS year,
                        count(distinct m.id) AS matches,count(distinct i.id) AS innings,
                        count(b.player_name) AS bowlingRows,
                        coalesce(sum(case when b.player_name is not null
                             and b.player_id is null then 1 else 0 end),0) AS missingBowlerID,
                        coalesce(sum(b.wickets),0) AS wickets,
                        coalesce(sum(b.legal_balls),0) AS legalBalls,
                        coalesce(sum(b.conceded),0) AS concededRuns
                    FROM matches m LEFT JOIN innings i ON i.match_id=m.id AND i.super_over=0
                    LEFT JOIN bowling b ON b.innings_id=i.id
                    WHERE m.gender='male' AND m.category IN ('test','odi','t20i')
                    GROUP BY m.category,substr(m.start_date,1,4)"""):
                    a=data[(x["fmt"],int(x["year"]))]
                    for k in ("matches","innings","bowlingRows","missingBowlerID","wickets",
                              "legalBalls","concededRuns"):a[k]+=int(x[k] or 0)
                for x in db.execute("""
                    SELECT m.category AS fmt,substr(m.start_date,1,4) AS year,
                           count(distinct m.id) AS noVenue
                    FROM matches m WHERE m.gender='male' AND m.category IN ('test','odi','t20i')
                    AND (m.venue IS NULL OR trim(m.venue)='')
                    GROUP BY m.category,substr(m.start_date,1,4)"""):
                    data[(x["fmt"],int(x["year"]))]["noVenue"]+=int(x["noVenue"])
                for x in db.execute("""
                    SELECT m.category AS fmt,substr(m.start_date,1,4) AS year,
                           count(distinct m.id) AS flagged
                    FROM matches m JOIN quality_flags q ON q.match_id=m.id
                    WHERE m.gender='male' AND m.category IN ('test','odi','t20i')
                    GROUP BY m.category,substr(m.start_date,1,4)"""):
                    data[(x["fmt"],int(x["year"]))]["flagged"]+=int(x["flagged"])
                for x in db.execute("""
                    SELECT m.category fmt,b.player_name name,b.player_id pid,
                           count(*) innings,coalesce(sum(b.wickets),0) wickets,
                           min(m.start_date) firstDate,max(m.start_date) lastDate
                    FROM matches m JOIN innings i ON i.match_id=m.id AND i.super_over=0
                    JOIN bowling b ON b.innings_id=i.id
                    WHERE m.gender='male' AND m.category IN ('test','odi','t20i')
                    GROUP BY m.category,b.player_name,b.player_id"""):
                    identity[x["name"].casefold()].append(dict(x))
            finally:db.close()
    by_format={}
    for fmt in FORMATS:
        years=sorted((yr,r) for (f,yr),r in data.items() if f==fmt and r["matches"])
        d={k:sum(row[k] for _,row in years) for k in ("matches","innings","bowlingRows",
                    "missingBowlerID","wickets","legalBalls","concededRuns","noVenue","flagged")}
        d.update(firstObservedYear=years[0][0] if years else None,
                 lastObservedYear=years[-1][0] if years else None,
                 historicallyComplete=False)
        by_format[fmt]=d
    players=[]
    for player,aliases in ALIASES.items():
        matches=[x for alias in aliases for x in identity[alias.casefold()]]
        players.append(dict(player=player,observedBowlingInnings=sum(x["innings"] for x in matches),
             observedWickets=sum(x["wickets"] for x in matches),sourceNames=sorted({x["name"] for x in matches}),
             observedDateSpans=[{"format":x["fmt"],"start":x["firstDate"],"end":x["lastDate"]}
                                for x in matches],
             isFullCareer=False,warning="Source-only, exact-alias candidates; not an official career total."))
    report={
      "generatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "licensedSource":"Cricsheet scorecard-derived; ODC-BY 1.0",
      "scope":"Mens Test, ODI, T20I; excludes domestic and women",
      "sourceShards":source,"byFormat":by_format,
      "byYear":[dict(format=f,year=y,**r) for (f,y),r in sorted(data.items())],
      "playerCaseStudies":players,
      "historicalBowlingCompletenessCertified":False,
      "officialMatchCensusReconciled":False,
      "officialPlayerCareerTotalsChecked":False,
      "rightsGate":"Only licensed Cricsheet source processed. No ESPN-derived archive ingested.",
      "fieldAvailability":{
        "wicketsConcededLegalBalls":"recorded in observed modern scorecards",
        "recordedOpponentNation":"from match teams and batting side",
        "sameInningsBowlingTeammates":"from observed licensed scorecards",
        "recordedVenueText":"available unless missing; host nation not normalized",
        "physicalPitchMeasurement":"not available",
        "paceSpin":"not systematically normalized from license-cleared register",
        "phaseSplits":"modern deliveries preserved in separate licensed master warehouse",
        "pre2001BowlingFigures":"not in current licensed modern warehouse"
      }}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"coverage.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# Men's International Bowling Data Availability Audit","",
      "This is a source-backed **availability audit**, not a bowling index.",
      "Only the licensed Cricsheet scorecard archive was processed. The batting app was not changed.",
      "","## Confirmed modern scorecard coverage","",
      "| Format | Observed matches | First year | Bowler-innings rows | Recorded wickets | Missing bowler IDs | Source-flagged matches |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for f,x in by_format.items():
        lines.append(f"| {f.upper()} | {x['matches']:,} | {x['firstObservedYear']} | {x['bowlingRows']:,} | {x['wickets']:,} | {x['missingBowlerID']:,} | {x['flagged']:,} |")
    lines+=["","These are observed-source wickets, not full-career totals. No data from pre-Cricsheet historical bowling scorecards are held in this open release.",
      "","## Historical greats: observed only, NOT full career","",
      "| Bowler | Observed bowler-innings | Recorded wickets | Source aliases |",
      "|---|---:|---:|---|"]
    for p in players:
        lines.append(f"| {p['player']} | {p['observedBowlingInnings']:,} | {p['observedWickets']:,} | {', '.join(p['sourceNames']) or 'none'} |")
    lines+=["","## Availability for proposed controls","",
      "| Control | Available today | Missing for all-era model |",
      "|---|---|---|",
      "| Era-adjusted wicket-taking and run prevention | Wickets, runs conceded, balls, year | Historical bowling figures before ~2001 |",
      "| Opposition strength | Opponent batting side, same-source batting | Historical bowling-opponent records |",
      "| Home/away | Match venue text, batting/bowling teams | Verified venue country for all matches |",
      "| Match and pitch difficulty | Same-match batting and other bowlers | Measured pitch properties unavailable |",
      "| Team carry | Other bowlers in same observed innings | Complete historic team bowling figures |",
      "| JAWS-inspired peak/career | Calendar dates, observed workload and wickets | Historical career segments, match opportunity adjustment |",
      "| Pace and spin | Not reliably recorded in scorecard fields | License-cleared style reference needed |",
      "| ODI/T20I phases | Licensed raw delivery warehouse can support | Never comparable to historical scorecard-only players |",
      "","## Historical rights assessment","",
      "| Source | Potential content | Clearance |",
      "|---|---|---|",
      "| Cricsheet / existing master warehouse | Modern international bowling scorecards | **ODC-BY 1.0; use now** |",
      "| Duncan Golicher crickdata (2017) | ESPN-derived bowling innings across Tests, ODIs, T20Is | **No verified redistribution license; do not bulk import** |",
      "| Philipson academic Test bowler dataset (2022) | 47,216 bowler-innings / 2,207 players, 1877–2022 | **Article CC BY, underlying GitHub dataset has no explicit license; request clarification** |",
      "| Hugging Face 1877–2014 Test Bowling Card | Historical per-innings bowling details | **Source provenance and reuse rights unverified** |",
      "| ACS Cricket / CricArcade / Howstat / CricketArchive / ESPN | Historical scorecards and checks | **Reference only; no unrestricted bulk license established** |",
      "","## Audit conclusion","",
      "**Modern model data readiness: YES.** The licensed scorecard warehouse supports a defensible bowling research prototype.",
      "**All-time historical model readiness: NO.** Older greats would be undercounted or absent.",
      "**Recommended next data acquisition: legally reusable historical bowling figures at player × match-innings level, then independent player/match reconciliation.**",
      "","Sources:",
      "- https://cricsheet.org/licensing/",
      "- https://github.com/dgolicher/crickdata",
      "- https://github.com/petephilipson/MPCMP_Test_bowlers",
      "- https://journals.sagepub.com/doi/full/10.1177/1471082X231178584",
      "- https://huggingface.co/datasets/bhuvaneshprasad/test-cricket-dataset-1877-2014"]
    (output/"coverage.md").write_text("\n".join(lines)+"\n")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--shards",nargs="+",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    report=run(args.shards,args.output)
    print(json.dumps(report["byFormat"],indent=2))
