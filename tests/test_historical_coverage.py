"""Aggregate-only historical source coverage tests using synthetic rows."""
import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from warehouse.historical_audit import audit

class HistoricalCoverageTests(unittest.TestCase):
    def test_public_report_does_not_publish_individual_scorecards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"historical-innings.csv.gz"
            rows=[
                {"date":"1930-01-01","format":"test","team":"Australia","opposition":"England",
                 "innings_number":"1","name":"Synthetic Batter X","runs":"120","balls":"0",
                 "position":"0","dismissal":"dismissed","team_total":"0","bowler_exposures":"{}"},
                {"date":"1930-01-01","format":"test","team":"England","opposition":"Australia",
                 "innings_number":"1","name":"Synthetic Batter Y","runs":"90","balls":"100",
                 "position":"0","dismissal":"not out","team_total":"250","bowler_exposures":"{}"}
            ]
            with gzip.open(source,"wt",newline="") as f:
                w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
            modern=root/"matches.json";modern.write_text("[]")
            out=root/"audit.json"
            r=audit(source,modern,out)
            self.assertEqual(r["formats"]["test"]["sourceCandidateMatches"],1)
            self.assertEqual(r["formats"]["test"]["historicalBattingRows"],2)
            self.assertEqual(r["formats"]["test"]["missingnessRowCounts"]["missing_batting_order"],2)
            self.assertFalse(r["scorecardCompletenessCertified"])
            content=out.read_text()
            self.assertNotIn("Synthetic Batter X",content)
            self.assertNotIn("1930-01-01",content)
            self.assertNotIn('"runs": "120"',content)
if __name__=="__main__": unittest.main()
