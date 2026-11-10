"""Unit tests for licensed-only bowling availability assessment.

Uses a tiny synthetic Cricsheet-style scorecard shard. Never reads or changes
the batting site's models, indices, user-facing data, or workflows.
"""
import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from .audit import run

class BowlingAuditTest(unittest.TestCase):
    def test_formats_career_gaps_and_source_quality(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            db=d/"scorecards_male_2020s.sqlite"
            con=sqlite3.connect(db)
            con.executescript("""
                CREATE TABLE matches (
                    id TEXT, start_date TEXT, gender TEXT, category TEXT, venue TEXT);
                CREATE TABLE innings (
                    id TEXT, match_id TEXT, super_over INT);
                CREATE TABLE bowling (
                    innings_id TEXT, player_id TEXT, player_name TEXT,
                    wickets INT, conceded INT, legal_balls INT);
                CREATE TABLE quality_flags (match_id TEXT, flag TEXT);
                INSERT INTO matches VALUES('t1','2024-01-07','male','test','Adelaide');
                INSERT INTO matches VALUES('o1','2024-02-07','male','odi',NULL);
                INSERT INTO matches VALUES('w1','2024-03-07','female','odi',NULL);
                INSERT INTO innings VALUES('i1','t1',0);
                INSERT INTO innings VALUES('i2','t1',1);
                INSERT INTO innings VALUES('i3','o1',0);
                INSERT INTO innings VALUES('i4','w1',0);
                INSERT INTO bowling VALUES('i1','pid-B','Jasprit Bumrah',3,50,120);
                INSERT INTO bowling VALUES('i1',NULL,'Pat Cummins',2,40,90);
                INSERT INTO bowling VALUES('i2','pid-B','Jasprit Bumrah',2,4,5);
                INSERT INTO bowling VALUES('i3','pid-B','Jasprit Bumrah',4,35,60);
                INSERT INTO bowling VALUES('i4','pid-Z','Jasprit Bumrah',9,0,66);
                INSERT INTO quality_flags VALUES('t1','SOURCE_MISSING');
                INSERT INTO quality_flags VALUES('t1','OTHER');
            """)
            con.commit()
            con.close()
            path=d/"scorecards_male_2020s.sqlite.gz"
            with db.open("rb") as fi,gzip.open(path,"wb") as fo:
                fo.write(fi.read())
            out=run([path],d/"audit")
            self.assertEqual(out["byFormat"]["test"]["matches"],1)
            self.assertEqual(out["byFormat"]["test"]["wickets"],5)
            self.assertEqual(out["byFormat"]["odi"]["wickets"],4)
            self.assertEqual(out["byFormat"]["odi"]["noVenue"],1)
            self.assertEqual(out["byFormat"]["test"]["missingBowlerID"],1)
            self.assertEqual(out["byFormat"]["test"]["flagged"],1)
            self.assertFalse(out["historicalBowlingCompletenessCertified"])
            candidates={x["player"]:x for x in out["playerCaseStudies"]}
            self.assertEqual(candidates["Jasprit Bumrah"]["observedWickets"],7)
            self.assertEqual(candidates["Sydney Barnes"]["observedWickets"],0)
            self.assertFalse(candidates["Sydney Barnes"]["isFullCareer"])
            self.assertIn("Only licensed Cricsheet",out["rightsGate"])
            self.assertNotIn("Batting Greatness",json.dumps(out))
            self.assertTrue((d/"audit"/"coverage.md").exists())
            self.assertTrue((d/"audit"/"coverage.json").exists())

if __name__=="__main__":unittest.main()
