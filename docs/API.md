# API v1

Base `/api/v1/`; authenticated OpenAPI `/api/v1/schema/`; generated contract `schemas/openapi.json` and TypeScript declarations `packages/api-client/schema.d.ts`. `make api-client` regenerates; `make check` checks drift. Health `/api/health/`, readiness `/api/ready/` are deliberately nonprivate.

GET session returns user, current memberships, demo_mode and csrfToken. POST login/logout, invite redemption and password-reset actions require a valid CSRF cookie/token, including before authentication. Browser uses same-origin credentials, X-CSRFToken, and a membership-validated X-Workspace-ID. Never send a browser-selected owner ID as authority. Non-demo workspace creation starts unlinked; a reviewer must verify public identity.

Success: `{data:...,meta:{...}}`. Errors: `{error:{code,message,fields}}`; inaccessible objects return404. Pagination uses page/page_size, maximum100; permission filtering precedes totals. Discovery accepts q,cause,country,population,location,size,budget_cents,risk,outcome_definition,horizon_days. Unknown geography yields no matches. Stable name/date ordering is used; arbitrary SQL ordering or arbitrary pooled filters are unsupported.

| Group | Implemented paths |
| --- | --- |
| Accounts | session, login, logout, members, invitations, invitations/redeem; pilot/workspaces; pilot/password-reset/request, confirm |
| Directory | organizations, organizations/:id, compare?ids=UUID,UUID, geographies |
| Plans | portfolios, portfolios/:id, reports/:artifact?format=csv; pilot/watchlist, pilot/watchlist/:id, pilot/monitor |
| Contributor | dashboard, programs, programs/:id; pilot/profile, pilot/benchmark, pilot/impact-report?format=csv |
| Ingestion | import-template?kind=outcomes\|costs, imports, imports/:id, imports/:id/commit, imports/:id/rejected, jobs, jobs/:id |
| Evidence | cards, cards/:id, observations, analyses, analyses/candidates, graph?root=entity-ID; pilot/bookmarks |
| Sources/sharing | sources, sources/:id, sources/:id/withdraw, source-issues, grants, grants/:id DELETE, audit |
| Review | artifacts/:id/submit, reviewers, reviews?status=approved, reviews/:id; pilot/identity-claims, pilot/identity-claims/:artifact/proof |
| Value/feedback | opportunities, requests, alerts, alerts/:id, subscriptions, metrics?format=csv; pilot/contact, pilot/introductions, pilot/introductions/:id/decision, pilot/introductions/:id/contact |
| Explanation | explanations/:artifact POST; deterministic provider by default |

Update requests carry revision where the resource supports editing. A stale revision returns409. Upload checksum+workspace and committed batch/source/cohort uniqueness provide idempotency; jobs have unique domain-derived keys and execution fencing. Arbitrary client idempotency headers are not accepted as proof of ownership. Withdrawal status is observable and physical deletion retries are bounded. Current consent is checked on export and at worker completion.

CSV exports escape spreadsheet formula prefixes. Printable reports use the actual artifact revision, source links and required attribution. Pooled exports use fixed compatible cohort sets; suppression does not expose reconstructable totals or source IDs. Analyses require separate publication grants from every contributor before review can approve a release.

Operator CLI imports preserve provenance and are separate from browser APIs: `manage.py import_public` for inspected official source adapters; `manage.py import_catalog` for exact registry/opportunity CSV templates. A platform staff flag authorizes this explicit operator action, not blanket private-data browsing. See DATA_SOURCES.md for manifests and local examples.

Portfolio responses include a current public service-area coverage view with source revisions. This separate live view does not expand the approved financial-plan snapshot. Possible gaps mean no selected organization reports that area within the available directory; overlaps suggest collaboration, never automatic waste or measured duplication. Metrics CSV retains collection method, period, definition, source kind and unverified ground-truth caveats.

Optional live Responses smoke: export OPENAI_API_KEY and PHILANTHRA_LLM_MODEL, then explicitly run `PHILANTHRA_LIVE_SMOKE=1 .venv/bin/pytest tests/live/smoke_provider.py -q`. It sends only a hard-coded fictional claim, does not read workspace data, and fails rather than counting deterministic fallback as live success. Its filename excludes it from normal test discovery; without the explicit flag it skips before any network call. No live request was executed during this build.
