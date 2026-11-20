"""Deterministic browser contract for the three-discipline source-free UI.

All API responses are synthetic bounded fixtures intercepted in the browser.
Real Cricsheet data, AWS S3, and the live staging API are NOT touched by
this test; a separate private GitHub workflow verifies real API post-release.
"""
from __future__ import annotations
import functools
import http.server
import json
import shutil
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

from playwright.sync_api import sync_playwright

FORMATS=("test","odi","t20i","test_odi","all_three")
DISCIPLINES=("bowling","allrounder")
API="https://abc123.execute-api.us-east-2.amazonaws.com"
PLAYERS=[
 {"playerId":"p_"+"a"*24,"name":"Sample Player One","team":"India",
  "innings":75,"runs":3000,"wickets":97,"greatness":88.6,
  "quality":90.1,"career":92.2,"peak":84.5,"batting":82.1,"bowling":91.2,
  "jawsPercentile":89.6,"teamCarry":75.4,"careerGreatness":91.3,"peakQuality":87.9,
  "bowlingAverage":26.1,"strikeRate":42.0,
  "opponentEvidencePct":67.5,"referenceEvidencePct":94.5},
 {"playerId":"p_"+"b"*24,"name":"Sample Player Two","team":"Australia",
  "innings":65,"runs":2850,"wickets":78,"greatness":85.4,
  "quality":89.0,"career":88.7,"peak":83.8,"batting":85.8,"bowling":82.8,
  "jawsPercentile":88.2,"teamCarry":71.6,"careerGreatness":87.6,"peakQuality":86.1,
  "bowlingAverage":28.0,"strikeRate":44.0,
  "opponentEvidencePct":59.1,"referenceEvidencePct":91.0}
]
MATCH={
 "matchId":"m_"+"c"*24,"date":"2026-01-20",
 "playerId":PLAYERS[0]["playerId"],"name":PLAYERS[0]["name"],
 "team":"India","opposition":"Australia","runs":35,"balls":31,
 "wickets":3,"bowlingBalls":48,"runsConceded":31
}
OLD_MATCH={
 "i":"odi:sample:1","p":"old-player","d":"2026-01-20",
 "n":"Sample Player One","o":"Australia","r":35,"b":31
}
STATS={f:{"qualifiedPlayers":2,"observedDistinctMatches":80} for f in FORMATS}
META={
 "schemaVersion":"cricket-results-v1",
 "formats":STATS,"coverage":{"formats":{f:{"observedMatches":80} for f in FORMATS}},
 "leaders":{f:[dict(PLAYERS[0])] for f in FORMATS}
}
DISC_META={
 "schemaVersion":"cricket-discipline-projection-v1",
 "disciplines":list(DISCIPLINES),
 "formats":{d:{f:{"qualifiedPlayers":2,"allTimeCertified":False}
                for f in FORMATS} for d in DISCIPLINES},
 "leaders":{d:{f:[dict(PLAYERS[0])] for f in FORMATS} for d in DISCIPLINES},
 "historicalRestrictedSourcesIncluded":False
}

def mock_response(route):
    url=urlsplit(route.request.url)
    if url.scheme!="https" or url.netloc!="abc123.execute-api.us-east-2.amazonaws.com":
        raise AssertionError("Unapproved browser API host "+url.netloc)
    if not url.path.startswith("/v1/cricket/"):
        raise AssertionError("Unapproved API route "+url.path)
    path=url.path.split("/v1/cricket/",1)[1]
    q={k:v[0] for k,v in parse_qs(url.query).items()}
    fmt=q.get("format","test")
    disc=q.get("discipline","bowling")
    if path=="bootstrap":value=META
    elif path=="disciplines":value=DISC_META
    elif path in ("rankings","discipline-rankings"):
        search=q.get("search","").casefold()
        country=q.get("country","")
        players=[dict(x) for x in PLAYERS
                 if (not search or search in x["name"].casefold()
                     or search in x["team"].casefold())
                 and (not country or x["team"]==country)]
        value={"schemaVersion":"cricket-discipline-projection-v1"
              if path=="discipline-rankings" else "cricket-results-v1",
               "discipline":disc,"format":fmt,"page":int(q.get("page","0")),
               "pageSize":40,"total":len(players),"items":players,
               "allTimeCertified":False}
    elif path in ("player","discipline-player"):
        found=next((dict(x) for x in PLAYERS
                    if x["playerId"]==q.get("playerId")),None)
        if found and fmt in ("test_odi","all_three"):
            found["formatBreakdown"]=[{"format":f,"greatness":88.0,
              "formatGreatnessPercentile":86.0,"innings":36,
              "wickets":45,"runs":1100}
              for f in (("test","odi") if fmt=="test_odi"
                        else ("test","odi","t20i"))]
        value={"player":found}
    elif path=="matches":
        value={"schemaVersion":"cricket-explorer-v1",
               "page":0,"pageSize":65,"total":1,"items":[OLD_MATCH]}
    elif path=="innings":
        value={"selected":OLD_MATCH,"teammates":[OLD_MATCH]}
    elif path=="discipline-matches":
        value={"schemaVersion":"cricket-discipline-matches-v1",
               "discipline":disc,"format":fmt,
               "page":0,"pageSize":40,"total":1,"items":[MATCH],
               "modernCricsheetOnly":True}
    elif path=="discipline-innings":
        value={"schemaVersion":"cricket-discipline-matches-v1",
               "selected":MATCH,"discipline":disc,"format":fmt}
    else:raise AssertionError("Unexpected or unsafe browser API route "+path)
    route.fulfill(status=200,
       headers={"content-type":"application/json",
                "access-control-allow-origin":"*"},
       body=json.dumps(value))

def run():
    src=Path("site")
    assert src.is_dir() and not (src/"data").exists()
    with tempfile.TemporaryDirectory(prefix="cricket-ui-mock-") as tmp:
        dest=Path(tmp)/"site"
        shutil.copytree(src,dest)
        config=dest/"assets/config.js"
        assert 'window.CRICKET_OUTPUTS_API_BASE = "";' in config.read_text()
        config.write_text("window.CRICKET_OUTPUTS_API_BASE = "+json.dumps(API)+";\n")
        handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(dest))
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        origin=f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True)
                context=browser.new_context(viewport={"width":1280,"height":800})
                context.route(API+"/**",mock_response)
                page=context.new_page()
                errors=[]
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.goto(origin+"/#overview")
                page.locator(".leader").first.wait_for(timeout=10000)
                assert page.locator('#sidebar [data-view="bowling"]').count()==0
                assert page.locator("#discipline-selector option").count()==3
                assert "Player Comparison" in page.locator('#navigation [data-view="compare"]').inner_text()
                checked=[]
                for discipline in ("batting","bowling","allrounder"):
                    page.locator("#discipline-selector").select_option(discipline)
                    page.goto(origin+"/#overview")
                    page.locator(".leader").first.wait_for(timeout=10000)
                    for fmt in FORMATS:
                        page.goto(origin+"/#"+fmt)
                        result=("#output-results" if discipline=="batting"
                                else "#discipline-results")
                        page.locator(result+" tbody tr").first.wait_for(timeout=10000)
                        if fmt=="all_three" and discipline!="batting":
                            page.locator("[data-discipline-player]").first.click()
                            page.locator("#discipline-profile .player-card").wait_for(timeout=10000)
                            assert page.get_by_text("Format-by-format context").count()
                        checked.append(discipline+"-"+fmt)
                    page.goto(origin+"/#compare")
                    page.locator("#compare-search").fill("Sample")
                    page.locator('#compare-hits [data-compare-id]').first.wait_for(timeout=10000)
                    assert page.locator("#compare-discipline").input_value()==discipline
                    page.locator("#compare-first-select").select_option(PLAYERS[0]["playerId"])
                    page.locator("#compare-first-result h3").wait_for(timeout=10000)
                    page.locator("#compare-second-select").select_option(PLAYERS[1]["playerId"])
                    page.locator("#compare-second-result h3").wait_for(timeout=10000)
                    checked.append(discipline+"-comparison")
                    page.goto(origin+"/#matches")
                    area=("#match-results" if discipline=="batting"
                          else "#discipline-match-results")
                    page.locator(area+" tbody tr").first.wait_for(timeout=10000)
                    if discipline=="batting":
                        page.locator("[data-match-innings]").first.click()
                        page.get_by_text("Selected innings:",exact=False).wait_for(timeout=10000)
                    else:
                        page.locator("[data-discipline-match-id]").first.click()
                        page.locator("#discipline-match-detail .section").first.wait_for(timeout=10000)
                    checked.append(discipline+"-matches")
                    for view in ("methodology","coverage"):
                        page.goto(origin+"/#"+view)
                        page.locator("#page-body .section").first.wait_for(timeout=10000)
                        checked.append(discipline+"-"+view)
                mobile=browser.new_context(viewport={"width":390,"height":844},
                    is_mobile=True,has_touch=True)
                mobile.route(API+"/**",mock_response)
                mp=mobile.new_page()
                mp.on("pageerror",lambda error:errors.append(str(error)))
                mp.goto(origin+"/#overview")
                mp.locator(".leader").first.wait_for(timeout=10000)
                mp.locator("#menu-button").click()
                assert "open" in mp.locator("#sidebar").get_attribute("class")
                assert not errors,errors
                browser.close()
                print(json.dumps({"status":"CRICKET_UNIFIED_UI_MOCK_PASS",
                    "routes":checked,"mobileNavigation":True,
                    "realAWSRequests":0,"sourceDatabasePublished":False},sort_keys=True))
        finally:
            server.shutdown()
            server.server_close()

if __name__=="__main__":run()
