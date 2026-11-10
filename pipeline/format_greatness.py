"""Shared-scorecard era format analysis & combined multi-format leaderboards.

Derived historical player-level aggregate research output only. No restricted
source innings or match records in newly published outputs. Rankings are
experimental; format ranks and overall percentiles are not probabilities.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from .ingest import ROOT
from .ledger import read_innings
from .test_greatness import build_from_rows

FORMATS=("test","odi","t20i")
COMBINATIONS={"test_odi":("test","odi"),"all_three":FORMATS}
MINIMUM={"test":35,"odi":35,"t20i":25}

def percentiles(players,metric):
    eligible=sorted((p for p in players if p.get(metric) is not None),key=lambda p:p[metric])
    n=len(eligible)
    return {p["playerId"]:round(100*(i+.5)/n,2) for i,p in enumerate(eligible)} if n else {}

def _identity(player):
    # A conservatively qualified identity: player display name + team.
    # Do not join ambiguous same-name players from different countries.
    return (player["name"].casefold().strip(),player["team"].casefold().strip())

def combined(reports):
    normalized={}
    for f in FORMATS:
        p=reports[f]["players"]
        normalized[f]={
            "quality":percentiles(p,"quality"),
            "teamCarry":percentiles(p,"teamCarry"),
            "careerGreatness":percentiles(p,"careerGreatness"),
            "jawsStyleValue":percentiles(p,"jawsStyleValue"),
            "bestSevenSeasonValue":percentiles(p,"bestSevenSeasonValue")}
    groups=defaultdict(dict)
    for f in FORMATS:
        for p in reports[f]["players"]:
            if p["innings"]>=MINIMUM[f]:
                groups[_identity(p)][f]=p
    result={}
    for key,formats in COMBINATIONS.items():
        rankings=[]
        for ident,found in groups.items():
            if any(f not in found for f in formats):
                continue
            base=found[formats[0]]
            pcts={f:{m:normalized[f][m].get(found[f]["playerId"])
                  for m in normalized[f]} for f in formats}
            def ave(metric):
                vals=[pcts[f][metric] for f in formats]
                if any(v is None for v in vals):return None
                return round(sum(vals)/len(vals),2)
            rankings.append({
                "playerId":base["playerId"],"name":base["name"],"team":base["team"],
                "overallQualityPercentile":ave("quality"),
                "overallCarryPercentile":ave("teamCarry"),
                "overallCareerPercentile":ave("careerGreatness"),
                "overallJawsPercentile":ave("jawsStyleValue"),
                "overallPeakPercentile":ave("bestSevenSeasonValue"),
                "overallIndex":ave("jawsStyleValue"),
                "totalInnings":sum(found[f]["innings"] for f in formats),
                "formats":{f:{"quality":found[f]["quality"],
                    "carry":found[f]["teamCarry"],
                    "career":found[f]["careerGreatness"],
                    "jawsStyleValue":found[f]["jawsStyleValue"],
                    "jawsPercentile":pcts[f]["jawsStyleValue"],
                    "innings":found[f]["innings"],
                    "historicInnings":found[f]["historicalInnings"]} for f in formats}
            })
        rankings.sort(key=lambda x: -x["overallIndex"])
        for i,p in enumerate(rankings,1):p["rank"]=i
        result[key]=rankings
    return result

def build(input_dir=ROOT/"data/generated", output_dir=ROOT/"site/data", bootstrap=True):
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    rows=read_innings(Path(input_dir))
    reports={}
    for f in FORMATS:
        r=build_from_rows(rows,bootstraps=bootstrap,format_code=f,minimum_innings=MINIMUM[f])
        r["modelVersion"]="scorecard-common-denominator-v0.4-jaws-experimental"
        r["format"]=f
        r["qualificationMinimumInnings"]=MINIMUM[f]
        # Keep per-format rankings and inputs identical across centuries.
        for p in r["players"]:
            p["jawsPercentile"]=None
        norm=percentiles([p for p in r["players"] if p["innings"]>=MINIMUM[f]],"jawsStyleValue")
        for p in r["players"]:p["jawsPercentile"]=norm.get(p["playerId"])
        reports[f]=r
        (output_dir/(f+"-greatness.json")).write_text(json.dumps(r,separators=(",",":"),ensure_ascii=False)+"\n")
    combos=combined(reports)
    meta={"modelVersion":"v0.4 scorecard-era JAWS-inspired",
          "allTimeCertified":False,
          "sourceRights":"Historical source derived from ESPN research; redistribution terms not established. Only calculated player-level aggregates and grouped context published.",
          "modernOnlyFeaturesInPrimaryIndex":False,
          "publishedHistoricalInningsRows":False,
          "methodology":{
             "singleFormat":"Era-adjusted quality, same-innings team carry, best rolling 25 innings and JAWS-inspired career/7-best-calendar-season surplus",
             "jaws":"JAWS-like = (career standardized contextual surplus + sum of seven highest observed season surpluses)/2. NOT baseball WAR and not adjusted for annual match opportunities.",
             "combined":"Equal-weight arithmetic mean of within-format percentile rankings for each qualifying player. Never compare raw format surplus units directly.",
             "eligibility":"Must meet minimum observed innings in every included format. Does not impute unplayed formats; pre-T20I stars absent from all-three ranking.",
             "careerScoring":"Longevity inherently rewarded. Short peak versus long career is shown separately.",
             "dataCaveat":"Historical source completeness, competition diversity, batting order and measured pitch remain unverified."
          },"formats":{f:{"qualifiedPlayers":r["qualifiedPlayers"],"observedInnings":r["observedTestInnings"],
                           "historicInnings":r["historicalTestInnings"]} for f,r in reports.items()},
          "combined":combos}
    (output_dir/"greatness-combined.json").write_text(json.dumps(meta,separators=(",",":"),ensure_ascii=False)+"\n")
    return meta

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,default=ROOT/"data/generated")
    a.add_argument("--output",type=Path,default=ROOT/"site/data")
    a.add_argument("--skip-bootstrap",action="store_true")
    args=a.parse_args()
    out=build(args.input,args.output,not args.skip_bootstrap)
    print(json.dumps({"formats":out["formats"],
        "combined":{k:{"eligible":len(v),"top":v[0]["name"] if v else None} for k,v in out["combined"].items()}},indent=2))

if __name__=="__main__":main()
