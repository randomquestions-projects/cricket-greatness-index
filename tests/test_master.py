"""All-match licensed master-warehouse synthetic fixture tests."""
import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from warehouse.master import build, classification

class MasterWarehouseTests(unittest.TestCase):
    def test_category_strict_international_separation(self):
        self.assertEqual(classification({"match_type":"T20","team_type":"international"}),"t20i")
        self.assertEqual(classification({"match_type":"T20","team_type":"club"}),"t20")
        self.assertEqual(classification({"match_type":"ODI","team_type":"international"}),"odi")
        self.assertEqual(classification({"match_type":"ODM","team_type":"club"}),"list_a")

    def test_full_source_events_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/"all_json.zip"
            doc={"meta":{"data_version":"1.1.0"},"info":{
                "gender":"female","match_type":"T20","team_type":"international",
                "dates":["2026-09-10"],"teams":["India","Australia"],
                "players":{"India":["A Batter"],"Australia":["B Bowler"]},
                "registry":{"people":{"A Batter":"key_a","B Bowler":"key_b"}},
                "event":{"name":"World Cup"},"match_type_number":44,
                "outcome":{"winner":"India"}},"innings":[{"team":"India","overs":[
                {"over":0,"deliveries":[
                    {"batter":"A Batter","non_striker":"A Partner","bowler":"B Bowler",
                     "runs":{"batter":4,"total":4},"wickets":[]},
                    {"batter":"A Batter","non_striker":"A Partner","bowler":"B Bowler",
                     "runs":{"batter":0,"total":1},"extras":{"wides":1},
                     "wickets":[{"player_out":"A Batter","kind":"run out","fielders":[{"name":"B Bowler"}]}]}
                ]}]}]}
            with ZipFile(path,"w") as z:
                z.writestr("333.json",json.dumps(doc))
            out=root/"output"; manifest=build(path,out)
            self.assertEqual(manifest["counts"]["matches"],1)
            self.assertEqual(manifest["counts"]["deliveries"],2)
            self.assertEqual(manifest["counts"]["wickets"],1)
            self.assertEqual(manifest["byGenderAndCategory"]["female:t20i"],1)
            data=out/"master_female_2020s.sqlite.gz"
            with gzip.open(data,"rb") as src:
                (root/"unpacked.sqlite").write_bytes(src.read())
            db=sqlite3.connect(root/"unpacked.sqlite")
            self.assertEqual(db.execute("SELECT count(*) FROM match_people").fetchone()[0],2)
            self.assertEqual(db.execute("SELECT match_type,category,official_match_type_number FROM matches").fetchone(),("T20","t20i",44))
            self.assertEqual(db.execute("SELECT sum(total_runs),sum(legal_ball),sum(faced_ball) FROM deliveries").fetchone(),(5,1,2))
            self.assertEqual(db.execute("SELECT dismissal_kind FROM wickets").fetchone()[0],"run out")
            self.assertEqual(db.execute("SELECT batter_id FROM deliveries LIMIT 1").fetchone()[0],"key_a")
            db.close()

if __name__=="__main__":unittest.main()
