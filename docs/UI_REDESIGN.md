# Philanthra UI redesign

Presentation-only refinement, 2026-09-19. The existing Next/React/custom CSS application, routes, backend, API transport, payloads, defaults, calculations, permissions and package versions remain unchanged. No production deployment. Screenshots contain only fictional records from isolated test databases; existing user/demo records were not reset.

## Direction and decisions

- Near-white canvas, white task surfaces, charcoal text and a restrained deep-green accent. Local system sans-serif, readable 15px body/13–14px supporting text, 28–30px workspace titles, modest radii, visible focus, tabular financial values.
- Grouped foundation funding/evidence/monitoring navigation and nonprofit programs/learning/monitoring navigation. Utilities separate. The existing foundation-kind and reviewer-role conditions are preserved. No route authorization is inferred from a label.
- Mobile navigation expands in document flow, moves focus to its close control, supports Escape and restores focus to its trigger. It does not overlay controls or trap focus.
- Discovery retains search/cause/service area above a mounted “More filters” disclosure. Additional set values remain indicated. One explicit submit preserves original query keys and cents conversion. Native validation and invalid budget errors reveal the affected field. List positions remain schematic markers, not ranks. The selected-organizations toolbar is in normal document flow above results; it wraps without covering focused controls or requiring a trip to the bottom of the list.
- Continuous evidence, detail, editor and methodology sections use dividers; distinct actions remain bounded panels. Study type, editorial review and data origin are labeled separately.
- Reports lead with existing amounts, allocation rows, program context, outcomes and costs. No new domain calculation or dataset request. Arbitrary cost currencies and decimal strings are retained. Complete technical payloads and unknown keys remain accessible.
- Generic details preserve null, unavailable, zero, false, empty text, empty list and empty object. Composite records use the full available width rather than successively narrowing columns. Source and technical disclosures expand for print and restore afterwards.
- No features added. Backend-dependent UX ideas, new filtering/sorting, autosave, additional metrics, geographic precision and new workflows are out of scope.

## Route and feature parity checklist

Dispatch remains 25 workspace route families plus `/admin` alias, with all public/auth and parameterized variants. “Preserved” below means implementation and diff review; execution evidence is recorded separately.

| Entry point / workflow | Controls and important states preserved | Presentation change |
| --- | --- | --- |
| `/` | Conditional demo/login destination, authenticated Open workspace destination, methodology | Literal two-audience introduction and Baltimore/demo scope |
| `/login`, `/demo`, `/join` | Username/password, invitation token, four gated demo roles, reset/error | Form-first purpose and distinct demo role section |
| `/password-reset?uid=&token=` | Request/confirm branches, generic response, mismatch/error retention | Direct headings and readable form width |
| `/methodology` | Public and authenticated rendering, all limitations | Continuous reference sections |
| No membership / unknown route | Membership notice/create action; login fallback or page-not-found | Shared primitives, original behavior |
| `/discover` | q/cause/location/population/size/risk/outcome_definition/horizon_days/budget_cents; list/table/map/context; max4/min2 selection, clear and links; empty/error | Compact primary fields, mounted additional filters, readable records |
| `/organizations/:id` | Identity, reported geography/capacity, financial history/signals/amendments, programs/evidence, watch, sources/missingness | Identity/context first; open data sections |
| `/compare?ids=` | All rows/values, selected IDs, planning destination | Bounded accessible side-by-side table |
| `/allocate?ids=` | Name/budget/candidates/weights/caps/minimums/exclusion/assumptions/four planning dimensions; exact-cent save | Plan details and candidate sections, same single form |
| `/portfolios`, `/portfolios/:id` | Draft list/detail, revision/status, budget/unallocated, allocation editing/rationale/caps, coverage, review/export/report/source | Funding plans terminology, useful data first |
| `/dashboard` | Accurate counts, inventory, quality gaps, every match/show-more, benchmarks, learning link/support form | Overview, quiet free-access note, ordered sections |
| `/programs`, `/programs/new`, `/programs/:id` | Inventory/editor, sources/context/defaults/revisions | Grouped editor and task titles |
| `/evidence`, `/evidence/new`, `/evidence/:id`, `/evidence/:id/edit` | Existing search behavior, all fields/enums, drafting/edit/save, explanations/provider behavior, review/report/graph/attribution | Scan-friendly library and structured reading hierarchy |
| `/uploads`, `/uploads/:id` | File limits/types, templates/history, quarantine, columns/mapping, preview/diagnostics/download, polling/commit and partial/invalid states | Upload guidance, mapping grid, actual server status |
| `/analyses` | Complete-cohort selection, inputs/calculate/current/saved, compatibility/suppression/thresholds/review/export | Setup/results/saved sections and distinct safeguards |
| `/graph?root=` | Root selection/reset, existing first12 edges and full table, selection/source/evidence/root links | Connection guide, selected state, legible relationships |
| `/alerts` | Subscription preferences, state/feedback/adoption note, artifacts, empty/invalidated states | Task title and clear response forms |
| `/opportunities` | Catalogue match/eligibility/source/deadline, saved introductions/permitted contact | Open records and request section |
| `/saved`, `/watchlist` | Bookmarks/removal, monitor/refresh/job state/removal and snapshot links; role conditions | Direct labels and monitoring separation |
| `/impact-report` | Private draft/origin/limitations, programs/outcomes/costs/cards/gaps, print/CSV/attribution/sources | Document hierarchy and full-data fallback |
| `/sharing` | Purpose/audience/recipient/expiry/attribution, external processing opt-in, grant/revoke, explicit withdrawal/confirmation | Clear scope and consequences retained |
| `/sources`, `/sources/:id` | Registry/detail, period/retrieval/state/original source, issue creation/list/review | Identity/context before technical metadata |
| `/settings` | Profile/context JSON, identity proof, contact consent, incoming introductions, create workspace, members/roles/invitation/token/metrics | Labeled continuous sections; consent remains explicit |
| `/reviews` | Pending/approved queues, all artifact kinds/identity proof, exact revision, evidence/source, decisions/reason/withdrawal | Supporting record and decision section |
| `/metrics`, `/jobs` | Opt-in/event definitions/forms/export; refresh/actual jobs/retries/errors | Task titles and operational tables |
| `/reports/:id` | Analysis/portfolio/card/identity/other kinds, status/method/policy/review/source/attribution/print/export | Results first, known shapes plus complete technical fallback |
| `/audit`, `/admin` | Same workspace audit data and metadata, original alias | Shared table/detail treatment |

Role review: foundation admin/analyst/viewer, NGO owner/editor/viewer, assigned reviewer and operator retain current controls. No operator-only UI was invented; `/admin` still maps to Audit. `philanthra:workspace-created`, session configuration, workspace selector, sign-out and main reset key are unchanged. API transport remains read-only.

## Terminology

Organizations (`/discover`), Funding plans (`/portfolios`), Plan funding (`/allocate`), Data uploads (`/uploads`), Combined analysis (`/analyses`), Connections (`/graph`), Reviews (`/reviews`). Direct task headings replace slogans throughout. Navigation URLs, query parameters and permissions are unchanged.

## Changed files

- Shell and presentation foundation: `apps/web/components/application.tsx`, `apps/web/components/ui.tsx`, `apps/web/app/globals.css`, `apps/web/app/layout.tsx`.
- Existing task views: `apps/web/components/donor.tsx`, `ngo.tsx`, `shared.tsx`, `pilot.tsx`. Added `apps/web/components/report-content.tsx` for known report/review shapes and complete technical fallback.
- Component regressions: `apps/web/tests/ui-redesign.test.tsx`, `apps/web/tests/public-entry.test.tsx`.
- Browser regressions: `tests/e2e/ui-redesign.spec.ts`; intentional headings/action-label updates and a main-content denial-message locator in `tests/e2e/journeys.spec.ts`.
- Evidence and records: this document, `docs/BUILD_STATUS.md`, `docs/ACCEPTANCE_MATRIX.md`, and `docs/screenshots/ui-redesign/`.

## Before/after evidence

`docs/screenshots/ui-redesign/before/`: 28 fresh PNGs, 14 surfaces at 1440×1000 and 390×844, filenames identify surface/role/viewport. Captured with original production build using the documented isolated test server, actual synthetic save/review/upload/analysis operations. No page errors observed by capture script. Existing historical `docs/screenshots/*.png` remain references only and are not baseline test evidence.

`docs/screenshots/ui-redesign/after/`: **63 PNGs**, comprising 56 matching full-page/`-viewport` images and 7 supplementary navigation, filter, print and enlarged-text images. Full-page images show content reachability; viewport images support first-glance review. The before and after captures use separate isolated synthetic databases, so generated record identifiers differ. The original ten historical screenshot paths were restored byte-for-byte after tests; they are not relabeled as current evidence.

| Filename prefix | Route / role | Captured state |
| --- | --- | --- |
| `landing-public` | `/`, signed out | Two user paths and pilot scope |
| `demo-public` | `/demo`, signed out | Ordinary sign-in because the isolated test server sets `demo_mode=false` |
| `discovery-foundation` | `/discover`, foundation administrator | Loaded results, empty selection, additional filters closed |
| `compare-foundation` | `/compare?ids=…`, foundation administrator | Two selected organizations |
| `allocation-foundation` | `/allocate?ids=…`, foundation administrator | Candidate constraints before submission |
| `portfolio-foundation` | `/portfolios/:id`, foundation administrator | Actual saved synthetic $100.01 draft |
| `report-foundation` | `/reports/:id`, foundation administrator | Source-linked report after separate synthetic review |
| `reviews-reviewer` | `/reviews`, assigned reviewer | Pending exact revision and decision form |
| `overview-nonprofit` | `/dashboard`, nonprofit owner | Program inventory, data quality and actual seed recommendations |
| `evidence-detail-nonprofit` | `/evidence/:id`, nonprofit owner | Existing synthetic card, context, limitations, source/review details |
| `uploads-nonprofit` | `/uploads`, nonprofit owner | Aggregate-only upload instructions and history |
| `upload-mapping-nonprofit` | `/uploads/:id`, nonprofit owner | Worker-returned invalid/unmapped import awaiting explicit validation |
| `analysis-nonprofit` | `/analyses`, nonprofit owner | Saved calculation from a selected complete cohort |
| `impact-report-nonprofit` | `/impact-report`, nonprofit owner | Existing programs, reported outcomes, costs, evidence and gaps |

Each prefix has desktop 1440×1000 and mobile 390×844 captures. Extra after images record expanded mobile navigation, active collapsed filters, expanded print content, and discovery at 320 CSS px with 200% root text. The demo-mode four-role entry remains gated and is covered by component tests with both session states; the screenshots do not claim a live demo-mode role-entry check. No demo credentials are visible in screenshots.

Screenshots and the first-glance review are design evidence, not user testing or accessibility/scientific certification.

## Verification log

- Initial Git preflight: `aarav`, intended existing origin, remote synchronized. Untracked `Archive.zip` preserved.
- `.venv/bin/python scripts/e2e-server.py`: original build baseline started after normal loopback escalation; fresh isolated DB migrated/seeded/worker-drained. Shut down cleanly after capture.
- `node /tmp/philanthra-ui-baseline.cjs`: exit0, 28 screenshots, no pageerrors; installed Chromium required normal escalation.
- First integrated presentation: `bash scripts/pnpm check`, `bash scripts/pnpm test` (14 tests), `bash scripts/pnpm format:check`, `make build`: all exit0. This precedes expanded redesign tests; no later result is implied.
- Source diff/handler audit: routes, API paths, request/form handlers, existing hook dependencies and form values preserved. Additional state is presentation-only (mobile navigation, advanced-filter indication, print disclosure restoration).
- Expanded initial `make test-e2e`: 17 passed, 7 failed. Failures exposed the mobile workspace label being hidden from assistive technology, a long landing word overflowing at 320px with enlarged text, and ambiguous selectors in newly added tests. Fixes keep the workspace label accessible, permit long text wrapping, and select the intended combobox/form alert. No substantive existing journey assertion was removed.
- Focused `bash scripts/pnpm test:e2e --grep 'advanced filters|representative screens|discovery keyboard|reports lead|public, editor'`: 8 passed, 2 failed on the new generic alert locator, corrected to the filter form. Follow-up `bash scripts/pnpm test:e2e --grep 'advanced filters'`: 2 passed. An intermediate browser startup overlapped a failed test-type build; neither is counted as successful verification. The unsupported test-only `exact` option was removed and strict TypeScript subsequently passed.
- Native read-only report review caught the existing manually edited portfolio payload variant. The review now retains its manual-edit context and original fields visibly, directs readers to the existing complete artifact link, and does not invent allocation rows. A component regression covers that shape.
- First `make verify` after integrated report fixes: exit0, 195 backend tests (47.09s), 24 component tests, 24 desktop/mobile browser tests, production build and real-backend smoke. A final presentation change moved the selection toolbar above results; final execution after that change is recorded below.
- The first post-toolbar `make verify` reached 23/24 browser passes. The existing withdrawal test's generic alert locator also matched Next's route announcer; the API 404 assertion had passed. The assertion now targets the main-content alert and additionally requires “Not found.” Persistence, source withdrawal, deletion-job and authorization assertions remain intact. No timeout, retry, permission or business-rule change was made.
- The next integrated run reached 23/24 browser passes; sign-in setup for a report case hit the existing anonymous request throttle after rapid six-role navigation checks. New-test setup now reuses an already visible sign-in form and, only on an actual 429, waits once for the server's bounded `Retry-After` before refreshing. No rate limit, authentication code, test timeout or assertion was relaxed; backend responses remain real.

## Coverage and limits

The unchanged real-backend journeys exercise exact-cent allocation, review and CSV export; aggregate upload, column mapping, validation, worker commit and withdrawal; compatible pooling; saved evidence, watchlist and worker monitoring; contributor profile error retention, contact consent, impact export and generic reset response; invitation/workspace creation and explicit metrics opt-in. New regressions cover every existing discovery query field through a closed disclosure, active-filter indication, invalid-value focus/retention, selection actions, navigation destinations for six representative roles, mobile focus, complete fallback data and report print disclosure restoration.

Installed axe scans retain the existing rules and add applicable WCAG 2.2 tags on representative landing, sign-in, discovery, program editor, funding report and assigned review surfaces. Keyboard checks include the existing map interactions and new mobile open/close/Escape/focus behavior. Reflow checks inspect 11 route surfaces at 320/390/768/1024/1440 CSS px and enlarged root text; 320px supplies the reflow equivalent of a 1280px viewport at 400% zoom. Console/page-error assertions remain enabled. This is representative Chromium coverage, not exhaustive assistive-technology, device or browser certification.

No routes, capabilities, API transport, backend modules, contracts, schemas, data fixtures, dependencies, lockfiles, runtime scripts, infrastructure, AGENTS.md or Codex configuration changed. No production deployment or live provider validation was attempted. Docker/Compose, other-browser/fresh-machine verification, production delivery/security prerequisites and human pilot governance retain their existing documented limitations. New search/sort/filter capabilities, onboarding workflows, payments and generated findings remain out of scope.

## Final integrated verification

Final `make verify` after all source and test corrections: **exit 0** on 2026-09-19.

| Exact command | Observed outcome |
| --- | --- |
| `bash scripts/pnpm check` | Passed strict TypeScript, both separately and inside the final gate |
| `bash scripts/pnpm test` | 24 tests passed across 6 files |
| `bash scripts/pnpm format:check` | Passed |
| `make check` (via `make verify`) | Ruff lint/format, mypy, Django system/migration checks, frontend checks and generated API-contract drift passed |
| `make test` (via `make verify`) | 195 backend tests passed in 49.19s; 24 component tests passed |
| `make build` (via `make verify`) | Production Next build passed |
| `make test-e2e` (via `make verify`) | 24 real-backend desktop/mobile cases passed in 1.9m |
| `make smoke` (via `make verify`) | Fresh isolated migration/seed, readiness, session/CSRF login and persisted discovery passed |
| `node /tmp/philanthra-ui-after.cjs` | Final build: 56 screenshots; zero page/console errors and zero page overflow at 1440/390px |
| `node /tmp/philanthra-ui-inspection.cjs` | Passed navigation focus/restore, active-filter indication, expanded print-source/technical content and 320px/200% text inspection; seven additional PNGs, no console/page errors |
| `git diff --check` | Passed before final staging |

Normal escalation was needed for loopback sockets, local PostgreSQL, installed Chromium and Git writes/network. No security gate or dependency version was changed. Final screenshots use this production build. Production prerequisites in README and BUILD_STATUS remain unchanged.

Final visual inspection opened actual rendered landing, discovery, report and print/source/navigation/text-enlargement screenshots. An independent native agent opened the final nonprofit overview, evidence detail, upload mapping, assigned review and impact-report viewport images; no concrete clipping or misleading state was found. Earlier oversized evidence metadata and raw review payload presentation are resolved. In the isolated `demo_mode=false` capture, the first discovery result begins at **549px** on desktop and **794px** on mobile; this is a layout measurement, not user research. Report print inspection shows all three disclosures open, including seven source records. `capture-results.json` and `inspection-results.json` record these checks.

The final isolated screenshot server exited cleanly with status0 and removed its scratch database. Existing demo/user records were not reset. To view the built redesign in the normal demo, use the documented `make stop`, `make build`, `make demo` sequence and open `http://127.0.0.1:8080/demo`; demo-only accounts remain in README. Final Git synchronization is reported in the handoff; `Archive.zip` remains unrelated and untracked.
