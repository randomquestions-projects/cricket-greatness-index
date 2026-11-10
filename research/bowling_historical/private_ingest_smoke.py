"""Temporary import check of the three public research source files.

This validates file readability and SQLite staging on a disposable CI runner.
No source rows, SQLite DB, or archives are committed/uploaded as artifacts.
For persistent PRIVATE use run the separate local-warehouse builder package.
"""
from __future__ import annotations
import csv,gzip,hashlib,json,sqlite3,urllib.request,os
from pathlib import Path
from datetime import datetime,timezone

BASE = {
"philipson_test":("https://raw.githubusercontent.com/petephilipson/MPCMP_Test_bowlers/main/bowldat2022_Toss.RData","bowldat2022_Toss.RData"),
"golicher_2017":("https://raw.githubusercontent.com/dgolicher/crickdata/master/data/bowling.rda","bowling.rda"),
"hf_test_bowling":("https://huggingface.co/datasets/bhuvaneshprasad/test-cricket-dataset-1877-2014/resolve/main/test_Bowling_Card.csv","test_Bowling_Card.csv"),
"hf_test_matches":("https://huggingface.co/datasets/bhuvaneshprasad/test-cricket-dataset-1877-2014/resolve/main/test_Matches_Data.csv","test_Matches_Data.csv"),
"hf_test_players":("https://huggingface.co/datasets/bhuvaneshprasad/test-cricket-dataset-1877-2014/resolve/main/players_info.csv","players_info.csv"),
}
def obtain(url,path):
    request=urllib.request.Request(url,headers={"User-Agent":"CricketBowlingPrivateResearch/1.0 (noncommercial private investigation)"})
    with urllib.request.urlopen(request,timeout=150) as resp,path.open("wb") as dest:
        total=0
        while True:
            piece=resp.read(1<<20)
            if not piece:break
            total+=len(piece)
            if total>90_000_000:raise ValueError("Oversize source, stopped: "+url)
            dest.write(piece)
    if total<1000:raise ValueError("Unusable download: "+url)
    return total
def profile(path, source):
    if path.suffix.lower() in (".rdata",".rda"):
        import pyreadr
        objects=pyreadr.read_r(str(path))
        if not objects:raise ValueError("No table-like R objects from "+source)
        for name,frame in objects.items():
            if not hasattr(frame,"columns"):
                continue
            yield str(name),frame
    else:
        import pandas as pd
        frame=pd.read_csv(path,dtype=str,low_memory=False)
        yield "csv",frame

def main():
    import pandas as pd
    local=Path(os.environ.get("RUNNER_TEMP", "/tmp"))/"bowling-source-private-research"
    local.mkdir(mode=0o700,parents=True,exist_ok=True)
    dbpath=local/"temporary_private_historical_bowling.sqlite"
    conn=sqlite3.connect(dbpath)
    report={"generatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sources":{}, "privateTemporarySQLiteCreated":False,
            "historicalRawRowsPublished":False, "dataReuseRightsUnverified":True,
            "publicBattingAppModified":False, "notes":[
              "Only temporary CI validation. No historical source rows committed or uploaded.",
              "Raw source output is deleted at end of runner job.",
              "Local persistent private warehouse builder is distributed separately."]}
    try:
        for id,(url,fn) in BASE.items():
            path=local/fn
            size=obtain(url,path)
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            descriptions=[]
            for obj,frame in profile(path,id):
                # A REAL SQLite staging table, preserved only on the temporary runner.
                temp_table="source_"+id+"_"+str(len(descriptions))
                frame.to_sql(temp_table,conn,index=False,if_exists="replace",chunksize=1000,method="multi")
                actual=conn.execute(f'SELECT COUNT(*) FROM "{temp_table}"').fetchone()[0]
                if actual != len(frame):raise ValueError(f"Row-count mismatch for {id}/{obj}")
                descriptions.append({"object":obj,"rows":int(len(frame)),"columns":list(map(str,frame.columns)),
                     "yearColumnCandidate":next((str(c) for c in frame.columns if str(c).lower() in ("year","match start date","date")),None)})
            if not descriptions:raise ValueError("No tabular records imported from "+id)
            report["sources"][id]={"url":url,"sizeBytes":size,"sha256":sha,"objects":descriptions}
            print("Validated",id,[(o["object"],o["rows"]) for o in descriptions],flush=True)
        # Verify the three actual desired bowling datasets (plus two historical joins)
        assert report["sources"]["philipson_test"]["objects"][0]["rows"]>10_000
        assert report["sources"]["golicher_2017"]["objects"][0]["rows"]>10_000
        assert report["sources"]["hf_test_bowling"]["objects"][0]["rows"]>10_000
        assert report["sources"]["hf_test_matches"]["objects"][0]["rows"]>1_000
        report["privateTemporarySQLiteCreated"]=True
        report["totalBowlingRowsAcrossSources"]=sum(
             o["rows"] for k in ("philipson_test","golicher_2017","hf_test_bowling")
             for o in report["sources"][k]["objects"])
        print("All 3 historical bowling source archives imported into temporary private SQLite for schema validation.",flush=True)
        # Aggregate provenance only; do not export DB/raw rows as a public artifact.
        out=Path("research/bowling_historical/source_import_profile.json")
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+"\n")
    finally:
        conn.close()
        # Deliberately delete raw source files and SQLite from CI runners.
        for p in local.iterdir():
            if p.is_file():p.unlink()
        local.rmdir()
if __name__=="__main__":
    main()
