"""Source-scoped official-number gap CANDIDATES, not official match census.

Use this to prioritize matches to verify from rights-cleared authoritative records.
A skipped integer can be an unobserved game or a provider numbering discrepancy.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from zipfile import ZipFile

from .master import ROOT, classification

def audit(archive, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    by_group=defaultdict(lambda:defaultdict(list))
    missing_number=Counter();matches=Counter();duplicated=[];potential_missing={}
    with ZipFile(archive) as bundle:
        for filename in sorted(n for n in bundle.namelist() if n.endswith(".json")):
            with bundle.open(filename) as f:
                info=(json.load(f).get("info") or {})
            category=classification(info)
            gender=str(info.get("gender") or "unknown").lower()
            group=f"{gender}:{category}"
            matches[group]+=1
            number=info.get("match_type_number")
            if number is None:
                missing_number[group]+=1;continue
            try:num=int(number)
            except (ValueError,TypeError):missing_number[group]+=1;continue
            by_group[group][num].append(Path(filename).stem)
    details={}
    for group,numbers in sorted(by_group.items()):
        candidates=[]
        if numbers:
            numlist=sorted(numbers)
            # Only gaps *inside* observed range. Never infer missing records
            # before earliest observed or after the last observed.
            for lower,upper in zip(numlist,numlist[1:]):
                if upper-lower>1:
                    candidates.extend(range(lower+1,upper))
            for number,files in numbers.items():
                if len(files)>1:
                    duplicated.append({"group":group,"matchTypeNumber":number,"sourceFiles":files})
            details[group]={
                "observedUniqueNumberedMatches":len(numbers),
                "observedWithoutMatchTypeNumber":missing_number[group],
                "minObservedNumber":numlist[0],
                "maxObservedNumber":numlist[-1],
                "potentialUnobservedNumbers":candidates,
                "potentialMissingCount":len(candidates)}
    report={
        "generatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source":"Cricsheet full public archive", "scope":"INTERNAL_SOURCE_GAP_CANDIDATES",
        "isOfficialIndependentCensus":False,
        "warning":"Internal gaps may be due to missing matches, delayed uploads, or mismatched numbering. This is not verification against an independent official match registry.",
        "observedMatchesByCategory":dict(sorted(matches.items())),
        "groups":details,"duplicateMatchTypeNumbers":duplicated
    }
    (output/"match_inventory.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,default=ROOT/"data"/"raw"/"all_json.zip")
    p.add_argument("--output",type=Path,default=ROOT/"warehouse"/"master")
    a=p.parse_args()
    x=audit(a.archive,a.output)
    print("Source match-number candidate gaps:",sum(g["potentialMissingCount"] for g in x["groups"].values()))
    print("Not independently verified official missing matches.")
if __name__=="__main__":main()
