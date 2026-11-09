"""Cricsheet ODC-BY ALL-MATCH warehouse. No restricted external scorecards included.

Output: versioned SQLite shards (gender x decade), original licensed ZIP,
match/innings/event/wicket/roster tables, SHA256 audit and coverage manifest.

This is source coverage, NOT a complete census of international cricket.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import urllib.request
from zipfile import ZipFile

URL = "https://cricsheet.org/downloads/all_json.zip"
ROOT = Path(__file__).resolve().parents[1]

DDL = """
CREATE TABLE matches (
 id TEXT PRIMARY KEY, original_file TEXT NOT NULL, start_date TEXT NOT NULL,
 year INTEGER NOT NULL, gender TEXT NOT NULL, match_type TEXT NOT NULL,
 category TEXT NOT NULL, team_type TEXT NOT NULL, competition TEXT,
 team_a TEXT, team_b TEXT, venue TEXT, city TEXT, result TEXT,
 official_match_type_number INTEGER, raw_info_json TEXT NOT NULL
);
CREATE TABLE innings (
 id TEXT PRIMARY KEY, match_id TEXT NOT NULL, sequence_number INTEGER NOT NULL,
 batting_team TEXT, super_over INTEGER, declared INTEGER, forfeited INTEGER,
 metadata_json TEXT, FOREIGN KEY(match_id) REFERENCES matches(id)
);
CREATE TABLE deliveries (
 innings_id TEXT NOT NULL, over_number INTEGER NOT NULL, ball_ordinal INTEGER NOT NULL,
 batter_id TEXT, bowler_id TEXT, non_striker_id TEXT,
 batter_name TEXT, bowler_name TEXT, non_striker_name TEXT,
 batter_runs INTEGER NOT NULL, total_runs INTEGER NOT NULL,
 legal_ball INTEGER NOT NULL, faced_ball INTEGER NOT NULL,
 raw_event_json TEXT NOT NULL,
 PRIMARY KEY(innings_id,over_number,ball_ordinal),
 FOREIGN KEY(innings_id) REFERENCES innings(id)
);
CREATE TABLE wickets (
 innings_id TEXT NOT NULL, over_number INTEGER NOT NULL, ball_ordinal INTEGER NOT NULL,
 wicket_ordinal INTEGER NOT NULL, dismissed_id TEXT, dismissed_name TEXT,
 dismissal_kind TEXT, fielders_json TEXT,
 PRIMARY KEY(innings_id,over_number,ball_ordinal,wicket_ordinal)
);
CREATE TABLE match_people (
 match_id TEXT NOT NULL, player_name TEXT NOT NULL, player_id TEXT,
 team TEXT, PRIMARY KEY(match_id, player_name)
);
CREATE INDEX ix_match_scope ON matches(gender,category,year);
CREATE INDEX ix_del_batter ON deliveries(batter_id);
CREATE INDEX ix_del_bowler ON deliveries(bowler_id);
CREATE INDEX ix_del_wickets ON wickets(dismissed_id);
"""

def get_archive(path, download):
    path = Path(path)
    if download:
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL,
            headers={"User-Agent": "CricketMasterWarehouse/1.0 (Cricsheet ODC-BY attribution)"})
        temp = path.with_suffix(".download")
        with urllib.request.urlopen(req, timeout=300) as response, temp.open("wb") as stream:
            while block := response.read(1024*1024):
                stream.write(block)
        if not ZipFile(temp).testzip() is None:
            raise RuntimeError("Cricsheet archive failed ZIP checksum")
        temp.replace(path)
    if not path.exists():
        raise FileNotFoundError(path)
    return path

def classification(info):
    match_type = str(info.get("match_type", "")).upper()
    team_type = str(info.get("team_type", "unknown")).lower()
    is_int = team_type == "international"
    if match_type == "TEST" and is_int: return "test"
    if match_type == "ODI" and is_int: return "odi"
    if match_type in ("T20", "IT20") and is_int:
        return "t20i" if match_type == "T20" else "nonofficial_t20i"
    if match_type in ("MDM", "ODM", "T20", "TEST", "ODI"):
        return {"MDM":"first_class","ODM":"list_a","T20":"t20",
                "TEST":"test","ODI":"odi"}[match_type]
    return "other"

def connect(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA journal_mode=OFF")
    con.executescript(DDL)
    return con

def archive_sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024*1024):
            digest.update(block)
    return digest.hexdigest()

def compress(source, destination):
    sha=hashlib.sha256()
    with source.open("rb") as stream, destination.open("wb") as dest:
        with gzip.GzipFile(fileobj=dest,mode="wb",filename="",mtime=0,compresslevel=6) as target:
            while block:=stream.read(1024*1024):
                target.write(block)
    with destination.open("rb") as stream:
        while block:=stream.read(1024*1024):
            sha.update(block)
    return {"sha256":sha.hexdigest(),"compressedBytes":destination.stat().st_size}

def build(archive,output,limit=0):
    archive=Path(archive);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    conns={};dbpaths={};counters=Counter();coverage=Counter();years=Counter()
    skipped=Counter();seen=set()
    try:
        with ZipFile(archive) as bundle:
            files=sorted(x for x in bundle.namelist() if x.endswith(".json") and not x.startswith("__MACOSX/"))
            license_seen=any(Path(x).name.upper()=="LICENSE.TXT" for x in bundle.namelist())
            for filename in files:
                if limit and counters["matches"]>=limit:break
                basename=Path(filename).stem
                if basename in seen:raise ValueError(f"Duplicate Cricsheet match file: {basename}")
                seen.add(basename)
                with bundle.open(filename) as file:
                    doc=json.load(file)
                info=doc.get("info") or {}
                dates=info.get("dates") or []
                teams=info.get("teams") or []
                if not dates or len(teams)!=2:
                    skipped["invalid_date_or_teams"]+=1;continue
                dt=str(dates[0])
                if len(dt)!=10 or not dt[:4].isdigit():
                    skipped["unparseable_date"]+=1;continue
                yr=int(dt[:4])
                gender=str(info.get("gender") or "unknown").lower()
                decade=yr//10*10
                key=f"{gender}_{decade}s"
                if key not in conns:
                    path=output/f"master_{key}.sqlite"
                    if path.exists():path.unlink()
                    conns[key]=connect(path);dbpaths[key]=path
                con=conns[key]
                fmt=classification(info)
                category=info.get("event") or {}
                competition=category.get("name") if isinstance(category,dict) else str(category)
                match_id="cricsheet:"+basename
                registry=(info.get("registry") or {}).get("people") or {}
                outcome=info.get("outcome") or {}
                con.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                    match_id,filename,dt,yr,gender,str(info.get("match_type") or ""),fmt,
                    str(info.get("team_type") or "unknown"),competition,teams[0],teams[1],
                    info.get("venue"),info.get("city"),outcome.get("winner") or outcome.get("result"),
                    info.get("match_type_number"),json.dumps(info,ensure_ascii=False,separators=(",",":"))))
                for team,names in (info.get("players") or {}).items():
                    for name in names:
                        con.execute("INSERT OR IGNORE INTO match_people VALUES (?,?,?,?)",
                            (match_id,name,registry.get(name),team))
                for name,pid in registry.items():
                    con.execute("INSERT OR IGNORE INTO match_people VALUES (?,?,?,?)",
                        (match_id,name,pid,None))
                nballs=0;nwickets=0
                for seq,inn in enumerate(doc.get("innings") or [],1):
                    iid=f"{match_id}:{seq}"
                    extra_info={k:v for k,v in inn.items() if k!="overs"}
                    con.execute("INSERT INTO innings VALUES (?,?,?,?,?,?,?,?)",(
                        iid,match_id,seq,inn.get("team"),
                        int(bool(inn.get("super_over"))),
                        int(bool(inn.get("declared"))),int(bool(inn.get("forfeited"))),
                        json.dumps(extra_info,ensure_ascii=False,separators=(",",":"))))
                    for over in inn.get("overs") or []:
                        overno=int(over.get("over",0))
                        for ordinal,ball in enumerate(over.get("deliveries") or [],1):
                            runs=ball.get("runs") or {}
                            extras=ball.get("extras") or {}
                            batter=ball.get("batter");bowler=ball.get("bowler");non=ball.get("non_striker")
                            legal=int("wides" not in extras and "noballs" not in extras)
                            faced=int("wides" not in extras)
                            con.execute("INSERT INTO deliveries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                                iid,overno,ordinal,registry.get(batter),registry.get(bowler),registry.get(non),
                                batter,bowler,non,
                                int(runs.get("batter",runs.get("batsman",0))),int(runs.get("total",0)),
                                legal,faced,json.dumps(ball,ensure_ascii=False,separators=(",",":"))))
                            nballs+=1
                            for wi,w in enumerate(ball.get("wickets") or [],1):
                                dismissed=w.get("player_out")
                                con.execute("INSERT INTO wickets VALUES (?,?,?,?,?,?,?,?)",(
                                    iid,overno,ordinal,wi,registry.get(dismissed),dismissed,
                                    w.get("kind"),json.dumps(w.get("fielders") or [],ensure_ascii=False)))
                                nwickets+=1
                counters["matches"]+=1;counters["deliveries"]+=nballs;counters["wickets"]+=nwickets
                counters["nonempty_matches"]+=int(nballs>0)
                coverage[(gender,fmt)]+=1;years[(gender,fmt,yr)]+=1
                if counters["matches"]%200==0:
                    for database in conns.values():database.commit()
        for con in conns.values():
            con.commit()
            if con.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise RuntimeError("SQLite integrity check failed")
    finally:
        for con in conns.values():con.close()
    shards={}
    for key,path in sorted(dbpaths.items()):
        zipped=path.with_suffix(".sqlite.gz")
        details=compress(path,zipped)
        shards[key]={"file":zipped.name,**details}
        path.unlink()
    result={
        "createdUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source":"Cricsheet.org","sourceURL":URL,"license":"ODC-BY 1.0",
        "attribution":"Data provided by Cricsheet.org under ODC-BY 1.0; transformed by Cricket Master Warehouse.",
        "sourceArchiveSHA256":archive_sha(archive),"sourceLicenseNoticePresent":license_seen,
        "allSourceMatches":len(seen),"counts":dict(counters),
        "byGenderAndCategory":{f"{g}:{f}":n for (g,f),n in sorted(coverage.items())},
        "byGenderCategoryYear":{f"{g}:{f}:{y}":n for (g,f,y),n in sorted(years.items())},
        "skipped":dict(skipped),"shards":shards,
        "scope":"All publicly supplied Cricsheet match JSON; source coverage != comprehensive official census.",
        "excludedSources":"No unlicensed historic ESPN-derived batting innings or scorecards included.",
        "storage":"Versioned open-data GitHub Release assets; raw ZIP + compressed SQLite shards.",
        "caveats":["No official match-by-match completeness certification",
                   "Official T20I requires source team_type international; other T20 kept separate",
                   "Fielders and wickets retained as original events; further normalization possible",
                   "No Hawkeye/ball tracking/weather/pitch measurements supplied by Cricsheet",
                   "No unique official match-ID crosswalk beyond available match_type_number"]
        }
    (output/"master_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,default=ROOT/"data"/"raw"/"all_json.zip")
    parser.add_argument("--output",type=Path,default=ROOT/"warehouse"/"master")
    parser.add_argument("--download",action="store_true")
    parser.add_argument("--limit",type=int,default=0)
    args=parser.parse_args()
    input_file=get_archive(args.archive,args.download)
    print(json.dumps(build(input_file,args.output,args.limit),indent=2))

if __name__=="__main__":main()
