"""Historical probability evaluation harness. It never trains or enables a model."""

from datetime import date
from decimal import Decimal

from .common import decimal, number, source_ids

METHOD_VERSION = "historical-evaluation-v1"


def _date(value):
    return date.fromisoformat(str(value)[:10])


def _metrics(rows, baseline):
    labels = [row["label"] for row in rows]
    predictions = [decimal(row["prediction"]) for row in rows]
    positive, negative = sum(labels), len(rows) - sum(labels)
    brier = sum((prediction - label) ** 2 for prediction, label in zip(predictions, labels)) / len(
        rows
    )
    baseline_brier = sum((baseline - label) ** 2 for label in labels) / len(rows)
    auc = None
    if positive and negative:
        wins = sum(
            Decimal(1) if a > b else Decimal("0.5") if a == b else Decimal(0)
            for a, label_a in zip(predictions, labels)
            if label_a
            for b, label_b in zip(predictions, labels)
            if not label_b
        )
        auc = wins / (positive * negative)
    bins = []
    for index in range(5):
        members = [(p, y) for p, y in zip(predictions, labels) if min(int(p * 5), 4) == index]
        if members:
            bins.append(
                {
                    "lower": number(Decimal(index) / 5),
                    "upper": number(Decimal(index + 1) / 5),
                    "count": len(members),
                    "mean_prediction": number(sum(p for p, _ in members) / len(members)),
                    "observed_fraction": number(Decimal(sum(y for _, y in members)) / len(members)),
                }
            )
    return {
        "count": len(rows),
        "positive_count": positive,
        "negative_count": negative,
        "prevalence": number(Decimal(positive) / len(rows)),
        "brier_score": number(brier),
        "training_prevalence_baseline_brier": number(baseline_brier),
        "roc_auc": number(auc),
        "auc_reason": None if auc is not None else "Both outcome classes required",
        "calibration_bins": bins,
        "uncertainty": "No interval estimated; finite historical sample",
    }


def evaluate_historical(
    records: list[dict],
    *,
    train_end: str,
    validation_end: str,
    label_definition: str,
    horizon_days: int,
    real_validation: bool = True,
) -> dict:
    """Evaluate precomputed held-out probabilities with explicit availability dates.

    Required row fields: organization_id, prediction_date, feature_available_at,
    label_available_at, outcome_date, label, prediction, label_source, source_kind.
    Predictions are supplied by an external experiment. The caller must preserve
    training provenance; these checks cannot certify how that experiment trained.
    """
    base = {
        "method_version": METHOD_VERSION,
        "model_enabled": False,
        "source_ids": [],
        "label_definition": label_definition,
        "horizon_days": horizon_days,
    }
    if (
        not label_definition.strip()
        or isinstance(horizon_days, bool)
        or not isinstance(horizon_days, int)
        or horizon_days <= 0
    ):
        raise ValueError("An explicit label definition and positive integer horizon are required")
    if _date(train_end) >= _date(validation_end):
        raise ValueError("Temporal cutoffs must be strictly increasing")
    if not records:
        return base | {
            "status": "not_validated",
            "reason": "No labeled historical dataset supplied",
        }
    if real_validation and any(row.get("source_kind") == "synthetic_demo" for row in records):
        return base | {
            "status": "not_validated",
            "reason": "Synthetic labels test software only; real validation unavailable",
        }
    splits: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    assigned: dict[str, str] = {}
    for row in records:
        if row.get("label") not in (0, 1) or isinstance(row.get("label"), bool):
            raise ValueError(
                "A verified binary outcome label is required; missing filings are not labels"
            )
        if row.get("label_source") in (None, "", "missing_filing", "auto_revocation"):
            raise ValueError(
                "Labels require independently documented outcomes, not administrative proxies"
            )
        if row.get("source_kind") not in ("synthetic_demo", "public_source", "ngo_contributed"):
            raise ValueError("Explicit source kind required")
        prediction = decimal(row.get("prediction"))
        if prediction is None or not 0 <= prediction <= 1:
            raise ValueError("Predictions must be finite probabilities in [0,1]")
        when = _date(row["prediction_date"])
        outcome = _date(row["outcome_date"])
        available = _date(row["label_available_at"])
        if _date(row["feature_available_at"]) > when:
            raise ValueError("Future-information leakage: feature unavailable at prediction time")
        # outcome_date is the horizon adjudication date, for both event and nonevent.
        if (outcome - when).days != horizon_days or available < outcome:
            raise ValueError(
                "Outcome adjudication must cover the exact declared horizon and precede label availability"
            )
        split = (
            "train"
            if when <= _date(train_end)
            else "validation"
            if when <= _date(validation_end)
            else "test"
        )
        if split == "train" and available > _date(train_end):
            raise ValueError("Training label was unavailable at training cutoff")
        if split == "validation" and available > _date(validation_end):
            raise ValueError("Validation label was unavailable at validation cutoff")
        organization = str(row.get("organization_id", ""))
        if not organization:
            raise ValueError("Organization grouping identifier required")
        if organization in assigned and assigned[organization] != split:
            raise ValueError("Organization leakage across temporal splits")
        assigned[organization] = split
        splits[split].append(row)
    if any(not values for values in splits.values()):
        return base | {
            "status": "not_validated",
            "reason": "Nonempty, organization-disjoint train/validation/test periods required",
            "split_counts": {key: len(rows) for key, rows in splits.items()},
        }
    baseline = Decimal(sum(row["label"] for row in splits["train"])) / len(splits["train"])
    return base | {
        "status": "historical_evaluation" if real_validation else "synthetic_harness_only",
        "source_ids": source_ids(records),
        "train_end": train_end,
        "validation_end": validation_end,
        "training_prevalence_baseline": number(baseline),
        "splits": {key: _metrics(rows, baseline) for key, rows in splits.items()},
        "limitations": [
            "Evaluation does not enable a probability model",
            "Source labels and external training provenance require independent review",
            "No prospective validity, calibration certification or causal interpretation claimed",
        ],
    }
