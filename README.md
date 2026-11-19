# Cricket Greatness Lab

Public, interactive cricket batting analyses and derived research outputs.

**Website:** https://randomquestions-projects.github.io/cricket-greatness-index/

The website uses a bounded, read-only results API and contains only presentation assets. Original research datasets, the master warehouse, model training code and analytical pipelines are maintained privately.

The displayed rankings are experimental and are not certified complete all-time records. Publicly displayed results can be copied; source datasets are not distributed through the active site.

## Data rights and attribution

See [LICENSE-NOTICE.md](LICENSE-NOTICE.md) for relevant source acknowledgments and license information. Historical records and older GitHub release assets require a separate legacy-publication retirement process. This repository's earlier Git history may contain source code and data; current-tree removal does not erase that history.

## Public release safeguards

- Current Pages: `site/` is restricted to HTML, CSS and browser JavaScript.
- The Pages build rejects source files, SQLite databases, CSV, ZIP, Parquet and data directories.
- `.github/workflows/verify-live-output-only.yml` checks that historical `site/data/*` download links return HTTP 404.
- The public API returns only filtered, paginated analysis summaries and bounded Match Explorer records.

For research methods and code changes, consult the private research repository with appropriate access.
