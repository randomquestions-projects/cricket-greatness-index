# Source acquisition and rights — master warehouse

Use approved data rather than maximizing the number of scraped websites. Most historical sites display public scorecards without granting the right to bulk scrape/redistribute them. Access to public webpages is **not a data license**.

## Automatically ingested
- **Cricsheet** `https://cricsheet.org/downloads/all_json.zip`, ODC-BY 1.0: open archive of original JSON match records across competitions and both genders, retained with source hash and attribution. Monthly/weekly snapshot.
- **Cricsheet People + Venue Registers**, ODC-BY 1.0: source IDs, aliases, and cross-reference IDs, independently stored in `warehouse/exports/identities.sqlite.gz`.
- **Duncan Golicher 2017 batting innings snapshot**: currently used downstream in legacy batting model but **NOT** open/rights-certified; excluded from open master release.

## Reference-only sources pending access/permissions
- ICC: official aggregates, competition details, laws/playing conditions and scorecards. Career-run reference checks currently exist; no authorized bulk match census.
- Cricket Database, CricArcade, Howstat, CricketArchive, ESPN Statsguru: historical scorecards and match inventories, but unrestricted bulk access or redistribution not established. Do not automatically scrape.
- `cricketdata` R: an adapter over upstream providers, not a source that grants additional ESPN rights.
- Doosra: mostly transformed Cricsheet, not an independent historical scorecard source.
- Copernicus ERA5: independent atmospheric context, not direct match/pitch data, needs venue lat/lon and historical time mapping.

## Why additional open data is useful
Cricsheet data support bowling, fielding, match state, over-by-over events and participant analysis, and multiple competition types in distinct categories. Historical batting-only results need a legally licensed scorecard source to cover bowling, innings order and players before ball-by-ball availability.

## QA scope
Every match has a stable Cricsheet file ID, optional match-type number, original metadata JSON and event sources. The repository's preexisting date/team synthetic match signature should **not** be treated as an official identifier. Separate official census alignment is still necessary. The master snapshot is complete *relative to the downloaded Cricsheet JSON* only.
