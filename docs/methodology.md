# Batting greatness methodology (research version 0.2)

**Scope:** men's international Tests, ODIs, T20Is. Women's cricket is a planned separate comparator cohort with its own exposure and era baselines. Domestic/IPL matches may inform bowling skill later but are NOT added to international batting totals.

## Why three indices instead of one

1. **Quality:** Runs and wicket survival in the context of what comparable batters could be expected to achieve. `index=100` is contextual parity, NOT a percentile or hypothetical win probability.
2. **Team carry:** How a batter performed relative to the *other actual batters in the same innings*, after comparing everyone to expected runs. Complement it with team run share, performances when top order collapsed and runs above par. A high share is not necessarily a causal impact.
3. **Career greatness:** Explicitly values sustained excellence and cumulative runs above par. Peak ratings and era dominance are distinct further metrics.

## Observation and identity

One row = one batter appearing in an official international innings. Ball event parsing uses `runs.batter` (runs credited to bat), no wide counted as a ball faced, no-balls count as faced, separate extras and team total, the named dismissed player, and an explicit wicket taxonomy. Run outs on the non-striker do not incorrectly count as a dismissal of the striker. Super-overs and forfeited innings do not affect official career aggregate calculations. Cricsheet's per-match player registry IDs are preserved; abbreviations map to readable names for site display, not for primary identity.

A match is identified by format and original archive file stem. Original filenames, source and archive SHA256 are retained. All observed innings can be retrieved from the generated `innings.csv.gz` or `innings.json.gz`.

## Reference peers and era standardization

A batter’s reference rates are estimated from a format × year × batting-role pool. Pooling windows widen from ±1 years to ±2, ±4, ±7 or ±12 until a minimum observation sample is available. This is a retrospective index, not a forward-looking prediction. Roles: openers 1–2, top 3–4, middle 5–7, lower 8+. A role is based on batting entry inferred from observed deliveries; its accuracy should be audited against source scorecards.

**Known issue:** Pooling within role does not fully isolate game state, because a top-order batter who enters at 10/2 and another who enters at 200/2 face different conditions. Ball-state modeling by wickets-down, over, innings and rule regime is planned for v1; current index is provisional.

## Bowlers and same-match proxy

For each bowler, format and year, runs per legal ball and credited wicket rate are compared to same-format pooled bowling peers in ±2 years. The signed log-rate improvement gives a strength score, shrunken toward zero by balls bowled (600-ball prior). For each batting innings, strength is averaged over the bowling attacks actually faced (weighted by counted balls). Expected runs change by `exp(-0.35*strength)` and dismissals by `exp(+0.25*strength)`. Those coefficients are open hypotheses, not fitted causal coefficients. The bowler statistic includes the evaluated match's data, so there is **some residual own-match endogeneity**; leave-match-out bowling modeling should replace this approach.

To address pitch and conditions, use all other batters **in the same match** across teams (when both teams and 100 other balls are observed) to calculate an expected-run-adjusted scoring factor. With a 100-run pseudo-sample, the observed factor is raised to the power of 0.45 and capped to [0.82, 1.22]. This partially controls the scoring environment, but remaining effects of attack, player skill, match stage, rules and weather cannot be identified independently. Field conditions are not measured; it is a **same-match scoring proxy**, not a true pitch score.

## Score and shrinkage formulas

Let `R` be actual runs, `E_R` expected runs after bowling and match adjustment, `D` actual dismissals, `E_D` expected dismissals, and `n` observed batting innings. Define:

- Run efficiency `A = (R + 25)/(E_R + 25)`
- Survival efficiency `S = (E_D + 3)/(D + 3)`
- Quality `Q = 100 × exp([w ln(A) + (1-w) ln(S)] × n/(n+28))`

Research weights: Test `w=0.32`; ODI `w=0.58`; T20I `w=0.78`. The front-end sensitivity slider can change them; this should be supplemented with out-of-time validation against match outcomes and benchmark rankings. Shrinkage limits fragile 10-innings careers dominating the leaderboard.

The **Team Carry Index** is `100 × (R+25)/(Σ(expected_runs_in_innings × teammates' run/expectation factor)+25)`, where the teammate factor excludes the evaluated batter and is shrunk with 25 expected runs. Supplementary metrics are player share of team total runs and sum of (actual − expected × peer factor) over innings.

The **Career Greatness Index** is `100 + (Quality−100)×sqrt(min(1,n/140)) + 10×asinh((R−E_R)/1250)`. It is a user-visible, configurable **research choice**, not a statistically determined truth.

**Multi-format** quality is the equal-format geometric mean. Eligibility currently requires at least 25 Test or ODI innings, 20 T20I innings, and roughly 2/3 as many distinct observed matches. `Tests + ODIs` and `All Three` exclude players who did not play all included formats. We do not insert fictitious zero scores.

## Statistical uncertainty

For a player with at least 15 distinct observed matches we run **180 seeded match-block bootstrap replicates** of the Quality Index, resampling entire matches together to preserve paired Test innings. The 5th and 95th bootstrap quantiles are shown as a **90% conditional uncertainty interval**. This is a preliminary sampling-uncertainty calculation. It **does not** propagate uncertainty in estimated bowlers, batting-role baselines, match conditions, fielding or changes to match availability. Intervals overlapping do not imply equal quality, and neither interval nor observed rank establishes all-time supremacy.

## Observed historical scoring environment

The report includes format/year empirical runs per 100 balls and runs per dismissal, calculated only from actual available deliveries. Changes show how the *observed sample* scored; changes in team/opponent composition and missing matches can produce trends unrelated to rules or pitch quality. The ODI rules-period labels are historical markers, not regression-discontinuity estimates.

## Historical scorecard parity — now an automatically imported (but unverified) second model

`pipeline.historical` downloads the 2017 Duncan Golicher ESPNcricinfo-derived batting innings snapshot and imports original observed innings into `historical-innings.csv.gz`. `pipeline.model` merges historical and modern sources by match start date, format and the pair of countries; Cricsheet wins for overlapping whole matches, preventing duplication. The provenance, checksum, historical year counts, likely mismatches and unrecognized rows are audited. The original historical CSVs are *not* redistributed in the project.

The common-denominator `scorecardParity` model uses only fields observable across eras: innings runs, dismissals, contemporaneous innings batting run environment and teams/teammate performance. Expected runs/dismissals are estimated using nearby-year peers excluding the evaluated player, with widening periods for sparse cohorts; index = `100 × exp(0.5 ln((R+25)/(expected runs+25)) + 0.5 ln((expected dismissals+3)/(D+3)))` shrunk by `n/(n+35)`. Historical teammates in the SAME batting innings provide a separate descriptive **team-carry index**, but not a causal pitch effect. The experimental parity model explicitly does **not** adjust historical batting position, specific bowlers faced, old rules, powerplays or missing balls. This model is separate from the modern Cricsheet bowler-exposure-adjusted index and cannot be presented as equally measured.

`pipeline.reconcile` compares observed aggregate runs for Bradman Test, Richards Test+ODI and Tendulkar Test+ODI against official ICC career totals and reports mismatches; this is necessary but **not sufficient** for career completeness, official match coverage or reliable name matching. Year-by-year `pipeline.audit` always sets `historicalCompletenessCertified=false` and `allTimeRankingPermitted=false` pending official match-ID reconciliation. The complete historical source downloads could not be run in the initial creation environment. See `docs/historical-backfill.md` for provenance, exact checks and limitations.

**Major limitations:** the dated legacy archive is only a 2017 snapshot; raw-scorecard collection licence is unverified; many 19th/20th-century records lack reliable balls faced and entry order; early-era opponent bowling exposures and pitch quality are unmeasured; the source can omit matches or mislabel players; and Test match first/second innings / same-day doubleheaders need careful match-key reconciliation. Historical scorecard parity is exploratory and must not be called a validated greatest-ever ranking.

## Evaluation plan for a defensible all-time verdict

1. **Coverage reconciliation:** known official numbers of Tests, ODIs, T20Is by year, team and format; avoid double counted scorecards.
2. **Statistical tests:** player-block and match-block bootstrap, 95% uncertainty by player and index; rank win-probability simulations with shrinkage.
3. **Alternative weighting:** match-outcome validation, cross-validated predictive runs/wicket model and stability under alternative quality/carry/greatness weights.
4. **Team context:** batting opportunity, position, team weakness, lineup sharing, rescue innings at 20/3, opponent strength, chase pressure, wicket resources.
5. **Opposition difficulty:** leave-one-match-out and prior-24-month bowling quality (seam/spin, new ball, peak bowlers). Prefer hierarchical attacker and bowler models.
6. **Venue and pitch:** ground effects by season, weather, player batting hand, toss, home field, innings-specific conditions and ball wear. Don't infer pitches from a single batting innings.
7. **Era and rules:** rule regime, 2011 two balls and 2015 fielding restrictions; separate regression discontinuity / difference-in-differences studies before causal claims.
8. **Conditions and competition:** per-country non-home SENA and subcontinent performance, opposition tier, world cups/knockouts, same number of innings and same age, career peak rolling windows.
9. **Transparency:** release code, data lineage and sources/coverage alongside ranks; never publish an unsupported "greatest ever" verdict.
