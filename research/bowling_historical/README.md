# Bowling research — historical-data acquisition gate

**Status: historical bowling figures not yet cleared for reuse/redistribution.**

This directory is a **bowling-only research workspace** and is not imported into the existing batting website or its models. The source registry is in [source_clearance_registry.json](source_clearance_registry.json).

## Open-source data we have already integrated

- Our existing men's international Cricsheet scorecard warehouse contains **899 Tests, 2,617 ODIs and 3,649 T20Is**, with 92,362 bowler–innings records (Nov 2026 source snapshot).
- The new [bowling reference enrichment](../bowling_enrichment/) imports **ODC-BY** Cricsheet stable player and venue IDs and **CC0** Wikidata bowling-style and country facts. It publishes join-confidence statuses and actual observed usage coverage. This does not make historic scorecards complete.
- The current source-derived pace/spin coverage is **12.49% Test**, **11.34% ODI** and **5.39% T20I** by observed bowler–innings, and the directly verified physical-country coverage is **4.67% Test**, **1.53% ODI**, **1.18% T20I** by matches. The majority of unknowns remain explicitly unknown.
- An optional Wikidata **venue-country candidate** process provides a review queue based on exact English label matches; these candidates are not automatically accepted as verified facts or used by any model.

## Historical datasets discovered but NOT imported

| Historical source | File | Potential benefit | Rights | Action |
|---|---|---|---|---|
| Philipson Test bowlers dataset | `bowldat2022_Toss.RData` | Test bowler–innings back to 1877, reportedly 47,216 observations | GitHub repository provides no explicit reuse license | Request author/dataset rights permission; inspect provenance, schema, duplicate matches before importing |
| Golicher 2017 historical bowling archive | `data/bowling.rda` (R package) | Historical Test/ODI/T20I bowler–innings through 2017 | `DESCRIPTION` explicitly says downloaded/reformatted from ESPNcricinfo; license field is unresolved | Need a defensible basis covering underlying ESPN source as well as author compilation |
| Hugging Face historical Test archive | `test_Bowling_Card.csv` (~3.19 MB) plus `test_Matches_Data.csv` | Older Test bowling cards, with match IDs and figures | No dataset card license/source provenance established | Verify source/reuse rights; check row-level scorecard parity and dataset file-format problems |

These data may be freely **viewable**, but that is distinct from permission to bulk copy, distribute, or maintain as a public historical warehouse. This is a conservative project governance choice, not legal advice; individual cricket statistics may be factual, while curated databases and website access contracts can raise separate concerns.

**Do not infer that no license means unrestricted reuse.** GitHub's documentation explicitly says default copyright restrictions apply when a repository has no license.

## Minimum requirements before including a historic dataset

1. Document publisher, origin, download URL, original upstream provider, version, exact redistribution basis/permission and any necessary attribution.
2. Store its original copy **only in a clearly authorized storage tier**, not the public GitHub repo by default.
3. Normalize to an isolated historical **bowler × match × innings** staging table with source record ID, player ID, year/date, team, opposition, venue, balls/overs, maidens, runs conceded, bowler-credited wickets, innings number, match ID and source provenance.
4. Resolve player aliases using independently validated IDs. Avoid joining surnames alone.
5. Independently check an official Test/ODI/T20I match inventory (not just historical career totals); distinguish missing scorecards, no bowling figure, DNB, washed-out match, unrecorded and unknown.
6. Compare source-by-source records in overlapping 2001–2017 matches against Cricsheet, then test retired greats (Barnes, Laker, Grimmett, Marshall, Hadlee, Wasim, Warne, Murali, McGrath) for complete career wicket/innings totals.
7. Maintain licensing boundaries in public releases. Publish derived aggregate analysis only when the input/data-use terms permit it.

**The JAWS-inspired bowling index will not be considered all-time-ready until these steps are addressed.** A modern-only exploratory bowling model could run now; historic bowling greats must not be scored as zero.

## No modification to batting

The separate `research/bowling_*` modules and `warehouse/exports/bowling_open_enrichment` do not change `site/`, `pipeline/`, the user's batting formulas, or the batting data files.
