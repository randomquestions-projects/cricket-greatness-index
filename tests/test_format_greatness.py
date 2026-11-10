"""Synthetic equality/eligibility checks for ODI T20I and JAWS-inspired composite."""
import unittest
from pipeline.format_greatness import combined, percentiles
from pipeline.scorecard_model import build_from_rows, _jaws_style

class FormatGreatnessTests(unittest.TestCase):
    def test_nonconsecutive_best_seven_calendar_seasons(self):
        rs=[{"year":2000+i,"runs":(90 if i in (0,2,4,6,8,10,12) else 25),
             "expectedRuns":40.0,"dismissed":1,"expectedOuts":.85} for i in range(14)]
        v=_jaws_style(rs)
        self.assertEqual(len(v["bestSevenSeasons"]),7)
        self.assertEqual(v["bestSevenSeasons"],[2000,2002,2004,2006,2008,2010,2012])
        self.assertAlmostEqual(v["jawsStyleValue"],round((v["careerValue"]+v["bestSevenSeasonValue"])/2,2),delta=.02)
        self.assertEqual(v["jawsUnits"],"context-standardized run-surplus equivalents, not WAR")

    def fake(self,name,team,fmt,innings=60,quality=150,career=150,jaws=10):
        return {"name":name,"team":team,"playerId":name+fmt,
                "innings":innings,"quality":quality,"teamCarry":120,
                "careerGreatness":career,"jawsStyleValue":jaws,
                "bestSevenSeasonValue":jaws*.8,"historicalInnings":innings//2}
    def test_two_format_not_requiring_t20(self):
        reports={f:{"players":[]} for f in ("test","odi","t20i")}
        for f in ("test","odi"):
            reports[f]["players"].extend([self.fake("Old Great","Australia",f,jaws=20),
                                          self.fake("Modern Great","India",f,jaws=10)])
        reports["t20i"]["players"].append(self.fake("Modern Great","India","t20i",jaws=9))
        result=combined(reports)
        self.assertIn("Old Great",[p["name"] for p in result["test_odi"]])
        self.assertNotIn("Old Great",[p["name"] for p in result["all_three"]])
        self.assertEqual(len(result["all_three"]),1)
        self.assertLessEqual(result["all_three"][0]["overallIndex"],100)
    def test_format_specific_era_pools(self):
        source=[]
        for f in ("test","odi","t20i"):
            for year in range(2010,2020):
                for match in range(4):
                    for i in range(9):
                        source.append({"format":f,"name":f+"_"+str(i),"team":"India",
                          "opposition":"Australia","host":"Australia",
                          "date":f"{year}-01-01","year":year,
                          "match_id":f"{f}:{year}:{match}","innings_id":f"{f}:{year}:{match}:1",
                          "player_id":f+"_"+str(i),"runs":45 if i==0 else 20+i,
                          "dismissed":1,"scorecardOnly":bool(i%2)})
        for f in ("test","odi","t20i"):
            result=build_from_rows(source,bootstraps=False,format_code=f)
            self.assertEqual(result["format"],f)
            self.assertTrue(all(p["name"].startswith(f) for p in result["players"]))
            self.assertTrue(all(p["jawsUnits"].endswith("not WAR") for p in result["players"]))

if __name__=="__main__":unittest.main()
