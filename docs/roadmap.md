# Build roadmap — what remains after this version

**P0: ingest current Cricsheet records**. Run `Refresh international cricket records` on a networked GitHub Actions runner. Confirm source SHA256, matched scores, format distribution, raw and derived ledger counts; this project cannot certify a populated index without that run.

**P1: comprehensive historical archive**. Identify legally reusable ODI batting scorecard rows from 1971 and Test batting scorecards from 1877, including exact run/out/position, match/date, opposition, host, provenance and stable player and match keys. Historical archives researched include Cricket Database, CricArcade, Howstat, ESPN Statsguru and the `cricketdata` package, but no verified redistributable full archive is bundled. Reconcile each source to official scorecard records.

**P2: measured, defensible cross-era index**. Refine common-denominator scorecard-parity model; calibrate modern innings under historical scoring rules; include uncertainty intervals, attack-weighted skill, wickets resource and match situation. Distinguish raw, era-adj, opposition-adj, match-adj, teammate-adj, all-time scores. Validate sensitivity against intuitive and historical benchmark periods.

**P3: comprehensive ball-level value model**. Learn expected runs and expected dismissal per ball using wicket count, over, innings, format, rule regime, ground, opposition bowler and match situation. Estimate batter adjusted run contributions per ball, rather than simplistic fixed average/strike-rate weights.

**P4: opponent bowler strength and pitch**. Train leave-one-match-out hierarchical bowler strength, distinguish seam/spin and new-ball exposure. Fit venue-season random effects with uncertainty, not one-match pitch assumption.

**P5: team carry and pressure**. Add rescue contributions, batting with tail, team-outcome leverage, chase difficulty, tournament stage with verified bracket labels, innings when teammates fail, consistency under difficult conditions.

**P6: narrative and analytics lab**. Automated report for Kohli/Gill/Tendulkar/Dravid/Ponting and 20+ leading run-scorers per format, contribution by era, same-age curves, same-innings curves, run-rate-vs-survival sensitivity, confidence intervals and exportable chart/table outputs. Update research dashboard when source data changes.
