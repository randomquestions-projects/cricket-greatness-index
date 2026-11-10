"""Measure reference usability among actual men’s international bowling observations.

Outputs aggregate coverage only, no raw player scorecards. Cricsheet
source identities + released ODC-BY/CC0 reference tables. Never reads or
changes the batting website or historical restricted sources.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from pathlib import Path

FORMATS=("test","odi","t20i")

def load_csv(path,key):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return {r[key]:r for r in csv.DictReader(f) if r.get(key)}

def run(shards,style_csv,venue_csv,venue_alias_csv,output):
    styles=load_csv(style_csv,"cricsheet_id")
    venue_country=load_csv(venue_csv,"cricsheet_venue_id")
    alias_map=defaultdict(set)
    # Venue matching only when a venue's registered unique name or alias
    # uniquely identifies the stable Cricsheet venue ID.
    for id_,r in venue_country.items():
        if r.get("venue_name"):
            alias_map[r["venue_name"].strip().casefold()].add(id_)
    with Path(venue_alias_csv).open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r.get("alias"):alias_map[r["alias"].strip().casefold()].add(r["cricsheet_venue_id"])
    agg=defaultdict(lambda:defaultdict(int))
    ids=defaultdict(set)
    with tempfile.TemporaryDirectory(prefix="bowling-reference-measure-") as d:
        for i,shard in enumerate(shards):
            shard=Path(shard)
            dbpath=Path(d)/f"shard_{i}.sqlite"
            with gzip.open(shard,"rb") as src,dbpath.open("wb") as dest:
                shutil.copyfileobj(src,dest)
            con=sqlite3.connect(f"file:{dbpath}?mode=ro",uri=True)
            try:
                for fmt,player,amount in con.execute("""
                    SELECT m.category,b.player_id,count(*)
                    FROM matches m JOIN innings i ON i.match_id=m.id
                    JOIN bowling b ON b.innings_id=i.id
                    WHERE m.gender='male' AND m.category IN ('test','odi','t20i')
                      AND i.super_over=0
                    GROUP BY m.category,b.player_id
                """):
                    if not player:continue
                    ids[fmt].add(player)
                    k=agg[fmt];k["bowlingInnings"]+=amount
                    style=styles.get(player,{})
                    if style.get("match_status")=="linked" and style.get("style_groups") in ("pace","spin"):
                        k["classifiedBowlingInnings"]+=amount
                        k[style["style_groups"]+"BowlingInnings"]+=amount
                    else:
                        k["unclassifiedBowlingInnings"]+=amount
                for fmt,venue,count in con.execute("""
                    SELECT category,venue,count(*)
                    FROM matches WHERE gender='male'
                     AND category IN ('test','odi','t20i')
                    GROUP BY category,venue
                """):
                    if fmt not in FORMATS:continue
                    k=agg[fmt]
                    k["matches"]+=count
                    alias=(venue or "").strip().casefold()
                    hits=alias_map[alias] if alias else set()
                    if not hits:k["venueNoIdentifierMatch"]+=count
                    elif len(hits)>1:k["venueAmbiguousIdentifier"]+=count
                    else:
                        stable=next(iter(hits))
                        k["venueIdentifiedByUniqueName"]+=count
                        country=venue_country[stable]
                        if country.get("match_status")=="linked" and country.get("physical_country"):
                            k["venuePhysicalCountryVerifiedMatches"]+=count
                        else:
                            k["venueKnownIdentifierCountryMissingMatches"]+=count
            finally:con.close()
    res={}
    for f in FORMATS:
        k=dict(agg[f]);k["uniqueObservedBowlers"]=len(ids[f])
        k["uniqueBowlersWithLicensedPaceSpin"]=sum(1 for player in ids[f]
             if styles.get(player,{}).get("match_status")=="linked"
             and styles[player].get("style_groups") in ("pace","spin"))
        k["classifiedBowlingInningsPercent"]=round(100*k.get("classifiedBowlingInnings",0)/max(1,k.get("bowlingInnings",0)),2)
        k["verifiedPhysicalCountryMatchesPercent"]=round(100*k.get("venuePhysicalCountryVerifiedMatches",0)/max(1,k.get("matches",0)),2)
        res[f]=k
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({
        "scope":"Men's Cricsheet-observed Test, ODI, T20I bowling only",
        "rights":"Cricsheet ODC-BY 1.0; Wikidata CC0 style/country claims",
        "coverage":res,
        "venueIdentityRule":"Unique exact Cricsheet venue register name/alias only; ambiguous names not joined.",
        "interpretation":"Pace/spin and physical-country matches are SOURCE coverage, not completeness. Physical country does not imply cricket host country.",
        "historicalScorecardsImported":False,
        "battingAppChanged":False
    },indent=2)+"\n")
    return res

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--shards",nargs="+",required=True)
    p.add_argument("--references",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(run(a.shards,a.references/"player_bowling_style.csv",
                           a.references/"venue_physical_country.csv",
                           a.references/"venue_aliases.csv",a.output),indent=2))
