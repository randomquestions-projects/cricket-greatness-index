# Scorecard-first Cricket Master Database — November 9, 2026

## Verified production results

Source: Cricsheet ODC-BY 1.0 all-match JSON, licensed with attribution; independently stored immutable open source snapshot. Build [42711950154](https://github.com/randomquestions-projects/cricket-greatness-index/actions/runs/42711950154) passed.

- **23,241 licensed matches** from the source snapshot, across men's and women's international/franchise/domestic cricket.
- **51,428 innings** reconstructed into structured, queryable cards.
- **440,949 batting rows**, **304,051 bowling rows**, **179,293 fielding rows**.
- **20,365 source-unflagged delivery-derived matches**, **2,876 source-flagged matches**. Unflagged does NOT mean independently complete versus official scorecards.
- Published six compressed SQLite scorecard shards by gender/decade, with a manifest and source SHA256, in the [durable open-data scorecard release](https://github.com/randomquestions-projects/cricket-greatness-index/releases/tag/cricket-scorecards-source-13f9f5d5153c3625).
- Existing modern international match coverage: men's Test 899, ODI 2,617, T20I 3,649.

## Historical coverage: batting records, not full cards

The existing 2017 snapshot from Duncan Golicher was built using ESPN-derived data. It is used by the existing batting research pipeline, **not** redistributed as an open master database, because its original rights have not been cleared.

The production **aggregate-only** historical audit (no players or match-level rows published) found:
| Format | Candidate matches in 2017 source before dedup | Historical batting rows in source | Historical extra matches after overlap removal with modern deliveries | Modern delivery-supported matches | Provisional combined observed matches |
|---|---:|---:|---:|---:|---:|
| Men's Tests | 2,269 | 80,203 | 1,728 | 899 | 2,627 |
| Men's ODIs | 4,057 | 68,091 | 2,475 | 2,617 | 5,092 |
| Men's T20Is | 685 | 9,897 | 168 | 3,649 | 3,817 |

The historical input preserves batting runs and some team totals, but **not** detailed batting order, individual bowling figures/exposures, verified dismissals with fielders, or an official match number. The 2017 data end date means the modern archive must supplement it.

Missingness counts in the original historical batting rows:
| Field | Tests | ODIs | T20Is |
|---|---:|---:|---:|
| Batting position unavailable | 80,203 | 68,091 | 9,897 |
| Detailed dismissal unavailable | 80,203 | 68,091 | 9,897 |
| Bowler exposures unavailable | 80,203 | 68,091 | 9,897 |
| Zero or unknown balls faced | 22,129 | 757 | 204 |
| Team total not reconciled | 24 | 1,671 | 685 |

Crucial: The scorecard-derived modern *open* dataset, historic batting-only records, independently official scorecards, and source-only candidate matches are **different data quality tiers**. They should never be reported interchangeably.

- [Historical field availability](audits/historical_scorecard_fields.json)
- [Combined scorecard readiness](audits/scorecard_readiness.json)
- [Source-level match number gap candidates](audits/match_inventory.json)
- [Open scorecard release](https://github.com/randomquestions-projects/cricket-greatness-index/releases/tag/cricket-scorecards-source-13f9f5d5153c3625)

## Query the modern scorecards

Download one of six `scorecards_<gender>_<decade>s.sqlite.gz` files from the release, decompress to SQLite and query it:

```sql
SELECT m.category, COUNT(*) AS matches
FROM matches m WHERE m.gender='male'
GROUP BY m.category ORDER BY matches DESC;

SELECT b.player_name, SUM(b.runs) AS runs, SUM(b.balls) AS balls
FROM batting b
JOIN innings i ON i.id=b.innings_id
WHERE i.super_over=0
GROUP BY b.player_id, b.player_name ORDER BY runs DESC LIMIT 20;

SELECT player_name, SUM(wickets) AS wickets,
       SUM(legal_balls) AS balls, SUM(conceded) AS conceded
FROM bowling
GROUP BY player_id,player_name ORDER BY wickets DESC LIMIT 20;
```

There are dedicated `matches`, `innings`, `batting`, `bowling`, `fielding`, `quality_flags` tables. Scorecard rows preserve source-backed ID fields, source attribution, and explicit missingness. Over-based bowling figures should be calculated from legal balls using six-ball overs for contemporary cricket; historical multi-ball over conventions require separate handling.

## What is still unverified

1. We have **not** cross-referenced every match to an independent official match index. Our 2,627 Test count is provisional, not a validated count of all historical Tests.
2. We have **not** obtained permission to bulk republish independently sourced historical full scorecards. We have not ingested Cricinfo, Howstat, CricketArchive, CricArcade, or Cricket Database into the open warehouse.
3. None of the 23,241 derived Cricsheet scorecards has been independently checked against a second, authorized scorecard source. The current quality flags only reflect known source/parser problems.
4. Actual historical bowling, fielding and batting-order data are absent in the 2017 batting snapshot. They cannot be reconstructed truthfully from batting totals alone.
5. These scorecards are the **open data warehouse**, not yet the single merged cross-era scorecard file. Because the historical source has uncertain reuse terms, a publicly redistributable union remains blocked.

## Refresh automation

The source-only master `.github/workflows/master-warehouse.yml` is scheduled for Mondays, and the licensed scorecard extractor `.github/workflows/scorecard-warehouse.yml` runs afterward, downloading the newest released master archive. Both use immutable versioned releases and source checksums. The historic 2017 snapshot is fixed, so new legal historical sources would require explicit new ingestion connectors.

This scorecard-first warehouse does **not** modify the existing Greatest Batters rankings. That work remains paused.
