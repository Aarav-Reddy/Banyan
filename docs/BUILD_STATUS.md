# Build checkpoint — 2026-09-19

## Resumable state

Working branch: `aarav`; no main changes or force pushes. Original proposal, Git instructions and complete build prompt are preserved. Foundation commit `00db4c3` was pushed. This checkpoint integrates the working application; final acceptance is still in progress.

M0/M1/M2 behavior is implemented: PostgreSQL migrations, session/CSRF accounts, isolated workspaces, source-backed directory, financial metrics, exact-cent portfolios, worker imports, card review/sharing, matching, withdrawal and deletion. M3/M4 backend behavior includes fixed pooled analyses, graph edges, watchlists/monitoring, contributor reports/benchmarks, identity claims, password reset, official-source adapters and optional grounded explanations. M5 verification is active. Additional pilot API controls still need frontend integration; no end-to-end completion claim is made yet.

## Observed checks

- Native `make demo` exits 0; HTTP homepage/readiness available at http://127.0.0.1:8080. Stop/restart preserves seeded records.
- PostgreSQL 17.11; Python 3.12.4 in project venv; Node24.14.0; pinned uv0.12.17/pnpm12.4.2; Django5.2.17, Next16.3.5/React19.3.0 from generated lockfiles.
- Full integrated backend rerun: **167 passed in17.76s**. Two earlier fixtures were corrected to require explicit third-party reviewer grants, without relaxing the policy. Ruff check/format and domain/parser mypy checks pass.
- Independent QA: nine PostgreSQL tenant/race tests passed. Tenth suppression/export case added; full run covers it.
- Analytics branch coverage 93%, allocation100% at specialist boundary. Integrated coverage currently73%; final exact report and gaps pending.
- Frontend TypeScript check, seven component tests and production build pass. First four desktop E2E tests exposed selector issues and actual contrast/SVG semantics defects; corrections applied, rerun pending. Eight desktop/mobile journeys exist. Actual discovery/reviewer screenshots opened; full visual QA remains pending.
- Local backup/restore verified43tables/1,137rows with full row hashes. Latest-schema rerun pending.
- Dependency audits with network reported no known Python or JS vulnerabilities. Offline audit unavailability is reported separately.
- Docker is absent; Compose definitions exist but container startup has not been tested here. Native PostgreSQL execution is the tested alternative.

## Important fixes integrated

Source locks fence job completion against withdrawal; alerts record target source revisions as well as evidence lineage. Review assignments cannot expand third-party consent. Allocation edits retain exclusions/caps/minimums and exact budget accounting. Withdrawn previews disappear immediately; required grant attribution travels into artifact JSON/CSV. Private scope is checked before retrieval, matching and pagination. API trailing slash rewriting was verified and corrected through the actual Next proxy.

## Ownership at checkpoint

All specialists paused before coordinator Git operations. Native GPT-6 Astra/high agents performed product, security, data, analytics, backend, frontend, QA and release responsibilities. Tool capacity permits coordinator plus three active workers; custom TOML definitions do not reload this session and native explicit briefs were used. No agent performed Git operations or spawned child agents.

Coordinator now owns integrated files, manifests/locks/contracts, Git, seed and documentation. Next wave: bounded frontend completion of pilot API controls, independent QA rerun and security follow-up. Preserve path ownership and isolate database tests.

## Next actions

1. Finish relevant integration checks, commit and push coherent application checkpoint.
2. Complete pilot controls, attribution rendering, verified public city-context display, source-issue review and complete graph relationships.
3. Run desktop/mobile persisted journeys, fix actual failures; inspect captured screenshots.
4. Finish architecture/data/API/privacy/threat/demo/roadmap docs and operational README; update requirement matrix with exact executable evidence.
5. Final `make verify`, updated restore/restart evidence, independent security review and final commit/push.

## Source boundaries

The Census API missing-key response is not treated as valid data. Local ACS import works with explicit snapshot/geography metadata. A separately stored, manually verified Census QuickFacts extract supplies city-wide2020–2024 income/connectivity context, never ZIP measurements or food-insecurity estimates. IRS XML fixtures are minimal parser fixtures based on inspected2022/2023/2024schemas, not complete tax returns; synthetic parser identifiers never become real EIN claims. No live LLM request was sent.
