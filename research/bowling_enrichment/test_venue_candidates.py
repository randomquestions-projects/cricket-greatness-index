"""Venue-country candidate matching is review-only, never silently verified."""
import csv
import tempfile
import unittest
from pathlib import Path
from .venue_candidates import find_candidates

def csvout(path,head,rows):
    with path.open("w",newline="") as f:
        w=csv.writer(f);w.writerow(head);w.writerows(rows)

class VenueCountryCandidatesTest(unittest.TestCase):
    def test_exact_name_candidates_do_not_override_verified_id_matches(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)/"refs";r.mkdir()
            csvout(r/"venue_physical_country.csv",
                   ["cricsheet_venue_id","venue_name","match_status","physical_country"],
                   [["a","Adelaide Oval","unmatched",""],
                    ["b","The Oval","unmatched",""],
                    ["c","Already Verified Stadium","linked","Australia"]])
            csvout(r/"venue_aliases.csv",["cricsheet_venue_id","alias"],
                   [["a","Stadium Adelaide"],["b","The Oval, London"]])
            def query(batch):
                result=[]
                if "Adelaide Oval" in batch:
                    result.append({"venueName":"Adelaide Oval",
                      "ground":"http://www.wikidata.org/entity/Q111",
                      "country":"http://www.wikidata.org/entity/Q408",
                      "countryLabel":"Australia","isoCode":"AU"})
                if "The Oval" in batch:
                    for q,c in [("Q1","United Kingdom"),("Q2","Canada")]:
                        result.append({"venueName":"The Oval",
                          "ground":"http://www.wikidata.org/entity/"+q,
                          "country":"http://www.wikidata.org/entity/Qx",
                          "countryLabel":c,"isoCode":""})
                return result
            o=find_candidates(r,Path(d)/"out",batch_size=2,loader=query)
            self.assertEqual(o["status"]["already_verified_by_espn_id"],1)
            with (Path(d)/"out"/"venue_country_candidates_REVIEW_ONLY.csv").open() as f:
                x={a["cricsheet_venue_id"]:a for a in csv.DictReader(f)}
            self.assertEqual(x["a"]["candidate_country"],"Australia")
            self.assertEqual(x["a"]["review_status"],"single_exact_label_candidate_review")
            self.assertEqual(x["b"]["review_status"],"multiple_countries_ambiguous")
            self.assertNotIn("c",x)
            self.assertEqual(x["a"]["verified_country"],"")
            self.assertFalse(o["modelFeedsAllowed"])
            self.assertFalse(o["verifiedCountryJoinUpdated"])

if __name__=="__main__": unittest.main()
