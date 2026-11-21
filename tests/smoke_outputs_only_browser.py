"""Headless browser parity test against the LIVE derived-only results API.

Only a temporary local static UI is served. Chromium's localhost CORS header is
adapted in the test proxy; the live GitHub Pages origin is separately tested by
the private API smoke (and Pages predeploy check). No raw database is downloaded.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ALLOWED_HOST = re.compile(r"^[a-z0-9-]+[.]execute-api[.]us-east-2[.]amazonaws[.]com$")
ROUTES = ("overview","test","odi","t20i","test_odi","all_three",
          "compare","matches","methodology","coverage")

def run():
    api = os.environ.get("CRICKET_OUTPUTS_API_BASE","").rstrip("/")
    parsed=urlparse(api)
    if (parsed.scheme!="https" or not ALLOWED_HOST.fullmatch(parsed.hostname or "")
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("Missing/invalid approved public output-only API variable")
    src=Path("site")
    assert src.is_dir() and not (src/"data").exists(), "Source/downloadable folder present"
    with tempfile.TemporaryDirectory(prefix="cricket-browser-ui-") as temp:
        dest=Path(temp)/"site"
        shutil.copytree(src,dest)
        config=dest/"assets/config.js"
        assert 'window.CRICKET_OUTPUTS_API_BASE = "";' in config.read_text()
        config.write_text("window.CRICKET_OUTPUTS_API_BASE = "+json.dumps(api)+";\n")
        handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(dest))
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        origin=f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                context=browser.new_context(viewport={"width":1280,"height":800})
                errors=[]
                api_requests=[]
                def forward(route):
                    if not route.request.url.startswith(api+"/v1/cricket/"):
                        raise AssertionError("Browser attempted external unapproved API fetch")
                    api_requests.append(route.request.url)
                    # Staging gateway limits sustained traffic to ~3 req/s.
                    # This browser suite navigates every route rapidly; obey
                    # the actual throttle and retry only transient HTTP 429.
                    if api_requests:
                        time.sleep(0.45)
                    reply=None
                    for attempt in range(6):
                        reply=route.fetch(timeout=25000)
                        if reply.status!=429:
                            break
                        time.sleep(min(1.5*(attempt+1),5))
                    if reply.status!=200 and not ("/v1/cricket/discipline-" in route.request.url
                         and reply.status in (400,404,503)):
                        raise AssertionError("Live API failed: "+str(reply.status))
                    headers=dict(reply.headers)
                    # The real service explicitly accepts the published github.io
                    # origin, not this local preview. CORS adapted for UI-only smoke.
                    headers["access-control-allow-origin"]=origin
                    route.fulfill(response=reply,headers=headers)
                context.route(api+"/**",forward)
                page=context.new_page()
                page.on("pageerror",lambda err:errors.append(str(err)))
                page.goto(origin+"/#overview")
                page.locator(".leader").first.wait_for(timeout=25000)
                assert "Cricket Greatness" in page.title()
                assert "Single-format GOATs · Career Greatness · ICC Full Members" in page.locator("#page-body").inner_text()
                assert "Multi-format GOATs · Career Greatness · ICC Full Members" in page.locator("#page-body").inner_text()
                assert page.locator(".leader").count()==5, "Overview must show 3 single-format + 2 combined-format leaders"
                assert [x.inner_text() for x in page.locator(".leader small").all()] == [
                    "Test Cricket","One-Day Internationals","T20 Internationals",
                    "Tests + ODIs","All Three Formats"]
                full_members={"Afghanistan","Australia","Bangladesh","England",
                              "India","Ireland","New Zealand","Pakistan",
                              "South Africa","Sri Lanka","West Indies","Zimbabwe"}
                for index in range(3):
                    leader=page.locator(".leader").nth(index).inner_text()
                    assert any(country in leader for country in full_members), leader
                    assert "Career greatness" in leader
                for index in (3,4):
                    # Combined-format APIs are independently staged. If unavailable,
                    # render a clear placeholder rather than stale/wrong source data.
                    combined_card=page.locator(".leader").nth(index).inner_text()
                    assert ("Career greatness" in combined_card or
                            "No qualified or verified combined-format leader available" in combined_card)
                    if "Career greatness" in combined_card:
                        assert any(country in combined_card for country in full_members), combined_card
                checked=["overview-five-career-goat-leaders"]
                for name in ("test","odi","t20i","test_odi","all_three"):
                    page.goto(origin+"/#"+name)
                    page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                    assert page.locator("#output-metric").input_value()=="careerGreatness"
                    assert page.locator("#full-member-filter").input_value()=="all"
                    assert page.locator("#innings-min").input_value()=="0"
                    assert int(page.locator("#innings-max").input_value())>0
                    assert not page.locator("#output-results").get_by_text("Results service unavailable").count()
                    checked.append(name)
                # Filter Test batting through the exact (server-side) subset.
                page.goto(origin+"/#odi")
                page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                unfiltered_max=page.locator("#innings-max").input_value()
                page.locator("#full-member-filter").select_option("yes")
                page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                assert page.locator("#full-member-filter").input_value()=="yes"
                assert page.locator("#innings-max").input_value()==unfiltered_max
                page.locator("#innings-min").fill("1")
                page.locator("#innings-min").press("Tab")
                page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                assert page.locator("#innings-min").input_value()=="1"
                page.locator("#full-member-filter").select_option("all")
                checked.append("batting-icc-full-member-innings-filter")
                # One selector controls existing pages; no separate discipline menu.
                assert page.locator("#global-discipline").count()==1
                assert page.locator("aside [data-view='bowling']").count()==0
                for discipline in ("bowling","allrounder"):
                    page.locator("#global-discipline").select_option(discipline)
                    page.goto(origin+"/#overview")
                    page.locator(".leader").first.wait_for(timeout=25000)
                    assert "Single-format GOATs · Career Greatness · ICC Full Members" in page.locator("#page-body").inner_text()
                    assert "Multi-format GOATs · Career Greatness · ICC Full Members" in page.locator("#page-body").inner_text()
                    assert page.locator(".leader").count()==5
                    for index in range(3):
                        leader=page.locator(".leader").nth(index).inner_text()
                        assert any(country in leader for country in full_members), (discipline,leader)
                        assert "Career greatness" in leader
                    for index in (3,4):
                        combined_card=page.locator(".leader").nth(index).inner_text()
                        assert ("Career greatness" in combined_card or
                                "No qualified or verified combined-format leader available" in combined_card)
                        if "Career greatness" in combined_card:
                            assert any(country in combined_card for country in full_members), (discipline,combined_card)
                    checked.append(discipline+"-five-career-goat-leaders")
                    for fmt in ("test","odi","t20i"):
                        page.goto(origin+"/#"+fmt)
                        page.locator("#discipline-results tbody tr").first.wait_for(timeout=25000)
                        assert page.locator("#discipline-metric").input_value()=="career"
                        assert page.locator("#full-member-filter").count()==1
                        assert page.locator("#innings-low").count()==1
                        assert page.locator("#innings-high").count()==1
                        if fmt=="odi":
                            page.locator("#full-member-filter").select_option("yes")
                            page.locator("#discipline-results tbody tr").first.wait_for(timeout=25000)
                            assert page.locator("#full-member-filter").input_value()=="yes"
                            page.locator("#full-member-filter").select_option("all")
                            page.locator("#discipline-results tbody tr").first.wait_for(timeout=25000)
                            checked.append(discipline+"-icc-filter")
                        page.locator("[data-discipline-player]").first.click()
                        page.locator("#discipline-profile h3").wait_for(timeout=20000)
                        checked.append(discipline+"-"+fmt)
                    # Combined-format APIs are upgraded separately; the client
                    # must render either derived rankings or a truthful error.
                    for fmt in ("test_odi","all_three"):
                        page.goto(origin+"/#"+fmt)
                        page.locator("#discipline-results").wait_for(timeout=15000)
                        page.wait_for_function("""() => {
                          const el=document.querySelector('#discipline-results');
                          return el && !el.textContent.includes('Loading ranking results');
                        }""",timeout=25000)
                        checked.append(discipline+"-"+fmt+"-page")
                    page.goto(origin+"/#compare")
                    page.locator("#compare-player-first option").nth(1).wait_for(state="attached",timeout=20000)
                    page.locator("#compare-player-first").select_option(index=1)
                    page.locator("#compare-first-result h3").wait_for(timeout=20000)
                    page.locator("#compare-player-second option").nth(1).wait_for(state="attached",timeout=20000)
                    page.locator("#compare-player-second").select_option(index=1)
                    page.locator("#compare-second-result h3").wait_for(timeout=20000)
                    checked.append(discipline+"-comparison")
                    page.goto(origin+"/#methodology")
                    methodology=page.locator("#page-body").inner_text()
                    assert discipline in methodology.lower().replace("-","")
                    assert "Private all-era research" in methodology
                    assert "195,226" in methodology
                    assert "Career" in methodology and "JAWS" in methodology
                    if discipline=="bowling":
                        assert "Wickets above expectation" in methodology
                        assert "Runs prevented" in methodology or "runs prevented" in methodology
                    else:
                        assert "harmonic mean" in methodology
                        assert "three matching dated" in methodology
                    page.goto(origin+"/#coverage")
                    page.locator("#page-body .section").first.wait_for(timeout=20000)
                    coverage=page.locator("#page-body").inner_text()
                    assert "Private all-era research" in coverage
                    assert "not live player profiles" in coverage
                    assert "195,226" in coverage
                    checked.append(discipline+"-historical-methodology-and-coverage")
                    page.goto(origin+"/#matches")
                    page.locator("#match-results").wait_for(timeout=15000)
                    page.wait_for_function("""() => {
                      const el=document.querySelector('#match-results');
                      return el && !el.textContent.includes('Loading…');
                    }""",timeout=25000)
                    message=page.locator("#match-results").inner_text()
                    if "match-summary API is still being staged" in message:
                        checked.append(discipline+"-match-staging-pending")
                    else:
                        page.locator("[data-discipline-match]").first.wait_for(timeout=20000)
                        page.locator("[data-discipline-match]").first.click()
                        page.locator("#match-detail h3").wait_for(timeout=20000)
                        checked.append(discipline+"-match-detail")
                    checked.append(discipline+"-coverage-methodology-explorer")
                page.locator("#global-discipline").select_option("batting")
                page.goto(origin+"/#test")
                page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                page.locator("[data-player]").first.click()
                page.locator("#output-profile h3").wait_for(timeout=20000)
                checked.append("player-profile")
                page.goto(origin+"/#compare")
                page.locator("#compare-player-first option").nth(1).wait_for(state="attached",timeout=20000)
                page.locator("#compare-player-first").select_option(index=1)
                page.locator("#compare-first-result h3").wait_for(timeout=20000)
                page.locator("#compare-player-second option").nth(1).wait_for(state="attached",timeout=20000)
                page.locator("#compare-player-second").select_option(index=1)
                page.locator("#compare-second-result h3").wait_for(timeout=20000)
                checked.append("batting-comparison")
                page.goto(origin+"/#matches")
                page.locator("#match-results tbody tr").first.wait_for(timeout=20000)
                page.locator("[data-match-innings]").first.click()
                page.get_by_text("Selected innings:",exact=False).first.wait_for(timeout=20000)
                checked.append("match-explorer-and-innings")
                for name in ("methodology","coverage"):
                    page.goto(origin+"/#"+name)
                    page.locator("#page-body .section").first.wait_for(timeout=20000)
                    checked.append(name)
                mobile=browser.new_context(viewport={"width":390,"height":844},
                                           is_mobile=True,has_touch=True)
                mobile.route(api+"/**",forward)
                mp=mobile.new_page()
                mp.on("pageerror",lambda err:errors.append(str(err)))
                mp.goto(origin+"/#overview")
                mp.locator(".leader").first.wait_for(timeout=25000)
                mp.locator("#menu-button").click()
                assert "open" in (mp.locator("#sidebar").get_attribute("class") or "")
                checked.append("mobile-navigation")
                assert not errors,errors
                assert len(api_requests)>=10,len(api_requests)
                assert all("/v1/cricket/" in url for url in api_requests)
                browser.close()
                print(json.dumps({"status":"BROWSER_CUTOVER_SMOKE_PASS",
                    "routesAndInteractions":checked,"boundedAPIRequests":len(api_requests),
                    "apiOrigin":api,"staticAssetsOnly":True},indent=2))
        finally:
            server.shutdown()
            server.server_close()

if __name__=="__main__":
    run()
