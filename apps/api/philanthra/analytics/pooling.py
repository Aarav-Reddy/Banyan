"""Narrow binary descriptive pooling with fail-closed compatibility and release checks."""

from collections import defaultdict
from decimal import Decimal
from itertools import combinations

from .common import integer, number, source_ids

METHOD_VERSION = "binary-descriptive-pooling-v1"
COMPATIBILITY_FIELDS = (
    "outcome_definition",
    "unit",
    "direction",
    "window_days",
    "population",
    "intervention",
    "comparator",
    "period",
)


def _rate(rows):
    return Decimal(sum(row["numerator"] for row in rows)) / sum(row["denominator"] for row in rows)


def pool_observations(
    observations: list[dict],
    *,
    purpose: str = "pooled_analysis",
    min_cell: int = 10,
    min_organizations: int = 3,
) -> dict:
    integer(min_cell, "min_cell", 10)
    integer(min_organizations, "min_organizations", 3)
    base = {
        "method_version": METHOD_VERSION,
        "purpose": purpose,
        "source_ids": [],
        "review_required": True,
        "evidence_label": "descriptive observation",
    }
    if purpose != "pooled_analysis":
        raise ValueError("Unsupported analysis purpose")
    if not observations:
        return base | {"status": "insufficient_data", "reason": "No eligible observations"}
    rows: list[dict] = []
    seen: dict[str, tuple] = {}
    duplicates = 0
    first = observations[0]
    for row in observations:
        if any(row.get(field) is None or row.get(field) == "" for field in COMPATIBILITY_FIELDS):
            return base | {
                "status": "incompatible",
                "reason": "Required outcome definition or context is missing",
            }
        if any(row[field] != first[field] for field in COMPATIBILITY_FIELDS):
            return base | {
                "status": "incompatible",
                "reason": "Outcome definition, unit, orientation, window, population, intervention, comparator and period must match",
            }
        if row["unit"] != "proportion" or row["direction"] not in (
            "higher_is_better",
            "lower_is_better",
        ):
            return base | {
                "status": "incompatible",
                "reason": "Only oriented binary proportions are supported",
            }
        if row.get("independent") is not True or not all(
            row.get(field) for field in ("organization_id", "study_id", "cohort_id")
        ):
            return base | {
                "status": "incompatible",
                "reason": "Explicit disjoint-cohort assertion and organization/study/cohort identifiers required",
            }
        try:
            integer(row.get("window_days"), "window_days", 1)
            integer(row.get("numerator"), "numerator")
            integer(row.get("denominator"), "denominator", 1)
            if row["numerator"] > row["denominator"]:
                raise ValueError("Numerator exceeds denominator")
        except ValueError:
            return base | {
                "status": "incompatible",
                "reason": "Invalid binary counts or follow-up duration",
            }
        cohort = str(row["cohort_id"])
        signature = tuple(
            row.get(key)
            for key in (
                *COMPATIBILITY_FIELDS,
                "organization_id",
                "study_id",
                "numerator",
                "denominator",
                "stratum",
            )
        )
        if cohort in seen:
            if seen[cohort] != signature:
                return base | {
                    "status": "incompatible",
                    "reason": "Conflicting or overlapping cohort reports cannot be pooled",
                }
            duplicates += 1
            continue
        seen[cohort] = signature
        rows.append(row)
    organizations = {str(row["organization_id"]) for row in rows}
    # Suppress the WHOLE release. Returning a total, exclusion count, source list
    # or complementary rate here can reconstruct the withheld observation.
    if len(organizations) < min_organizations or any(
        min(row["numerator"], row["denominator"] - row["numerator"]) < min_cell for row in rows
    ):
        return base | {
            "status": "suppressed",
            "reason": "Fixed release does not meet organization and binary-cell/complement thresholds",
            "thresholds": {"minimum_cell": min_cell, "minimum_organizations": min_organizations},
        }
    groups = defaultdict(list)
    for row in rows:
        groups[str(row["organization_id"])].append(row)
    per_org = [
        {
            "organization_id": organization,
            "numerator": sum(r["numerator"] for r in group),
            "denominator": sum(r["denominator"] for r in group),
            "rate": number(_rate(group)),
            "study_count": len({r["study_id"] for r in group}),
            "source_ids": source_ids(group),
        }
        for organization, group in sorted(groups.items())
    ]
    rates = [_rate(group) for group in groups.values()]
    warnings = []
    spread = max(rates) - min(rates)
    if spread >= Decimal("0.20"):
        warnings.append(
            "Heterogeneity: organization rates span at least 20 percentage points; inspect context before using the aggregate"
        )
    strata: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get("stratum") is not None:
            strata[str(row["organization_id"])][str(row["stratum"])].append(row)
    reversal = False
    for a, b in combinations(sorted(strata), 2):
        common = set(strata[a]) & set(strata[b])
        if len(common) >= 2 and common == set(strata[a]) == set(strata[b]):
            differences = [_rate(strata[a][s]) - _rate(strata[b][s]) for s in common]
            overall = _rate(groups[a]) - _rate(groups[b])
            if (overall > 0 and all(d < 0 for d in differences)) or (
                overall < 0 and all(d > 0 for d in differences)
            ):
                reversal = True
    if reversal:
        warnings.append(
            "Simpson reversal: a between-organization ordering reverses within every shared stratum; the overall comparison can mislead"
        )
    if any(not row.get("stratum") for row in rows):
        warnings.append("Incomplete strata: Simpson reversal cannot be ruled out")
    if any(row.get("contradictory") or row.get("failed_intervention") for row in rows):
        warnings.append(
            "Contradictory or failed intervention observations are included, not filtered away"
        )
    return base | {
        "status": "draft",
        "source_ids": source_ids(rows),
        "compatibility": {field: first[field] for field in COMPATIBILITY_FIELDS},
        "organization_count": len(organizations),
        "study_count": len({r["study_id"] for r in rows}),
        "cohort_count": len(rows),
        "duplicate_reports_excluded": duplicates,
        "per_organization": per_org,
        "numerator": sum(r["numerator"] for r in rows),
        "denominator": sum(r["denominator"] for r in rows),
        "weighted_rate": number(_rate(rows)),
        "equal_organization_rate": number(sum(rates) / len(rates)),
        "rate_range": number(spread),
        "simpson_reversal": reversal,
        "warnings": warnings,
        "uncertainty": "No interval estimated: sampling design and dependence information are insufficient",
        "limitations": [
            "Descriptive rates are not causal effects or evidence of statistical significance",
            "Contributor sample is not representative",
            "Threshold suppression is not anonymization or differential privacy",
        ],
        "thresholds": {"minimum_cell": min_cell, "minimum_organizations": min_organizations},
    }
