"""Synthetic invariance and historical fairness checks for the shared v0.4 scorecard-era model."""
import unittest
from pipeline.scorecard_model import build_from_rows, _rating, host_class, _peak

def row(name,year,match,index,runs,team="Australia",opponent="England",host="England",hist=True):
    return {
      "format":"test","date":f"{year}-06-{(match%25)+1:02d}",
      "year":year,"match_id":f"test:{year}:{match}:{team}:{opponent}",
      "innings_id":f"test:{year}:{match}:{team}:{opponent}:{index}",
      "player_id":name.replace(" ","_"),"name":name,"team":team,
      "opposition":opponent,"host":host,"scorecardOnly":hist,
      "runs":runs,"dismissed":int(runs<90)
    }

class TestEraModel(unittest.TestCase):
    def fixture(self):
        rows=[]
        for yr in range(1932,1942):
            for m in range(1,5):
                # Same match, 9 observed batters; enough match peer context
                for j in range(1,10):
                    nm="Don Bradman" if j==1 else f"Era {j}"
                    score=102 if j==1 else 20+j*2
                    rows.append(row(nm,yr,m,j,score,hist=True))
        for yr in range(2014,2024):
            for m in range(1,5):
                for j in range(1,10):
                    nm="Virat Kohli" if j==1 else f"Modern {j}"
                    score=100 if j==1 else 20+j*2
                    rows.append(row(nm,yr,m,j,score,team="India",opponent="Australia",host="Australia",hist=False))
        return rows
    def test_all_eras_use_identical_features(self):
        result=build_from_rows(self.fixture(),bootstraps=False)
        self.assertFalse(result["modernOnlyFeaturesInPrimaryModel"])
        self.assertFalse(result["certifiedAllTimeRanking"])
        names={p["name"]:p for p in result["players"]}
        self.assertIn("Don Bradman",names);self.assertIn("Virat Kohli",names)
        self.assertGreater(names["Don Bradman"]["quality"],100)
        self.assertGreater(names["Virat Kohli"]["quality"],100)
        self.assertEqual(names["Don Bradman"]["innings"],40)
        self.assertTrue(any(x["opponent"]=="England" and x["venueClass"]=="away" for x in names["Don Bradman"]["opponentAndVenue"]))
        self.assertEqual(names["Virat Kohli"]["innings"],40)
        self.assertIsNone(names["Virat Kohli"]["qualityInterval90"])
        self.assertTrue(any(p.get("careerCheck") for p in result["players"]))
    def test_road_home_unknown(self):
        self.assertEqual(host_class({"team":"India","opposition":"Australia","host":"Australia"}),"away")
        self.assertEqual(host_class({"team":"India","opposition":"Australia","host":"India"}),"home")
        self.assertEqual(host_class({"team":"India","opposition":"Australia","host":""}),"unknown")
    def test_rolling_peak(self):
        rows=[{"runs":40,"dismissed":1,"expectedRuns":29,"expectedOuts":.82,
               "date":f"2001-01-{i+1:02d}","match_id":f"m{i}","innings_id":f"i{i}"}
              for i in range(25)]
        self.assertGreater(_peak(rows)["index"],100)
        self.assertIsNone(_peak(rows[:24]))
    def test_quality_discounts_low_performance(self):
        q1=_rating(600,500,10,10,20)
        q2=_rating(400,500,10,10,20)
        self.assertGreater(q1,q2)

if __name__=="__main__": unittest.main()
