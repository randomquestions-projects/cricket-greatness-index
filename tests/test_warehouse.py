"""Synthetic fixtures only; no synthesized data is published as real observations."""
import json
import sqlite3
import tempfile
import unittest
import zipfile
import gzip
from pathlib import Path
from warehouse.events import build
from warehouse.registers import load

class WarehouseTests(unittest.TestCase):
    def test_cricsheet_event_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);archives=base/"raw";archives.mkdir()
            doc={"info":{"gender":"male","team_type":"international",
                  "match_type":"Test","dates":["2001-01-01"],
                  "teams":["India","Australia"],"venue":"Test Ground",
                  "registry":{"people":{"A Batter":"abc","B Bowler":"def"}}},
                  "innings":[{"team":"India","overs":[{"over":0,"deliveries":[
                  {"batter":"A Batter","non_striker":"Other","bowler":"B Bowler",
                   "runs":{"batter":4,"total":4},"wickets":[]},
                  {"batter":"A Batter","non_striker":"Other","bowler":"B Bowler",
                   "runs":{"batter":0,"total":1},"extras":{"wides":1}}]}]}]}
            for fmt,name in [("test","tests_male_json.zip"),("odi","odis_male_json.zip"),("t20i","t20s_male_json.zip")]:
                with zipfile.ZipFile(archives/name,"w") as z:
                    if fmt=="test":z.writestr("123.json",json.dumps(doc))
                    else:z.writestr("ignore.txt","not an international record")
            manifest=build(archives,base/"out")
            self.assertEqual(manifest["counts"]["test_matches"],1)
            self.assertEqual(manifest["counts"]["test_deliveries"],2)
            with gzip.open(base/"out"/"cricket-events.sqlite.gz","rb") as source:
                (base/"out"/"unpacked.sqlite").write_bytes(source.read())
            conn=sqlite3.connect(base/"out"/"unpacked.sqlite")
            self.assertEqual(conn.execute("SELECT sum(runs_total) FROM deliveries").fetchone()[0],5)
            self.assertEqual(conn.execute("SELECT batter_id FROM deliveries LIMIT 1").fetchone()[0],"abc")
            self.assertEqual(conn.execute("SELECT count(*) FROM deliveries WHERE extras_json LIKE '%wides%'").fetchone()[0],1)
            conn.close()
    def test_reference_csv_identity(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);raw=base/"raw";raw.mkdir()
            csvs={
              "people.csv":"identifier,name,unique_name,key_cricinfo\np01,ABC,ABC (IND),42\n",
              "names.csv":"identifier,name\np01,ABC Alias\n",
              "venues.csv":"identifier,name,unique_name,key_cricinfo\nv01,Ground,Ground,12\n",
              "venue_names.csv":"identifier,name\nv01,Old Ground\n"}
            for name,content in csvs.items():(raw/name).write_text(content)
            stats=load(base/"out",raw)
            self.assertEqual(stats["tableCounts"]["people"],1)
            self.assertEqual(stats["tableCounts"]["person_external_ids"],1)
            self.assertEqual(stats["tableCounts"]["venue_aliases"],1)

if __name__=="__main__": unittest.main()
