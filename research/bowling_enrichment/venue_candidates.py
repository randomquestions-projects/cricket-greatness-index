"""Generate REVIEW-ONLY Wikidata exact-label venue-country candidates.

This file does not assert identities, update the verified ground-country field,
or affect batting rankings. Exact English venue labels are searched only in
Wikidata's CC0 claims. Ambiguous identical labels and conflicting countries
are not automatically resolved.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

WDQS="https://query.wikidata.org/sparql"
UA="CricketGreatnessLab-BowlingVenueAudit/1.0 (https://github.com/randomquestions-projects/cricket-greatness-index)"
def csvread(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def quote(s):
    return json.dumps(s,ensure_ascii=False)+"@en"
def query_batch(names):
    values=" ".join(quote(s) for s in names)
    q= """SELECT DISTINCT ?venueName ?ground ?country ?countryLabel ?isoCode WHERE {
      VALUES ?venueName { %s }
      ?ground rdfs:label ?venueName; wdt:P17 ?country.
      OPTIONAL { ?country wdt:P297 ?isoCode. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }""" % values
    u=WDQS+"?"+urllib.parse.urlencode({"query":q,"format":"json"})
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"application/sparql-results+json"})
    with urllib.request.urlopen(req,timeout=65) as r:
        b=r.read(8_000_000)
    j=json.loads(b)
    return [{k:v["value"] for k,v in x.items()} for x in j["results"]["bindings"]]

def find_candidates(references,output,batch_size=25,loader=query_batch):
    references=Path(references);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    venues=csvread(references/"venue_physical_country.csv")
    aliases=csvread(references/"venue_aliases.csv")
    by_id=defaultdict(set)
    for r in venues:
        if r["venue_name"]:by_id[r["cricsheet_venue_id"]].add(r["venue_name"].strip())
    for r in aliases:
        if r["alias"]:by_id[r["cricsheet_venue_id"]].add(r["alias"].strip())
    names=sorted({name for opts in by_id.values() for name in opts if len(name)>=5
                  and len(name)<130 and not re.search(r"[\n\r\t]",name)})
    matches=defaultdict(set)
    errors=[]
    for offset in range(0,len(names),batch_size):
        batch=names[offset:offset+batch_size]
        try:
            for r in loader(batch):
                name=r.get("venueName","")
                if name in batch and r.get("countryLabel"):
                    matches[name].add((r.get("ground",""),r.get("country",""),
                                       r.get("countryLabel",""),r.get("isoCode","")))
        except Exception as e:
            errors.append({"firstName":batch[0],"error":str(e)[:240]})
        if loader is query_batch:time.sleep(.4)
    rows=[];status=defaultdict(int)
    for v in venues:
        vid=v["cricsheet_venue_id"]
        if v.get("match_status")=="linked" and v.get("physical_country"):
            status["already_verified_by_espn_id"]+=1
            continue
        observations=set()
        for name in by_id.get(vid,set()):
            for ground,country,countryLabel,code in matches.get(name,set()):
                observations.add((name,ground,country,countryLabel,code))
        countries={(c,lab,code) for _,_,c,lab,code in observations}
        if not observations:kind="no_candidate"
        elif len(countries)>1:kind="multiple_countries_ambiguous"
        elif len({o[1] for o in observations})>1:kind="multiple_grounds_same_country_review"
        else:kind="single_exact_label_candidate_review"
        status[kind]+=1
        rows.append({"cricsheet_venue_id":vid,"venue_name":v["venue_name"],
            "candidate_country":" | ".join(sorted({c[1] for c in countries})),
            "candidate_iso":" | ".join(sorted({c[2] for c in countries if c[2]})),
            "candidate_wikidata_ground_ids":" | ".join(sorted({o[1].rsplit("/",1)[-1] for o in observations})),
            "matching_venue_aliases":" | ".join(sorted({o[0] for o in observations})),
            "review_status":kind,
            "verified_country":""})
    with (output/"venue_country_candidates_REVIEW_ONLY.csv").open("w",newline="",encoding="utf-8") as f:
        fields=["cricsheet_venue_id","venue_name","candidate_country","candidate_iso",
                "candidate_wikidata_ground_ids","matching_venue_aliases","review_status","verified_country"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    report={"status":dict(status),"queriedNames":len(names),"queriedNamesMatched":len(matches),
      "lookupErrors":errors,
      "rights":"Wikidata CC0 only; Cricsheet ODC-BY 1.0",
      "verifiedCountryJoinUpdated":False,
      "historicalMatchDataImported":False,
      "modelFeedsAllowed":False,
      "notes":["Exact string matches are review candidates, NOT verified identifications.",
               "Match location physical country is distinct from the cricket host nation.",
               "Ambiguous names/countries remain unresolved.",
               "No inference from venue name geographic substrings."]}
    (output/"candidate_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--references",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--batch-size",type=int,default=25)
    a=p.parse_args()
    print(json.dumps(find_candidates(a.references,a.output,a.batch_size),indent=2))
