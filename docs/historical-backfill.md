# Historical scorecards — acquisition, backfill, reconciliation and limits

**Status: importer written and tested on synthetic 1877–2018 fixtures; upstream production CSVs NOT downloaded or independently audited in this build environment.** The GitHub Actions job downloads both source layers on its first run and each subsequent Monday. A successful downloader execution does NOT mean the historical corpus is complete.

## Why this dataset

Duncan Golicher published research CSV snapshots of *individual international batter innings* and team innings, downloaded from ESPNcricinfo in 2017:

- <https://github.com/dgolicher/cricket/blob/master/all-innings.csv> — individual innings, original date/format/opponent/ground/runs/balls-faceds where recorded; approximately 27.5 MB
- <https://github.com/dgolicher/cricket/blob/master/all-match_innings.csv> — team innings scores; approximately 2.3 MB
- <https://github.com/dgolicher/cricket/blob/master/Downloading_cricket.Rmd> — original collection and cleaning methods
- <https://rdrr.io/github/dgolicher/crickdata/> — R package documentation describing scorecard innings, bowling figures, and Test/ODI/T20I coverage at the 2017 snapshot

This is **historical innings data, not original scanned complete match scorecards**, and the source was extracted from ESPNcricinfo. We have **not confirmed a licence** that permits reproducing or redistributing the entire source. The workflow downloads its CSVs to `.gitignore`d raw paths and publishes a limited research-derived result. Check upstream and ESPN reuse terms before publishing historical innings extracts. Source availability or terms may change.

## One scheduled pipeline (weekly)

```text
Monday 05:35 UTC (or manual workflow_dispatch)
  Cricsheet -> download current men's Test / ODI / T20I JSON ZIPs
             -> parse deliveries and bowler/innings records
  Historical -> download 2017 individual innings + team innings CSV
             -> parse scorecard-only innings, preserve uncertain fields
  Merge      -> deduplicate by (start date, format, two national teams)
             -> use Cricsheet for any modern overlapping entire match
             -> retain historical records for uncovered matches
             -> join obvious historical / Cricsheet player aliases where unique
  Analyze    -> modern bowler/situation index (delivery-only records)
             -> common-denominator historical/modern scorecard parity index
             -> modern and historical batting contributions
  Verify     -> ICC retired-career reference runs; first-year and format checks
             -> annual observed coverage; explicitly NOT official completeness
  Publish    -> commit derived statistics and serve via GitHub Pages
```

### Input schema and reasonable assumptions

The historical innings archive provides the original batter, country, opponent, format, date, score, some dismissal status and sometimes balls faced. It **does not contain authoritative batting order, ball-by-ball bowler exposures, weather, over-by-over state or pitch reports for all years**. The parser writes `position=0`, `role=unknown`, `balls=0` where unknown; historical index never uses those unavailable measurements or treats their zeros as genuine attempts.

Matching `(start date, format, two teams)` is deliberately conservative. Tests with multiple innings are grouped under one match; modern source records supersede legacy records for a whole match to prevent partial double counting. This does not distinguish genuine same-day doubleheaders with the same teams; such collisions need an authoritative match-ID register. Source records often use initials instead of full names; if an alias cannot be uniquely linked, the audit retains an independent historical ID and records the risk rather than guessing a person.

### Reconciliation against ICC records

`python -m pipeline.reconcile` independently totals the merged observed runs from each of these *completed* careers and compares with primary published totals:

| Player | Format | Official reference runs | Primary source |
|---|---|---:|---|
| Don Bradman | Tests | 6,996 | [ICC Hall of Fame](https://www.icc-cricket.com/hall-of-fame/hall-of-famers/hall-of-famer-donald-bradman) |
| Viv Richards | Tests | 8,540 | [ICC player profile](https://www.icc-cricket.com/rankings/2536/vivian-richards) |
| Viv Richards | ODIs | 6,721 | [ICC player profile](https://www.icc-cricket.com/rankings/2536/vivian-richards) |
| Sachin Tendulkar | Tests | 15,921 | [ICC player profile](https://www.icc-cricket.com/rankings/2962/sachin-tendulkar) |
| Sachin Tendulkar | ODIs | 18,426 | [ICC player profile](https://www.icc-cricket.com/rankings/2962/sachin-tendulkar) |

The report `site/data/career-reconciliation.json` and `data/coverage.md` show **actual, expected, difference, match counts and PASS/MISSING**. They are generated only after acquiring the data, never typed in as observed. A failed check means we must investigate source incompleteness, double counting, aliases, withdrawn matches, and or other reconciliation issues before making claims for that career. Even if all five pass, **complete match-level data is not certified**: a missing positive innings might cancel with a duplicate, batting averages may not reconcile, and non-selected players may remain incomplete.

### All-time indices: explicitly not certified

`scorecardParity` is a separate exploratory index that uses the same observed features for historical and modern batters: batting runs, dismissals, date, format and teammates' scoring. It uses a rolling +/-year contemporary baseline and sample shrinkage. Unlike modern `quality`, it does NOT use individual bowler exposure, batting order, wicket state or rules-adjusted scoring tempo. It should **not** be displayed as if equivalent to the Cricsheet modern-only index. The raw archive currently contains no verified official match-by-match completeness register.

**Before saying “all-time best”:** Acquire authoritative match IDs and results for every official Test/ODI/T20I, reconcile every season to included scorecards, reconcile innings/dismissals for the leading 50–100 batters, resolve historically ambiguous identities, document permission to publish derived excerpts, and run held-out/uncertainty/sensitivity analysis with fair era handling. The build deliberately sets `historicalCompletenessCertified=false` and `allTimeRankingPermitted=false` until these gates are met and explicitly implemented.

## Locally reproducing with downloadable access

```bash
python -m pipeline.ingest --download
python -m pipeline.historical --download
python -m pipeline.model
python -m pipeline.reconcile
python -m pipeline.audit
python -m pipeline.standalone
```

If historical downloading is blocked, obtain the two research CSVs from the documented repository (only if you have rights to use them) and place them at `data/raw/historical/all-innings.csv` and `data/raw/historical/all-match_innings.csv`; then use `python -m pipeline.historical` without `--download`. Do not commit or publish source CSVs.

## Failure handling and weekly refreshes

Raw source archives are fetched if not already cached; hosted GitHub Actions starts with a fresh checkout, so it refreshes sources every week. The workflow checks that the historical snapshots have records for at least one pre-1930 period, multiple historical eras, and leading retired players. If the source has vanished, the job fails rather than reporting a newly computed all-time rank from missing inputs. GitHub may skip scheduled jobs under load or disable schedules in public repositories after 60 days of inactivity; watch run history and notification settings. Historical archive itself remains **frozen at its 2017 acquisition date**; Cricsheet supplies the weekly updates for post-2001 matches. New official matches absent from Cricsheet or source snapshots may remain missing until another authorized scorecard source is added.
