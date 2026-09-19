# Philanthra — complete repository build prompt

You are the lead engineer and integrating coordinator for Philanthra. **Build the application in this repository now.** Do not return only a plan, sample snippets, a frontend mockup, or instructions for another developer. Implement, run, debug, verify, and document the complete pilot product described below.

Use **GPT-6 Astra with high reasoning** and real native subagents where available. Follow the root `AGENTS.md`, especially the collaborative `aarav` branch workflow. This is a substantial build: work through bounded milestones and maintain a resumable implementation record. Continue autonomously through ordinary implementation decisions; pause only for a genuine permission/safety blocker or an external capability that cannot be substituted locally.

The requested deliverable is a complete, runnable, deployment-prepared **pilot repository**, not a claim that an unvalidated worldwide philanthropic allocation platform is ready for consequential real-world use. All required pilot features below must be implemented. Do not quietly reduce this to a directory or static demo. Keep later research and licensed enterprise integrations clearly separate from completed functionality.

## 1. Product intent and explicit decisions

Philanthra connects two questions:

1. Where should a donor or foundation investigate allocating philanthropic capital?
2. What should an NGO learn from other organizations before choosing or changing an intervention?

Its shared data model connects **Organization → Program → Problem → Intervention → Population → Geography → Cost → Outcome → Evidence → Funder**. Public financial records and permissioned NGO program data feed both products. The donor product must not obscure evidence limitations; the NGO product must give contributors useful intelligence in return.

The supplied proposal uses the working label “Impact Commons.” **Philanthra is the product/repository name.** Preserve the original proposal and original Git instructions under `docs/source-materials/`. If the repository contains the proposal as `README.md` or `README(1).md`, preserve it before replacing the operational README. Do not overwrite the archive with a generated rewrite.

These are build decisions, not claims from the proposal:

- Start with **Baltimore metropolitan-area food security** for the pilot; retain configurable geography and cause taxonomies.
- Seed 20 fictional local nonprofits, two fictional foundation workspaces, and four explicitly fictional international NGO examples.
- Provide a professional multi-tenant web application with both donor and NGO workspaces, a reviewer workbench, and a shared evidence explorer.
- Use a rules-based financial signal engine until real labeled data can justify probabilistic modeling.
- Use a fully functional deterministic knowledge engine first; an optional LLM enhances explanation rather than powering correctness.
- Treat actual grantmaking, real-world adoption, and outcome validation as human pilot activities. Code must not fabricate these accomplishments.

Retain the broader proposal in product documentation: institutional subscribers, free/subsidized NGO contributors, sponsored data preparation, portfolio monitoring, integrations, API access, custom analyses, white-label opportunities, research partnerships, and eventual international expansion. Do not implement payments or accept a percentage of recommended donations. Never sell ranking position.

## 2. Preflight and real subagent setup

Inspect the working tree, active branch, remote state, instruction files, existing code, runtime tooling, and installed Codex capabilities before edits. Preserve collaborators' work. On an existing checkout not on `aarav`, report the branch blocker without editing. In a truly new directory, `git init -b aarav` is allowed. Do not create `main`, create a remote, or change repository visibility.

Read the entire root `AGENTS.md`, this prompt, the original proposal, and any existing build-status documents. Use current official documentation for APIs and schemas that you need to implement. Record the important sources in `docs/SOURCES.md`. Prefer the supplied, verified source index over guessing URLs. Do not browse with private data in search queries.

Create or validate the following project configuration. The current documented custom-agent format is standalone TOML files, not invented Markdown personas. Retain stricter user/organization permission settings. Do not use dangerous full-access flags to avoid a blocked command.

```toml
# .codex/config.toml
model = "gpt-6-astra"
model_reasoning_effort = "high"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "live"

[agents]
enabled = true
max_concurrent_threads_per_session = 4
default_subagent_model = "gpt-6-astra"
default_subagent_reasoning_effort = "high"
```

Create/validate `.codex/agents/product_architect.toml`, `data_engineer.toml`, `backend_engineer.toml`, `analytics_engineer.toml`, `frontend_engineer.toml`, `qa_engineer.toml`, `security_reviewer.toml`, and `release_engineer.toml`. Each must define its `name`, `description`, and detailed `developer_instructions`, with role-specific ownership and handoff rules. Read-only reviewers use `sandbox_mode = "read-only"`; implementation agents inherit the parent's permissions. Use the included definitions when present rather than replacing them with less specific ones.

Do not assume editing a configuration file reloads the current session. Check whether these agents are callable. Use native built-in agents with the same explicit role brief when custom definitions are not yet loaded. If native delegation is genuinely unavailable, record that fact and perform the same responsibilities sequentially. Do not misrepresent simulated personas as spawned agents.

### Delegation plan

The main agent owns integration, manifests/lockfiles, generated contracts, final decisions, and all Git operations. No subagent may spawn other agents or mutate Git. Maximum four concurrent subagents; close completed threads before opening new ones.

Begin with three bounded parallel reviews: `product_architect` maps requirements and contracts, `security_reviewer` defines the permission/data-threat model, and `data_engineer` inspects official source schemas and proposes fixture mappings without edits. The coordinator inspects the repo and prepares the skeleton. Integrate these findings before schema/API implementation.

Then delegate independent, path-scoped work in waves. Backend owns all database models and migrations; analytics owns pure domain calculations; data owns parsers and ingestion fixtures; frontend consumes frozen APIs. Release work and QA begin as soon as the skeleton permits useful independent work. Reuse specialists for focused fixes and final review rather than asking all agents to redesign everything.

Each assignment must specify objective, allowed write paths, read-only dependencies, frozen interfaces, test expectations, and a short handoff format. Record current ownership. Shared worktree means shared files: do not edit a worker's files while it is active. Run conflicting DB/integration tests serially or in isolated test databases.

## 3. Architecture and repository layout

Use the following default architecture unless the existing repo already has a demonstrably better compatible foundation. Record a concrete reason for deviations; preference alone is not enough to expand the stack.

- Frontend: current supported Next.js App Router, React, strict TypeScript, `pnpm`, a small accessible component system, accessible charting, and local geography assets.
- Backend: current patched Django 5.2 LTS, Django REST Framework, PostgreSQL, Python 3.12 or another compatible supported version, `uv`, pytest, Ruff, and appropriate static typing.
- Authentication: Django server-side sessions, CSRF protection, secure cookie settings, and tenant membership checks. No separate frontend auth database and no browser local-storage tokens.
- Deployment: Docker Compose with database, a one-time migration/init job, API, web, worker, and same-origin reverse proxy. Only the proxy needs a host port for ordinary use. Bind the demo to loopback.
- Background work: a job table and separate worker using leased, retryable, idempotent work items. Use transactional enqueue/outbox patterns where needed. Do not execute long imports inside HTTP requests.
- Search/graph: PostgreSQL full-text and structured filtering, typed entity relationships, bounded graph traversal. No required external graph/vector service.
- Optional AI: server-only provider boundary, default off, typed output validation, grounded citations, consent checks, and deterministic fallback. It must never be required for allocation calculations or authentication.

Suggested structure; modest changes are allowed when they improve clarity:

```text
AGENTS.md
CODEX_BUILD_PROMPT.md
README.md
.env.example
.gitignore
Makefile
compose.yaml
pnpm-workspace.yaml
package.json
pnpm-lock.yaml
pyproject.toml
uv.lock
.codex/config.toml
.codex/agents/*.toml
.github/workflows/ci.yml
apps/web/                       # routes, components, typed client, component tests
apps/api/manage.py
apps/api/config/                # settings, URL configuration, deployment entrypoint
apps/api/philanthra/
  accounts/                     # users, workspace membership, session endpoints
  organizations/                # public identities, filings, service areas
  programs/                     # programs, populations, interventions, outcomes
  evidence/                     # sources, claims, review, graph relationships
  ingestion/                    # adapters, quarantine, mapping, validation
  analytics/                    # pure financial, matching, pooling, allocation logic
  sharing/                      # grants, policy evaluation, withdrawal
  portfolios/                   # donor plans and reviewed snapshots
  alerts/                       # subscriptions, events, user feedback
  audit/                        # security and data-use records
  jobs/                         # worker lifecycle, retries, leases, outbox
packages/api-client/            # generated from OpenAPI; do not hand-edit
schemas/                        # import formats, taxonomy versions, mapping documents
scripts/                        # setup, doctor, seed, smoke, reset safeguards
infra/                          # proxy and container configuration
data/fixtures/                  # small, redistributable fixtures with manifests
tests/integration/
tests/e2e/
docs/                           # design, methodology, data and operations documentation
```

Do not scatter business logic through views. API endpoints call policy-checked services; services call pure calculations or explicit persistence operations. Use database constraints and transactions as well as application validation. Define a versioned OpenAPI contract and generate the TypeScript client after every approved contract change.

## 4. Shared domain contract

Model the public directory separately from private workspace ownership. A user may belong to multiple NGO/foundation workspaces. Do not use one unverified `organization_id` from the browser as both public identity and access authority.

The schema must support the following concepts, using normalized models or clearly justified equivalents:

- User, Workspace, Membership, Role, invitation, and reviewer assignment.
- Organization, external identifier, nonprofit filing, filing revision, funding record, service area, program, funder, and grant opportunity.
- Problem/cause, intervention, target population, context profile, outcome definition, aggregate outcome observation, cost observation, evidence record, and operational/implementation guide.
- Dataset, upload, import job, validation issue, source record, source locator, claim, and claim-to-source relationship.
- Data-use grant with purpose/recipient/cause/geography restrictions; consent/policy revision; analysis release; withdrawal request; and dependent-artifact lineage.
- Financial signal, recommendation draft, review decision, approved recommendation snapshot, portfolio, allocation, alert, alert subscription, and user feedback.
- Immutable application audit events, job execution attempts, feature/plan entitlement, sponsored onboarding request, and pilot metric event.

For relevant records preserve UUID, owner/visibility, source kind, reporting/effective period, created/updated times, provenance, and revision. Store money as decimal or integer minor units with ISO currency; return decimal strings in JSON where precision matters. Store EIN as a string on real U.S. identities, not an integer. Use namespaced external identifiers for international organizations. Synthetic demo entities must not claim real EINs.

An outcome requires definition, unit, direction, numerator/denominator where applicable, measurement window, population, study design, comparator when applicable, sample/cohort identity, missingness, and uncertainty where actually reported. Separate output counts from outcomes. Keep source-reported claims distinct from platform-derived calculations and reviewer opinions.

Define JSON error conventions, pagination, allowed filters, ordering, idempotency keys, resource versions, and structured validation errors. Permissions apply before pagination/counting and before retrieval/scoring. Do not leak private existence through search totals or citation metadata.

## 5. Required product capabilities

Implement every requirement R01–R24. Create `docs/ACCEPTANCE_MATRIX.md` linking each to implementation and executable tests. A screenshot alone does not prove backend behavior.

### R01 — Accounts, workspaces, and legitimate permissions

Build login/logout, current-user/session endpoints, account onboarding appropriate for an invite-only pilot, workspace selection, and membership management. Use roles for foundation administrator/analyst/viewer, NGO owner/editor/viewer, assigned reviewer, and platform administrator. Model real permissions, not only hidden navigation items.

Offer seeded role entry points only in isolated demo mode. Non-demo creation of a workspace must not confer ownership of an existing public NGO identity without a claim/verification review. Invite redemption must be scoped, expiring, and single-use. Password reset can use a local development mail sink; outbound production email needs explicit configuration. Keep login and other unsafe session operations CSRF-protected.

### R02 — Donor discovery

Build an interactive discovery page with cause, ZIP/location, donation budget, population, organization size, risk preferences, desired outcome, and time horizon. Persist query parameters and provide useful empty-state explanations. A result should show mission, service geography, organization size, program-spending data, evidence availability, financial flags, source freshness, and missing information.

Provide synchronized map/list views and a table alternative. Distinguish headquarters from verified/reported service areas. Give donors multiple candidates with inspectable reasons, not a universal opaque score. Search filters and budget changes must actually influence the backend result when relevant. A low budget or unsupported geography must not produce invented matches.

### R03 — Organization detail and comparison

Provide real detail pages: identity/status, mission and programs, multi-year finances, financial signals, program-spending ratio, evidence, local context, funding/capacity disclosures, and source links. Show absent metrics as unknown with an explanation.

Allow comparison of two to four organizations with comparable periods/units and visible caveats. Include a sources drawer showing source type, retrieval date, original location, and transformation. Distinguish externally reported data from NGO-verified information and reviewed platform analysis.

### R04 — Explainable allocation workbench

A donor can create a planning portfolio, select candidates, choose disclosed priorities and risk/capacity constraints, request an allocation draft, edit allocations, and submit for review. Allocation logic is server-side and deterministic. Show which objective and assumptions produced the amounts.

Use exact minor units. Respect total budget, per-organization approved caps, exclusions, and any explicitly implemented minimums. Missing absorptive-capacity information must be visible; require a donor-entered planning assumption or verified request before claiming a capacity-aware allocation. An infeasible request returns reasons and unallocated funds, not a fake complete distribution.

Use a transparent constrained allocation heuristic; do not label it a proven impact optimizer. Retain need, evidence, financial uncertainty, goal fit, and capacity as separate dimensions. Missing data must not quietly become zeros or favorable defaults. Document any heuristic weights as product assumptions. A financially strained NGO may be considered for capacity-building support.

Drafts are visibly unreviewed. Approval binds a specific portfolio version and source snapshot. Later edits, withdrawals, or source changes invalidate approval. Export a human-readable, source-linked report and CSV; no transfer of money and no donation-fee workflow.

### R05 — Foundation portfolio monitoring

Save portfolios and watchlists. Detect new filings/changed signals, changed funding context, newly relevant evidence, stale information, and revoked approvals using real stored revisions. Show geographic coverage and possible gaps or duplication only within explicitly stated data coverage.

Distinguish “little funding recorded in this dataset” from “underfunded in reality.” Show potential collaboration instead of treating overlapping programs as automatically wasteful. Include alert acknowledgement, resolution/feedback, and reproducible trigger explanations.

### R06 — NGO contributor workspace

Give an NGO its own mission/service-area profile, program inventory, outcomes, contributor data-quality checklist, financial context, peer benchmarking, relevant evidence, transfer suggestions, collaboration leads, and funding opportunities. Provide actionable collection suggestions for missing denominators, inconsistent units, absent follow-up periods, and unknown outcome definitions.

Core contributor functions are free in the product entitlement model. Subscription tiers must never change donor ranking. Expose an honest sponsored-onboarding request flow with stored status; do not display nonexistent integrations or fabricated sponsor commitments.

### R07 — Secure data onboarding

Implement CSV and XLSX aggregate-data import with downloadable templates, explicit column mapping, preview, row-level validation, rejected-row export, and idempotent commit. Support UTF-8/BOM, leading-zero identifiers, dates, blank values, currency/units, and duplicate imports. Provide normalized outcome and cost formats.

Support text PDFs and plain-text reports as **quarantined source documents** with text extraction, source/page locators, and a manual structured-evidence drafting/review flow. Do not pretend an unreviewed report has become reliable structured outcome data. Scanned/image-only PDFs may return a clear “text extraction unavailable; provide text or CSV” result. OCR is not mandatory.

Reject beneficiary-level identifiers and unsupported sensitive fields. Suspicious content must not enter analytics, indexing, or external AI processing. Do not assume a simple PII regex proves de-identification. Keep raw files private, short-lived, size-limited, and separable from approved normalized records. Do not retain unmapped raw columns indefinitely.

Jobs expose actual stages: queued, processing, needs input/review, completed, failed, canceled. Preserve validation errors without logging private row contents. Imports must be resumable or safely retryable and must not duplicate records after retries.

### R08 — Intervention cards and implementation knowledge

Build structured cards explaining problem, intervention, delivery partner, target population, geography, cost, outputs, outcomes, follow-up, implementation steps, operational barriers, failures, caveats, attribution, and evidence sources. Record both successful and discontinued approaches.

Use the proposal's evidence labels, but store underlying study design separately from repetition and expert review. Human editorial review cannot transform an observational report into a randomized evaluation. Each significant claim has a supporting source locator or is explicitly labeled an analyst hypothesis.

Cards can be drafted, edited, reviewed, shared under a data-use grant, saved, and withdrawn. Include attribution and contact/introduction options only when permissioned and actually available. Do not invent quotes, staff names, or contact information.

### R09 — Context-aware NGO recommendations and alerts

Match an NGO's planned/existing program to relevant interventions using cause, population, outcome definition, delivery mechanism, setting, duration, infrastructure, resource level, and contextual constraints. Country identity alone is neither proof of transferability nor a reason to reject useful evidence.

Return why matched, important similarities, important differences, missing context, failed/contradictory evidence, evidence strength, and adaptation questions. Label the result a transferability heuristic, not an externally validated likelihood of success.

After a newly approved eligible card or program-profile change, the worker recomputes relevant recommendations and creates deduplicated **in-app** alerts. Support subscription controls, read/dismiss/save, relevance feedback, and “adopted for a pilot” with an owner note. Email delivery is optional and separately configured. The Ethiopia/Mexico illustration must remain clearly fictional in demo data.

### R10 — Cross-NGO pooled evidence, not just document search

Implement an actual analysis workbench for compatible **aggregated** observations from multiple consenting NGOs. Demonstrate the essential idea that a shared, permissioned analysis can reveal a pattern that is not visible in one NGO's small dataset.

The initial supported analysis may be intentionally narrow: one normalized binary outcome, comparable periods/populations/interventions, and explicitly disjoint cohorts, with organization-level rates, sample-size-weighted descriptive rates, and equal-organization summaries. Additional analysis types are optional, not excuses to skip this working case.

Require compatible definitions, units, orientation, time windows, cohort independence, and declared purpose before combining. Detect duplicate cohort/study reports. An org count is not an independent-study count. Show per-organization results, heterogeneity, exclusions with reasons, and sample coverage. Never convert a pooled association into a causal claim or report unsupported statistical significance.

Use a synthetic multi-organization fixture that demonstrates a shared pattern, an incompatible-data fixture that is correctly rejected, and a heterogeneous/Simpson's-paradox fixture that is flagged instead of averaged into a misleading conclusion. Any interval requires a defensible method and actual necessary inputs; otherwise say uncertainty cannot be estimated.

Publish only approved, fixed analysis releases after privacy checks. Default release thresholds are a configurable **10 participants per disclosed contributing cell and 3 independent contributing organizations**, not legal guarantees of anonymity. Use stricter constraints where needed. Prevent complementary totals and arbitrary filter combinations from reconstructing suppressed information. Unknown cohort overlap means “not poolable,” not “assume independent.”

### R11 — Shared knowledge graph

Store and visualize real relationships among organizations, programs, causes, interventions, populations, geographies, costs, outcomes, evidence, and funders. Clicking an edge shows its meaning and supporting records. Provide list/tabular navigation for accessibility and small screens.

Enforce bounded graph queries and permissions before traversal. No private edges, counts, titles, or source existence may leak through an otherwise public graph. This graph must support retrieval/explanations rather than exist as an ornamental animation.

### R12 — Source provenance and reproducible claims

Provide a source registry and claim-level source links across profiles, charts, cards, alerts, allocations, and exported reports. Store source version/checksum, source type, retrieval/publication/reporting dates, parser version, and field/page/row/XML locator as appropriate.

A derived metric records formula version and all input references. A recommendation records its input snapshot, policy version, method version, and reviewer state. Citations are permission-checked. “Open original source” may link to an authoritative public URL; private uploads require authenticated access. Never create a plausible-looking source URL for a synthetic example.

Show source-freshness limitations. Do not silently merge original and amended filings, infer values from a missing field, or treat retrieval time as event time.

### R13 — Financial resilience signals and honest model evaluation

Compute applicable metrics from normalized inputs, with explicit validity checks:

- Program-spending share = program expenses / total expenses, only when denominator is positive and comparable fields exist.
- Operating margin = (revenue − expenses) / revenue, only for positive revenue; show the underlying deficit amount separately.
- Liabilities/assets only for positive assets. Record negative net assets separately rather than inventing a ratio with a zero denominator.
- Revenue/expense growth only with comparable consecutive periods and valid nonzero baselines; use an explicit policy for negative or exceptional values.
- Repeated deficits, shrinking program expenses, unsupported expense growth, revenue variability where enough comparable periods exist, leverage, and reported cash/liquidity information where supported.
- Filing freshness and completeness as data-quality signals, not automatic proof of financial distress or wrongdoing.

Preserve one-off grants, accounting changes, pandemic disruptions, and short fiscal periods as comparability caveats where known. Funding-source concentration requires actual source-level funding data; revenue categories alone are insufficient. Cash months require actual eligible cash data and an explicitly stated restriction limitation; net assets are not cash.

Return versioned signal labels, thresholds, source inputs, direction, missingness, and explanation. Any baseline threshold is a configurable policy assumption, not a validated prediction. Do not output a numeric “chance of collapse” in the pilot.

Implement a reproducible evaluation harness that can consume a properly labeled historical dataset in the future: documented label definition/horizon, data availability cutoff, temporal splits, organization grouping, class-balance reporting, calibration/discrimination metrics where estimable, and comparison to a simple baseline. Include leakage tests. Synthetic tests validate the harness only; without real labels, a real validation command must return an honest unavailable/not-validated status. Auto-revocation or missing filings must not silently become a bankruptcy label.

### R14 — Working public-data adapters

Implement real adapters with small fixture-backed tests and explicit opt-in network commands. Default setup must not download huge archives.

**IRS:** Parse the official index and supported full Form 990 XML variants into normalized identity, period, revenue, expense, assets/liabilities, program descriptions, and program-expense fields that actually exist. Support three tax-year fixture versions with inspected mappings. Handle namespaces, amendments, unavailable fields, duplicates, and malformed inputs. Support 990-EZ for the metrics it actually supplies; identify 990-PF separately as foundation data; treat 990-N as limited filing/status information rather than detailed finances. Unsupported variants return structured diagnostics, not fabricated success.

Provide bounded index/filter/download ingestion where official distribution permits it and a local archive/file ingestion path when individual download is unavailable. Check archive expansion and paths. Source discovery must use actual index/distribution documentation instead of guessed object URLs.

**Tax-exempt/status data:** Import an EO BMF state CSV and independently sourced TEOS/revocation records when provided. Show source/date/status uncertainty; headquarters location is not service geography and revocation is not proof of insolvency. Do not certify deductibility from an unverified status inference.

**Census/context:** Implement a configurable ACS five-year adapter using verified variables and supported geography levels, and a local file mode with recorded snapshot year, estimate, margin of error, denominator, and boundary/crosswalk vintage. Never silently substitute county data for a ZIP-level measurement.

**IATI:** Implement a standards-based activity XML importer for identity, participating organizations, countries/sectors, budgets/transactions, document links, and reported results where present. Distinguish targets from actuals and commitments from disbursements; avoid duplicate transaction totals. IATI activity publication is not proof of intervention effectiveness. Network retrieval can be optional, but local standards-based import must work.

Use source manifests and redistribution/licensing notes. Candid and other commercial APIs require permission/credentials; provide a clean extension interface and explicit unavailable status, not scraping or a fake operational integration. Add a documented manual registry/grant/annual-report import path rather than inventing worldwide source coverage.

### R15 — Community context and fair comparison

Link each program to known setting, income/cost context, infrastructure, public services, population characteristics, language/cultural context, delivery partner, duration, and resources where provided. Record missing fields rather than inventing values for a country or demographic group.

For the initial donor map, show a small set of verifiable community-need indicators such as poverty or other appropriately sourced proxies. Do not call an income indicator a direct measurement of food insecurity. Geographic overlap must use service areas or explicitly labeled approximations. Preserve the distinction between USPS ZIP and Census ZCTA.

Benchmarks compare compatible causes, sizes, periods, and contexts with clear sample coverage. Missing reporting and a small organizational budget must not automatically push an NGO below more polished organizations. Show uncertainty and sensitivity of planning heuristics to weights/missingness.

### R16 — Consent, sharing, withdrawal, and auditability

Owners set purpose-specific grants for benchmarking, pooled analysis, donor access, publication, and external AI. Represent permitted recipients, geography, cause, expiration, and attribution requirements. Default is private. A unsupported policy combination fails closed; never ignore restrictions because the UI did not expose them.

Apply policy to source access and derived artifacts. Combining multiple restricted sources requires all applicable grants, not the most permissive source's grant. Authorization is checked when jobs execute and when outputs are viewed/exported, not only when work is queued.

On withdrawal, immediately block new use and serving of affected derivatives. Invalidate summaries, cached retrieval, graph paths, published analysis releases, alerts, and recommendation approvals. Cancel or reauthorize pending work. Complete physical deletion asynchronously with observable status and bounded retries; retained audit entries must avoid private content. Document backups and external exports honestly: previously downloaded files cannot be remotely recalled.

Expose an NGO-visible data-use activity log and a platform audit trail for review, imports, sharing, exports, and deletion. Do not advertise tamper-proof audit logs if they are merely application-enforced append-only records.

### R17 — Human review workbench

Provide an assigned-reviewer queue for intervention cards, shared analysis releases, consequential recommendations, source issues, and identity claims. Reviewers can request changes, approve, reject, or withdraw a particular revision with a reason.

Enforce appropriate separation between contributor and reviewer, scoped source access, and no self-approval for consequential publication. Approved output includes reviewer identity/role, timestamp, scope, caveats, and source snapshot. Changed inputs invalidate review. Ordinary admins do not gain unlogged blanket private-data access through this workbench.

In demo mode, approvals by demo accounts are clearly demo events. Real human expert review is a pilot requirement, not something an automated coding agent has completed.

### R18 — Optional grounded AI explanations

Provide an optional server-side OpenAI Responses API adapter behind `PHILANTHRA_LLM_PROVIDER=none|openai`, explicit key configuration, and a separate configurable application model. The coding model selection is not an application credential or a promise of free model access.

The default `none` provider still supports search, structured transfer matching, pooled analyses, readable explanations, and report generation. A network/API failure falls back cleanly. Do not send request traffic during ordinary tests; use provider-boundary tests and an explicitly enabled live smoke test.

Before generation, retrieve only authorized, non-revoked, shareable evidence and check external-processing permission. Validate structured output, source IDs, numerical claims, and evidence labels. Rendering must clearly distinguish generated synthesis from source quotations. Prefer dropping an unsupported claim to inventing a citation. Do not send arbitrary untrusted report instructions to tools or give the explanation model autonomous database/file/network access.

Implement tests for source prompt injection, irrelevant/unsupported citations, empty evidence, revoked evidence, malformed output, timeout, and accidental private-data egress. Logs contain operational metadata, not full private prompts.

### R19 — Reporting, funder matching, and contributor value

Implement source-linked portfolio reports, an NGO impact-report draft, data-quality feedback, and a permission-safe aggregate export. Reports identify missing information, synthetic data, and review status. Generate printable HTML with a working print stylesheet plus CSV; automated PDF generation is optional.

Provide a small manually curated/importable grant-opportunity catalogue with real stored eligibility, geography/cause, deadline, source, freshness, and explicit synthetic labeling for demo entries. Match to NGO profiles with eligibility explanations; do not claim complete market coverage or submit applications.

Provide collaboration/introduction requests with stored state and permissioned contact details. Actual outbound introductions, grant submissions, billing, and payment processing require separate user authorization and configured integrations. The pilot UI must be honest about this boundary rather than presenting dead controls as live features.

### R20 — Deterministic, genuinely connected demo

Seed through the same backend/domain services used by the app, not static frontend arrays. Use a fixed seed and a documented demo clock. Include:

- 20 fictional Baltimore-area nonprofits with varied sizes, service areas, evidence completeness, and three years of plausible financial fixtures.
- Two foundation workspaces, accounts for each role, and at least four separately permissioned NGO workspaces to exercise pooled evidence and isolation.
- Four fictional international examples illustrating contextual transfer; none are asserted real partners or real studies.
- At least 24 intervention cards, 60 aggregate observations, 8 local geographic/context areas, 6 alerts, and 3 portfolio drafts with different constraints.
- Cases for high program spending but weak evidence, lower program-spending share with stronger evidence, repeated deficits, one-time revenue, unknown capacity, limited 990-EZ data, amended filings, stale sources, missing denominators, contradictory outcomes, and successful implementation learning.
- A real calculated cross-NGO descriptive pattern, an incompatible analysis rejection, and a suppression case.

Separate synthetic sample data from any downloaded real public fixtures. Demo organization names/EINs/contacts must not impersonate actual NGOs. All relevant UI panels and exports visibly identify demo content. The same import, calculation, review, permissions, and persistence logic must work on non-demo authorized data.

Provide a short demonstration script showing donor discovery → compare → draft allocation → review → report, then NGO upload → validate → intervention card → share → cross-NGO analysis → matched alert → withdraw → invalidated derivative. These state changes must actually persist.

### R21 — Complete interface and accessibility

Implement an intentional visual system with readable typography, off-white/neutral surfaces, dark readable text, a restrained green/teal accent, and distinct warning/review states. Use evidence and financial data as the visual focus. Avoid generic AI-generated slogans, fake customer logos, arbitrary progress rings, and excessive marketing decoration.

Required navigable areas: landing/demo entry, discovery, organization detail, comparison, allocation, saved portfolios, NGO dashboard, upload/import status, program/card editor, evidence library, pooled analysis, graph explorer, alerts, sharing/settings, reviewer queue, sources/methodology, and administration as appropriate.

Every core route needs loading, empty, error, permission-denied, insufficient-data, and review/withdrawal states where applicable. Layouts must work on a 1440px desktop and a 390px mobile viewport. Use visible form labels, keyboard focus, non-color status indicators, accessible dialogs, and readable table alternatives to visualizations. Avoid remote fonts, map tiles, or CDN assets in the offline demo. A schematic map must be labeled schematic rather than presented as an accurate boundary map.

Use browser testing and inspect actual screenshots. Fix clipped controls, broken charts, hydration failures, console errors, and awkward empty states. Do not claim a visual review without opening the rendered result using the available browser/image tools.

### R22 — Operational safety and reproducibility

Provide configuration separation for demo, development, test, and production. Production must refuse to boot with demo credentials/auth shortcuts, debug settings, missing secrets, wildcard allowed hosts, or insecure required settings. Document TLS and real encryption-at-rest requirements; do not claim local filesystem storage is encrypted by application code unless implemented.

Secure upload storage, parser limits, anti-XXE handling, spreadsheet safety, CSV export safety, SSRF prevention, password/session handling, rate limiting, and tenant-aware logs/caches must be tested. Never disable CSRF or broadly trust `Origin: null` to make a demo work. Correct the proxy/origin configuration instead.

Include health/readiness endpoints, structured redacted logs, request/job correlation IDs, migration management, backup/restore instructions with a tested local restore path, and worker recovery behavior. Distinguish transaction durability from best-effort logging.

Create actual `make doctor`, `make setup`, `make demo`, `make dev`, `make check`, `make test`, `make test-e2e`, `make build`, `make smoke`, and `make verify` targets. `make demo` builds/starts required services, runs migrations safely, seeds only an explicitly identified demo database, waits for readiness, and prints the URL plus demo access instructions. Re-running it must not erase user-created data. Provide a guarded `make reset-demo CONFIRM=philanthra-demo` limited to the known demo environment.

Initial dependency/image installation may require internet. After setup, default tests and the seeded demo work without live external APIs. Include a quoted-path macOS `Start Philanthra Demo.command` launcher and Linux/macOS terminal instructions. Do not require altering the user's global conda installation.

CI must run formatting/lint/type checks, backend/frontend tests, migration drift detection, API-client drift detection, build, and real-backend E2E tests. Use a PostgreSQL test service, isolated credentials, pinned compatible tooling, and meaningful dependency/security checks. Network-dependent audits should be reported distinctly; do not mislabel an unavailable audit as passed.

### R23 — Pilot measurement and accountability

Implement tenant-aware event/feedback capture and a small pilot metrics view/export. Track the proposal's outcomes where actual pilot input makes them measurable: previously overlooked grantees funded, funding reaching high-need areas, donor research time, usefulness/accuracy of alerts, insight adoption, data-quality improvement, implementation cost avoided, outcome changes after adoption, and continuing contributors.

Define each numerator, denominator, timeframe, and collection method. Mark missing ground truth as unavailable. Grant drafts are not completed grants; clicking “save” is not adoption; fictional seed events are not traction. Outcome improvement is not automatically caused by Philanthra. These measurements are opt-in, privacy-preserving, and do not require third-party analytics.

### R24 — Interoperability and honest expansion boundaries

Expose the implemented authenticated API through OpenAPI, typed clients, import templates, and permission-safe exports. Document how an authorized adapter can add country registries, licensed funder data, nonprofit monitoring-system exports, and new context/evidence types without bypassing policy or provenance.

Implement the local import/export and API paths now. Document but do not pretend to have completed: blanket worldwide coverage, Candid access without a license, direct integrations for every NGO system, production billing, automatic grant submission, federated analysis, secure enclaves, advanced causal inference, validated distress probabilities, enterprise SSO, or a real governance council. A short extension boundary is acceptable; an unimplemented core path hidden behind a TODO is not.

## 6. Verification: tests that must expose real failures

Create tests as implementation proceeds. Critical policy and numerical behavior needs hand-checkable examples and property-based cases, not only snapshots of your own output. Every R requirement needs mapped verification. Do not target an arbitrary test count; target failure modes.

At minimum, verify:

1. Fresh setup, migrations, seed idempotency, service readiness, restart persistence, and the documented demo command.
2. Login/logout and CSRF on unsafe requests including login. No demo shortcuts in production.
3. Cross-tenant list/detail/mutation/export/search/graph/citation/job access is denied, including guessed IDs, forged owner IDs, and leaked existence/counts.
4. IRS form/year/namespace variants, missing versus zero, malformed XML, amendment selection, duplicates, and source-period handling.
5. Money precision, invalid denominators, short fiscal periods, negative/exceptional values, unknown capacity, and non-comparable metrics.
6. Allocation determinism, caps, exclusions, exact budget accounting, small/remainder amounts, zero candidates, infeasibility, and preserved unallocated funds. A changed relevant input must alter or explain unchanged output.
7. CSV/XLSX mapping and validation, malformed/oversized/bomb files, rejected sensitive columns, formula-injection-safe exports, and document quarantine.
8. Actual source-adapter normalization for ACS/IATI, target-versus-actual distinction, geography mapping, unknown fields, and absent network credentials.
9. Cross-NGO compatible pooling, incompatible outcome rejection, cohort duplication/overlap rejection, contradictory evidence, and heterogeneity warnings.
10. Release thresholds, complementary suppression, repeated queries, and inability to reconstruct suppressed cells from totals/exports/citations.
11. Grant-purpose/recipient/cause/geography enforcement and restriction intersection on derived artifacts.
12. Withdrawal immediately prevents access, invalidates derived caches/alerts/approvals, and cannot be defeated by a job already queued or running. Test transaction/race boundaries, not only sequential happy paths.
13. Reviewer separation, version-bound approval, rejected publication, and stale-source invalidation.
14. LLM absence, timeout, invalid output, fabricated citation rejection, prompt injection, and nonconsensual egress denial.
15. Worker retry, lease expiry, crash recovery, duplicate delivery, and concurrent import idempotency.
16. Financial-model evaluation refuses to call synthetic labels real validation and blocks future-information leakage.
17. Public-source fetches reject unauthorized hosts, private/loopback/metadata addresses, malicious redirects, and oversized responses; fixtures must not make real network requests.
18. Browser journeys for donor and NGO workflows, reviewer approval, pooled analysis, permissions, and withdrawal; assertions must observe actual persisted backend changes, not mocked browser API success.
19. Desktop/mobile rendering, keyboard operation, chart/table accessibility, and useful no-data/error states.
20. Export provenance, synthetic labels, missing-data caveats, accurate metric definitions, redacted logs, and a local backup/restore round trip.

Aim for strong branch coverage on money calculations, permissions, and consent/withdrawal modules; report actual coverage and gaps. Do not remove useful tests or dilute assertions to meet a number. Isolate test databases and freeze time. Keep optional live-source and live-model smoke tests explicitly separate from deterministic CI.

## 7. Milestones and integration gates

Create a concise dependency-aware plan, then execute it. Do not spend the session producing more planning files than software.

**M0 — Foundation and contracts.** Preflight; archive inputs; real subagent setup; architecture/permission decisions; requirement matrix; schema/API skeleton; environment and Compose skeleton; initial auth/health and test harness. Lock interfaces before parallel implementation.

**M1 — Working donor vertical slice.** Seed actual backend records; ingest a financial fixture; calculate real metrics; discover/view/compare organizations; create a persistent allocation draft. Establish provenance and tenant isolation from the first slice.

**M2 — Working NGO vertical slice.** Upload and validate aggregate data; persist a program and intervention card; review/share it; create a real matched recommendation/alert; revoke the grant and verify access denial. Do not postpone privacy until the end.

**M3 — Shared intelligence and portfolio monitoring.** Compatible cross-NGO analysis, incompatibility/suppression handling, knowledge-graph navigation, watched portfolios, review-bound reports, contributor benchmarking/funder matching, and pilot feedback.

**M4 — Data adapters and optional AI.** Complete IRS/status/context/IATI adapter coverage and fixtures, deterministic explanations, optional grounded provider, evaluation harness, and appropriate diagnostics. Keep the offline product working throughout.

**M5 — Hardening, usability, and release.** Independent QA and security reviews; fix findings; inspect actual pages; confirm fresh setup, offline runtime, and restart behavior; full verification; precise runbooks and handoff.

Each milestone requires runnable behavior, relevant passing checks, updated acceptance/status records, a reviewed coherent commit, and a push to `origin/aarav` when permitted and available. Subagents finish writes before integration/Git mutation. Run the full suite after final functional changes, not after every minor documentation edit.

Build in this order to protect a coherent application, **not** to justify stopping after M1 or M2. Continue through all required milestones within the available execution session. If a real interruption/capability limit occurs, leave an exact checkpoint and honest blockers; never announce that unstarted work is finished or will run invisibly later.

## 8. Required documentation and final handoff

Create an operational README with exact prerequisites, quickstart, credentials restricted to demo use, screenshots actually captured, commands, tests, architecture overview, data/source modes, and limitations. Preserve original proposal content in its archive.

Create concise, useful versions of:

- `docs/BUILD_STATUS.md` and `docs/ACCEPTANCE_MATRIX.md` with actual evidence.
- `docs/ARCHITECTURE.md`, `docs/DATA_DICTIONARY.md`, and `docs/API.md`.
- `docs/METHODOLOGY.md` covering formulas, warning thresholds, planning weights, transfer matching, pooling criteria, suppression, uncertainty, and limitations.
- `docs/PRIVACY_AND_GOVERNANCE.md` and `docs/THREAT_MODEL.md`.
- `docs/DATA_SOURCES.md` with supported fields/variants, provenance/licensing, refresh limits, and honest integration status.
- `docs/DEMO_SCRIPT.md`, `docs/DEPLOYMENT.md`, and `docs/OPERATIONS.md` with local recovery/restore instructions.
- `docs/MODEL_CARD.md` describing the rules engine and the unvalidated/disabled status of any probabilistic experiment.
- `docs/ROADMAP.md` retaining the proposal's commercial/international/research direction without pretending it was built.

End with a factual handoff: what works, exact launch command, observed checks/results and limitations, real demo routes/access, actual commit and push status, acceptance gaps if any, and production prerequisites. Do not dump thousands of lines of code into chat; the deliverable is the repository.

**Begin with preflight and real bounded delegation, then implement.**
