# Cricket Greatness Lab · independent international batting research

> **2026-11-09 MASTER DATA MILESTONE — OPEN WAREHOUSE LIVE.** The source-first cricket master warehouse is now published separately from the batting website. The verified first version contains **23,241 Cricsheet matches, 11,739,488 delivery events and 358,978 wicket events**, across men's and women's internationals, domestic, and franchise formats. Original open-licensed archive + six reusable SQLite gender/decade partitions: [GitHub Release](https://github.com/randomquestions-projects/cricket-greatness-index/releases/tag/cricket-master-2026-11-09-42707561618). [Warehouse quick start](warehouse/QUICKSTART.md) · [Source match-number gap audit](warehouse/audits/match_inventory.json). **This does NOT certify complete historical or official match coverage.** The older batting section below describes the legacy site pipeline; it is not the source-of-truth warehouse.


**Built from scratch. This project does not import Claude's rankings, reference HTML or any fabricated score.**

Goal: rank international cricket batters in Tests, ODIs, T20Is, Tests+ODIs and all three formats, while distinguishing (1) quality, (2) team carry and (3) career greatness. Match-level records are the unit of evidence. All reported values are computed from supplied original source data.

## Important status — November 2026

**This is a new independent project; no scores or charts were transplanted from Claude's HTML.** The code for both historical scorecard innings and modern delivery-level matches is implemented and passes synthetic-data tests. The full source archives have **not** been retrieved or independently analyzed in this build environment (external download hosts are inaccessible here), so the supplied website starts **without batting rankings**. A first GitHub Actions run now fetches **BOTH** source layers and computes both separate indices. It is not a certified *complete all-time* analysis yet.

### What the one GitHub run now does

| Layer | Source | Date span | Acquisition | What it can measure |
|---|---|---|---|---|
| Historical scorecard innings | [Duncan Golicher's 2017 ESPNcricinfo-derived international innings snapshot](https://github.com/dgolicher/cricket) | Intended to cover historical Tests, ODIs and T20Is up to 2017; **exact beginning and completeness need audit** | `python -m pipeline.historical --download` runs automatically | Batter runs, dismissals, same-innings teammate scoring, opponent, date, broad era |
| Modern delivery records | [Cricsheet](https://cricsheet.org/downloads/) | Since roughly 2001 Tests, 2002 ODIs, 2005 T20Is, through its latest published archive | `python -m pipeline.ingest --download` runs automatically | Measured balls, bowling exposures, batting position, match-level scoring context |
| Merged ledger | Historical + Cricsheet, modern match wins on overlaps | Earliest imported historical date through current Cricsheet release | Automatically in `pipeline.model` | One non-double-counted innings ledger plus source and identity flags |
| Retired-career validation | Published ICC career totals | Bradman, Richards and Tendulkar | `python -m pipeline.reconcile` runs automatically | Observed-vs-official run totals with clear discrepancies |

**Historical does not mean complete.** The 2017 snapshot is not guaranteed to contain every historical match, reliable batting orders, or full balls-faced data. There is not yet an independent official match-by-match ID census, and the licence to redistribute the original ESPN-derived scorecards has not been verified. Source presence, matching career runs, and historical-year counts are **necessary but insufficient** evidence for all-time completeness. The UI will say **not certified**, not declare a definitive all-time winner.

A weekly automated workflow is already configured for **Mondays at 05:35 UTC** and refreshes both source layers. The 2017 historical snapshot itself is fixed; adding newly uncovered historical scorecards would require another permitted source. GitHub may delay/skip runs and may disable scheduled workflows on public repositories after 60 days of inactivity. Monitor Actions and configure failure notification if ongoing operation matters.

Details: [`docs/historical-backfill.md`](docs/historical-backfill.md), `docs/methodology.md`, `docs/sources.md`.

## GitHub Pages setup (recommended)

1. Create a **new public GitHub repository**, for example `cricket-greatness-lab`.
2. Upload the CONTENTS of this project folder, including `.github/workflows` (uploading a folder inside another folder changes page paths).
3. In **Settings → Pages**, set **Build and deployment / Source: GitHub Actions**.
4. Navigate to **Actions → Refresh international cricket records → Run workflow**. The workflow runs tests, downloads both Cricsheet deliveries and the documented historical innings snapshot, merges them without duplicated matches, computes both models, checks historic career totals, commits derived `site/data` JSON (not raw source CSV/ZIP), and publishes the site through the follow-on deployment workflow.
5. GitHub will provide the Pages URL in the deployment output. The data refresh also runs weekly, subject to GitHub Actions restrictions and any source availability changes.

If GitHub Actions needs enabling or write permissions, enable Actions and grant workflow `contents: write` (workflow declaration already requests this permission). It may take time for the first import because every original match must be parsed. The workflow fails rather than showing a false “successful” build if historical source records or modern match records do not meet minimum integrity gates.

## Run locally (Python 3.10+; no third-party packages required)

```bash
python -m unittest discover -s tests -v
python -m pipeline.ingest --download
python -m pipeline.historical --download
python -m pipeline.model
python -m pipeline.reconcile
python -m pipeline.audit
python -m pipeline.standalone
python -m http.server 8000 -d site
```

Open `http://localhost:8000`. To create a one-file shareable site after ingestion, use `site/standalone.html` (includes main dashboards and a curated set of full-career match records for comparison; the full innings explorer works best when hosted alongside the generated data files).

If auto-download is blocked, download from [Cricsheet](https://cricsheet.org/downloads/) in your own browser and put the three men's international ZIPs in `data/raw`: `tests_male_json.zip`, `odis_male_json.zip`, and `t20s_male_json.zip`. If historical downloads are unavailable, also download `all-innings.csv` and `all-match_innings.csv` into `data/raw/historical/` from the documented historical repository (subject to source permissions) and call `python -m pipeline.historical` without `--download`. **Never substitute mock data as production research.**

## What the model currently implements

| Layer | Derived from | Status |
|---|---|---|
| Scorecards & player identity | Cricsheet JSON, registry IDs in each source file | Implemented, source-download required |
| Modern batting quality | Runs and dismissals, contemporary format/year/role peers, bowler difficulty, match conditions | Implemented, retrospective provisional model |
| Team carry | Runs and model residuals versus same-innings teammates | Implemented, descriptive |
| Career greatness | Quality + effective innings volume + cumulative above-expectation runs | Implemented, sensitivity required |
| Home / away / India / SENA | Ground city, team and host country | Implemented with known mapping gaps |
| Same age / same innings | Match-level innings with date of birth where verified | Implemented for curated DOB list; coverage incomplete |
| Match explorer | Complete match-id-linked batter innings ledger | Implemented after ingestion |
| Tests + ODIs / all three | Equal-format geometric mean; qualification requires all formats | Implemented for observed modern data |
| Historical scorecard parity | Duncan Golicher 2017 scorecard-innings backfill, deduplicated with Cricsheet | **Automatically downloaded on GitHub first run**, experimental model; completeness NOT verified |
| True all-time, age- and bowler-matched conclusions | Validated match-complete historical scorecards, robust pitch/attack controls | **Not yet established** |
| Win-probability or causal score | Full state-level run/wicket forecasts and counterfactual models | Roadmap |

## Analysis details

The script `pipeline/model.py` contains actual equations and values. Current run/survival weights: Test 0.32/0.68, ODI 0.58/0.42, T20I 0.78/0.22. Weights are **explicit design assumptions**, not empirically optimized. Rankings shrink small samples, include a match-block conditional 90% bootstrap interval, and the website can change the weighting in sensitivity mode. Bowling attack skill comes from the bowling ledger of nearby years. Match effect uses other batters from the match only when both teams and sufficient balls are observed.

Data movement:

```
Cricsheet original ZIPs (ODC-BY) → pipeline.ingest → modern innings & bowling
Historical 2017 scorecard CSVs (reuse terms unconfirmed) → pipeline.historical → historical innings
  → pipeline.model (deduplicate, score independent modern & scorecard parity indices)
  → pipeline.reconcile (ICC career runs check)
  → pipeline.audit (historical season and match coverage)
  → site/data/report.json + focus-innings.json + innings.csv.gz + innings.json.gz
  → static GitHub Pages research site
```

Raw ZIPs are **gitignored**. Derived batters' observed statistical records are published with source attribution. Historical scorecard CSV input is ignored by default to avoid republishing material without appropriate rights.

## Files

- `pipeline/ingest.py` parse modern international JSON delivery by delivery, source lineage, extras, wickets and batting order
- `pipeline/historical.py` download/normalize independent historical international batting-innings and team-innings records
- `pipeline/reconcile.py` check complete retired-career observed runs against ICC reference totals
- `pipeline/model.py` independently computed provisional indices, eligibility, research slices, comparison ledger, historical parity extension
- `pipeline/audit.py` full audit output by format and archive checksums
- `pipeline/standalone.py` build optional one-file HTML
- `tests/test_pipeline.py`, `tests/test_historical.py` test delivery parsing, historical innings, matching, duplicate suppression and missingness with **synthetic** data (never published as observations)
- `site/index.html`, `site/assets/app.js`, `site/assets/styles.css` GitHub Pages interface
- `site/data/` derived results written by Actions after first successful full build
- `docs/methodology.md`, `docs/sources.md`, `docs/roadmap.md` research specification and extension plan

## Crediting original data

Data: **Cricsheet.org**, ODC-BY 1.0 ([Cricsheet licence](https://cricsheet.org/licensing/)). Cricsheet has no relationship with this site and does not endorse it. Original player and match records have not been manually altered to fit any favored player narrative.
