"""Bowling enrichment tests: no name joins, no fielding, no batting app changes."""
import csv
import tempfile
import unittest
from pathlib import Path
from .build import build, style_group

def sample(*lines):
    return ("\n".join(lines)+"\n").encode()

class BowlingEnrichmentTests(unittest.TestCase):
    def test_style_classifier(self):
        self.assertEqual(style_group("right-arm fast"),"pace")
        self.assertEqual(style_group("left-arm medium-fast"),"pace")
        self.assertEqual(style_group("right-arm offbreak"),"spin")
        self.assertEqual(style_group("leg break"),"spin")
        self.assertEqual(style_group("slow left-arm orthodox"),"spin")
        self.assertEqual(style_group("right arm"),"unknown")
        self.assertEqual(style_group("right-arm fast and leg spin"),"unknown")

    def test_licensed_identifier_joins_and_conflicts(self):
        payloads={
          "people":sample("identifier,name,unique_name,key_cricinfo",
             "abc,Test Player,Test Player,123",
             "def,Unknown Player,Unknown Player,",
             "ghi,Conflicting Player,Conflicting Player,456"),
          "names":sample("identifier,name","abc,Player Alias","def,Other Name"),
          "venues":sample("identifier,name,unique_name,key_cricinfo",
             "v1,Ground A,Ground A,900",
             "v2,Ground B,Ground B,901",
             "v3,Ground C,Ground C,"),
          "venue_names":sample("identifier,name","v1,Stadium A","v2,Stadium B")
        }
        def get_register(name,url):
            return payloads[name]
        def get_wikidata(query):
            if "P2545" in query:
                return [
                  {"espnId":"123","player":"http://www.wikidata.org/entity/Q123",
                   "bowlingStyleLabel":"right-arm fast"},
                  {"espnId":"456","player":"http://www.wikidata.org/entity/Q456",
                   "bowlingStyleLabel":"right-arm fast"},
                  {"espnId":"456","player":"http://www.wikidata.org/entity/Q456",
                   "bowlingStyleLabel":"leg break"}]
            return [
              {"espnId":"900","ground":"http://www.wikidata.org/entity/Q900",
                "country":"http://www.wikidata.org/entity/Q30","countryLabel":"United States",
                "isoCode":"US"},
              {"espnId":"901","ground":"http://www.wikidata.org/entity/Q901",
                "country":"http://www.wikidata.org/entity/Q30","countryLabel":"United States",
                "isoCode":"US"},
              {"espnId":"901","ground":"http://www.wikidata.org/entity/Q901",
                "country":"http://www.wikidata.org/entity/Q145","countryLabel":"United Kingdom",
                "isoCode":"GB"}]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            report=build(out,get_register,get_wikidata)
            self.assertEqual(report["player_count"],3)
            self.assertEqual(report["venue_count"],3)
            with (out/"player_bowling_style.csv").open() as f:
                p={r["cricsheet_id"]:r for r in csv.DictReader(f)}
            self.assertEqual(p["abc"]["style_groups"],"pace")
            self.assertEqual(p["abc"]["match_status"],"linked")
            self.assertEqual(p["def"]["match_status"],"unmatched")
            self.assertEqual(p["ghi"]["match_status"],"conflicting_styles")
            self.assertEqual(p["ghi"]["style_groups"],"unknown")
            with (out/"venue_physical_country.csv").open() as f:
                v={r["cricsheet_venue_id"]:r for r in csv.DictReader(f)}
            self.assertEqual(v["v1"]["physical_country"],"United States")
            self.assertEqual(v["v2"]["physical_country"],"")
            self.assertEqual(v["v2"]["match_status"],"conflicting_countries")
            self.assertEqual(v["v3"]["match_status"],"unmatched")
            self.assertEqual(v["v1"]["cricket_host_team"],"")
            self.assertEqual(report["rights"]["wikidata_structured_claims"],"CC0")
            for path in ["player_bowling_style.csv","venue_physical_country.csv",
                         "player_aliases.csv","venue_aliases.csv","provenance.json"]:
                self.assertTrue((out/path).exists())
            self.assertEqual(len(report["errors"]),0)

if __name__=="__main__":unittest.main()
