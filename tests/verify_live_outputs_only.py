"""Check the ACTUAL public GitHub Pages release has no downloadable source data.

Does not fetch source databases: for old file URLs it only checks the HTTP status,
and aborts if a server unexpectedly responds HTTP 200.
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request

ROOT="https://randomquestions-projects.github.io/cricket-greatness-index/"
API="https://kwrvxk313g.execute-api.us-east-2.amazonaws.com"
OLD_DOWNLOADS=(
    "data/innings.json.gz",
    "data/test-greatness.json",
    "data/odi-greatness.json",
    "data/t20i-greatness.json",
    "data/greatness-combined.json",
    "data/career-reconciliation.json",
    "data/coverage-status.json",
)
def response(path,method="GET"):
    req=urllib.request.Request(ROOT+path,method=method,headers={
       "Cache-Control":"no-cache","User-Agent":"cricket-output-only-release-validator/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=20) as resp:
            if resp.status!=200:raise AssertionError(f"{path}: HTTP {resp.status}")
            return resp.status,resp.read(240_000)
    except urllib.error.HTTPError as err:
        return err.code,b""

def main():
    homepage,html=response("")
    assert homepage==200 and b"assets/config.js" in html and b"assets/app.js" in html
    config_code,config=response("assets/config.js")
    assert config_code==200 and API.encode() in config
    assert b"AWS_ACCESS_KEY" not in config and b"rq-analytics-master-" not in config
    app_code,app=response("assets/app.js")
    assert app_code==200 and b"CRICKET_OUTPUTS_API_BASE" in app
    assert b"data/innings.json.gz" not in app
    failures={}
    status_report={}
    for file in OLD_DOWNLOADS:
        status,_=response(file,method="HEAD")
        if status==503:
            # GitHub Pages edge can reject HEAD. Test GET without reading any
            # response body, so no source file is downloaded by this test.
            for attempt in range(3):
                request=urllib.request.Request(ROOT+file,method="GET",headers={
                    "Cache-Control":"no-cache","Range":"bytes=0-0",
                    "User-Agent":"cricket-output-only-release-validator/1.0"})
                try:
                    with urllib.request.urlopen(request,timeout=20) as resp:
                        status=resp.status
                except urllib.error.HTTPError as err:
                    status=err.code
                if status!=503:break
                time.sleep(2)
        status_report[file]=status
        if status!=404:failures[file]=status
    print("Old public download status verification:",json.dumps(status_report,sort_keys=True))
    assert not failures, f"Legacy source downloads still accessible or unexpected statuses: {failures}"
    print(json.dumps({
       "status":"PUBLIC_CRICKET_PAGES_OUTPUTS_ONLY_VERIFIED",
       "homepageHTTP":homepage,
       "publicConfigAPIOriginMatches":True,
       "publicAppScriptHTTP":app_code,
       "oldDownloadURLsHTTP404":len(OLD_DOWNLOADS),
       "scope":"Current GitHub Pages release ONLY; past GitHub Releases and commit history are not retired"
    },indent=2))

if __name__=="__main__":main()
