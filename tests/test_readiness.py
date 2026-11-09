"""Sanity checks for aggregate public scorecard coverage readiness."""
import json
import tempfile
import unittest
from pathlib import Path
from warehouse.readiness import build

class ReadinessTests(unittest.TestCase):
    def test_distinguishes_historic_batting_from_complete_cards(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cv={"allTimeRankingPermitted":False,
              "formats":{"test":{"observedMatches":2,"historicalScorecardMatches":1,"deliveryMatches":1},
              "odi":{"observedMatches":3,"historicalScorecardMatches":2,"deliveryMatches":1},
              "t20i":{"observedMatches":1,"historicalScorecardMatches":0,"deliveryMatches":1}}}
            hist={"sourceSHA256":"example","formats":{
              "test":{"sourceCandidateMatches":2,"historicalBattingRows":20,"missingnessRowCounts":{"missing_batting_order":20}},
              "odi":{"sourceCandidateMatches":2,"historicalBattingRows":20,"missingnessRowCounts":{}},
              "t20i":{"sourceCandidateMatches":0,"historicalBattingRows":0,"missingnessRowCounts":{}}}}
            cric={"independentlyCompleteScorecards":False,"counts":{"matches":6},
              "sourceArchiveSHA256":"test", "byGenderAndFormat":{
              "male:test":1,"male:odi":1,"male:t20i":1}}
            for name,doc in [("coverage.json",cv),("history.json",hist),("cric.json",cric)]:
                (root/name).write_text(json.dumps(doc))
            r=build(root/"coverage.json",root/"history.json",root/"cric.json",root/"result.json")
            self.assertEqual(r["formatCoverage"]["test"]["historicBattingOnlyMatchesAfterOverlapSuppression"],1)
            self.assertEqual(r["formatCoverage"]["test"]["independentlyCertifiedCompleteScorecards"],0)
            self.assertFalse(r["independentScorecardComparisonComplete"])
            self.assertNotIn("player_id",(root/"result.json").read_text())
    def test_fails_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cv={"allTimeRankingPermitted":False,"formats":{
              fmt:{"observedMatches":1,"historicalScorecardMatches":0,"deliveryMatches":1}
              for fmt in ("test","odi","t20i")}}
            hist={"formats":{}};cric={"independentlyCompleteScorecards":False,
                 "counts":{"matches":1},"sourceArchiveSHA256":"a","byGenderAndFormat":{"male:test":2}}
            for name,doc in [("coverage.json",cv),("history.json",hist),("cric.json",cric)]:
                (root/name).write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                build(root/"coverage.json",root/"history.json",root/"cric.json",root/"result.json")

if __name__=="__main__":unittest.main()
