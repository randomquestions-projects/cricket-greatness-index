"""Aggregate ONLY audit of the restricted 2017 historical innings snapshot.

This program reads local restricted-source snapshots, but NEVER serializes
individual player performances, innings, match IDs, venue, or scorecard rows
into the public report. Summaries are descriptive and not a rights conclusion.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
from .master import ROOT

def audit(history_rows,modern_matches,output, historical_manifest=None):
    """Review source missingness, not complete official scorecards."""
    history_rows=Path(history_rows);modern_matches=Path(modern_matches);output=Path(output)
    by_format=Counter();groupkeys=defaultdict(set);team_innings=defaultdict(set)
    missing=defaultdict(Counter); decades=Counter()
    modern=set()
    if modern_matches.exists():
        with modern_matches.open() as stream:
            for m in json.load(stream):
                teams=m.get("teams") or []
                if len(teams)==2:
                    from pipeline.historical import country
                    key=(m["date"],m["format"],*sorted(country(t) for t in teams))
                    modern.add(key)
    from pipeline.historical import country
    opener=gzip.open if history_rows.suffix==".gz" else open
    with opener(history_rows,"rt",encoding="utf-8",newline="") as stream:
        for row in csv.DictReader(stream):
            fmt=row.get("format")
            if fmt not in ("test","odi","t20i"):continue
            date=row.get("date") or ""
            if len(date)<10:continue
            year=int(date[:4])
            team=country(row.get("team"));opp=country(row.get("opposition"))
            key=(date,fmt,*sorted((team,opp)))
            by_format[fmt]+=1
            decades[(fmt,year//10*10)]+=1
            groupkeys[fmt].add(key)
            team_innings[fmt].add((key,team,row.get("innings_number")))
            if key in modern:missing[fmt]["has_modern_overlap"]+=1
            if int(float(row.get("position") or 0))==0:missing[fmt]["missing_batting_order"]+=1
            if int(float(row.get("balls") or 0))==0:missing[fmt]["zero_or_unknown_balls_faced"]+=1
            if not row.get("dismissal") or row.get("dismissal") in ("dismissed","not out"):
                missing[fmt]["no_detailed_dismissal_type"]+=1
            if int(float(row.get("team_total") or 0))==0:
                missing[fmt]["no_reconciled_team_total"]+=1
            if row.get("bowler_exposures","{}").strip() in ("{}",""):
                missing[fmt]["no_bowler_exposures"]+=1
    per_format={}
    for fmt,n in by_format.items():
        per_format[fmt]={
          "historicalBattingRows":n,
          "sourceCandidateMatches":len(groupkeys[fmt]),
          "sourceTeamInningsGroups":len(team_innings[fmt]),
          "fields":{"battingRuns":"observed_in_source",
                    "bowlingFigures":"not_provided",
                    "fieldingDismissalTypes":"not_provided",
                    "extras":"not_systematically_reconciled",
                    "battingPosition":"unavailable",
                    "matchResult":"unavailable",
                    "officialMatchNumber":"unavailable"},
          "missingnessRowCounts":dict(missing[fmt]),
          "decadeBattingRows":{str(dec):count for (f,dec),count in sorted(decades.items()) if f==fmt}}
    meta=json.loads(Path(historical_manifest).read_text()) if historical_manifest and Path(historical_manifest).exists() else {}
    report={
      "generatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "source":"2017 historical innings snapshot, restricted derivative",
      "rightsStatus":"UNVERIFIED: historical records must not be distributed as an open database",
      "individualHistoricalSourceRowsPublished":False,
      "containsIndividualMatchScorecards":False,
      "officialMatchCensusCertified":False,
      "scorecardCompletenessCertified":False,
      "sourceSHA256":meta.get("sourceSHA256"),
      "formats":per_format,
      "methodology":"Aggregate field presence and candidate match keys only; no individual player, innings or match rows are released.",
      "limitations":[
        "Match counts use date+teams+format as a provisional signature; may merge same-day matches",
        "A zero balls-faced value can mean either genuine 0 or unknown; source schema cannot distinguish",
        "Missing bowling/fielding/official match identifiers cannot be supplied by this snapshot",
        "A historical batting row with a team total is still not a full scorecard",
        "No historical original data is added to the public master warehouse or release"
      ]
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--historical",type=Path,default=ROOT/"data/generated/historical-innings.csv.gz")
    p.add_argument("--modern",type=Path,default=ROOT/"data/generated/matches.json")
    p.add_argument("--historical-manifest",type=Path,default=ROOT/"data/generated/historical-manifest.json")
    p.add_argument("--output",type=Path,default=ROOT/"warehouse/audits/historical_scorecard_fields.json")
    a=p.parse_args()
    r=audit(a.historical,a.modern,a.output,a.historical_manifest)
    print("Historical source audit:",{k:{"rows":v["historicalBattingRows"],"candidate_matches":v["sourceCandidateMatches"]} for k,v in r["formats"].items()})
    print("No historical individual record data published.")
if __name__=="__main__":main()
