"""Retire only the three verified, privately archived data-only GitHub Releases.

This tool NEVER rewrites public Git history or changes GitHub Pages.
Use only through the manually gated workflow, after verifying both S3 backups.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

REPO="randomquestions-projects/cricket-greatness-index"
API=f"https://api.github.com/repos/{REPO}"
CONFIRM="RETIRE-3-VERIFIED-CRICKET-RELEASES"
# Pinned to the real private S3 backup manifest from GitHub Actions run #44455762845
ASSET_MANIFEST_SHA="d2fc81858b1040649834029a593147ecac29a5cd6f8425b578613f4009b10816"
HISTORY_MANIFEST_SHA="b6fcbf438a6e5d0222b10feaced7024af35bb328f1a453f072dc383f5328afbe"
RELEASES=(
 ("cricket-master-source-13f9f5d5153c3625",446879930,{
 754388418:("cricsheet-all-json.zip",149036509),
 754388419:("master_female_2000s.sqlite.gz",712363),
 754388417:("master_female_2010s.sqlite.gz",15689681),
 754388420:("master_female_2020s.sqlite.gz",51905215),
 754388416:("master_male_2000s.sqlite.gz",36732941),
 754388468:("master_male_2010s.sqlite.gz",189287543),
 754388540:("master_male_2020s.sqlite.gz",222609433),
 754388557:("master_manifest.json",9032),
 754388582:("match_inventory.json",52940)}),
 ("cricket-scorecards-source-13f9f5d5153c3625",439720261,{
 729213105:("LICENSE-ATTRIBUTION.md",1646),
 729213108:("scorecards_female_2000s.sqlite.gz",37043),
 729213104:("scorecards_female_2010s.sqlite.gz",1316268),
 729213106:("scorecards_female_2020s.sqlite.gz",4631364),
 729213107:("scorecards_male_2000s.sqlite.gz",1804425),
 729213127:("scorecards_male_2010s.sqlite.gz",11276174),
 729213124:("scorecards_male_2020s.sqlite.gz",15310581),
 729213132:("scorecards_manifest.json",2400)}),
 ("cricket-master-2026-11-09-42707561618",439698221,{
 729135950:("cricsheet-all-json.zip",149036509),
 729154371:("LICENSE-ATTRIBUTION.md",1646),
 729135947:("master_female_2000s.sqlite.gz",712363),
 729135949:("master_female_2010s.sqlite.gz",15689681),
 729135955:("master_female_2020s.sqlite.gz",51905215),
 729135953:("master_male_2000s.sqlite.gz",36732941),
 729135999:("master_male_2010s.sqlite.gz",189287543),
 729136055:("master_male_2020s.sqlite.gz",222609433),
 729136260:("master_manifest.json",8968)}),
)

def request(url,method="GET"):
    if not url.startswith(API+"/releases/") or not url.startswith("https://api.github.com/"):
        raise ValueError("Unexpected GitHub API endpoint")
    token=os.environ.get("GITHUB_TOKEN","")
    if not token:raise RuntimeError("Authenticated ephemeral GitHub token required")
    req=urllib.request.Request(url,method=method,headers={
      "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28","User-Agent":"cricket-release-retirement/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=35) as resp:
            data=resp.read(250_000)
            return resp.status,json.loads(data) if data else None
    except urllib.error.HTTPError as err:
        if err.code==404:return 404,None
        raise

def verify_catalog(fetch=request):
    """Fail if even one release/asset unexpectedly changed since verified backup."""
    counts=[]
    for tag,release_id,expected_assets in RELEASES:
        url=API+"/releases/tags/"+urllib.parse.quote(tag)
        status,release=fetch(url)
        if status!=200 or not release:
            raise ValueError("Expected backed-up GitHub release unavailable: "+tag)
        if release.get("id")!=release_id or release.get("tag_name")!=tag:
            raise ValueError("GitHub release identity changed: "+tag)
        actual={a["id"]:(a["name"],a["size"]) for a in release.get("assets",[])}
        if actual!=expected_assets:
            raise ValueError("GitHub release asset drift: "+tag)
        counts.append({"tag":tag,"id":release_id,"assets":len(actual)})
    assert sum(x["assets"] for x in counts)==26
    return counts

def gate(confirm,asset_sha,history_sha):
    if confirm!=CONFIRM:raise PermissionError("Explicit retirement phrase missing")
    if asset_sha!=ASSET_MANIFEST_SHA or history_sha!=HISTORY_MANIFEST_SHA:
        raise PermissionError("Backup manifest hashes differ from verified private S3 run")

def retire(confirm,asset_sha,history_sha,*,fetch=request):
    gate(confirm,asset_sha,history_sha)
    checked=verify_catalog(fetch)
    results=[]
    for row in checked:
        status,_=fetch(API+"/releases/"+str(row["id"]),method="DELETE")
        if status!=204:raise RuntimeError("GitHub release deletion not acknowledged: "+row["tag"])
        status,_=fetch(API+"/releases/tags/"+urllib.parse.quote(row["tag"]))
        if status!=404:raise RuntimeError("GitHub release still accessible: "+row["tag"])
        results.append(row["tag"])
    print(json.dumps({"status":"LEGACY_CRICKET_RELEASES_RETIRED",
                      "releaseCount":len(results),"retiredTags":results,
                      "previouslyArchivedAssetRecords":26,
                      "gitHistoryStillPublic":True,
                      "websiteUntouched":True},indent=2))
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--confirmation",default="")
    p.add_argument("--asset-manifest-sha",default="")
    p.add_argument("--history-manifest-sha",default="")
    args=p.parse_args()
    checked=verify_catalog()
    print(json.dumps({"status":"LEGACY_RELEASE_RETIREMENT_PREVIEW","catalog":checked,
                      "assetsBackedUpAccordingToVerifiedRun":26,
                      "privateBackupRun":"https://github.com/randomquestions-projects/analytics-research-private/actions/runs/44455762845",
                      "actualGitHistoryStillPublic":True},indent=2))
    if not args.apply:return
    retire(args.confirmation,args.asset_manifest_sha,args.history_manifest_sha)

if __name__=="__main__":main()
