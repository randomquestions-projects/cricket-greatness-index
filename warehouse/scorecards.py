"""Scorecard-first research tables built only from licensed Cricsheet match JSON.

No raw or derived ESPNcricinfo historical batting scorecards are published here.
Original match events retained separately in the master event warehouse.
Derived scorecards MUST be described as delivery-derived, not official-complete.
"""
from __future__ import annotations
import argparse
from collections import Counter, OrderedDict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

from .master import ROOT, classification, compress, archive_sha

DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE matches (
 id TEXT PRIMARY KEY, source_file TEXT, start_date TEXT, gender TEXT, category TEXT,
 team_a TEXT, team_b TEXT, venue TEXT, match_result TEXT, match_type_number INTEGER,
 original_missing_json TEXT, source_tier TEXT NOT NULL
);
CREATE TABLE innings (
 id TEXT PRIMARY KEY, match_id TEXT, ordinal INTEGER, batting_team TEXT, super_over INTEGER,
 runs INTEGER, batter_runs INTEGER, extras INTEGER, wickets INTEGER, legal_balls INTEGER,
 event_count INTEGER, batters_count INTEGER, bowlers_count INTEGER,
 team_penalty_runs INTEGER, source_missing_fields INTEGER, scorecard_tier TEXT,
 FOREIGN KEY(match_id) REFERENCES matches(id)
);
CREATE TABLE batting (
 innings_id TEXT, player_id TEXT, player_name TEXT, observed_entry_order INTEGER,
 runs INTEGER, balls INTEGER, fours INTEGER, sixes INTEGER, dismissed INTEGER,
 dismissal_kind TEXT, dismissal_fielders_json TEXT,
 PRIMARY KEY(innings_id,player_name), FOREIGN KEY(innings_id) REFERENCES innings(id)
);
CREATE TABLE bowling (
 innings_id TEXT, player_id TEXT, player_name TEXT, legal_balls INTEGER,
 conceded INTEGER, wickets INTEGER, wides INTEGER, noballs INTEGER,
 PRIMARY KEY(innings_id,player_name), FOREIGN KEY(innings_id) REFERENCES innings(id)
);
CREATE TABLE fielding (
 innings_id TEXT, player_id TEXT, player_name TEXT, catches INTEGER,
 stumpings INTEGER, run_outs_involved INTEGER, other_dismissal_involvements INTEGER,
 PRIMARY KEY(innings_id,player_name), FOREIGN KEY(innings_id) REFERENCES innings(id)
);
CREATE TABLE quality_flags (
 match_id TEXT, innings_id TEXT, flag TEXT, details TEXT
);
CREATE INDEX idx_match_scope ON matches(gender,category,start_date);
CREATE INDEX idx_batter_name ON batting(player_id);
CREATE INDEX idx_bowler_name ON bowling(player_id);
"""

BOWLER_UNCREDITED = {"run out", "retired out", "obstructing the field", "retired hurt",
    "absent hurt", "retired not out"}
NOT_A_WICKET = {"retired hurt", "absent hurt", "retired not out"}

def fresh_batter():
    return {"runs":0,"balls":0,"fours":0,"sixes":0,
            "dismissed":0,"dismissal_kind":None,"fielders":[]}

def fresh_bowler():
    return {"legal":0,"conceded":0,"wickets":0,"wides":0,"noballs":0}

def fresh_fielder():
    return {"catches":0,"stumpings":0,"run_outs_involved":0,"other":0}

def scorecard(doc, source_file):
    """Produce match/innings/stat rows and explicit completeness flags.

    Batting order is first observed participation, not an independently verified scorecard.
    Not-outs are only as reliable as the coverage of source events.
    """
    info=doc.get("info") or {}
    dates=info.get("dates") or []
    teams=info.get("teams") or []
    if not dates or len(teams)!=2:
        return None
    day=str(dates[0])
    if len(day)!=10 or not day[:4].isdigit():return None
    match_id="cricsheet:"+Path(source_file).stem
    reg=(info.get("registry") or {}).get("people") or {}
    outcome=info.get("outcome") or {}
    missing=info.get("missing") or []
    match=(match_id,source_file,day,str(info.get("gender") or "unknown").lower(),
       classification(info),teams[0],teams[1],info.get("venue"),
       outcome.get("winner") or outcome.get("result"),
       info.get("match_type_number"),json.dumps(missing,ensure_ascii=False),
       "delivery-derived;source-missing" if missing else "delivery-derived")
    cards=[];batting_rows=[];bowling_rows=[];fielding_rows=[];flags=[]
    if missing:flags.append((match_id,None,"SOURCE_MISSING",json.dumps(missing)))
    innings=doc.get("innings") or []
    if not innings:flags.append((match_id,None,"NO_INNINGS",""))
    for seq,inn in enumerate(innings,1):
        iid=f"{match_id}:{seq}"
        batters=OrderedDict();bowlers=OrderedDict();fielders=OrderedDict()
        team_total=0;legal_count=0;events=0;dismissals=0
        for over in inn.get("overs") or []:
            for ball in over.get("deliveries") or []:
                batter=ball.get("batter"); non=ball.get("non_striker"); bowler=ball.get("bowler")
                if batter is None or bowler is None:
                    flags.append((match_id,iid,"MISSING_BATTER_OR_BOWLER",""))
                    continue
                for person in (batter,non):
                    if person and person not in batters:batters[person]=fresh_batter()
                if bowler not in bowlers:bowlers[bowler]=fresh_bowler()
                runs=ball.get("runs") or {};extras=ball.get("extras") or {}
                run_bat=int(runs.get("batter",runs.get("batsman",0)) or 0)
                run_total=int(runs.get("total",0) or 0)
                legal=int("wides" not in extras and "noballs" not in extras)
                faced=int("wides" not in extras)
                events+=1;legal_count+=legal;team_total+=run_total
                b=batters[batter];b["runs"]+=run_bat;b["balls"]+=faced
                if not (runs.get("non_boundary") or ball.get("non_boundary")):
                    b["fours"]+=int(run_bat==4);b["sixes"]+=int(run_bat==6)
                p=bowlers[bowler];p["legal"]+=legal
                p["wides"]+=int(extras.get("wides",0) or 0)
                p["noballs"]+=int(extras.get("noballs",0) or 0)
                p["conceded"]+=run_total-sum(int(extras.get(k,0) or 0)
                          for k in ("byes","legbyes","penalty"))
                for wicket in ball.get("wickets") or []:
                    victim=wicket.get("player_out");kind=str(wicket.get("kind") or "unknown")
                    if kind not in NOT_A_WICKET:dismissals+=1
                    if victim:
                        if victim not in batters:batters[victim]=fresh_batter()
                        if kind not in NOT_A_WICKET:
                            batters[victim]["dismissed"]=1
                        batters[victim]["dismissal_kind"]=kind
                        batters[victim]["fielders"]=wicket.get("fielders") or []
                    if kind not in BOWLER_UNCREDITED:p["wickets"]+=1
                    for involved in wicket.get("fielders") or []:
                        f=involved.get("name") if isinstance(involved,dict) else involved
                        if not f:continue
                        if f not in fielders:fielders[f]=fresh_fielder()
                        stat=fielders[f]
                        if kind=="caught" or kind=="caught and bowled":stat["catches"]+=1
                        elif kind=="stumped":stat["stumpings"]+=1
                        elif kind=="run out":stat["run_outs_involved"]+=1
                        else:stat["other"]+=1
        penalty=inn.get("penalty_runs") or {}
        total_penalty=int(penalty.get("pre",0) or 0)+int(penalty.get("post",0) or 0)
        team_total+=total_penalty
        batter_runs=sum(s["runs"] for s in batters.values())
        extras=team_total-batter_runs
        complete=bool(events) and not missing
        tier="delivery-derived" if complete else "delivery-partial"
        if not events:flags.append((match_id,iid,"NO_DELIVERIES",""))
        if not batters:flags.append((match_id,iid,"NO_BATTING_PARTICIPANTS",""))
        if not bowlers:flags.append((match_id,iid,"NO_BOWLING_PARTICIPANTS",""))
        if extras<0:flags.append((match_id,iid,"NEGATIVE_EXTRAS",str(extras)))
        if len(batters)>11 and not inn.get("super_over"):
            flags.append((match_id,iid,"OVER_11_BATTERS",str(len(batters))))
        if dismissals>10 and not inn.get("super_over"):
            flags.append((match_id,iid,"OVER_10_WICKETS",str(dismissals)))
        cards.append((iid,match_id,seq,inn.get("team"),int(bool(inn.get("super_over"))),
            team_total,batter_runs,extras,dismissals,legal_count,events,len(batters),
            len(bowlers),total_penalty,int(bool(missing)),tier))
        for ordinal,(name,b) in enumerate(batters.items(),1):
            batting_rows.append((iid,reg.get(name),name,ordinal,b["runs"],b["balls"],
                b["fours"],b["sixes"],b["dismissed"],b["dismissal_kind"],
                json.dumps(b["fielders"],ensure_ascii=False)))
        for name,b in bowlers.items():
            bowling_rows.append((iid,reg.get(name),name,b["legal"],b["conceded"],
                b["wickets"],b["wides"],b["noballs"]))
        for name,b in fielders.items():
            fielding_rows.append((iid,reg.get(name),name,b["catches"],b["stumpings"],
                b["run_outs_involved"],b["other"]))
    return match,cards,batting_rows,bowling_rows,fielding_rows,flags

def build(archive,output,limit=0):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    databases={};paths={};counts=Counter();category_counts=Counter()
    try:
        with ZipFile(archive) as archive_zip:
            for filename in sorted(n for n in archive_zip.namelist() if n.endswith(".json")):
                if limit and counts["matches"]>=limit:break
                with archive_zip.open(filename) as file:doc=json.load(file)
                parsed=scorecard(doc,filename)
                if parsed is None:
                    counts["invalid_match_metadata"]+=1
                    continue
                match,innings,batters,bowlers,fielders,flags=parsed
                year=int(match[2][:4]);key=f"{match[3]}_{year//10*10}s"
                if key not in databases:
                    db=output/f"scorecards_{key}.sqlite"
                    if db.exists():db.unlink()
                    conn=sqlite3.connect(db)
                    conn.executescript(DDL);databases[key]=conn;paths[key]=db
                conn=databases[key]
                conn.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",match)
                conn.executemany("INSERT INTO innings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",innings)
                conn.executemany("INSERT INTO batting VALUES (?,?,?,?,?,?,?,?,?,?,?)",batters)
                conn.executemany("INSERT INTO bowling VALUES (?,?,?,?,?,?,?,?)",bowlers)
                conn.executemany("INSERT INTO fielding VALUES (?,?,?,?,?,?,?)",fielders)
                conn.executemany("INSERT INTO quality_flags VALUES (?,?,?,?)",flags)
                counts["matches"]+=1;counts["innings"]+=len(innings)
                counts["batting_rows"]+=len(batters);counts["bowling_rows"]+=len(bowlers)
                counts["fielding_rows"]+=len(fielders);counts["flagged_matches"]+=int(bool(flags))
                counts["delivery_derived_matches"]+=int(bool(innings) and not flags)
                category_counts[f"{match[3]}:{match[4]}"]+=1
                if counts["matches"]%500==0:
                    for conn in databases.values():conn.commit()
        for conn in databases.values():
            conn.commit()
            if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("Failed SQLite integrity check")
    finally:
        for conn in databases.values():conn.close()
    shards={}
    for key,db in sorted(paths.items()):
        target=db.with_suffix(".sqlite.gz")
        shards[key]={"file":target.name,**compress(db,target)}
        db.unlink()
    result={"generatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source":"Cricsheet ODC-BY 1.0","sourceArchiveSHA256":archive_sha(Path(archive)),
        "sourceCoverageOnly":True,"independentlyCompleteScorecards":False,
        "sourceRights":"ODC-BY-1.0 with attribution",
        "counts":dict(counts),"byGenderAndFormat":dict(sorted(category_counts.items())),
        "shards":shards,
        "notes":["Scorecards reconstructed exclusively from source deliveries.",
          "Observed batting entry sequence is not an independently verified batting order.",
          "Historic ESPN-derived innings and scorecards are excluded.",
          "An unflagged delivery-derived card is not certified against a second scorecard source."]}
    (output/"scorecards_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,default=ROOT/"data"/"raw"/"all_json.zip")
    p.add_argument("--output",type=Path,default=ROOT/"warehouse"/"scorecards")
    p.add_argument("--limit",type=int,default=0)
    a=p.parse_args()
    print(json.dumps(build(a.archive,a.output,a.limit),indent=2))

if __name__=="__main__":main()
