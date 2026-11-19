"""Offline regression checks for safe, exact three-release retirement."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

target=Path(__file__).resolve().parents[1]/".github/scripts/retire_legacy_cricket_releases.py"
spec=importlib.util.spec_from_file_location("cricket_release_retirement",target)
retire=importlib.util.module_from_spec(spec)
spec.loader.exec_module(retire)

class ReleaseRetirementTests(unittest.TestCase):
    def fake_api(self,mutated=False):
        catalog={}
        for tag,release_id,assets in retire.RELEASES:
            matching=[{"id":id,"name":name,"size":size} for id,(name,size) in assets.items()]
            if mutated and tag==retire.RELEASES[0][0]:
                matching[0]["size"]+=1
            catalog[tag]={"id":release_id,"tag_name":tag,"assets":matching}
        deleted=[]
        def fetch(url,method="GET"):
            if url.startswith(retire.API+"/releases/tags/"):
                tag=url.split("/")[-1]
                return (404,None) if tag in deleted else (200,catalog[tag])
            if method=="DELETE":
                release_id=int(url.split("/")[-1])
                tag=next((k for k,v in catalog.items() if v["id"]==release_id),None)
                if tag is None:raise ValueError("Unexpected release")
                deleted.append(tag)
                return 204,None
            raise ValueError("Unexpected API call")
        return fetch,deleted
    def test_preview_exact_pinned_26_assets(self):
        fetch,deleted=self.fake_api()
        counts=retire.verify_catalog(fetch)
        self.assertEqual(len(counts),3)
        self.assertEqual(sum(x["assets"] for x in counts),26)
        self.assertEqual(deleted,[])
    def test_release_drift_blocks_deletion(self):
        fetch,deleted=self.fake_api(mutated=True)
        with self.assertRaisesRegex(ValueError,"asset drift"):
            retire.retire(retire.CONFIRM,retire.ASSET_MANIFEST_SHA,
                          retire.HISTORY_MANIFEST_SHA,fetch=fetch)
        self.assertEqual(deleted,[])
    def test_wrong_confirmation_or_backup_hash_blocks_deletion(self):
        fetch,deleted=self.fake_api()
        for confirmation,asset_sha,history_sha in (
            ("wrong",retire.ASSET_MANIFEST_SHA,retire.HISTORY_MANIFEST_SHA),
            (retire.CONFIRM,"wrong",retire.HISTORY_MANIFEST_SHA),
            (retire.CONFIRM,retire.ASSET_MANIFEST_SHA,"wrong")):
            with self.assertRaises(PermissionError):
                retire.retire(confirmation,asset_sha,history_sha,fetch=fetch)
        self.assertEqual(deleted,[])
    def test_explicit_verified_retirement_only_three_expected_releases(self):
        fetch,deleted=self.fake_api()
        done=retire.retire(retire.CONFIRM,retire.ASSET_MANIFEST_SHA,
                          retire.HISTORY_MANIFEST_SHA,fetch=fetch)
        self.assertEqual(done,deleted)
        self.assertEqual(set(deleted),{x[0] for x in retire.RELEASES})
        self.assertEqual(len(deleted),3)
    def test_mandatory_ephemeral_token(self):
        with patch.dict(os.environ,{"GITHUB_TOKEN":""}):
            with self.assertRaises(RuntimeError):
                retire.request(retire.API+"/releases/tags/cricket-master-source-13f9f5d5153c3625")
    def test_unapproved_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            retire.request("https://api.github.com/repos/other/repo/releases/123")

if __name__=="__main__":unittest.main()
