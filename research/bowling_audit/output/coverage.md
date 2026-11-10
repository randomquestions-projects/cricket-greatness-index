# Men's International Bowling Data Availability Audit

This is a source-backed **availability audit**, not a bowling index.
Only the licensed Cricsheet scorecard archive was processed. The batting app was not changed.

## Confirmed modern scorecard coverage

| Format | Observed matches | First year | Bowler-innings rows | Recorded wickets | Missing bowler IDs | Source-flagged matches |
|---|---:|---:|---:|---:|---:|---:|
| TEST | 899 | 2001 | 17,708 | 28,138 | 0 | 7 |
| ODI | 2,617 | 2002 | 31,380 | 35,207 | 0 | 167 |
| T20I | 3,649 | 2005 | 43,274 | 43,111 | 0 | 392 |

These are observed-source wickets, not full-career totals. No data from pre-Cricsheet historical bowling scorecards are held in this open release.

## Historical greats: observed only, NOT full career

| Bowler | Observed bowler-innings | Recorded wickets | Source aliases |
|---|---:|---:|---|
| Sydney Barnes | 0 | 0 | none |
| Jim Laker | 0 | 0 | none |
| Clarrie Grimmett | 0 | 0 | none |
| Malcolm Marshall | 0 | 0 | none |
| Richard Hadlee | 0 | 0 | none |
| Wasim Akram | 5 | 12 | Wasim Akram |
| Waqar Younis | 6 | 11 | Waqar Younis |
| Shane Warne | 48 | 138 | SK Warne |
| Muttiah Muralitharan | 206 | 446 | M Muralitharan |
| Glenn McGrath | 109 | 195 | GD McGrath |
| Anil Kumble | 103 | 219 | A Kumble |
| James Anderson | 535 | 950 | JM Anderson |
| Dale Steyn | 334 | 686 | DW Steyn |
| Ravichandran Ashwin | 373 | 752 | R Ashwin |
| Mitchell Starc | 404 | 778 | MA Starc |
| Pat Cummins | 286 | 531 | PJ Cummins |
| Jasprit Bumrah | 279 | 498 | JJ Bumrah |

## Availability for proposed controls

| Control | Available today | Missing for all-era model |
|---|---|---|
| Era-adjusted wicket-taking and run prevention | Wickets, runs conceded, balls, year | Historical bowling figures before ~2001 |
| Opposition strength | Opponent batting side, same-source batting | Historical bowling-opponent records |
| Home/away | Match venue text, batting/bowling teams | Verified venue country for all matches |
| Match and pitch difficulty | Same-match batting and other bowlers | Measured pitch properties unavailable |
| Team carry | Other bowlers in same observed innings | Complete historic team bowling figures |
| JAWS-inspired peak/career | Calendar dates, observed workload and wickets | Historical career segments, match opportunity adjustment |
| Pace and spin | Not reliably recorded in scorecard fields | License-cleared style reference needed |
| ODI/T20I phases | Licensed raw delivery warehouse can support | Never comparable to historical scorecard-only players |

## Historical rights assessment

| Source | Potential content | Clearance |
|---|---|---|
| Cricsheet / existing master warehouse | Modern international bowling scorecards | **ODC-BY 1.0; use now** |
| Duncan Golicher crickdata (2017) | ESPN-derived bowling innings across Tests, ODIs, T20Is | **No verified redistribution license; do not bulk import** |
| Philipson academic Test bowler dataset (2022) | 47,216 bowler-innings / 2,207 players, 1877–2022 | **Article CC BY, underlying GitHub dataset has no explicit license; request clarification** |
| Hugging Face 1877–2014 Test Bowling Card | Historical per-innings bowling details | **Source provenance and reuse rights unverified** |
| ACS Cricket / CricArcade / Howstat / CricketArchive / ESPN | Historical scorecards and checks | **Reference only; no unrestricted bulk license established** |

## Audit conclusion

**Modern model data readiness: YES.** The licensed scorecard warehouse supports a defensible bowling research prototype.
**All-time historical model readiness: NO.** Older greats would be undercounted or absent.
**Recommended next data acquisition: legally reusable historical bowling figures at player × match-innings level, then independent player/match reconciliation.**

Sources:
- https://cricsheet.org/licensing/
- https://github.com/dgolicher/crickdata
- https://github.com/petephilipson/MPCMP_Test_bowlers
- https://journals.sagepub.com/doi/full/10.1177/1471082X231178584
- https://huggingface.co/datasets/bhuvaneshprasad/test-cricket-dataset-1877-2014
