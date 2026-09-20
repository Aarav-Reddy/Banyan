# Banyan methodology

All methods below are deterministic, versioned planning or descriptive calculations. They do not measure causal impact, predict organizational collapse, or move money. Input source IDs travel with available results. The API must authorize input records before calling these pure functions and retain source/grant revisions in persisted artifacts. A calculation result never confers permission to publish.

## Financial signals (`financial-signals-v1`)

`financial_signals(filings, as_of=..., thresholds=...)` uses normalized decimal-string monetary values. Missing values remain null. NaN, infinity, binary floats and booleans are rejected. One explicitly active revision per tax year is required; inactive amendments are ignored. All ratios serialize as six-place decimal strings. The underlying monetary values and source IDs remain visible.

| Metric | Formula and validity |
| --- | --- |
| Program-spending share | Program expenses / total expenses. Total must be positive; program expenses must lie between zero and total. This is spending composition, not effectiveness. |
| Operating surplus | Revenue − expenses; expenses must be nonnegative. A negative amount is a reported deficit. |
| Operating margin | Operating surplus / revenue, only for positive revenue. |
| Liabilities/assets | Liabilities / assets, only for positive assets and nonnegative liabilities. |
| Net assets | Assets − liabilities. Negative net assets receive a separate signal and are never substituted for cash. |
| Annual growth | (Current − previous) / previous. Positive baseline, nonnegative current value, consecutive tax years, same known currency and comparable annual periods are required. |
| Reported unrestricted cash months | Documented unrestricted cash / (annual expenses / 12). Requires explicit known restrictions, nonnegative unrestricted cash, positive annual expenses, and unrestricted cash no greater than reported cash when supplied. This describes a historical expense equivalent, not a forward cash-runway prediction. |
| Revenue variability | Population standard deviation / mean over at least three comparable consecutive annual revenues, all positive. |

Annual comparability in this pilot means a reported period of 350–380 days, matching currencies and no recorded comparability caveats. Known one-off grants, accounting changes, pandemic disruptions or exceptional periods prevent growth and consecutive-deficit comparison; values remain visible. Period end determines freshness, never retrieval date. Forms 990-EZ, 990-PF and 990-N must retain form type and unavailable fields from ingestion; the engine never fills absent fields by analogy to Form 990.

Default warning policies are assumptions, not fitted or validated thresholds: liabilities/assets ≥0.8; revenue variability ≥0.25; two consecutive comparable deficits; declining program expenses; growing expenses faster than revenue; negative net assets; financial period end older than 730 days. Freshness and completeness are explicitly data-quality signals. Missing filings or fields do not establish wrongdoing, poor performance or bankruptcy. Administrative spending is not labeled waste. Revenue categories cannot identify funder concentration, so the current engine does not produce it.

## Allocation (`allocation-weighted-caps-v1`)

`allocate(budget_cents, candidates)` accepts integer cents only. Each candidate needs a unique stable ID, explicit positive decimal planning weight and a disclosed cap. Unknown capacity requires `assumption_cap_cents` plus a nonblank `assumption_note`; otherwise that candidate receives zero with an explanation. Assumed capacity remains labeled as a donor assumption. No capacity is inferred from organization budget, financial ratios or missing data.

Excluded candidates receive zero. Minimums are assigned first. A minimum exceeding its candidate's cap makes that candidate infeasible. If the sum of otherwise feasible required minimums exceeds the budget, the eligible set receives zero and the full budget remains unallocated, with an explanation. The remaining budget is divided in proportion to explicit weights. Saturated caps are removed and shares recomputed; final fractional cents use largest remainders, ties resolved lexically by candidate ID. This preserves `allocated + unallocated = budget` exactly, is invariant to input ordering and respects every cap. Infeasible constraints never produce a fabricated full allocation.

Weights express the donor's planning preferences; there is no universal charity score or validated impact optimum. Goal fit, financial uncertainty, community context, evidence strength and capacity remain inspectable rather than secretly folded into a default weight. Users can rerun with alternative weights to see sensitivity. Financial strain may justify capacity-building support. Every result is a draft requiring human review; persistence must bind approval to the exact portfolio version and current source snapshot.

## Transfer matching (`context-match-v1`)

`match_transfer(profile, cards)` compares cause, population, outcome definition, delivery mechanism, setting, duration, infrastructure, resources, language, public services, delivery partner and constraints. A known cause mismatch excludes a card; at least one known match on cause/population/outcome is required. Results sort by the count of matching known dimensions, then stable ID. Equal weighting is a disclosed product assumption. Context agreement is matches / known fields; coverage is known fields / all 12 fields. Reporting both prevents sparse records from quietly appearing complete.

Each match returns similarities with source IDs, differences, missing context, adaptation questions, study design, reviewer status, evidence label, failures and contradictions. A source country's identity alone cannot prove compatibility or incompatibility. This is a transferability heuristic, not a calibrated success likelihood. Callers supply authorized, current cards; the calculation neither approves evidence nor changes evidence labels.

## Binary pooling (`binary-descriptive-pooling-v1`)

`pool_observations(observations, purpose='pooled_analysis', min_cell=10, min_organizations=3)` supports one narrow descriptive binary outcome. Every record must have identical outcome definition, proportion unit, orientation, follow-up days, population, intervention, comparator and reporting period. Numerators and denominators are integers with `0 ≤ numerator ≤ denominator` and denominator >0. Both higher-is-better and lower-is-better are supported, without silently reversing data.

Organization, study and cohort identifiers plus explicit `independent=True` disjointness assertions are mandatory. A repeated identical cohort report is counted once; conflicting reports for the same cohort reject the analysis. Multiple disjoint cohorts in one study remain one study. Independence assertions require evidence/reviewer verification; the software cannot discover hidden overlap from aggregate counts. Unknown overlap is not poolable. Any incompatible record rejects the requested set with a reason; it is not silently discarded into a favorable pooled result.

For compatible eligible observations, each organization has `sum(numerator)/sum(denominator)`. The sample-size-weighted descriptive rate is total numerator / total denominator; the equal-organization summary is the arithmetic mean of organization rates. Organization and study counts, cohort coverage, excluded duplicate reports and per-organization results are separate. No interval or significance claim is produced because the pilot inputs do not establish sampling design or dependence adequately.

An organization-rate range of at least 0.20 produces a heterogeneity warning (policy assumption). For pairs of organizations with the same two or more supplied strata, the engine flags a Simpson reversal when every within-stratum rate difference has the opposite sign to the overall difference. Missing strata are explicitly flagged: absence of a detected reversal does not rule one out. Contradictory/failed observations remain included and disclosed. Aggregation does not transform descriptive or observational evidence into causal findings.

### Release checks and complementary suppression

At least three contributing organizations and at least ten successes **and ten nonsuccesses in every contributing observation** are required. Configurable thresholds may only become stricter. A failure suppresses the whole fixed release: no numerator, denominator, rates, organization/study/cohort counts, excluded count, source ID list or per-organization results are returned. This conservative rule prevents a total or complement from revealing a suppressed cell inside the same release.

These pure-function checks are only one layer. The service must prohibit arbitrary private-data slicing and intersecting releases that allow cross-release subtraction; require current consent, fixed reviewed releases, and revocation propagation. Suppression is neither anonymization nor differential privacy and cannot revoke previously downloaded exports.

## Compatible peer benchmarks (`compatible-benchmark-v1`)

`benchmark(target, peers)` requires identical cause, explicit size band, period, context, metric and unit. One value per identified organization prevents repeated submissions inflating coverage. Fewer than three compatible peers suppresses the result. The median, min/max and organization count describe only that contributor sample; an unknown target remains unknown and receives no position/penalty. This function is intended for authorized contributor views, not arbitrary public releases; the caller owns consent and release policy.

## Historical evaluation (`historical-evaluation-v1`)

`evaluate_historical` accepts already-computed experimental probabilities, an explicit binary outcome definition, positive integer horizon, training cutoff and validation cutoff. It does not train a model. Required dates distinguish feature availability, prediction, horizon adjudication and label availability. Features after prediction are rejected; adjudication must cover exactly the stated horizon; training/validation labels must be available by their respective cutoffs. Organizations may not cross temporal partitions. Unknown labels, missing-filing and auto-revocation proxy labels are rejected. Actual outcome validity and the provenance of externally trained predictions still need independent audit.

Each nonempty partition reports class balance, Brier score (mean squared probability error), training-prevalence baseline Brier score, five fixed calibration-bin means and observed frequencies, and pairwise ROC AUC with half credit for ties when both classes exist. AUC is unavailable for single-class partitions. No confidence intervals or prospective validity are asserted. Empty data or a real-validation request containing any synthetic records returns `not_validated`. Explicit synthetic-mode runs return `synthetic_harness_only`. **Every path leaves `model_enabled=False`.** The repository tests exercise software correctness, not real-world predictive validity.

## Planning dimensions and evaluation command

Candidate planning notes retain need, evidence, financial uncertainty and goal fit separately; capacity is a distinct cap/assumption. Blank notes remain null. These notes do not secretly change weights. Donors explicitly set positive proportional weights (equal default 1 is disclosed), caps, minimums and exclusions; consequential review binds the stored input notes/constraints plus source snapshot. Sensitivity is inspectable by recalculating with different disclosed weights, not an assertion of a validated optimum.

```sh
PYTHONPATH=apps/api .venv/bin/python -m philanthra.analytics.evaluate
```

Without a real label dataset the command prints not_validated/model_enabled:false and exits 2. Supply --input with JSON containing records, train_end, validation_end, label_definition and horizon_days. Synthetic harness mode requires --synthetic-harness-only and is never empirical validation. The CLI forwards to the same leakage-checked pure function tested in tests/analytics.

## Current portfolio geography

The service-area coverage view considers active public reported/verified records (including explicitly synthetic reported demo records) for the candidate causes and countries. Only positive planning allocations count as selected. It groups exact recorded area codes; it does not infer polygon intersections, ZIP/ZCTA equivalence, headquarters service areas or a geographic distribution of money. Two selected organizations reporting one area suggest possible collaboration. Areas represented elsewhere in the directory but absent from the plan are investigation gaps within the dataset, not proof of real-world underfunding. Missing private/withdrawn service records do not contribute titles, counts or citations. The source-versioned current view is labeled separately from an approved allocation snapshot.
