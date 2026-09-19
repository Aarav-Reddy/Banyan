# Build status — 2026-09-19

## Repository and milestones

The runnable pilot is implemented on `aarav`. No main changes, force push, invented remote, payment workflow or public deployment occurred. The original proposal is archived byte-for-byte (SHA-256 `d599bff2bdba60792f1ec7024835ede99071db77e6c5a9cba0c48cb521e8a0a4`), along with original Git instructions and the complete build request. Foundation commit `00db4c3` and integrated application commit `4f50a0e` were pushed to origin/aarav. The final release commit is the commit containing this checkpoint; consult `git log -1` for its ID.

| Milestone | Delivered behavior |
| --- | --- |
| M0 | Preflight, archived inputs, native specialist reviews, TOML role definitions, architecture/contracts, normalized schema, auth/health, environment and test harness. |
| M1 | Backend-seeded directory, fixture financial ingestion/signals, discovery/detail/comparison and exact-cent persistent allocation with provenance and isolation. |
| M2 | Mapped aggregate upload, leased worker validation/commit, program/card editing, independent review, purpose-specific sharing, matching/alerts, withdrawal and deletion. |
| M3 | Fixed pooled binary analysis/suppression, graph, source-bound reports, watchlists/periodic monitoring, current geographic coverage, benchmarks/opportunities, identity/contact/onboarding and opt-in metrics. |
| M4 | Inspected IRS/status/ACS/IATI local adapters, bounded opt-in source fetching, manual catalogue import, deterministic explanations, optional grounded provider and honest evaluation harness. |
| M5 | Full interface, desktop/mobile persisted journeys, independent security/race regressions, production guards, setup/restore/restart checks, source-linked docs and handoff. Compose verification remains external. |

## Observed final checks

Native environment: macOS ARM64; PostgreSQL 17.11; project Python 3.12.4; Node 24.14.0; pinned uv 0.12.17 / pnpm 12.4.2. Lockfiles resolve Django 5.2.17, Next 16.3.5 and React 19.3.0.

| Command / check | Observed result |
| --- | --- |
| `make doctor` | Passed; Docker absent, native PostgreSQL detected. |
| `make setup` | Passed using frozen lockfiles and registry access; 68 Python packages checked, JavaScript lock unchanged. Initial sandbox DNS failure was not treated as success. No global conda modification. |
| `make verify` | Passed, exit 0: **192 backend tests in 49.27 seconds, 13 component tests, 14 browser tests**, production build, checks and real-backend smoke. |
| `make check` (within verify) | Ruff lint/format, domain/parser mypy (14 files), Django system/migration drift, Prettier, strict TypeScript and generated OpenAPI/client drift passed. |
| `make build` | Production Next build passed. |
| Real-backend browser tests | Passed all fourteen cases across 1440px desktop and 390px mobile; main contexts block external destinations and use real local API responses. |
| `make smoke` | Passed fresh migrations/seed, readiness, session/CSRF login and persisted discovery. |
| `make demo`, repeated `make stop`/`make demo` | Passed actual loopback readiness. Rapid restart regression fixed; **183 records across seven domain tables** retained matching full-row hashes. Running URL: http://127.0.0.1:8080/demo. |
| `make restore-test` | Passed isolated scratch restore: **49 tables / 1,244 rows**, full-row SHA-256 hashes from the same PostgreSQL snapshot. Scratch database removed. This does not certify future backups. |
| Dependency audits | Earlier Python and JavaScript network advisory audits reported no known vulnerabilities for these lockfiles. No dependency changes followed. Network audits are separate from the deterministic gate. |
| Optional live provider smoke | Explicitly running without its opt-in flag produced **1 skipped**, no network. Not part of default test collection; no live model test success is claimed. |
| Original archive and diff | Original README blob equals archived proposal byte-for-byte; `git diff --check` passed. |

## Coverage and what it proves

Backend coverage includes branch measurement: approximately **81.6% line coverage and 65.6% branch coverage** (combined pytest-cov display 78%). Allocation has **100% line and branch coverage**; pooling 97.4% lines / 95.2% branches; policy 80.4% / 71.9%; core transactional services 90.1% / 72.6%; worker 83.2% / 64.1%. These are observed module coverage, not claims of exhaustive security. API orchestration branches, operator CLI error variants, graph variants and rare worker recovery paths have lower coverage. Browser execution is separate and is not merged into Python coverage. See generated local `coverage.xml` for exact statement/branch counts: 3,780 / 4,631 lines and 940 / 1,432 branches.

Tests use hand-checkable financial/pooling examples, Hypothesis allocation properties and real PostgreSQL concurrent transactions. Independent regressions verify queued edits, publication and workers waiting behind withdrawal locks, stale lease fencing, reviewer authority, private existence/count/citation/export isolation and identity invalidation. Default tests never call live external data/model services.

## Inspection, findings and ownership

Actual desktop/mobile screenshots were captured and opened using image tools. Discovery passed configured axe WCAG A/AA checks and keyboard/overflow/console assertions at both widths. This is not application-wide accessibility certification. Representative review, analysis, portfolio and NGO views were inspected; screenshots prove rendering, not backend/scientific correctness.

Security findings and focused rechecks are in SECURITY_REVIEW.md; independent journey evidence is in QA_REPORT.md. Fixed integration defects include reviewer privilege escalation, authorization after a blocked edit, stale identity linkage, production host defaults, opportunity lookup, forgotten attribution, source/target alert invalidation, hidden match titles, missing-numerator collection prompts, contrast/SVG semantics, synthetic service-area omission and TCP TIME_WAIT restart handling. Assertions were retained when fixing defects.

Native GPT-6 Astra/high agents performed product, security, data, analytics, backend, frontend, QA and release responsibilities through bounded assignments. Custom TOML definitions do not reload this session; equivalent explicit native role briefs were used. All specialist threads completed and handed ownership back before Git operations. No subagent spawned another agent or mutated Git. Coordinator owns the final integrated files, manifests/contracts, documentation and Git.

## Acceptance boundaries and next operator actions

R01–R24 are mapped to implementation and executable checks in ACCEPTANCE_MATRIX.md. The final independent read-only audit found and rechecked the workspace-creation UI and portfolio geography additions; no material concern remained from that bounded review.

- **Docker/Compose has not been executed here** because Docker is unavailable. Linux/fresh clone on another machine, production TLS/proxy, real email, encrypted production storage/backups, operational load and remote CI are not claimed verified. Run the documented Compose/fresh-clone gate before deployment.
- Fixtures cover inspected minimal IRS variants, not every authentic filing. IATI/status adapters preserve source-reported registry structures; they do not manufacture validated program outcomes. Public community context is a narrow city QuickFacts extract, not ZIP-level food insecurity. Grant eligibility text requires human confirmation beyond the implemented cause/geography match.
- No real labeled financial evaluation, live provider request, real grant, pilot adoption, expert review, outcome improvement, sponsor commitment or governance council is claimed. Optional and licensed integrations remain explicit extension boundaries.
- Production requires dedicated clean storage, strong secrets, exact hosts/HTTPS origins, TLS, encrypted disks/backups, retention/withdrawal replay, configured delivery/monitoring, qualified independent reviewers and human pilot governance. Demo credentials/data must never be promoted.

To resume development: read this checkpoint and AGENTS.md, fetch origin on aarav, keep isolated test databases, make a bounded change and rerun relevant gates. To run the pilot now: `make demo`; use the README's demo-only accounts. No work is promised to continue invisibly after handoff.
