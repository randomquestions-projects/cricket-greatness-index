# Cricket Master Data Platform — source-first foundation

> **Production update (2026-11-09):** The open-licensed Cricsheet master archive and six durable SQLite shards have **successfully been published in [the master release](https://github.com/randomquestions-projects/cricket-greatness-index/releases/tag/cricket-master-2026-11-09-42707561618)**. It contains 23,241 matches and 11,739,488 deliveries. Read [QUICKSTART.md](QUICKSTART.md). The historical rights/match census work is NOT completed. The earlier implementation notes below describe the pre-release state.


**Status (2026-11-09):** active batting site currently consumes TWO primary datasets. This directory is the start of a REUSABLE data platform, not a claim that all historical cricket scorecards are complete. Ranking models live downstream and must never be used as the source-of-truth data.

## Source catalog and access decisions
| Source | Scope | In the current batting analysis? | Allowed action |
|---|---|---|---|
| [Cricsheet men's international downloads](https://cricsheet.org/downloads/) | Men's Tests, ODIs, T20Is since ~2001 | **YES**, 7,165 delivery matches | ODC-BY: retain originals and normalized deliveries; attribute |
| [Duncan Golicher historical snapshot](https://github.com/dgolicher/cricket) | 1877–2017 historical batting innings | **YES**, 4,371 additional matches | Source rights NOT verified; keep source CSV private/restricted, do not redistribute |
| [Cricsheet People and Venue Registers](https://cricsheet.org/register/) | Unique IDs, cross-site IDs, aliases, grounds | **NEW**, independent reference pipeline added here | ODC-BY; can publish with attribution |
| [Cricsheet all-match archive](https://cricsheet.org/downloads/) | Women's internationals, IPL, domestic, T20 leagues and more | NO | ODC-BY; future ingest without mixing competition tiers |
| [Cricket Database](https://cricketdatabase.com/) | Historical inventory, full/partial scorecards, modern events | NO | Paid historical API; permission and match-level completeness to evaluate |
| [CricArcade](https://cricarcade.com/data-sources) | Historic Tests/ODIs, detailed innings, venue/players | NO | Independent reference; no demonstrated bulk rights |
| [ESPN Statsguru](https://stats.espncricinfo.com/) | Scores, splits, historical match records | NO direct importer | Reference; verify site terms before bulk acquisition |
| [ICC](https://www.icc-cricket.com/) | Official records, match numbering, playing conditions | 5 career-run validations only | Reference; expand licensed match census |
| [Howstat](https://www.howstat.com/) | Historical match scorecards and fielding/bowling | NO | Reference; automated bulk terms unverified |
| [CricketArchive](https://cricketarchive.com/) | Very deep historic, domestic, List A records | NO | Subscription and separate data licence needed |
| [cricketdata R](https://pkg.robjhyndman.com/cricketdata/) | Adapter over ESPN/Cricsheet, NOT independent upstream | NO | GPL software; does not override original-source terms |
| [Cricket Scorecard Accuracy Project](https://thesanctityofwickets.com/) | Scorecard disagreement examples | NO | Data-quality methodology |
| [Doosra transformed archive](https://huggingface.co/datasets/Sarthak213/doosra-cricket) | Cricsheet-derived pre-aggregated records | NO | Validation only; not new historical matches |
| [Copernicus ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries) | Venue weather from 1940 (modeled atmospheric conditions) | NO | Separate contextual layer; weather != observed pitch state |

## Architecture (build this BEFORE treating rankings as final)
- **Bronze — original source snapshots**: retained with immutable source URL, date and checksum, gated by source rights.
- **Silver — canonical entities**: match (with official ID if known), competing teams, innings, ball events, wickets, batting/bowling/fielding cards, players, aliases, venue, competition, source mappings and quality flags. No fuzzy identity merger without evidence.
- **Gold — independent research marts**: era normalization, venue par scores, team strength, opposition attack, batting quality, bowling, pressure, rankings, projections and comparisons.
- **Storage**: GitHub stores code and small ODC-BY reference snapshots. A versioned SQLite or Parquet warehouse in persistent object storage is recommended for the full event lake (GitHub Pages is NOT the source database). GitHub Actions orchestrates and audits.
- **Source rights**: historical ESPN-derived records are quarantined until reuse rights are resolved. Public open-data exports must omit unlicensed raw scorecards.
- **Independent official match census**: reconcile by match number, date, format, teams, venue and status; don't treat unrelated provider homepage counts as authoritative.

## Known data gaps / correctness risks
- Current batting analysis has 11,536 deduplicated matches: Test 2,627, ODI 5,092, T20I 3,817; this is an OBSERVED COUNT, not the official denominator.
- Five historical player-format RUN TOTALS reconcile; that does NOT validate every match, scorecard field or player identity.
- Cricsheet deliberately withholds some Afghanistan matches. Missing results and unobserved deliveries must be explicit NULL/not-covered, not zero.
- Modern ingestion currently computes delivery-level aggregates but does **not persist every individual ball** into a durable warehouse; that is a key next engineering milestone.
- Historical merge keys are based on date + format + two teams. Official match-number crosswalk is required to identify ambiguous same-day fixtures.
- Historical source may not provide batting order, balls faced, full bowling/fielding, DRS or observed pitch condition. Never impute them as if observed.
- Compare match census with multiple providers but independently confirm their competition classifications: e.g. some online provider pages label non-international games with Test/ODI format tags.

## New reference-data import
`python -m warehouse.registers` downloads four **Cricsheet ODC-BY** registers, validates unique IDs, and creates a reusable compressed SQLite identity database at `warehouse/exports/identities.sqlite.gz` plus a source-hash/count manifest. This is the FIRST new data source added to the master-data foundation, not a complete match warehouse.

The workflow `Refresh cricket identity reference data` automatically updates the reference database every Monday and exposes it as a GitHub artifact. It also commits the open reference snapshot for durable reuse. Next steps are official match census, granular deliveries warehouse and rights-cleared historical scorecard connectors.

Data provenance: **Cricsheet.org — ODC-BY 1.0**. See <https://cricsheet.org/licensing/> and <https://cricsheet.org/register/>.
