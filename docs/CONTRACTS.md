# Integration contracts v1

## Transport

Base `/api/v1/`; trailing slash accepted. Django session cookies, CSRF token from session response and X-CSRFToken for every unsafe request including login. X-Workspace-ID chooses a validated membership, never authority. Success `{data, meta}`; errors `{error: {code, message, fields}}`. Lists are scoped before counts and pagination; page_size maximum 100. UUID strings. Monetary observations decimal strings with ISO currency; allocation amounts integer minor units. JSON null denotes missing data, never inferred zero. Private missing/unauthorized objects return identical 404. Reviewed updates require integer revision; stale 409.

## Persistence and policy

Public Organization is independent of Workspace ownership. Source records have owner (nullable only for vetted public/synthetic directory records), kind, revision, checksum, locator, reporting/retrieval dates, active/withdrawn state. Private datasets and all artifacts retain source dependencies. Grants combine purposes, recipients, causes, geographies and expiry within a complete tuple. Unknown scope fails closed. External AI always requires separate permission. Approved artifacts are immutable snapshots and are unusable when any recorded source/grant revision changes. Withdrawal and publication lock the same source rows; workers reauthorize before committing. Platform staff have no implicit private access.

## Pure analytics boundary

Modules under `philanthra.analytics` import no Django models. Functions accept normalized dictionaries/lists and return JSON-compatible dicts. Financial inputs decimal strings/null; allocation budgets/caps/minimums integer cents; deterministic tie-break by stable identifier. Pooling inputs include organization_id, numerator, denominator, cohort_id, study_id, independence assertion, outcome definition/unit/direction/window/population/intervention/comparator and context strata. No unknown overlap assumption. Complete signatures are frozen with implementer before integration.

## Parser boundary

Modules under `philanthra.ingestion` parse bytes into `{records, diagnostics}` with explicit field locators, source metadata, decimal strings/null. No database writes or network during ordinary tests. Quarantine row validation is distinct from approval and sharing. Parsers reject executable/sensitive/unmapped content, bounded archives and XML entities. Persistence is owned by backend services.

## Demo

All seed content explicitly synthetic; fixed clock 2026-09-01T12:00:00Z. 20 local organizations, four international illustrations, two foundation workspaces and four NGO workspaces minimum. Demo seeding is idempotent and enabled only in a named demo environment/database; never overwrites user edits.
