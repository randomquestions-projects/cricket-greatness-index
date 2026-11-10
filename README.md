# Cricket Greatness Lab

**One independent cricket batting research platform. One public analytical model. One website.**

[Visit the live analytics website](https://randomquestions-projects.github.io/cricket-greatness-index/) · [Current model and limitations](docs/format-greatness-methodology.md) · [Open Cricket Master data warehouse](warehouse/QUICKSTART.md)

## What the platform does

Compare men's international batters across the sport's history using a common **scorecard-era model** for Test cricket, ODIs and T20Is. The interface is one responsive web app (`site/index.html` + `site/assets/app.js` + `site/assets/styles.css`) with exactly one menu and ten views.

| Public view | Purpose | Data / score source |
|---|---|---|
| Overview | Introduce the three measurements and show comparable format leaders | `*-greatness.json` only |
| Tests | Era-adjusted Test batting research | `test-greatness.json` |
| ODIs | Era-adjusted ODI batting research | `odi-greatness.json` |
| T20Is | Era-adjusted T20I batting research | `t20i-greatness.json` |
| Tests + ODIs | Equal-weight format-percentile greatness | `greatness-combined.json` |
| All three formats | Eligible all-format greatness; no imputed T20I scores for pre-T20I legends | `greatness-combined.json` |
| Batter comparison | Two-player context, opposition, home/away, team carry, JAWS and sensitivity | Same public player aggregates |
| Match explorer | Search actual source-backed modern player innings | Licensed Cricsheet-only `innings.json.gz` |
| Methodology | Formula and contextual limitations | Shared v0.4 documentation |
| Data & coverage | Historical/modern match census, career audits, source rights | `coverage-status.json`, `career-reconciliation.json` |

**No v0.1 or v0.2 rankings are displayed on the website.** The old modern-only rankings, separate legacy Test page, duplicate scripts and multiple serialized public rankings have been removed. Old page URLs redirect into the unified interface, preserving links.

## The statistical foundation

All eras use **the same observable scorecard inputs**: batter runs, dismissals, teammates, match identity, date/year, opposing nation and known venue host. Modern-only delivery statistics may inform future secondary research but never automatically improve someone's all-era primary ranking.

There are **three main lenses**:

1. **Era-adjusted quality** — context-adjusted run production and dismissal survival relative to other batters of the period. Opponent, home/away and same-match scoring are cautiously shrunken *proxies*.
2. **Team carry** — within each innings, compare runs with other teammates rather than automatically rewarding a large score in a high-scoring game.
3. **Peak vs career** — both career quality/volume and best rolling 25-innings quality, plus a JAWS-inspired `(career surplus + seven best annual surpluses)/2` measure. The latter is **not baseball WAR** and remains biased by different historical match opportunities.

Combined Test + ODI and all-three rankings use **equal-weight within-format percentiles**, subject to qualification in each included format. A player who retired before T20Is existed is **not assigned zero**.

Qualifying sample as of November 2026: **809 Test**, **706 ODI**, **733 T20I**, **384 Test+ODI**, **101 all-three** batters. These are actual computed study outputs, not official career-census certifications.

**Do not interpret these experimental rankings as a definitive verdict.** Source completeness, individual historical bowler exposure, pitch measurement, exact batting order, some venue data, historical scheduling, and opportunity-adjusted JAWS require additional validation. Conditional match-bootstrap intervals for quality and carry are not full uncertainty intervals for cross-era greatness.

## Data architecture

```text
Rights-cleared original Cricsheet archives ─────────┐
                                                      ├─ pipeline/ledger.py ──┐
2017 historical batting research (restricted) ───────┘                        │
                                                                               ├─ pipeline/format_greatness.py
                                                                               │  ├─ test-greatness.json
                                                                               │  ├─ odi-greatness.json
                                                                               │  ├─ t20i-greatness.json
                                                                               │  └─ greatness-combined.json
                                                                               │
                   pipeline/reconcile.py ◄────────── merged innings ledger ──────┤
                   pipeline/audit.py     ◄───────────────────────────────────────┤
                                                                               │
Licensed Cricsheet modern innings ─────────────── pipeline/publication.py       │
                                                 └─ innings.json.gz             │
                                                                               ▼
                                    site/index.html + assets/app.js + styles.css
```

The warehouse under `warehouse/` is a *separate, reusable open-data foundation* with a public Cricsheet snapshot, licensed SQLite shards and original event preservation. The public batting research site does not redistribute the older ESPN-derived historical innings, whose licensing remains unverified.

**Publication rights:** [Cricsheet licensing](https://cricsheet.org/licensing/) permits attribution-based use; the historical 2017 source is a separate research input whose original bulk redistribution terms require review. We therefore publish only aggregated historical model results, not original historical individual innings or scorecards. Avoid assuming public visibility grants redistribution rights.

## Refresh and maintenance

`.github/workflows/refresh-data.yml` runs weekly on Mondays at 05:35 UTC and can be triggered manually from GitHub Actions. It:

1. Tests the source ingestion and unified models.
2. Refreshes the published Cricsheet international match archive and the fixed 2017 historical research source.
3. Recomputes the **single v0.4** Test/ODI/T20I and combined metrics.
4. Updates career-reference reconciliation, independent *observed-match* coverage audit and licensed modern match-explorer data.
5. Fails if any legacy rank report, duplicate site output or unverified historical individual record was published.
6. Publishes the validated derived artifacts for GitHub Pages to deploy.

Scheduled GitHub Actions execution is best-effort, not a guaranteed hourly/live feed. Old Git commit history and released data remain available for audit, even though unused legacy outputs are no longer served.

## Source code

- `pipeline/ingest.py`, `pipeline/historical.py`: ingest the two permitted research input types.
- `pipeline/ledger.py`: deduplicated, normalized player and match ledger, without a ranking.
- `pipeline/scorecard_model.py`: the **single** parameterized per-format scorecard-era quality/carry/peak/JAWS implementation (the filename reflects the original Test pilot).
- `pipeline/format_greatness.py`: generate the three format datasets and normalize multi-format percentiles.
- `pipeline/publication.py`: licensed modern-only match explorer.
- `pipeline/reconcile.py`, `pipeline/audit.py`: career totals and source quality.
- `site/index.html`, `site/assets/app.js`, `site/assets/styles.css`: the **single public app**.
- `tests/`: synthetic and integration regressions; `tests/site_smoke.mjs` loads actual published JSON in a browser-like test.
- `warehouse/`: durable open-licensed cross-competition cricket data and its separate source/provenance reports.

See [comprehensive v0.4 methodology](docs/format-greatness-methodology.md) and [scorecard completeness report](warehouse/SCORECARD_STATUS.md).

**Historical batting records are extensive but are not independently certified complete match scorecards.** No restricted commercial scorecard site has been bulk scraped to fill the remaining gaps.
