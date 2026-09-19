"""Exact-cent constrained weighted planning heuristic, not an impact optimizer."""

from decimal import Decimal

from .common import decimal, integer, number, source_ids

METHOD_VERSION = "allocation-weighted-caps-v1"


def allocate(budget_cents: int, candidates: list[dict]) -> dict:
    integer(budget_cents, "budget_cents")
    ids = [str(row["id"]) for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate identifiers must be unique")
    rows, eligible = [], []
    for candidate in sorted(candidates, key=lambda item: str(item["id"])):
        row = {
            "id": str(candidate["id"]),
            "amount_cents": 0,
            "cap_cents": None,
            "source_ids": source_ids([candidate]),
        }
        rows.append(row)
        if candidate.get("excluded"):
            row["reason"] = "Explicitly excluded"
            continue
        cap = candidate.get("cap_cents")
        if cap is None:
            cap = candidate.get("assumption_cap_cents")
            if cap is None or not str(candidate.get("assumption_note", "")).strip():
                row["reason"] = "Unknown capacity: enter a planning cap and assumption note"
                continue
            row["capacity_basis"] = "donor_planning_assumption"
            row["assumption_note"] = candidate["assumption_note"]
        else:
            row["capacity_basis"] = "disclosed_cap"
        integer(cap, "cap_cents")
        minimum = integer(candidate.get("minimum_cents", 0), "minimum_cents")
        weight = decimal(candidate.get("weight"))
        if weight is None or weight <= 0:
            row["reason"] = "An explicit positive planning weight is required"
            continue
        row.update(cap_cents=cap, minimum_cents=minimum, weight=number(weight))
        if minimum > cap:
            row["reason"] = "Minimum exceeds capacity cap"
            continue
        eligible.append((row, cap, minimum, weight))

    minimum_total = sum(item[2] for item in eligible)
    if minimum_total > budget_cents:
        for row, *_ in eligible:
            row["reason"] = "Combined required minimums exceed budget; revise constraints"
        eligible = []
    else:
        for row, _, minimum, _ in eligible:
            row["amount_cents"] = minimum
            row["reason"] = "Required minimum, then weighted distribution within cap"
    remaining = budget_cents - sum(row["amount_cents"] for row in rows)
    # Each pass either exhausts the budget or fills at least one cap. Largest
    # remainders use stable identifiers, so input ordering never changes cents.
    while remaining:
        active = [
            (row, cap, weight) for row, cap, _, weight in eligible if row["amount_cents"] < cap
        ]
        if not active:
            break
        total_weight = sum((weight for _, _, weight in active), Decimal(0))
        shares = [
            (row, cap, Decimal(remaining) * weight / total_weight) for row, cap, weight in active
        ]
        capped = [(row, cap) for row, cap, share in shares if share >= cap - row["amount_cents"]]
        if capped:
            for row, cap in capped:
                remaining -= cap - row["amount_cents"]
                row["amount_cents"] = cap
            continue
        for row, _, share in shares:
            amount = int(share)
            row["amount_cents"] += amount
            remaining -= amount
        for row, _, _ in sorted(shares, key=lambda item: (-(item[2] % 1), item[0]["id"]))[
            :remaining
        ]:
            row["amount_cents"] += 1
        remaining = 0
    for row in rows:
        row["explanation"] = row["reason"]
    return {
        "method_version": METHOD_VERSION,
        "status": "draft",
        "budget_cents": budget_cents,
        "allocated_cents": budget_cents - remaining,
        "unallocated_cents": remaining,
        "allocations": rows,
        "source_ids": source_ids(candidates),
        "review_required": True,
        "objective": "User-supplied planning weights subject to exact-cent caps and minimums",
        "limitations": [
            "Not a prediction of impact or money movement",
            "Weights are assumptions; missing capacity is not inferred",
        ],
    }
