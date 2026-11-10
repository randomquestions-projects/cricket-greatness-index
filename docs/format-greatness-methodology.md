# Cricket Greatness v0.4 — all-era batting analysis across three formats

## What changed

The original V1 navigation has been restored and connected to new computed scorecard-era outputs for Tests, ODIs, T20Is, Tests + ODIs and All Three Formats. Other V1 modules, including batter comparison and match explorer, remain reachable. The new interactive scorecard model has its own per-format comparison views.

The core same-era scorecard model deliberately uses **runs, dismissal, nearby-year peers, opponent, venue host, contemporaneous match scoring and same-innings teammates** for all eras. Individual modern bowler exposures, Powerplay data, balls faced and delivery-level pitch proxies are **not allowed in the all-era primary model** because historical records frequently do not contain them.

The primary code is `pipeline/test_greatness.py`, now parameterized for Test, ODI and T20I. `pipeline/format_greatness.py` generates `test-greatness.json`, `odi-greatness.json`, `t20i-greatness.json` and `greatness-combined.json` at each successful build.

## Three headline measurements

**Era-adjusted quality:** expected runs and dismissals use nearby-year scoring with the rated batter removed, plus cautiously shrunken opponent-team, home/away and same-match scoring effects. The latter is a **scorecard difficulty proxy**, not measured pitch quality. Actual historical individual bowler matchups cannot be consistently incorporated.

**Team carry:** score relative to other batters within the **same team innings** and apply reliability shrinkage. Does not claim causal credit for match outcomes or estimate whether an innings single-handedly won the game.

**Peak versus career / JAWS inspired:** Baseball's JAWS combines career WAR and a player's best seven seasons of WAR. Here we cannot claim to have cricket WAR or comparable match-opportunity values. Instead, the research constructs:

- Per-innings context-standardized surplus: `s = (actual_runs - expected_runs)/max(10, expected_runs) + 0.35*(expected_dismissals - observed_dismissals)`. This includes wicket survival in the same units but is **not** causal run value.
- `Career Value = sum(s)` over all observed innings.
- `Peak 7-season Value = sum of the seven largest calendar-season sums of s`, potentially **nonconsecutive** seasons.
- `JAWS-style Value = (Career Value + Peak 7-season Value) / 2`.

The sum treats each calendar year as a season, not a seven-calendar-year rolling window. The separate quality peak remains the **best rolling 25 Test/ODI/T20I batting innings**, which measures a different thing.

This combines a longevity-sensitive career measure with a peak measure in **the same underlying scoring units**. However, a 1930s Test season offered fewer games than modern ones, ODI and T20I match availability varies considerably by nation and year, and cumulative surplus is therefore opportunity-biased. Treat this as a *first iteration*, not a definitive all-era career-value estimator. Calibrated opportunities/matches-per-era and sensitivity checks are future statistical work.

## Combined formats

**Tests + ODIs:** players must meet the observed minimum innings in both Test (35) and ODI (35). This is a particularly useful historically broad comparison.

**All Three Formats:** players must meet Test (35), ODI (35) and T20I (25). This is a **modern cross-format eligibility ranking** — not an all-time batting ranking that can fairly compare players who retired before T20Is existed. Bradman and Viv Richards are excluded by definition, **not assigned zero**.

We normalize each format's quality, carry, career and JAWS-style scores to within-format percentiles; each eligible format is given equal weight in the multi-format composite. We do not add raw Test and T20I surplus or combine unrelated index units. Composite percentiles are relative rankings among observed, eligible data and are not probabilities.

## Data, rights, caveats

- Input: existing historical-innings research ledger (1877–2017 snapshot, ESPN-derived, rights unresolved) plus Cricsheet licensed modern deliveries and scorecards (ODC-BY). Source matches are provisionally deduplicated using date/teams; not certified official census.
- Published new JSON contains **player-level model aggregates**, context-group summaries and uncertainties only; no new individual historical innings/scorecard record exports.
- Tests/ODI/T20I historical coverage is not identical, and missing pitches, individual historical bowlers, match stakes, exact batting orders and rules eras are not imputed.
- 240 fixed-reference whole-match cluster bootstrap draws create conditional 90% intervals for Quality and Carry for per-format scores. They do **not** capture model selection, bias from opponent schedule, the 2017 source's rights or historical missing matches.
- Scores in the first pilot require further sensitivity testing on the 72% runs / 28% survival weighting, carry stabilization and seven-season JAWS analogue.
- The `format-greatness.html?format=<format>` page is the new all-era format model. The older V1 match explorer shows Cricsheet-observed delivery records, not every historical match. Its source rights and missingness are labeled separately.

**Links:**
- [Tests](../site/format-greatness.html?format=test)
- [ODIs](../site/format-greatness.html?format=odi)
- [T20Is](../site/format-greatness.html?format=t20i)
- [Tests + ODIs](../site/format-greatness.html?format=test_odi)
- [All three formats](../site/format-greatness.html?format=all_three)

Neither the combined rank nor the JAWS-inspired score answers with confidence who would be best if all batters played in the same era under identical bowling conditions. It answers a narrower question about performance above observable era/context expectations.
