"""Download the ODC-BY Cricsheet people/venue registers into reusable SQLite.
Only Cricsheet-licensed reference data are redistributed. No ESPN scorecards.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import io
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://cricsheet.org/register/"
FILES = ("people.csv", "names.csv", "venues.csv", "venue_names.csv")
SCHEMA = """
CREATE TABLE people (id TEXT PRIMARY KEY, name TEXT NOT NULL, unique_name TEXT);
CREATE TABLE person_aliases (id TEXT NOT NULL, alias TEXT NOT NULL,
  PRIMARY KEY(id,alias));
CREATE TABLE person_external_ids (id TEXT NOT NULL, provider TEXT NOT NULL, external_id TEXT NOT NULL,
  PRIMARY KEY(provider,external_id));
CREATE TABLE venues (id TEXT PRIMARY KEY, name TEXT NOT NULL, unique_name TEXT);
CREATE TABLE venue_aliases (id TEXT NOT NULL, alias TEXT NOT NULL,
  PRIMARY KEY(id,alias));
CREATE TABLE venue_external_ids (id TEXT NOT NULL, provider TEXT NOT NULL, external_id TEXT NOT NULL,
  PRIMARY KEY(provider,external_id));
CREATE INDEX person_alias_lookup ON person_aliases(alias);
CREATE INDEX venue_alias_lookup ON venue_aliases(alias);
"""

def load(output=ROOT / "warehouse" / "exports", source_dir=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sources = {}
    rows = {}
    for filename in FILES:
        if source_dir:
            payload = (Path(source_dir) / filename).read_bytes()
        else:
            req = urllib.request.Request(BASE + filename,
                headers={"User-Agent":"CricketGreatnessLab/2.0 (Cricsheet ODC-BY attribution)"})
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = response.read()
        if len(payload) < 15:
            raise ValueError("Empty register: " + filename)
        sources[filename] = hashlib.sha256(payload).hexdigest()
        rows[filename] = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    for name in ("people.csv", "venues.csv"):
        if not {"identifier", "name"}.issubset(rows[name][0]):
            raise ValueError("Register missing identifier/name: " + name)
    db = output / "identities.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    try:
        con.executescript(SCHEMA)
        for r in rows["people.csv"]:
            pid = (r.get("identifier") or "").strip()
            if not pid:
                continue
            con.execute("INSERT INTO people VALUES (?,?,?)",
                (pid, r["name"], r.get("unique_name")))
            for col, val in r.items():
                if col.startswith("key_") and val and val.strip():
                    con.execute("INSERT OR IGNORE INTO person_external_ids VALUES (?,?,?)",
                        (pid, col[4:], val.strip()))
        for r in rows["names.csv"]:
            if r.get("identifier") and r.get("name"):
                con.execute("INSERT OR IGNORE INTO person_aliases VALUES (?,?)",
                    (r["identifier"], r["name"]))
        for r in rows["venues.csv"]:
            vid = (r.get("identifier") or "").strip()
            if not vid:
                continue
            con.execute("INSERT INTO venues VALUES (?,?,?)",
                (vid, r["name"], r.get("unique_name")))
            for col, val in r.items():
                if col.startswith("key_") and val and val.strip():
                    con.execute("INSERT OR IGNORE INTO venue_external_ids VALUES (?,?,?)",
                        (vid, col[4:], val.strip()))
        for r in rows["venue_names.csv"]:
            if r.get("identifier") and r.get("name"):
                con.execute("INSERT OR IGNORE INTO venue_aliases VALUES (?,?)",
                    (r["identifier"], r["name"]))
        counts = {table: con.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for table in ("people", "person_aliases", "person_external_ids",
                          "venues", "venue_aliases", "venue_external_ids")}
        if not counts["people"] or not counts["venues"]:
            raise ValueError("People or venue register empty")
        con.commit()
        check = con.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise ValueError("SQLite integrity failed: " + check)
    finally:
        con.close()
    gz = output / "identities.sqlite.gz"
    with db.open("rb") as src, gz.open("wb") as dest:
        with gzip.GzipFile(fileobj=dest, mode="wb", filename="", mtime=0) as zipped:
            while True:
                block = src.read(1024*1024)
                if not block:
                    break
                zipped.write(block)
    db.unlink()
    result = {"asOfUTC": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source":"Cricsheet.org", "url":BASE, "license":"ODC-BY 1.0",
        "sourceSHA256": sources, "tableCounts":counts,
        "outputSHA256":hashlib.sha256(gz.read_bytes()).hexdigest(),
        "note":"IDs and aliases are REFERENCES; do not merge ambiguous historic people on name alone."}
    (output / "identity_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=ROOT/"warehouse"/"exports")
    p.add_argument("--source-dir",type=Path)
    args = p.parse_args()
    print(json.dumps(load(args.output,args.source_dir),indent=2))

if __name__ == "__main__":
    main()
