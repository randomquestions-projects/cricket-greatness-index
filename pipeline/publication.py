"""Publish only licensed modern match-explorer data.

All-era batting leaderboards are written by pipeline.format_greatness.
Never publish historical ESPN-derived scorecard rows to the website.
"""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
from .ingest import ROOT
from .ledger import lookup_name,reading

def publish(source=ROOT/"data/generated/innings.csv.gz", dest=ROOT/"site/data/innings.json.gz"):
    source=Path(source);dest=Path(dest)
    if not source.exists():raise FileNotFoundError(source)
    results=[]
    for r in reading(source):
        # Generated Cricsheet innings only. This file must never read
        # historical-innings.csv.gz or any historical research source.
        if r.get("format") not in ("test","odi","t20i"):continue
        results.append({"m":r.get("match_id"),"i":r.get("innings_id"),
            "d":r.get("date"),"f":r.get("format"),"p":r.get("player_id"),
            "n":lookup_name(r),"t":r.get("team"),"o":r.get("opposition"),
            "r":int(float(r.get("runs") or 0)),
            "b":int(float(r.get("balls") or 0)),
            "x":int(float(r.get("dismissed") or 0)),
            "source":"Cricsheet ODC-BY 1.0"})
    dest.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(dest,"wt",encoding="utf-8") as f:
        json.dump(results,f,separators=(",",":"),ensure_ascii=False)
    return len(results)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=ROOT/"data/generated/innings.csv.gz")
    p.add_argument("--output",type=Path,default=ROOT/"site/data/innings.json.gz")
    args=p.parse_args()
    print("Published",publish(args.source,args.output),"licensed Cricsheet modern batting appearances only")
if __name__=="__main__":main()
