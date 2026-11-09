# Test batting greatness methodology — research v0.3

This is the Test-only common-denominator batting model. The three headline measurements are **era-adjusted quality**, **team carry**, and **career greatness**, with a fourth descriptive metric: **peak quality**. It is experimental and not an independently validated greatest-ever ranking.

## Data fairness

All Test batters (Bradman, Kohli, Sobers, Tendulkar, Lara, Ponting, Smith, etc.) are scored from the same scorecard-level inputs: runs, dismissal/not-out status, year, opponent nation, known venue host, match identity, and teammates in the same innings. Modern-only ball-by-ball records and individual bowlers faced do NOT enter this shared historical index.

Source is the existing merged research ledger: 2017 ESPN-derived historical batting-innings snapshot, supplemented by current openly licensed Cricsheet match records. Historical data rights for redistribution remain unverified; only model-derived player-level aggregates and nation/home-away summaries are produced by this new model. Historical innings-level records are NOT published by this model. The old website previously included historical extracts; those are separately removed from publication.

## Three measures

**1. Era-adjusted quality:** Reference batting runs per appearance and dismissals per appearance are calculated from nearby-year peers, excluding the rated batter. Start with ±2 years, widen to ±5, ±10, ±18 and ±30 if the sample is too small; weight neighboring years by 1/(1+year gap). Expected runs are multiplied by modest, shrunk factors for opposing nation's batting suppression, home-vs-away context, and same-match scoring, where supported.

Opposition factor: scorecard-era runs per batter appearance allowed by an opposing nation over a ±5-year window, *excluding the whole evaluated match*, relative to other nearby Tests. It is a crude, confounded **opposition-team quality proxy**, not the skill of bowlers actually faced. Cap log effect at ±0.22.

Venue factor: nearby-year away/home scoring effect relative to peers; only applied when host is known. Neutral/unknown venue does not receive an inferred adjustment. Cap log effect at ±0.12.

Match difficulty: other batters in the same Test, excluding all appearances of the rated batter. Shrunk toward era baseline, log effect capped ±0.17. It is a same-match batting-scoring **proxy**, not observed pitch condition.

ExpectedRuns_i = era_runs_per_innings_i × oppositionFactor_i × venueFactor_i × matchFactor_i.

ExpectedDismissals_i approximately scales era dismissal rate with the inverse square root of these context factors, capped to [0.35,0.99]. This is an explicit research approximation, not an outcome-calibrated probability model.

Quality = 100 × exp{ [0.72 ln((R+25)/(ExpectedRuns+25)) + 0.28 ln((ExpectedOuts+3)/(D+3))] × n/(n+35) }.

100 means contextual parity; the 72/28 weights and smoothing priors are hypotheses, not learned coefficients.

**2. Team carry:** For each innings with at least 6 observed batters, compare player's runs to the *average other batter* in exactly that innings, stabilized by adding 10 runs. Average the log comparisons and shrink by n/(n+20). A score of 70 when teammates struggle earns relatively more carry than 70 when teammates all score well. This is a descriptive team-contribution index and not causal.

**3. Career greatness / peak:** Career Greatness = 100+(Quality−100)×(0.65+0.35×min(n,180)/180)+9×asinh((runs−expectedRuns)/1400). This explicitly rewards volume and sustained surplus; the formula is researcher-designed, not externally calibrated. Peak uses the maximum rolling 25-innings (same scorecard model) quality with no shrinkage; searching many windows induces selection bias.

## Uncertainty and diagnostics

240 seeded whole-match block-bootstrap replicates estimate **conditional 90% intervals** for Quality and Team Carry. Baselines and context corrections are held fixed, so these do not include model fitting, coverage gaps or source uncertainty. Source fields carry match coverage, historic-innings count, venue-known percent, opponent support, number of team-carry innings, and sensitivity results removing each of opponent, home/away, or same-match run expectations.

The quick sensitivity calculation holds dismissal expectation fixed; it should be interpreted directionally, not as a fully re-estimated model. Bradman and Kohli's official reference runs and innings are checked against observations, but a career match does NOT establish comprehensive match-by-match official scorecards.

## What is NOT controlled

Specific historical bowler-by-bowler exposures, historical batting positions, balls faced, physical pitch measurements, weather, series-level conditions, all venue host classifications, and historical series IDs. Opponent-batting results proxy attack quality but are confounded by who the team played, scheduling and conditions. Some earlier eras feature fewer nations and less diverse opposition. Venue and match proxies may themselves depend on team strength.

We can therefore compare **dominance relative to observed contemporaries** using the best common available evidence. We cannot deduce who would fare better against today's bowlers or assert any model's top rank as definitive all-time superiority.

## Publication and reproducibility

Source code: pipeline/test_greatness.py. Tests: tests/test_test_greatness.py. Site: site/test-greatness.html. Generated model: site/data/test-greatness.json.

The new site presents only derived aggregate player scores, nation-group summaries and venue-group summaries, not historical third-party match-by-match records. The older publication needed cleanup because it had selected historical inning extracts. Source reuse rights remain an important limitation; further commercialization or distribution requires dedicated legal review.

Existing ODI/T20 and modern-only metrics are not silently renamed to v0.3 and continue to represent their older methodology until separately upgraded.
