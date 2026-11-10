"""Rights-cleared bowling-only reference enrichment.

Cricsheet People/Venue registers: ODC-BY 1.0 (attribution required).
Wikidata structured facts: CC0 (P2697 player IDs + P2545 bowling style;
P3572 ground IDs + P17 country).
Never request ESPN, historical scorecards or their unlicensed data.
Unmatched / conflicting reference values remain UNKNOWN; no name-only joins.
Does not change the batting app or any of its public data.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "bowling_enrichment" / "output"
REGISTERS = {
    "people": "https://cricsheet.org/register/people.csv",
    "names": "https://cricsheet.org/register/names.csv",
    "venues": "https://cricsheet.org/register/venues.csv",
    "venue_names": "https://cricsheet.org/register/venue_names.csv",
}
SPARQL = "https://query.wikidata.org/sparql"
PLAYER_QUERY = """SELECT DISTINCT ?espnId ?player ?bowlingStyleLabel WHERE {
  ?player wdt:P2697 ?espnId; wdt:P2545 ?bowlingStyle.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""
VENUE_QUERY = """SELECT DISTINCT ?espnId ?ground ?country ?countryLabel ?isoCode WHERE {
  ?ground wdt:P3572 ?espnId; wdt:P17 ?country.
  OPTIONAL { ?country wdt:P297 ?isoCode. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""
AGENT = "CricketGreatnessLabBowlingResearch/1.0 (https://github.com/randomquestions-projects/cricket-greatness-index; licensed-data-enrichment)"
HEADERS = {"User-Agent": AGENT, "Accept": "text/csv,application/sparql-results+json,application/json"}

def fetch(url, retry=2):
    last = None
    for attempt in range(retry + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=110) as resp:
                content = resp.read(15_000_000)
                if resp.read(1):
                    raise ValueError("Source exceeded 15 MB per individual source; refusing")
                return content
        except Exception as err:
            last = err
            if attempt < retry:
                time.sleep(4 + attempt * 7)
    raise RuntimeError("Source unavailable: " + url + ": " + str(last))

def csv_rows(payload):
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))

def normalize_id(value):
    v = str(value or "").strip()
    if v.endswith(".0") and v[:-2].isdigit():
        v = v[:-2]
    return v if re.fullmatch(r"[0-9]+", v) else ""

def qid(uri):
    return str(uri or "").rstrip("/").rsplit("/", 1)[-1]

def wd_rows(query):
    u = SPARQL + "?" + urllib.parse.urlencode({"query":query,"format":"json"})
    obj = json.loads(fetch(u))
    return [{key:val.get("value","") for key,val in row.items()} for row in obj["results"]["bindings"]]

def style_group(label):
    s = (label or "").casefold()
    pace = any(x in s for x in ["fast","medium","seam","pace"])
    spin = any(x in s for x in ["spin","orthodox","break","googly","wrist","chinaman"])
    if pace and not spin:
        return "pace"
    if spin and not pace:
        return "spin"
    return "unknown"

def write_csv(path, fieldnames, rows):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f,fieldnames=fieldnames,extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def build(output=OUT, register_loader=None, wikidata_loader=None):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    source = {}
    registers = {}
    for name,url in REGISTERS.items():
        payload = register_loader(name,url) if register_loader else fetch(url)
        registers[name] = csv_rows(payload)
        source[name]={"url":url, "bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),
                      "rows":len(registers[name]),"license":"ODC-BY-1.0"}
    wd = wikidata_loader or wd_rows
    wikidata_errors = []
    try:
        player_wd = wd(PLAYER_QUERY)
    except Exception as err:
        player_wd = []
        wikidata_errors.append("Player bowling styles query unavailable: " + str(err)[:250])
    try:
        ground_wd = wd(VENUE_QUERY)
    except Exception as err:
        ground_wd = []
        wikidata_errors.append("Venue country query unavailable: " + str(err)[:250])

    by_player=defaultdict(set)
    for item in player_wd:
        pid=normalize_id(item.get("espnId"))
        style=item.get("bowlingStyleLabel") or ""
        if pid and style:
            by_player[pid].add((qid(item.get("player")),style,style_group(style)))

    by_ground=defaultdict(set)
    for item in ground_wd:
        pid=normalize_id(item.get("espnId"))
        country=item.get("countryLabel") or ""
        if pid and country:
            by_ground[pid].add((qid(item.get("ground")),qid(item.get("country")),
                                country,item.get("isoCode") or ""))

    people=[]
    for p in registers["people"]:
        key=normalize_id(p.get("key_cricinfo"))
        styles=sorted(by_player.get(key,set()))
        groups={x[2] for x in styles}
        # Multiple styles in one category are valid; conflicting pace/spin
        # observations must be explicitly treated as ambiguous, not guessed.
        group=next(iter(groups)) if len(groups)==1 else "unknown"
        if len(styles)==0:status="unmatched"
        elif len(groups)>1:status="conflicting_styles"
        elif group=="unknown":status="unclassified_style"
        else:status="linked"
        people.append({"cricsheet_id":p.get("identifier",""),
          "name":p.get("unique_name") or p.get("name",""),
          "espn_player_id":key,"style_groups":group,
          "bowling_styles":" | ".join(sorted({x[1] for x in styles})),
          "wikidata_ids":" | ".join(sorted({x[0] for x in styles})),
          "match_status":status,"license":"Cricsheet ODC-BY + Wikidata CC0"})
    grounds=[]
    for g in registers["venues"]:
        key=normalize_id(g.get("key_cricinfo"))
        entries=sorted(by_ground.get(key,set()))
        countries={(x[1],x[2],x[3]) for x in entries}
        unique=next(iter(countries)) if len(countries)==1 else None
        status="unmatched" if not entries else "conflicting_countries" if len(countries)>1 else "linked"
        grounds.append({"cricsheet_venue_id":g.get("identifier",""),
            "venue_name":g.get("unique_name") or g.get("name",""),
            "espn_ground_id":key,
            "physical_country":unique[1] if unique else "",
            "iso3166_alpha2":unique[2] if unique else "",
            "wikidata_country_id":unique[0] if unique else "",
            "wikidata_ground_ids":" | ".join(sorted({x[0] for x in entries})),
            "match_status":status,
            "cricket_host_team":"", # Cannot infer from physical country alone
            "license":"Cricsheet ODC-BY + Wikidata CC0"})
    # Cricsheet venue aliases are not unique: preserve every alias with
    # the original stable venue ID. Do not automatically name-match duplicates.
    venue_alias=[{"cricsheet_venue_id":r.get("identifier",""),"alias":r.get("name","")}
                 for r in registers["venue_names"]]
    player_alias=[{"cricsheet_id":r.get("identifier",""),"alias":r.get("name","")}
                  for r in registers["names"]]
    write_csv(output/"player_bowling_style.csv",[
        "cricsheet_id","name","espn_player_id","style_groups","bowling_styles",
        "wikidata_ids","match_status","license"],people)
    write_csv(output/"venue_physical_country.csv",[
        "cricsheet_venue_id","venue_name","espn_ground_id","physical_country",
        "iso3166_alpha2","wikidata_country_id","wikidata_ground_ids",
        "match_status","cricket_host_team","license"],grounds)
    write_csv(output/"venue_aliases.csv",["cricsheet_venue_id","alias"],venue_alias)
    write_csv(output/"player_aliases.csv",["cricsheet_id","alias"],player_alias)
    def statuses(rows):
        counts=defaultdict(int)
        for x in rows:counts[x["match_status"]]+=1
        return dict(sorted(counts.items()))
    report={"generated_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rights":{"cricsheet_register":"ODC-BY-1.0, attribution required",
                  "wikidata_structured_claims":"CC0"},
        "source":source,"wikidata_queries":{"styles":PLAYER_QUERY,"venues":VENUE_QUERY},
        "wikidata_rows":{"style_claims":len(player_wd),"ground_claims":len(ground_wd)},
        "status":{"player_bowling_style":statuses(people),
                   "venue_physical_country":statuses(grounds)},
        "player_count":len(people),"venue_count":len(grounds),
        "notes":["ESPN numeric identifiers are used only as join keys; no ESPN pages were downloaded.",
           "Wikidata bowling-style names may represent multiple styles; pace/spin conflicts are unknown.",
           "Missing and ambiguous venue host countries are not imputed.",
           "Physical country alone does NOT establish Test/ODI/T20I host cricket team, especially England/UK, UAE or neutral sites.",
           "No external historical bowling scorecards ingested; no batting app files touched.",
           "If WDQS fails or rate limits, enrichment must be described as partial, not complete."],
        "errors":wikidata_errors}
    (output/"provenance.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=OUT)
    a=p.parse_args()
    x=build(a.output)
    print(json.dumps({"players":x["player_count"],"venues":x["venue_count"],
                      "statuses":x["status"],"warnings":x["errors"]},indent=2))
