# Philanthra UI redesign

Presentation-only refinement, 2026-09-19. The existing Next/React/custom CSS application, routes, backend, API transport, payloads, defaults, calculations, permissions and package versions remain unchanged. No production deployment. Screenshots contain only fictional records from isolated test databases; existing user/demo records were not reset.

## Direction and decisions

- Near-white canvas, white task surfaces, charcoal text and a restrained deep-green accent. Local system sans-serif, readable 15px body/13–14px supporting text, 28–30px workspace titles, modest radii, visible focus, tabular financial values.
- Grouped foundation funding/evidence/monitoring navigation and nonprofit programs/learning/monitoring navigation. Utilities separate. The existing foundation-kind and reviewer-role conditions are preserved. No route authorization is inferred from a label.
- Mobile navigation expands in document flow, moves focus to its close control, supports Escape and restores focus to its trigger. It does not overlay controls or trap focus.
- Discovery retains search/cause/service area above a mounted “More filters” disclosure. Additional set values remain indicated. One explicit submit preserves original query keys and cents conversion. Native validation and invalid budget errors reveal the affected field. List positions remain schematic markers, not ranks.
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

## Before/after evidence

`docs/screenshots/ui-redesign/before/`: 28 fresh PNGs, 14 surfaces at 1440×1000 and 390×844, filenames identify surface/role/viewport. Captured with original production build using the documented isolated test server, actual synthetic save/review/upload/analysis operations. No page errors observed by capture script. Existing historical `docs/screenshots/*.png` remain references only and are not baseline test evidence.

After evidence and final results are appended after actual execution. Full-page images show content reachability; viewport images support first-glance review. Screenshots are visual evidence, not user testing or accessibility/scientific certification.

## Verification log

- Initial Git preflight: `aarav`, intended existing origin, remote synchronized. Untracked `Archive.zip` preserved.
- `.venv/bin/python scripts/e2e-server.py`: original build baseline started after normal loopback escalation; fresh isolated DB migrated/seeded/worker-drained. Shut down cleanly after capture.
- `node /tmp/philanthra-ui-baseline.cjs`: exit0, 28 screenshots, no pageerrors; installed Chromium required normal escalation.
- First integrated presentation: `bash scripts/pnpm check`, `bash scripts/pnpm test` (14 tests), `bash scripts/pnpm format:check`, `make build`: all exit0. This precedes expanded redesign tests; no later result is implied.
- Source diff/handler audit: routes, API paths, request/form handlers, existing hook dependencies and form values preserved. Additional state is presentation-only (mobile navigation, advanced-filter indication, print disclosure restoration).

Remaining verification: expanded component/browser checks, responsive and axe/keyboard inspection, after screenshots, final `make verify`, staged review/commits/push. Production prerequisites in README and BUILD_STATUS remain unchanged.
