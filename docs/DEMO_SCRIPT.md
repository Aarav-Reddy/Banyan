# Demonstration script

Run `make demo`, open http://127.0.0.1:8080/demo. Demo-only password for the listed accounts: `Demo-only-Philanthra-2026!`. Demo role buttons are served only in demo mode. The fixed fixture clock is 2026-09-01; public source retrieval dates remain actual retrieval dates. No money is moved and no outbound message is sent.

## Donor journey

1. Enter as `foundation-admin`. On Discover choose food security and a reported Baltimore service area; try an unsupported location through the URL to see a real empty result. Change budget/risk/outcome/horizon and inspect backend-filtered results.
2. Select 2–4 organizations and compare. Distinguish program-spending share from evidence quality; inspect original/amended filings and unknown metrics.
3. Open Allocation. Enter exact budget, priorities/weights, exclusions and caps. For unknown capacity, supply an explicit planning assumption or leave funds unallocated. Save the persisted draft.
4. Submit its current revision to `reviewer`. Sign out, sign in as reviewer and approve with a demo-only reason/caveats. Return as foundation-admin; open source-linked printable report and CSV. Editing amounts returns the plan to draft; withdrawn inputs revoke serving/approval.
5. Add an organization to Watchlist, run monitoring and inspect the queued/completed job. An unchanged baseline produces no fake new event; a subsequently imported/activated filing or evidence revision produces a reproducible change alert. Seed alerts are visibly synthetic.

## Contributor journey

1. Enter as `ngo-owner`. Inspect the data-quality checklist, programs, compatible financial benchmark, funding opportunities and transfer matches, including missing context and failures. Save a permitted evidence card and inspect bookmarks.
2. Data & uploads: download outcome/cost template; use a new explicit outcome code if its definition differs from the seeded definition. Upload CSV/XLSX, map every column and review diagnostics. Rejected rows are downloadable. The worker commits only a validated batch; retry/duplicate upload does not duplicate normalized records.
3. For a text report, upload TXT/PDF into quarantine. Inspect page locators, create a manual source/program/card and enter sourced claims. Extraction is not approval or outcome validation. Image-only PDFs report unavailable text extraction.
4. Submit card for reviewer approval, then create purpose/recipient/cause/geography grants in Sharing. Publication, donor access, benchmarking, pooled analysis and external AI are distinct. New eligible approved cards trigger worker-generated matching alerts for consenting peers. No external AI permission is needed for deterministic matching.
5. In Pooled analysis select the complete compatible 2025 food-security cohort set from four consenting NGO workspaces. Inspect organization rates and descriptive weighted/equal-organization summaries. Separate 2024 sparse cells suppress; missing/incompatible sets do not become plausible complete analyses. Sharing a release requires contributor publication consent and independent review.
6. Withdraw an input source in Sharing. New views/exports of dependent cards/analyses/alerts are denied immediately; deletion job status is visible. Existing downloaded files cannot be recalled. Data-use activity records the action without raw report contents.
7. NGO impact report prints current authorized records and exports CSV with provenance; it remains a draft unless its components were reviewed. Optional profile/contact edits persist. Introduction requests are stored and recipients must accept and enable contact consent before a requester can read contact details.

## Additional role checks

`foundation-viewer` and `ngo-viewer` cannot mutate. `second-foundation` cannot inspect the first foundation's private plans. `platform-admin` has no automatic private NGO access. NGO workspaces 2–4 use `ngo2-owner`, `ngo3-owner`, `ngo4-owner`. Trusted reviewers can withdraw a specific approved revision through the Approved queue. Non-demo invited accounts create unlinked workspaces and require identity verification; password-reset mail is local by default.

Automated journeys in tests/e2e/journeys.spec.ts use isolated real PostgreSQL/API/worker processes and persist/reload state. They do not mock successful API writes. See QA_REPORT.md for actually observed results/screenshots.
