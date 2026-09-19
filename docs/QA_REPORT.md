# Independent QA evidence

This report describes executed checks, not a production certification. All browser actions use fictional seeded organizations, normal Django login, a real isolated PostgreSQL database, and the actual API and worker. No browser API responses are mocked.

## Current verification

| Command | Observed result |
| --- | --- |
| `DATABASE_URL=postgresql://philanthra:philanthra-local@127.0.0.1:55432/philanthra_qa PHILANTHRA_ENV=test .venv/bin/pytest tests/integration -q --tb=short` | 10 passed in 2.83 seconds in a dedicated QA test database. |
| `bash scripts/pnpm build` | Passed before the current browser run. |
| `bash scripts/pnpm exec playwright test` | 12 passed in 1.4 minutes after the final fixes. All six journeys passed at 1440px and 390px, including zero axe WCAG A/AA violations on discovery. |
| `bash scripts/pnpm exec prettier --write playwright.config.ts tests/e2e/journeys.spec.ts` | Passed. |

## What the tests establish

`tests/integration/test_concurrency_and_isolation.py` checks withdrawal against a waiting worker and a waiting reviewer through separate PostgreSQL connections, stale lease fencing with concurrent finalizers, recommendation finalization racing withdrawal, target-program withdrawal, reviewer access to third-party contributions, immediate denial of withdrawn upload previews, and cross-workspace guessed identifiers. It checks list, mutation, report/CSV, graph, explanation/citation, import, and job boundaries. Monetary edits cannot bypass frozen exclusions or minimums. A fixed suppressed release cannot expose totals or citations, and arbitrary complementary cohort slices are rejected.

`tests/e2e/journeys.spec.ts` verifies these persisted journeys on desktop and mobile:

- Discovery → two-organization comparison → a $100.01 portfolio → separate reviewer approval → CSV export with provenance and synthetic labels → printable report. The API confirms exact-cent budget accounting and persisted approval.
- Aggregate CSV upload → explicit mapping → worker validation and commit → persisted program → intervention card → independent approval → public donor-access grant → another account reads it → withdrawal → immediate HTTP 404 and a deletion job.
- A complete compatible cohort set → stored descriptive pooled analysis with at least three organizations and visible limitations.
- Keyboard skip link, discovery overflow check, WCAG A/AA automated audit, useful no-match state, and persisted filter query. JavaScript page errors and console errors are checked.
- Save and remove permissioned evidence; watch and remove an organization; request monitoring and observe the actual worker job complete.
- Reject invalid contributor context while retaining the entered mission; persist a valid profile; enable and withdraw contact-sharing consent; export the private source-linked impact-report CSV; request a generic password reset for a nonexistent synthetic address.

The browser fixture uses a fresh UUID-named local PostgreSQL database, separate API/worker/web processes, and a same-origin proxy at port 8081. It removes its own processes and database at teardown. Browser tests do not share or reset the normal demo database.

## Findings and corrections

- **Fixed and exercised:** fresh seeding failed when an unknown allocation cap was persisted as NULL; the coordinator preserved the unknown constraint while using a zero edit ceiling.
- **Fixed and exercised:** recommendation fingerprints exceeded PostgreSQL's 100-character column. Stable hashed fingerprints now allow the race regression to complete.
- **Fixed and exercised:** running recommendations now serialize against source withdrawal and track the target source; withdrawn target context invalidates its alerts.
- **Fixed and exercised:** source-owner withdrawal immediately denies import preview/error-export access; reviewer assignment cannot widen third-party grants; manual allocations preserve exclusions and minimums.
- **Fixed and exercised:** CSV report requests needed DRF format-override separation; mixed planning inputs and synthetic candidate data needed honest synthetic provenance in reports.
- **Fixed and exercised:** interactive map descendants inside an image-role SVG were inaccessible; the group role passes the current automated check.
- **Fixed and exercised:** insufficient contrast in metadata, map notes/legend, footer, and financial warning badges. Discovery now has zero violations in the configured axe WCAG A/AA checks at both widths. Assertions remain enabled.
- **Fixed and exercised:** deterministic recommendation results dropped authorized titles, leaving blank links. Titles are now preserved and the browser checks every rendered recommendation title is nonempty.
- **Fixed and exercised:** the contributor dashboard incorrectly reported no quality issues for a stored missing numerator. It now displays an explicit collection prompt, and the browser rejects the misleading success notice.

Early browser attempts also exposed test-selector/fixture mistakes: select/textarea label matching included default text, one action ran before client navigation completed, and a cohort option displays its definition rather than its code. These were corrected without changing behavioral assertions. The final full run has no retries or skipped tests.

## Visual inspection and limits

The QA agent opened actual rendered desktop discovery and reviewer screenshots from the first run, portfolio reports at both widths, and pooled analyses at both widths. After the final run, it opened the updated `docs/screenshots/discovery-desktop.png`, `ngo-mobile.png`, `review-desktop.png`, and `analysis-mobile.png`. The final NGO screenshot shows named recommendations and the missing-numerator collection prompt. Layout, labels, amounts, review states, synthetic report labeling, and descriptive-analysis caveats are visible. Full-page screenshots show long lists; mobile analysis tables retain horizontal scrolling. Screenshots establish rendering, not scientific validity.

Automated axe coverage is limited to discovery; this is not a whole-application accessibility certification. Browser coverage does not include every pilot route, real expert review, production deployment, or a fresh clone on another machine. The fixture verifies fresh migrations and seeding on each run. Coordinator additions verify seed idempotency while preserving user records, block external requests in the main browser contexts, and compare domain row hashes across an actual native service restart. The coordinator owns the final combined release gate and remaining acceptance gaps.

## Coordinator integration additions

Following the independent twelve-case run, the coordinator added two desktop/mobile cases for unlinked workspace creation, tenant metrics opt-in and CSV, and assertions for current service-area coverage. The final fourteen-case run exercises real persisted state. A coverage filter initially omitted `synthetic_reported` records; that failure was corrected without weakening the assertion. The main Playwright contexts block external network destinations, while actual local API requests continue normally. Geographic coverage tests independently exclude private, withdrawn and headquarters-only records.

The native rapid restart check exposed TCP TIME_WAIT being mistaken for an active listener. The launcher now uses address reuse consistently with its server while still rejecting live listeners; a real-socket regression distinguishes both cases. Final counts and command results are recorded in BUILD_STATUS.md.
