from copy import deepcopy
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from philanthra.analytics import (
    allocate,
    benchmark,
    financial_signals,
    match_transfer,
    pool_observations,
)
from philanthra.analytics.evaluation import evaluate_historical


def filing(year=2025, **changes):
    return {
        "id": str(year),
        "source_id": f"filing-{year}",
        "tax_year": year,
        "period_start": f"{year}-01-01",
        "period_end": f"{year}-12-31",
        "currency": "USD",
        "form_type": "990",
        "revenue": "100.00",
        "expenses": "120.00",
        "program_expenses": "90.00",
        "assets": "150.00",
        "liabilities": "160.00",
        **changes,
    }


def observation(org, **changes):
    return {
        "id": f"row-{org}",
        "source_id": f"source-{org}",
        "organization_id": str(org),
        "cohort_id": f"cohort-{org}",
        "study_id": f"study-{org}",
        "independent": True,
        "numerator": 30,
        "denominator": 50,
        "outcome_definition": "food_security_improved",
        "unit": "proportion",
        "direction": "higher_is_better",
        "window_days": 90,
        "population": "household",
        "intervention": "food_access",
        "comparator": "none",
        "period": "2025",
        **changes,
    }


def test_financial_hand_calculation_and_limits():
    result = financial_signals(
        [
            filing(2024),
            filing(2025, unrestricted_cash="30", cash="40", cash_restrictions_known=True),
        ]
    )
    metrics = result["periods"][-1]["metrics"]
    assert metrics["program_spending_share"]["value"] == "0.750000"
    assert metrics["operating_surplus"]["value"] == "-20.000000"
    assert metrics["operating_margin"]["value"] == "-0.200000"
    assert metrics["net_assets"]["value"] == "-10.000000"
    assert metrics["reported_unrestricted_cash_months"]["value"] == "3.000000"
    assert "repeated_deficits" in {row["code"] for row in result["signals"]}
    assert result["source_ids"] == ["filing-2024", "filing-2025"]
    assert "probability" not in result


@pytest.mark.parametrize("change", [{"revenue": "0"}, {"revenue": None}, {"revenue": "-100"}])
def test_margin_invalid_denominator(change):
    metrics = financial_signals([filing(**change)])["periods"][0]["metrics"]
    assert metrics["operating_margin"]["value"] is None


def test_missing_is_not_zero_and_net_assets_not_cash():
    missing = financial_signals([filing(program_expenses=None)])["periods"][0]
    zero = financial_signals([filing(program_expenses="0")])["periods"][0]
    assert missing["metrics"]["program_spending_share"]["value"] is None
    assert zero["metrics"]["program_spending_share"]["value"] == "0.000000"
    assert zero["metrics"]["reported_unrestricted_cash_months"]["value"] is None


@pytest.mark.parametrize(
    "previous,current",
    [
        (filing(2023), filing(2025)),
        (filing(2024, period_start="2024-10-01"), filing()),
        (filing(2024, currency="EUR"), filing()),
        (filing(2024), filing(caveats=["one-off grant"])),
    ],
)
def test_incomparable_growth_and_deficits(previous, current):
    result = financial_signals([previous, current])
    assert result["periods"][-1]["metrics"]["revenue_growth"]["value"] is None
    assert "repeated_deficits" not in {row["code"] for row in result["signals"]}


def test_active_revision_required_and_decimal_validation():
    with pytest.raises(ValueError):
        financial_signals([filing(), filing()])
    for value in (float("nan"), "NaN", "Infinity", True):
        with pytest.raises(ValueError):
            financial_signals([filing(revenue=value)])
    assert len(financial_signals([filing(active=False), filing()])["periods"]) == 1


def test_exact_caps_remainders_minimums_and_unknown_capacity():
    result = allocate(
        101,
        [
            {"id": "b", "cap_cents": 90, "weight": "1"},
            {"id": "a", "cap_cents": 30, "weight": "1"},
            {"id": "unknown", "weight": "100"},
        ],
    )
    assert [(r["id"], r["amount_cents"]) for r in result["allocations"]] == [
        ("a", 30),
        ("b", 71),
        ("unknown", 0),
    ]
    assert result["unallocated_cents"] == 0
    assert (
        allocate(10, [{"id": "a", "minimum_cents": 20, "cap_cents": 30, "weight": "1"}])[
            "unallocated_cents"
        ]
        == 10
    )
    assert (
        allocate(
            10,
            [
                {
                    "id": "a",
                    "assumption_cap_cents": 10,
                    "assumption_note": "Planning assumption, not verified",
                    "weight": "1",
                }
            ],
        )["allocated_cents"]
        == 10
    )
    assert (
        allocate(10, [{"id": "a", "assumption_cap_cents": 10, "weight": "1"}])["unallocated_cents"]
        == 10
    )
    assert (
        allocate(
            3,
            [
                {"id": "b", "cap_cents": 100, "weight": "1"},
                {"id": "a", "cap_cents": 100, "weight": "1"},
            ],
        )["allocations"][0]["amount_cents"]
        == 2
    )


@given(
    st.integers(min_value=0, max_value=10**9),
    st.lists(st.tuples(st.integers(0, 10**8), st.integers(1, 1000)), max_size=20),
)
def test_allocation_properties(budget, values):
    candidates = [
        {"id": str(i), "cap_cents": cap, "weight": str(weight)}
        for i, (cap, weight) in enumerate(values)
    ]
    result = allocate(budget, candidates)
    assert result == allocate(budget, list(reversed(candidates)))
    assert (
        sum(row["amount_cents"] for row in result["allocations"]) + result["unallocated_cents"]
        == budget
    )
    assert all(0 <= row["amount_cents"] <= row["cap_cents"] for row in result["allocations"])
    assert result["allocated_cents"] == min(budget, sum(cap for cap, _ in values))


def test_weights_change_result_and_exclusion():
    rows = [
        {"id": "a", "weight": "1", "cap_cents": 1000},
        {"id": "b", "weight": "1", "cap_cents": 1000},
    ]
    assert allocate(100, rows)["allocations"][0]["amount_cents"] == 50
    rows[0]["weight"] = "3"
    assert allocate(100, rows)["allocations"][0]["amount_cents"] == 75
    rows[0]["excluded"] = True
    assert allocate(100, rows)["allocations"][0]["amount_cents"] == 0


def test_pool_hand_calculation_dedup_and_independent_counts():
    rows = [
        observation(1),
        observation(2, numerator=20, denominator=100),
        observation(3, numerator=80, denominator=100, study_id="study-1"),
    ]
    result = pool_observations(rows + [deepcopy(rows[0])])
    assert result["status"] == "draft"
    assert result["weighted_rate"] == "0.520000"
    assert result["equal_organization_rate"] == "0.533333"
    assert result["organization_count"] == 3
    assert result["study_count"] == 2
    assert result["duplicate_reports_excluded"] == 1
    assert any("Heterogeneity" in item for item in result["warnings"])


@pytest.mark.parametrize(
    "change",
    [
        {"window_days": 180},
        {"denominator": None},
        {"population": None},
        {"independent": None},
        {"unit": "count"},
        {"direction": "lower_is_better"},
        {"numerator": 51},
    ],
)
def test_pool_rejects_incompatible_and_unknown(change):
    assert (
        pool_observations([observation(1), observation(2), observation(3, **change)])["status"]
        == "incompatible"
    )


@pytest.mark.parametrize("numerator", [0, 1, 9, 41, 49, 50])
def test_pool_suppresses_complements_and_all_derivatives(numerator):
    result = pool_observations(
        [observation(1, numerator=numerator), observation(2), observation(3)]
    )
    assert result["status"] == "suppressed"
    assert result["source_ids"] == []
    assert (
        not {
            "numerator",
            "denominator",
            "organization_count",
            "weighted_rate",
            "per_organization",
            "duplicate_reports_excluded",
        }
        & result.keys()
    )


def test_overlap_rejected_and_threshold_floor():
    rows = [observation(1), observation(2), observation(3, cohort_id="cohort-1")]
    assert pool_observations(rows)["status"] == "incompatible"
    with pytest.raises(ValueError):
        pool_observations([], min_cell=1)


def test_simpson_reversal():
    rows = []
    for org, pairs in [
        (1, [(81, 90), (30, 100)]),
        (2, [(180, 210), (10, 40)]),
        (3, [(30, 50), (30, 50)]),
    ]:
        for index, (num, denom) in enumerate(pairs):
            # Multiply by two so every contributing success and complement is >=10.
            rows.append(
                observation(
                    org,
                    numerator=num * 2,
                    denominator=denom * 2,
                    cohort_id=f"{org}-{index}",
                    stratum=str(index),
                )
            )
    result = pool_observations(rows)
    assert result["status"] == "draft"
    assert result["simpson_reversal"] is True


def test_transfer_retains_missing_and_failures_not_country_assumptions():
    result = match_transfer(
        {"cause": "food", "population": "household", "setting": "urban", "country": "US"},
        [
            {
                "id": "card",
                "source_id": "source",
                "cause": "food",
                "population": "household",
                "setting": "rural",
                "country": "MX",
                "failures": ["delivery interrupted"],
            }
        ],
    )
    match = result["matches"][0]
    assert match["failures"] == ["delivery interrupted"]
    assert "resource_level" in match["missing_context"]
    assert match["differences"][0]["field"] == "setting"
    assert result["source_ids"] == ["source"]
    assert match_transfer({"cause": "food"}, [{"cause": "housing", "id": "x"}])["matches"] == []


def test_benchmark_no_missing_penalty():
    target = dict(
        organization_id="target",
        cause="food",
        size_band="small",
        period="2025",
        context="urban",
        metric="share",
        unit="proportion",
        value=None,
    )
    peers = [
        target | {"organization_id": str(i), "value": str(v)}
        for i, v in enumerate(["0.2", "0.4", "0.9"])
    ]
    result = benchmark(target, peers)
    assert result["median"] == "0.400000"
    assert result["target_value"] is None
    assert result["difference_from_median"] is None


def historical():
    rows = []
    for index, year in enumerate((2020, 2021, 2022)):
        for label in (0, 1):
            rows.append(
                {
                    "organization_id": f"{year}-{label}",
                    "source_kind": "synthetic_demo",
                    "source_id": f"label-{year}-{label}",
                    "prediction_date": f"{year}-01-01",
                    "feature_available_at": f"{year - 1}-12-31",
                    "outcome_date": f"{year}-01-31",
                    "label_available_at": f"{year}-02-01",
                    "label": label,
                    "label_source": "independently_adjudicated_outcome",
                    "prediction": "0.8" if label else "0.2",
                }
            )
    return rows


def evaluate(rows, **kwargs):
    return evaluate_historical(
        rows,
        train_end="2020-12-31",
        validation_end="2021-12-31",
        label_definition="adjudicated cessation by 30 days",
        horizon_days=30,
        **kwargs,
    )


def test_synthetic_cannot_claim_real_validation_and_metrics():
    assert evaluate(historical())["status"] == "not_validated"
    result = evaluate(historical(), real_validation=False)
    assert result["status"] == "synthetic_harness_only"
    assert result["splits"]["test"]["roc_auc"] == "1.000000"
    assert Decimal(result["splits"]["test"]["brier_score"]) == Decimal("0.04")
    assert Decimal(result["splits"]["test"]["training_prevalence_baseline_brier"]) == Decimal(
        "0.25"
    )
    assert result["model_enabled"] is False
    assert evaluate([])["status"] == "not_validated"


@pytest.mark.parametrize(
    "change",
    [
        {"feature_available_at": "2025-01-01"},
        {"label_available_at": "2025-01-01"},
        {"outcome_date": "2020-02-01"},
        {"label_source": "missing_filing"},
    ],
)
def test_evaluation_leakage_and_proxy_labels(change):
    rows = historical()
    rows[0].update(change)
    with pytest.raises(ValueError):
        evaluate(rows, real_validation=False)


def test_organization_leakage():
    rows = historical()
    rows[2]["organization_id"] = rows[0]["organization_id"]
    with pytest.raises(ValueError):
        evaluate(rows, real_validation=False)


def test_invalid_allocation_inputs_and_constraints():
    for budget in (-1, 1.5, True):
        with pytest.raises(ValueError):
            allocate(budget, [])
    with pytest.raises(ValueError):
        allocate(10, [{"id": "duplicate"}, {"id": "duplicate"}])
    result = allocate(
        100,
        [
            {"id": "bad-minimum", "cap_cents": 20, "minimum_cents": 30, "weight": "1"},
            {"id": "missing-weight", "cap_cents": 100},
            {"id": "valid", "cap_cents": 40, "minimum_cents": 10, "weight": "1"},
        ],
    )
    assert result["allocated_cents"] == 40
    assert result["unallocated_cents"] == 60


def test_growth_variability_and_cash_restrictions():
    result = financial_signals(
        [
            filing(2023, revenue="100", expenses="80", program_expenses="70"),
            filing(2024, revenue="200", expenses="100", program_expenses="60"),
            filing(
                2025,
                revenue="300",
                expenses="250",
                program_expenses="50",
                unrestricted_cash="100",
                cash="90",
                cash_restrictions_known=True,
            ),
        ],
        as_of="2026-09-01",
    )
    codes = {row["code"] for row in result["signals"]}
    assert {
        "revenue_variability",
        "shrinking_program_expenses",
        "expense_growth_above_revenue_growth",
    } <= codes
    assert result["periods"][-1]["metrics"]["reported_unrestricted_cash_months"]["value"] is None
    assert result["periods"][-1]["metrics"]["revenue_growth"]["value"] == "0.500000"
    assert Decimal(result["revenue_variability"]) > Decimal("0.25")


def test_freshness_not_refreshed_by_download():
    result = financial_signals([filing(2020, retrieved_at="2026-09-01")], as_of="2026-09-01")
    freshness = next(row for row in result["signals"] if row["code"] == "filing_freshness")
    assert freshness["state"] == "flag"
    assert freshness["direction"] == "data_quality"


def test_single_class_real_harness_and_required_splits():
    rows = historical()
    for row in rows:
        row["source_kind"] = "public_source"
        row["label"] = 0
    result = evaluate(rows)
    assert result["status"] == "historical_evaluation"
    assert result["splits"]["test"]["roc_auc"] is None
    assert result["model_enabled"] is False
    assert evaluate(rows[:2])["status"] == "not_validated"


def test_contradictions_survive_pool_and_unknown_overlap_fails():
    rows = [observation(1, contradictory=True), observation(2), observation(3)]
    result = pool_observations(rows)
    assert any("Contradictory" in warning for warning in result["warnings"])
    del rows[0]["independent"]
    assert pool_observations(rows)["status"] == "incompatible"


def test_benchmark_rejects_duplicate_organizations_and_missing_context():
    target = dict(
        organization_id="target",
        cause="food",
        size_band="small",
        period="2025",
        context="urban",
        metric="share",
        unit="proportion",
        value="0.5",
    )
    peer = target | {"organization_id": "peer", "value": "0.6"}
    assert benchmark(target, [peer])["status"] == "suppressed"
    assert benchmark(target, [peer, peer, peer])["status"] == "incompatible"
    assert benchmark(target | {"context": None}, [peer])["status"] == "insufficient_data"
