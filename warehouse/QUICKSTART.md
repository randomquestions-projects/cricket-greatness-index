# Cricket Master Database — quick start

The reusable **open/licensed** source-first data warehouse is independent from Greatest Batters. The first production snapshot succeeded on November 9, 2026.

## Get a versioned snapshot

Open [the first successful warehouse release](https://github.com/randomquestions-projects/cricket-greatness-index/releases/tag/cricket-master-2026-11-09-42707561618).

It contains:
- `cricsheet-all-json.zip`: original Cricsheet all-match JSON, ODC-BY 1.0, source of truth for reproducible transforms
- `master_manifest.json`: source SHA256 and coverage by competition, gender, year, and shard SHA256
- `master_female_2000s.sqlite.gz`, `master_female_2010s.sqlite.gz`, `master_female_2020s.sqlite.gz`
- `master_male_2000s.sqlite.gz`, `master_male_2010s.sqlite.gz`, `master_male_2020s.sqlite.gz`

These are SQLite databases compressed with gzip. Download the desired `.sqlite.gz` file and decompress it to `.sqlite`. For example:

```bash
gh release download cricket-master-2026-11-09-42707561618 \
  --repo randomquestions-projects/cricket-greatness-index \
  --pattern 'master_male_2020s.sqlite.gz' --pattern 'master_manifest.json'

gzip -dk master_male_2020s.sqlite.gz
sqlite3 master_male_2020s.sqlite 'SELECT count(*) FROM matches;'
```

For reproducible research, **pin the exact release tag and checksum**. Do not silently mix shards from different source snapshots.

## Tables

| Table | Grain | Important fields |
|---|---|---|
| matches | one Cricsheet match | `id`, `start_date`, `gender`, `category`, `match_type`, `team_type`, `team_a`, `team_b`, `venue`, `official_match_type_number`, `raw_info_json` |
| innings | one batting innings incl. super overs | `id`, `match_id`, `sequence_number`, `batting_team`, `super_over`, `metadata_json` |
| deliveries | one event in the JSON overs list | `innings_id`, `over_number`, `ball_ordinal`, batter/bowler IDs, `batter_runs`, `total_runs`, `legal_ball`, `faced_ball`, `raw_event_json` |
| wickets | one wicket event | `innings_id`, `over_number`, `ball_ordinal`, `wicket_ordinal`, `dismissed_id`, `dismissal_kind`, `fielders_json` |
| match_people | participation + registry crosswalk | `match_id`, `player_name`, `player_id`, `team` |

**Data semantics:** count all deliveries including wides and no-balls. Legal ball excludes both wides and no-balls. Batter-faced balls exclude wides but include no-balls. Bowler runs conceded must separately handle byes and leg-byes from `raw_event_json`.

## Example queries

```sql
-- Men's ODI matches (one partition)
SELECT COUNT(*) FROM matches WHERE gender='male' AND category='odi';

-- Batters by runs, excluding super overs
SELECT d.batter_name, SUM(d.batter_runs) AS runs, SUM(d.faced_ball) AS balls
FROM deliveries d JOIN innings i ON i.id=d.innings_id
WHERE i.super_over=0
GROUP BY d.batter_id, d.batter_name ORDER BY runs DESC LIMIT 20;

-- Ball-level dismissals, including run-outs and assisted fielders
SELECT dismissal_kind, COUNT(*) AS total FROM wickets
GROUP BY dismissal_kind ORDER BY total DESC;

-- Player format/era scope
SELECT gender,category,strftime('%Y',start_date) AS year,COUNT(*) AS matches
FROM matches GROUP BY gender,category,year ORDER BY year;
```

The six shards are designed to be queried across multiple files with **DuckDB's SQLite extension** or `ATTACH DATABASE` in SQLite. Be careful: `id` is unique globally within the source, but bare cross-shard SQL queries must explicitly union tables.

## Data quality, scope and rights

- Only Cricsheet-published matches are present; this is NOT every official international match.
- Historical independent match census and historical batting/bowling/fielding scorecards remain separate pending rights review and match-by-match integration.
- `warehouse/match_inventory.py` produces **source-internal** candidate gaps using `match_type_number`; gaps are not certified missing matches.
- Six database shards are durable in GitHub Releases; the previous GitHub Actions event warehouse artifact (60-day expiry) is no longer the sole storage.
- The register warehouse `warehouse/exports/identities.sqlite.gz` includes IDs and aliases and is committed in the repository.
- Attribution: Cricsheet.org, Open Data Commons Attribution License (ODC-BY 1.0), <https://cricsheet.org/licensing/>.
- The historical 2017 ESPN-derived batting-innings snapshot is **excluded** from the public master release because its independent redistribution rights are unverified.

To rebuild from original open data:

```bash
python -m unittest tests.test_master tests.test_match_inventory -v
python -m warehouse.master --archive data/raw/all_json.zip --output warehouse/master
python -m warehouse.match_inventory --archive data/raw/all_json.zip --output warehouse/master
```

## Future development priorities

1. Acquire an **independent, legally usable** official match-number census with match-by-match records and reconcile it to the open source IDs; publish exact missing and ambiguous matches.
2. Add permitted historical full scorecards, including bowling, fielding, and innings order; keep private licensed materials private.
3. Expand QA to innings scores, dismissals, wickets, rosters, alias collisions, source rights and historical missingness.
4. Build gold tables for batting/bowling/fielding, pressure, venues, era comparisons, team strength and forecasting.
5. Rewire Greatest Batters to consume only stable and validated marts rather than its bespoke current ingestion.
