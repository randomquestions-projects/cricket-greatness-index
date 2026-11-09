"""Synthetic tests of scorecard calculations and incomplete-source indicators."""
import tempfile
import unittest
import json
import gzip
import sqlite3
from pathlib import Path
from zipfile import ZipFile
from warehouse.scorecards import scorecard,build

def example():
    return {"info":{"dates":["2026-01-01"],"gender":"male","match_type":"ODI",
        "team_type":"international","teams":["India","Australia"],
        "registry":{"people":{"A":"p-a","B":"p-b","C":"p-c","Bowler":"p-x","Fielder":"p-f"}}},
        "innings":[{"team":"India","overs":[{"over":0,"deliveries":[
        {"batter":"A","non_striker":"B","bowler":"Bowler","runs":{"batter":4,"total":4}},
        {"batter":"A","non_striker":"B","bowler":"Bowler","runs":{"batter":0,"total":1},"extras":{"wides":1}},
        {"batter":"A","non_striker":"B","bowler":"Bowler","runs":{"batter":0,"total":0},
         "wickets":[{"player_out":"A","kind":"caught","fielders":[{"name":"Fielder"}]}]},
        {"batter":"C","non_striker":"B","bowler":"Bowler","runs":{"batter":0,"total":1},"extras":{"byes":1}}
        ]}]}]}

class ScorecardTest(unittest.TestCase):
    def test_runs_bowling_and_fielding_reconcile(self):
        result=scorecard(example(),"123.json")
        self.assertIsNotNone(result)
        _,innings,batting,bowling,fielding,flags=result
        self.assertEqual(innings[0][5],6)
        self.assertEqual(innings[0][6],4)
        self.assertEqual(innings[0][7],2)
        self.assertEqual(innings[0][8],1)
        self.assertEqual(innings[0][9],3)
        self.assertEqual(sum(x[4] for x in batting),4)
        self.assertEqual(sum(x[6] for x in bowling),1)
        self.assertEqual(sum(x[5] for x in bowling),1)
        self.assertEqual(fielding[0][3],1)
        self.assertFalse(flags)
    def test_missing_source_is_flagged(self):
        doc=example()
        doc["info"]["missing"]=["1st over absent"]
        result=scorecard(doc,"888.json")
        self.assertEqual(result[1][0][-1],"delivery-partial")
        self.assertTrue(any(f[2]=="SOURCE_MISSING" for f in result[-1]))
    def test_source_shard_and_qa(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            path=base/"all_json.zip"
            with ZipFile(path,"w") as z:z.writestr("123.json",json.dumps(example()))
            result=build(path,base/"out")
            self.assertEqual(result["counts"]["matches"],1)
            self.assertEqual(result["counts"]["bowling_rows"],1)
            self.assertFalse(result["independentlyCompleteScorecards"])
            with gzip.open(base/"out"/"scorecards_male_2020s.sqlite.gz","rb") as f:
                (base/"temp.sqlite").write_bytes(f.read())
            conn=sqlite3.connect(base/"temp.sqlite")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM batting").fetchone()[0],3)
            self.assertEqual(conn.execute("SELECT runs,extras FROM innings").fetchone(),(6,2))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM quality_flags").fetchone()[0],0)
            conn.close()
if __name__=="__main__": unittest.main()
