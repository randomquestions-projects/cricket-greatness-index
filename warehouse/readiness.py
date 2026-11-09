"""Unified *aggregate-only* scorecard coverage/readiness report.

Requires only rights-safe previously published aggregate manifests. Never copies
historical player/match-level records into a publicly redistributable dataset.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime,timezone
from .master import ROOT

def build(coverage,history,open_scorecards,output):
    coverage=json.loads(Path(coverage).read_text())
    history=json.loads(Path(history).read_text())
    open_scorecards=json.loads(Path(open_scorecards).read_text())
    if open_scorecards.get("independentlyCompleteScorecards") is not False:
        raise ValueError("Source-only scorecards must never be called independently complete")
    if coverage.get("allTimeRankingPermitted") is not False:
        raise ValueError("Historical coverage not officially reconciled")
    formats={}
    for fmt in ("test","odi","t20i"):
        old=coverage["formats"][fmt]
        historical=history["formats"].get(fmt,{})
        open_counts=open_scorecards["byGenderAndFormat"].get("male:"+fmt,0)
        if open_counts!=old["deliveryMatches"]:
            raise ValueError(f"Cricsheet match count mismatch for {fmt}: {open_counts} vs {old['deliveryMatches']}")
        formats[fmt]={
          "currentObservedMatches":old["observedMatches"],
          "openDeliveryDerivedMatches":open_counts,
          "historicBattingOnlyMatchesAfterOverlapSuppression":old["historicalScorecardMatches"],
          "sourceHistoricCandidateMatchesBeforeOverlap":historical.get("sourceCandidateMatches"),
          "historicBattingRowsBeforeOverlap":historical.get("historicalBattingRows"),
          "historicMissingnessRowCounts":historical.get("missingnessRowCounts",{}),
          "independentlyCertifiedCompleteScorecards":0,
          "independentMatchByMatchReconciliation":"NOT_DONE",
          "historicBowlingFigures":"MISSING_FROM_CURRENT_SOURCE",
          "historicFieldingFigures":"MISSING_FROM_CURRENT_SOURCE",
          "historicBattingOrder":"MISSING_FROM_CURRENT_SOURCE",
          "rightsToPublishHistoricScorecards":"NOT_VERIFIED",
          "interpretation":"Observed historical coverage is batting-only, not a complete scorecard."
        }
    result={
      "calculatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "purpose":"Publication-safe coverage across existing batting study and licensed scorecard warehouse",
      "historicalRecordRedistributionRights":"NOT_ESTABLISHED",
      "publishedRawHistoricalRows":False,
      "independentOfficialCensusComplete":False,
      "independentScorecardComparisonComplete":False,
      "allTimeRankingsCertified":False,
      "formatCoverage":formats,
      "openScorecardWarehouseMatches":open_scorecards["counts"]["matches"],
      "openScorecardWarehouseSource":"Cricsheet ODC-BY 1.0",
      "openScorecardSourceSHA256":open_scorecards["sourceArchiveSHA256"],
      "historicalSourceSHA256":history.get("sourceSHA256"),
      "limitations":[
        "These values combine aggregate manifests, not independently verified identical match IDs.",
        "Historical post-dedup coverage stems from the existing batting pipeline's provisional date/team keys.",
        "No historical scorecard row is redistributed here; source licensing not established.",
        "Modern scorecards are delivery-derived and may lack independently published field corrections.",
        "The number zero for independently certified complete scorecards means no independent comparison performed, NOT proof the cards are incomplete.",
        "Candidate historical matches may include key collisions; source rows differ from post-overlap counts."
      ]}
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    return result

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--coverage",type=Path,default=ROOT/"site/data/coverage-status.json")
    a.add_argument("--history",type=Path,default=ROOT/"warehouse/audits/historical_scorecard_fields.json")
    a.add_argument("--open-scorecards",type=Path,default=ROOT/"warehouse/scorecards/scorecards_manifest.json")
    a.add_argument("--output",type=Path,default=ROOT/"warehouse/audits/scorecard_readiness.json")
    args=a.parse_args()
    r=build(args.coverage,args.history,args.open_scorecards,args.output)
    print(json.dumps({k:v["currentObservedMatches"] for k,v in r["formatCoverage"].items()},indent=2))
if __name__=="__main__":main()
