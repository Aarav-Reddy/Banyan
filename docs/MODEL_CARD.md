# Philanthra rules engine and experimental evaluation

## Intended use

The pilot supports donor investigation and NGO learning using transparent financial warning signals, configurable allocation planning, inspectable contextual matches and descriptive binary pooling. These are decision-support methods requiring human judgment, permissioned inputs and appropriate review. They are not bankruptcy predictions, causal impact estimates or endorsements.

## Status and training data

There is no trained or enabled probability-producing model. No historical real-world distress-label dataset has been supplied or validated. Demo records and evaluation fixtures are synthetic and cannot establish discrimination, calibration, fairness, real-world performance or partnerships. The evaluation harness always returns `model_enabled=False`; an empty real-validation run returns `not_validated`.

## Methods and outputs

See [METHODOLOGY.md](METHODOLOGY.md) for exact formulas, validity conditions, threshold assumptions, weighting, pooling compatibility and release suppression. Methods retain version identifiers and input source IDs where disclosure is safe. Financial outputs contain warning labels and data-quality caveats, never numeric collapse odds. Missing input is unknown, not zero. Financial fragility does not automatically disqualify an NGO.

## Evaluation completed by software tests

Hand-calculated fixtures test ratios, negative net assets, deficits, unavailable denominators, currency and period incompatibility, restricted cash, exact allocation conservation, capacity and minimum constraints, deterministic remainders, pooling/deduplication, complementary suppression, heterogeneity, Simpson reversals and source references. Property tests generate budgets, caps and weights. Evaluation tests check temporal and organization leakage, proxy-label rejection, synthetic gating, Brier scores and AUC. Test execution evidence belongs in `docs/BUILD_STATUS.md`; these assertions are not empirical validation.

## Evaluation needed before any probability model could be enabled

Obtain permissioned historical outcomes with a defensible label definition/horizon and actual feature-availability dates; audit administrative-proxy and survivorship bias; separate organizations and time periods; audit externally trained predictions for leakage; compare held-out discrimination/calibration to simple baselines; examine missingness and performance across causes, organizational sizes and contexts; assess deployment drift and errors with human pilot reviewers. A documented model-enabling governance decision and corresponding implementation change would be required. Merely running the harness cannot enable a model.

## Limitations and misuse

Filing lag, differences among form types, exceptional grants, restricted assets, incomplete reporting, nonrepresentative contributors and hidden cohort overlap limit inference. Threshold choices are product assumptions. Program-spending share is not outcomes; small budgets and missing reporting are not evidence of ineffectiveness. Country names do not establish transferability. Aggregate rates are not causal effects. Suppression thresholds are not legal guarantees of anonymity. No automated grant approval or transfer is supported.

## Human oversight and withdrawal

API services must authorize each source, retain source/grant revisions, require independent revision-bound review for consequential releases, and stop serving outputs when permissions or dependencies change. The pure calculations contain no access-control bypass, persistence, network calls, LLM processing or publication mechanism. Owners and reviewers remain accountable for source validity, restrictions and decisions.
