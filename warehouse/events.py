"""Build a queryable all-deliveries cricket warehouse from original Cricsheet JSON.

Preserves original event JSON, original match metadata and Cricsheet registry IDs.
Works independently from ranking model and historical scorecard overlay.
This is NOT a full official census or a replacement for historical scorecards.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from pipeline.ingest import ROOT, FILES, download_archives

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE matches (
 match_id TEXT PRIMARY KEY, cricsheet_file TEXT NOT NULL, format TEXT NOT NULL,
 start_date TEXT NOT NULL, year INTEGER NOT NULL, gender TEXT,
 teams_json TEXT NOT NULL, venue TEXT, city TEXT, winner TEXT,
 match_type_number INTEGER, registry_json TEXT,
 source_json TEXT NOT NULL
);
CREATE TABLE innings (
 innings_id TEXT PRIMARY KEY, match_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL, batting_team TEXT NOT NULL,
 super_over INTEGER NOT NULL, target_json TEXT,
 extras_json TEXT, FOREIGN KEY(match_id) REFERENCES matches(match_id)
);
CREATE TABLE deliveries (
 innings_id TEXT NOT NULL, over_number INTEGER NOT NULL,
 ball_ordinal INTEGER NOT NULL, batter TEXT, bowler TEXT, non_striker TEXT,
 batter_id TEXT, bowler_id TEXT, non_striker_id TEXT,
 runs_batter INTEGER NOT NULL, runs_total INTEGER NOT NULL,
 extras_json TEXT, wickets_json TEXT, raw_event_json TEXT NOT NULL,
 PRIMARY KEY(innings_id,over_number,ball_ordinal),
 FOREIGN KEY(innings_id) REFERENCES innings(innings_id)
);
CREATE INDEX delivery_batter ON deliveries(batter_id,innings_id);
CREATE INDEX delivery_bowler ON deliveries(bowler_id,innings_id);
CREATE INDEX match_date ON matches(start_date,format);
CREATE TABLE source_snapshots (
 name TEXT PRIMARY KEY, url TEXT NOT NULL, sha256 TEXT NOT NULL,
 imported_matches INTEGER NOT NULL, imported_deliveries INTEGER NOT NULL
);
"""

def build(archives, output, limit=0):
    archives=Path(archives);output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    db=output/"cricket-events.sqlite"
    if db.exists():db.unlink()
    con=sqlite3.connect(db)
    con.executescript(SCHEMA)
    counts=Counter();last_date=None;first_date=None;sources={}
    try:
        for fmt,file in FILES.items():
            archive=archives/file
            if not archive.exists():raise FileNotFoundError(str(archive))
            sha=hashlib.sha256(archive.read_bytes()).hexdigest()
            nmatch=0; nball=0
            with ZipFile(archive) as bundle:
                for filename in sorted(bundle.namelist()):
                    if not filename.endswith(".json") or filename.startswith("__MACOSX/"):continue
                    if limit and nmatch>=limit:break
                    with bundle.open(filename) as f:doc=json.load(f)
                    info=doc.get("info") or {}
                    if info.get("gender")!="male" or info.get("team_type","international")!="international":continue
                    if fmt=="test" and info.get("match_type")!="Test":continue
                    if fmt=="odi" and info.get("match_type")!="ODI":continue
                    if fmt=="t20i" and info.get("match_type") not in ("T20","IT20"):continue
                    teams=info.get("teams") or []
                    dates=info.get("dates") or []
                    if len(teams)!=2 or not dates or not doc.get("innings"):continue
                    date=str(dates[0])
                    if len(date)<10:continue
                    matchid=fmt+":"+Path(filename).stem
                    registry=info.get("registry",{}).get("people",{})
                    result=info.get("outcome") or {}
                    n_before=nball
                    con.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                        matchid,filename,fmt,date,int(date[:4]),info.get("gender"),
                        json.dumps(teams,ensure_ascii=False),info.get("venue"),info.get("city"),
                        result.get("winner"),info.get("match_type_number"),
                        json.dumps(registry,ensure_ascii=False),json.dumps(info,ensure_ascii=False)))
                    for ordinal,inn in enumerate(doc["innings"],1):
                        innid=f"{matchid}:{ordinal}"
                        con.execute("INSERT INTO innings VALUES (?,?,?,?,?,?,?)",(
                            innid,matchid,ordinal,str(inn.get("team","")),
                            int(bool(inn.get("super_over"))),
                            json.dumps(inn.get("target")),json.dumps(inn.get("penalty_runs"))))
                        for over in inn.get("overs",[]):
                            overno=int(over.get("over",0))
                            for ballno,ball in enumerate(over.get("deliveries",[]),1):
                                runs=ball.get("runs") or {}
                                con.execute("INSERT INTO deliveries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                                    innid,overno,ballno,ball.get("batter"),ball.get("bowler"),ball.get("non_striker"),
                                    registry.get(ball.get("batter")),registry.get(ball.get("bowler")),
                                    registry.get(ball.get("non_striker")),
                                    int(runs.get("batter",runs.get("batsman",0))),int(runs.get("total",0)),
                                    json.dumps(ball.get("extras")),json.dumps(ball.get("wickets")),
                                    json.dumps(ball,ensure_ascii=False)))
                                nball+=1
                    if nball==n_before:
                        con.execute("DELETE FROM innings WHERE match_id=?",(matchid,))
                        con.execute("DELETE FROM matches WHERE match_id=?",(matchid,))
                        continue
                    nmatch+=1;counts[fmt+"_matches"]+=1;counts[fmt+"_deliveries"]+=nball-n_before
                    first_date=min(date,first_date) if first_date else date
                    last_date=max(date,last_date) if last_date else date
            con.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)",(
                file,"https://cricsheet.org/downloads/"+file,sha,nmatch,nball))
            sources[file]={"sha256":sha,"matches":nmatch,"deliveries":nball}
            con.commit()
        if not sum(v for k,v in counts.items() if k.endswith("_matches")):
            raise ValueError("No international matches ingested")
        validity=con.execute("PRAGMA integrity_check").fetchone()[0]
        if validity!="ok":raise RuntimeError("SQLite validation failed: "+validity)
        orphan=con.execute("SELECT count(*) FROM deliveries d LEFT JOIN innings i USING(innings_id) WHERE i.innings_id IS NULL").fetchone()[0]
        if orphan:raise RuntimeError(f"{orphan} orphan deliveries")
    finally:
        con.close()
    compressed=output/"cricket-events.sqlite.gz"
    with db.open("rb") as source,compressed.open("wb") as target:
        with gzip.GzipFile(fileobj=target,mode="wb",filename="",mtime=0,compresslevel=6) as zipped:
            while chunk:=source.read(1024*1024):zipped.write(chunk)
    db.unlink()
    summary={"createdUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "source":"Cricsheet men's international JSON; ODC-BY 1.0",
      "formats":["test","odi","t20i"],
      "counts":dict(counts),"earliestMatch":first_date,"latestMatch":last_date,
      "sources":sources,"archiveSHA256":hashlib.sha256(compressed.read_bytes()).hexdigest(),
      "coverageWarning":"Only Cricsheet-published matches; incomplete official census. Historical scorecard snapshots NOT in this events database.",
      "dataRights":"Cricsheet ODC-BY attribution required.",
      "storageWarning":"GitHub Actions artifacts expire; configure separate durable object storage before calling warehouse persistent."}
    (output/"events_manifest.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archives",type=Path,default=ROOT/"data"/"raw")
    p.add_argument("--output",type=Path,default=ROOT/"warehouse"/"exports")
    p.add_argument("--download",action="store_true")
    p.add_argument("--limit",type=int,default=0)
    args=p.parse_args()
    if args.download:download_archives(args.archives)
    print(json.dumps(build(args.archives,args.output,args.limit),indent=2))

if __name__=="__main__":main()
