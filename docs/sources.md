# Data source research and licensing

Research date: 2026-11-09. These are publicly inspectable resources. **Not all sources grant rights to bulk extract or redistribute them.**

| Source | Coverage / use | Limitations / legal notes | Verified link |
|---|---|---|---|
| Cricsheet men’s Test JSON | ~899 available source matches in its public November 2026 listings; archive extends back to ~2001 | Not the full history; some matches withheld; ODC-BY attribution | https://cricsheet.org/downloads/ |
| Cricsheet men’s ODI JSON | ~2,617 available public source matches (Nov 2026) | Not ODIs 1971–2001, some newer matches withheld; ODC-BY | https://cricsheet.org/downloads/ |
| Cricsheet men’s T20I JSON | ~3,649 available public source matches (Nov 2026) | Missing and withheld matches; incomplete even in modern years | https://cricsheet.org/downloads/ |
| Duncan Golicher 2017 innings snapshot | Public GitHub `all-innings.csv` and `all-match_innings.csv` of historical Test/ODI/T20I batting innings and teams derived from ESPNcricinfo; imported by scheduled workflow | **Original reuse licence UNKNOWN; raw CSV never republished; historical completeness unverified** | https://github.com/dgolicher/cricket |
| Cricsheet register | Identifiers and links to other cricket records | IDs not universally shared across historical sources | https://cricsheet.org/register/ |
| Cricket Database | Lists all Test dates since 1877, ODIs 1971 onward, and has historical scorecards | Free API has limits / recent-data restrictions; no bulk rights established | https://cricketdatabase.com/ |
| CricArcade | Reports 2,537 Test scorecards through March 2024 and 4,981 ODIs through August 2026 | Site describes provenance but a licence allowing full data reuse was not identified | https://cricarcade.com/data-sources |
| ESPN Statsguru | Official-style historical player and match splits across formats | Site terms may restrict automated collection and redistribution | https://stats.espncricinfo.com/ |
| `cricketdata` R | `fetch_cricinfo(type='innings')` can retrieve historical innings metadata | Uses ESPN records; check ESPN terms; not bundled | https://pkg.robjhyndman.com/cricketdata/ |
| Doosra Hugging Face | Independent transformation of Cricsheet: ~22,983 matches at Sep 2026, 435,515 batting innings | Overlaps Cricsheet; primarily useful for validation, not independent pre-2001 coverage | https://huggingface.co/datasets/Sarthak213/doosra-cricket |
| ICC playing conditions | 2011 two new balls; 2015 Powerplay changes; later changes | Exogenous interventions can be researched; not automatically causal | https://www.icc-cricket.com/news/new-playing-conditions-come-into-effect |

## Historical ingestion route

The workflow automatically fetches Duncan Golicher's research snapshot with `python -m pipeline.historical --download`, parses individual batting scorecard innings and teammate sums, deduplicates overlap at the match level against Cricsheet, then computes an exploratory **scorecard-common-denominator** rating alongside the modern model. Raw historical CSVs stay gitignored. It produces `data/generated/historical-manifest.json`, `site/data/career-reconciliation.json` and `data/coverage.md`. See [`historical-backfill.md`](historical-backfill.md) for exact fields, limitations and verification gates.

Another independent historical scorecard input can optionally be placed in `data/historical/innings.csv`; the file `data/historical/SCHEMA.csv` specifies the expected fields. The two legacy sources are deduplicated by match, not concatenated blindly. Never commit source scorecards without established redistribution rights. Historical player IDs need cautious alias crosswalks, with unknown identities left separate rather than automatically merged.

## Coverage risk

Note that headline count from a website (all official Tests/ODIs) is not an indication that the data is freely usable for bulk distribution. The all-time claim requires audited counts by year/format, missingness analysis, source cross-checks, near-complete first-innings scorecards and explicit license coverage. It also needs a common-denominator model (scorecard-parity) instead of mixing post-2001 delivery-based features with older careers.

## Independent completeness denominator (research note)

As of 2026-11-09, the public Cricket Database views list approximately 5,064 men's ODIs since 1971 and 2,644 men's Tests since 1877; these lists combine ball-by-ball, scorecard-only, and result-only levels. Links: https://cricketdatabase.com/matches/odi/men and https://cricketdatabase.com/ . These are **NOT** imported source records and have not been independently reconciled to the ICC register. They suggest substantial modern-archive gaps, but are not a substitute for a match-by-match ID crosswalk. Do not divide Cricsheet matches by these counts and claim a verified completeness percentage.

Official-format history starts in 1877 for Tests, 1971 for ODIs, and 2005 for men's T20Is. Cricsheet's earliest available years are considerably later for Tests and ODIs. The site should retain a source-tier label for all imported material.
