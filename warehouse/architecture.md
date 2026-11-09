# Master cricket warehouse — data contracts and acceptance gates

The goal is a durable cricket data source *independent of* batting rankings, built to enable future projects. This is an implementation plan; features marked planned are not silently assumed implemented.

## Implemented and verified, 2026-11-09

1. **Ball-event warehouse (Cricsheet open data):** `warehouse/events.py` ingested 7,165 men's Test/ODI/T20I matches and preserved 3,939,822 events, including raw ball JSON, wickets, extras, runs, original match metadata, registry IDs, and file hashes. Stores a compressed SQLite artifact from the successful GitHub Action; weekly rebuild configured.
2. **Identity and venue warehouse (Cricsheet open data):** `warehouse/registers.py` ingested 18,698 people, 28,603 provider crosswalk IDs and 591 venues. Other provider IDs are stored as mappings, not guessed name matches. Weekly rebuild configured.
3. **Existing rankings:** 4,371 extra non-overlapping historical scorecard matches, 103,626 historical batting innings and 5 career-format run reconciliations. This historical layer is NOT certified complete or independently rights-cleared.
4. **Rights-aware source inventory:** `warehouse/source_registry.json` plus `warehouse/README.md`.

## Storage: next blocker

Current GitHub Actions artifacts expire in 60 days. GitHub Pages is a read-only public website, NOT a database. To make the warehouse reliable for years of additional research, configure one of: AWS S3 with versioning and restricted/public prefixes, or equivalent durable object storage. Keep raw historic ESPN-derived records in a private access-controlled prefix until rights are clear; publish only rights-cleared open data.

Suggested logical prefixes:
- `bronze/cricsheet/YYYY-MM-DD/` original source archives and checksum;
- `bronze/historical-restricted/` restricted historical inputs and permission metadata;
- `silver/matches/`, `silver/innings/`, `silver/deliveries/`, `silver/players/`, `silver/venues/`, `silver/participation/`, `silver/scorecards/`;
- `gold/batting/`, `gold/bowling/`, `gold/team/`, `gold/venue/`, `gold/match-state/`;
- `quality/YYYY-MM-DD/` official census and source parity reports.

Prefer Parquet partitioned by `format/year` for large event history plus DuckDB for SQL queries. Version every snapshot by date, parser revision and sha256. Retain original Cricsheet source JSON to regenerate derived tables; attach a source-specific record key to every row.

## Data types — required state and limitations

| Data product | Today | Next |
|---|---|---|
| Open modern deliveries, wickets, extras, registry IDs | Implemented, validated, ephemeral artifact | Durable storage, Parquet and QA contracts |
| Historical scorecard *batting* innings | Initial 2017 derived source present in ranking pipeline | Match-ID reconciliation, coverage and rights audit |
| Historical scorecard *bowling*, fielding, fall-of-wickets | Missing | Rights-cleared supplier + normalization |
| Independent official match ID census | Missing | Obtain authorized IDs, reconcile format/year/team/venue/date |
| Player and venue master IDs | Cricsheet registry downloaded, independent tables | Map historical aliases and match participants, flag collisions |
| Historical match results, captains, toss, officials, playing XI | Partial | Census + scorecard source |
| Match-state and partnerships | Preserved for Cricsheet deliveries | Build indexed marts with correctly measured legal balls |
| Weather, pitch, ground coordinates and historical playing conditions | Missing | Separate versioned contextual data, explicit observation/proxy status |
| Women's internationals, franchise and domestic cricket | Missing | Expand only into separate competition categories after men's baseline is tested |

## Acceptance criteria before calling all-time dataset complete

- Reconcile each **official match identifier** and match classification; publish exact missing/ambiguous lists, not just percentages from two unrelated website totals.
- Independently compare innings totals, wickets, dismissals, innings counts and match result to scorecards, not career aggregate RUNS alone.
- Separate `delivery`, `complete_scorecard`, `batting_innings_only`, `team_total_only`, `result_only` and `missing` coverage.
- Identify same-day/doubleheader collisions. No canonical match merge based only on date and participating teams.
- No player identity match from surname or initials without verifiable crosswalk evidence.
- Preserve `NULL` for historical unknown balls faced, bowling exposures, pitch and toss. Zero must mean observed zero.
- Audit age/era bias and missingness by year, format, team, venue, player and source tier.
- Record data license, provenance, acquisition hash, source date and access tier; never automatically publish raw restricted records.
- Model uses only data columns whose observation status is valid for the format and era being compared.
- Keep warehouse extraction separate from website publication and validate downstream outputs against source snapshots.

## New-source priority

**P0** independent historic match census and field-level coverage comparison; durable event storage.
**P1** legally usable historical full scorecards for bowling/fielding/innings and team results; official match numbers and source ID mapping.
**P2** women's internationals, tournament metadata, franchise T20, richer pitch/ground, weather and ODI rule eras.
**P3** domestic first-class/List A scores, contracts/auctions, injuries, workload and optional video/ball-tracking integrations where licensing permits.

Third-party website accessibility is **not** permission to bulk collect or redistribute. Upstream libraries (e.g. cricketdata R) do not confer upstream ESPN record licensing.
