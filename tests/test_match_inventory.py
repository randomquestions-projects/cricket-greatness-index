"""Verify source-only matching gap logic on nonreal fixtures."""
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from warehouse.match_inventory import audit

class NumberedMatchTests(unittest.TestCase):
    def test_does_not_claim_official_completeness(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/"sample.zip"
            with ZipFile(archive,"w") as z:
                for n in (11,13):
                    x={"info":{"gender":"male","team_type":"international",
                       "match_type":"Test","match_type_number":n}}
                    z.writestr(f"{n}.json",json.dumps(x))
            result=audit(archive,root/"out")
            self.assertFalse(result["isOfficialIndependentCensus"])
            self.assertEqual(result["groups"]["male:test"]["potentialUnobservedNumbers"],[12])
            self.assertEqual(result["groups"]["male:test"]["potentialMissingCount"],1)

if __name__=="__main__":unittest.main()
