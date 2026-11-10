"""Source-ledger coverage audit for the single v0.4 analysis platform.

Computes observed modern/historical match counts directly from the normalized
innings ledger and the Cricsheet manifest. Never depends on retired legacy
scorecards or generates unlicensed individual historical records.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date,datetime,timezone
import json
from pathlib import Path
from .ingest import ROOT
from .ledger import read_innings

FORMAT_START={"test":1877,"odi":1971,"t20i":2005}
FORMAT_NAMES={"test":"Tests","odi":"ODIs","t20i":"T20Is"}

def audit(root=ROOT):
    root=Path(root)
    folder=root/"data/generated"
    manifest=json.loads((folder/"manifest.json").read_text())
    matches=json.loads((folder/"matches.json").read_text())
    if len(matches)!=manifest["matchCount"]:
        raise ValueError("Cricsheet source manifest and actual match records disagree")
    rows=read_innings(folder)
    modern=defaultdict(set);historical=defaultdict(set)
    for m in matches:
        modern[(m["format"],int(m["year"]))].add(str(m["id"]) if "id" in m else str(m.get("match_id") or m.get("file") or m))
    for r in rows:
        if not r.get("scorecardOnly"):continue
        historical[(r["format"],int(r["year"]))].add(r["match_id"])
    end_year=max([date.today().year]+[int(m["year"]) for m in matches])
    formats={}
    for fmt,start in FORMAT_START.items():
        yearly=[]
        for year in range(start,end_year+1):
            old=len(historical[(fmt,year)])
            new=len(modern[(fmt,year)])
            yearly.append({"year":year,"historicalScorecardMatches":old,
                 "deliveryMatches":new,"observedMatches":old+new})
        observed=[x["year"] for x in yearly if x["observedMatches"]]
        formats[fmt]={"firstOfficialYear":start,
          "firstObservedYear":min(observed) if observed else None,
          "lastObservedYear":max(observed) if observed else None,
          "observedMatches":sum(x["observedMatches"] for x in yearly),
          "historicalScorecardMatches":sum(x["historicalScorecardMatches"] for x in yearly),
          "deliveryMatches":sum(x["deliveryMatches"] for x in yearly),
          "yearsWithZeroObservedMatches":[x["year"] for x in yearly if x["observedMatches"]==0],
          "yearly":yearly,"officialMatchesCoveredPercent":None}
    rec=root/"site/data/career-reconciliation.json"
    career=json.loads(rec.read_text()) if rec.exists() else {}
    coverage={"calculatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
       "scope":"Merged nonoverlapping source batting records; not an independently verified official census",
       "deliveryObservedMatches":manifest["matchCount"],
       "historicalObservedMatches":sum(x["historicalScorecardMatches"] for x in formats.values()),
       "totalObservedMatches":sum(x["observedMatches"] for x in formats.values()),
       "earliestDeliveryDate":manifest["earliestDate"],"latestDeliveryDate":manifest["latestDate"],
       "historicalSourceImported":any(r.get("scorecardOnly") for r in rows),
       "historicalInnings":sum(bool(r.get("scorecardOnly")) for r in rows),
       "historicalSource":"2017 ESPN-derived research snapshot; redistribution rights unverified",
       "historicalCompletenessCertified":False,"allTimeRankingPermitted":False,
       "referenceCareerRunsPassing":career.get("passingCareers",0),
       "referenceCareerRunsChecked":career.get("checkedCareers",0),
       "historicalIdentityAmbiguities":read_innings.last_audit.get("ambiguousIdentityCount",0),
       "historicalDuplicatesSuppressed":read_innings.last_audit.get("duplicateHistoricalMatchInningsSuppressed",0),
       "officialCensusReconciliation":"NOT COMPLETED",
       "notes":["Historical data include batting-only cards, not complete bowling/fielding scorecards.",
         "No independently verified all-time official match census.",
         "The source-ledger importer suppresses complete historical matches when a modern Cricsheet match overlaps.",
         "All three batting formats use the same scorecard-era index model.",
         "Historical individual source rows are excluded from public site output."],
       "formats":formats}
    out=root/"site/data";out.mkdir(parents=True,exist_ok=True)
    (out/"coverage-status.json").write_text(json.dumps(coverage,indent=2)+"\n")
    lines=["# Cricket Greatness Lab · source coverage audit","",
      f"Generated {coverage['calculatedUTC']}.","",
      "**Official all-time completeness: NOT CERTIFIED.** This is a count of observed research records, not official match-by-match validation.","",
      "| Format | Modern delivery matches | Historic batting-only matches | Provisional combined total |",
      "|---|---:|---:|---:|"]
    for f,x in formats.items():
        lines.append(f"| {FORMAT_NAMES[f]} | {x['deliveryMatches']:,} | {x['historicalScorecardMatches']:,} | {x['observedMatches']:,} |")
    lines += ["","Historical batting data are derived from a 2017 ESPN research snapshot whose redistribution rights remain unverified.","",
      f"Reference career run checks: {career.get('passingCareers',0)}/{career.get('checkedCareers',0)}; matching run totals alone does not verify every scorecard.","",
      "The new public research model publishes derived player-level metrics only; modern Cricsheet events retain ODC-BY attribution.","",
      "## Annual observed source matches","",
      "| Year | Tests modern | Tests historic | ODIs modern | ODIs historic | T20Is modern | T20Is historic |",
      "|---:|---:|---:|---:|---:|---:|---:|"]
    for yr in range(1877,end_year+1):
        values=[]
        for f in FORMAT_START:
            if yr<FORMAT_START[f]:values.extend(["—","—"])
            else:values.extend([str(len(modern[(f,yr)])),str(len(historical[(f,yr)]))])
        lines.append("| "+str(yr)+" | "+" | ".join(values)+" |")
    doc=root/"data/coverage.md";doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text("\n".join(lines)+"\n")
    return coverage

def main():
    c=audit()
    print("Coverage audit:",c["totalObservedMatches"],"source matches; certified:",c["historicalCompletenessCertified"])

if __name__=="__main__":main()
