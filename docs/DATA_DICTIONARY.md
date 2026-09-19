# Data dictionary

All Record subclasses use UUID identifiers and created/updated timestamps. Users retain Django's user ID. Public organizations do not grant workspace authority. Money is Decimal with currency or integer cents; API Decimal values are strings. Dates denote actual reporting windows independently of retrieval timestamps. Empty means unknown, not zero.

| Stored concept | Representation and important semantics |
| --- | --- |
| Users/workspaces/roles | Django User; Workspace(kind,plan,organization nullable); Membership; expiring single-use hashed Invitation. Roles owner/administrator/analyst/editor/viewer/reviewer; staff provisions trusted reviewers but never bypasses source policy. |
| Public identities | Organization; ExternalIdentifier(namespace,value) preserves strings, including leading zeroes. Real IRS EIN namespace differs from synthetic/parser namespaces. Workspace linkage requires reviewed IdentityClaim. |
| Filings and funds | Filing source, form, period, taxyear, amendment, active revision, Decimal finances/caveats; FundingRecord distinguishes commitment/disbursement and stores funder as Organization. No sum across transaction types. |
| Service/context | Geography(kind/code/vintage/context/source), ServiceArea(basis/source). Headquarters ZIP is separate. Program has cause, intervention, population, geography and explicit JSON context. Missing context remains absent. |
| Taxonomies | Versioned string codes for cause/intervention/population/geography; normalized OutcomeDefinition(code,definition,unit,direction). Configurable new codes require domain consistency, not country stereotypes. |
| Outcomes/costs | Observation: definition, numerator/denominator, cohort/study IDs, independence, window, follow-up, comparator, study design, uncertainty/missingness, stratum and row locator. CostObservation: Decimal amount/currency/unit/denominator/window. Outputs use distinct definitions. |
| Sources and ingestion | Source version/checksum/type/retrieval/publication/period/parser/locator/transformations; ImportBatch raw private bytes, mapping/preview/diagnostics/status. The batch is the dataset/upload entity; normalized rows retain its source, not arbitrary unmapped columns. Source.transformations retains normalized public registry/IATI source-record fields. |
| Evidence and guides | Artifact(kind=card) + Card: implementation steps, failures, barriers, caveats, evidence label and separately study design; Claim source/locator/text/label; GraphEdge typed relationships. No fabricated source URLs for synthetic data. |
| Consent | DataGrant complete restriction tuple, revision/active/expiry/attribution/external processing. Dependency preserves source and grant revisions. Withdrawal records request/deletion status. Consent changes invalidate affected derivatives. |
| Review/releases | ReviewAssignment reviewer/revision; ReviewDecision immutable-intent snapshot/reason; Artifact revision/status/payload/method/policy/source kind. An approved analysis Artifact is a fixed AnalysisRelease; an approved portfolio Artifact is the recommendation snapshot. Source issue and identity claim use the same review machinery. |
| Portfolio | Portfolio budget/currency/frozen constraints/unallocated; Allocation exact cents/cap/weight/reason. Unknown capacity stays explicit in constraints/output; stored edit ceiling 0 prevents funding without an assumption. No payments. |
| Monitoring | WatchItem, MonitorSnapshot; Alert evidence artifact and optional target program/source revision, state/adoption note/feedback; Subscription evidence/financial/stale controls; Bookmark. |
| Onboarding/value | WorkspaceProfile owner-reported mission/service assertions/context; ContactConsent revisions; ServiceRequest sponsored onboarding/introduction state; Opportunity eligibility/cause/geography/deadline/source. Core contributor entitlement is free. |
| Operations/measurement | Job idempotency key/state/lease/attempt count; JobAttempt token/status/error code; AuditEvent operational metadata only; PilotEvent value/denominator/window/collection method/source kind, workspace opt-in. |

Foreign keys and database constraints enforce unique scoped imports, source/cohort/outcome records, positive/valid binary counts, valid money bounds and memberships. Services add authorization, source locks, exact revision review and numerical compatibility. JSON context/payload is used where source-specific context or versioned calculation output varies; it does not replace tenant ownership or consent checks.

Pilot metrics are attested measurements, not automatically proven outcomes. Seed events are marked synthetic. Approval by a demo reviewer is a demonstration event, not expert validation.
