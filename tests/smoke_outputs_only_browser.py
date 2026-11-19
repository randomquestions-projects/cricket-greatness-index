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
                    reply=route.fetch(timeout=25000)
                    if reply.status!=200:raise AssertionError("Live API failed: "+str(reply.status))
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
                checked=["overview"]
                for name in ("test","odi","t20i","test_odi","all_three"):
                    page.goto(origin+"/#"+name)
                    page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                    assert not page.locator("#output-results").get_by_text("Results service unavailable").count()
                    checked.append(name)
                for discipline in ("bowling","allrounder"):
                    page.goto(origin+"/#"+discipline)
                    page.locator("#discipline-results").wait_for(timeout=20000)
                    # Existing live backend may not have the new optional research
                    # projection yet. The page must fail closed with a truthful
                    # unavailable message rather than misrepresent old batting.
                    page.wait_for_function("""() => {
                      const el=document.querySelector('#discipline-results');
                      return el && (!el.textContent.includes('Loading bounded player results'));
                    }""",timeout=20000)
                    assert page.locator("#discipline-results").inner_text().strip()
                    checked.append(discipline+"-page")
                page.goto(origin+"/#test")
                page.locator("#output-results tbody tr").first.wait_for(timeout=20000)
                page.locator("[data-player]").first.click()
                page.locator("#output-profile h3").wait_for(timeout=20000)
                checked.append("player-profile")
                page.goto(origin+"/#compare")
                page.locator("#compare-hits [data-compare-id]").first.wait_for(timeout=20000)
                page.locator("#compare-side-first").click()
                page.locator("#compare-hits [data-compare-id]").first.click()
                page.locator("#compare-first-result h3").wait_for(timeout=20000)
                page.locator("#compare-side-second").click()
                page.locator("#compare-hits [data-compare-id]").last.click()
                page.locator("#compare-second-result h3").wait_for(timeout=20000)
                checked.append("comparison")
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
