# Outputs-only cricket Pages cutover (staged, NOT LIVE)

The existing live cricket website is deliberately still served from public `main`.
This **unmerged feature branch** is the eventual presentation-only cutover
and must not be merged until the private AWS results API is working.

## What changes
- `site/` has only HTML, CSS, and client JavaScript (plus public API origin
  injected at deploy). There are no dataset files, JSON rankings, CSV, ZIP,
  SQLite, data folders or precomputed downloadable archives in the Pages artifact.
- Results are requested through private-data-backed, bounded GET endpoints:
  `/v1/cricket/bootstrap`, `rankings`, `player`, `matches`, `innings`.
- The new Pages workflow has no `workflow_run` trigger from the legacy public
  ranking generator and fails closed unless a real API returns a valid health
  response, leaders, rankings and the Match Explorer.
- Previously scheduled public archive/warehouse builders are retired in the
  *candidate branch* to prevent them regenerating downloadable source assets
  after the cutover.
- A PR check confirms the exact small site asset allowlist and refuses any
  `site/data` file.

## What remains before merging this branch
1. Activate the private S3 Bronze/Silver historical bowling warehouse.
2. Build and upload approved, independently audited **Gold display projections**
   and Lambda code bundle from the private research repository.
3. Deploy and verify the output-only API (review IAM, CORS, throttling, checksum,
   bounded page sizes, exact allowlisted endpoints, malicious/oversize inputs).
4. Set the public repository variable `CRICKET_OUTPUTS_API_BASE` to the
   verified `https://<api-id>.execute-api.us-east-2.amazonaws.com` origin.
5. Stage the website and compare all routes, search, player profiles, rankings,
   comparison, matches, mobile, and browser console to live.
6. Only then merge this branch. Its deploy job refuses publication if API
   smoke checks fail, leaving the existing live deployment unchanged.
7. Confirm `site/data/*` returns 404 on the new Pages deployment and no
   files are embedded in the public Pages artifact.

## Historical GitHub releases and repository history are a separate exposure

Old public **GitHub Releases** may still have ZIP/SQLite scorecard archives
and old public Git commits may still contain data, even after `site/data` is
deleted. Therefore 'not downloadable anywhere under our GitHub account'
**cannot** be claimed solely from this branch. Address obsolete release
assets and old public source history deliberately (e.g. archive/restrict
the old repo, migrate to a clean public presentation-only repo, and update
Pages configuration). Preserve accessible research outputs and links.
Do not delete or force-rewrite production history without an independently
tested migration/rollback plan.

## Limitations

Publicly displayed results and API responses can always be copied; rate
limits/pagination do not constitute DRM. The goal is no **complete underlying
warehouse download**, not concealing visible scientific conclusions.
Historical sources with unresolved reuse permissions remain private and
must not enter public Gold without explicit source authorization/review.
