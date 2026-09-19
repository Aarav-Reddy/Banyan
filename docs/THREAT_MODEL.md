# Threat model

Assets: private aggregate evidence, raw quarantined reports, tenant memberships, consent/review lineage, source integrity, financial calculations and application availability. Attackers considered: unauthenticated clients, authenticated users guessing tenant IDs, malicious contributors/files, stale or duplicated workers, untrusted external source servers and malicious text inside reports. Infrastructure administrators/database superusers are trusted operators; application policy cannot constrain a compromised database administrator.

| Boundary / threat | Implemented control and verification |
| --- | --- |
| Session impersonation/CSRF | Server sessions; CSRF on login/reset and unsafe API actions; secure production cookies; same-origin proxy. accounts/core and pilot tests. |
| Tenant-ID/owner forgery | Membership-checked X-Workspace-ID; server-side owner assignment; inaccessible IDs return404; permissions before totals/search/scoring. QA guessed-ID tests. |
| Reviewer privilege laundering | Staff-only trusted reviewer provisioning, independent contributor check, current assigned revision and third-party grant scope. security extension tests. |
| Withdrawal race/stale job | Shared source-row locks, fresh authorization after locks, job lease/token/source revision fences; real PostgreSQL blocked-update tests. |
| Hidden data in pooled outputs | Fixed complete cohorts; cell/complement/org thresholds; no reconstructable suppressed totals/citations; no arbitrary slices. pooling property tests and integration export checks. |
| Untrusted files | Bounded bytes/rows/archive ratio/path limits, defused XML without DTD/entities, spreadsheet external-link/formula rejection, private short-lived quarantine, document extraction limits. ingestion tests. |
| SSRF / source egress | Reviewed exact source catalogue, credential-free HTTPS, globally routable resolved addresses pinned to connection with TLS hostname verification; no redirects; response limits; opt-in network. fixture network-boundary tests make no requests. |
| Spreadsheet export execution | CSV formula-prefix escaping including headers/leading whitespace. parser/export tests. |
| Model prompt injection / leakage | Default none, no model tools, explicit external-processing consent, suspicious text filtering, typed allowed-ID output, numerical/source-label content rendered from stored reviewed claims. malformed/timeout/revoked/private-egress tests. |
| Stale source approval | Source/grant revision dependencies, fixed review snapshots, invalidation on source changes/withdrawal, current authorization on reports/graph. core/pilot tests. |
| Production misconfiguration | Explicit strong secret/hosts, no demo/debug/insecure origins, dedicated database, storage-encryption acknowledgment; production WSGI/worker reject pending migrations or seeded demo database. |
| Unsafe local process/reset | Known demo database/loopback guards, PID start-command identity checks, explicit reset phrase, isolated E2E databases and restore targets. release tests. |

Residual risks: aggregate privacy depends on context and auxiliary data; manually supplied claims can be false; reviewer independence requires real organizational governance; parsers support explicitly documented variants only; local throttling is process-local and production should add shared edge limiting; application audit immutability is not database-level tamper resistance; deployment TLS/storage encryption/backup retention depend on operators. No penetration test or external certification is claimed. See SECURITY_REVIEW.md for actual independent findings and fixes, rather than treating this design table as proof.
