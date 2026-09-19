"""Financial warning and data-quality signals; no distress probabilities."""

from datetime import date

from .common import decimal, number, source_ids

METHOD_VERSION = "financial-signals-v1"
FIELDS = (
    "revenue",
    "expenses",
    "program_expenses",
    "assets",
    "liabilities",
    "cash",
    "unrestricted_cash",
)
DEFAULT_THRESHOLDS = {"leverage": "0.8", "revenue_variability": "0.25", "stale_days": 730}


def _day(value):
    return date.fromisoformat(str(value)[:10])


def _annual(row):
    return row.get("period_days") is not None and 350 <= row["period_days"] <= 380


def financial_signals(
    filings: list[dict], *, as_of: str | None = None, thresholds: dict | None = None
) -> dict:
    policy = DEFAULT_THRESHOLDS | (thresholds or {})
    today = _day(as_of) if as_of is not None else date.today()
    selected = [row for row in filings if row.get("active", True)]
    years = [row.get("tax_year") for row in selected]
    if None in years or len(years) != len(set(years)):
        raise ValueError("Select exactly one active filing revision per tax year")
    periods, signals = [], []

    def signal(code, state, explanation, inputs, threshold=None, direction="investigate"):
        signals.append(
            {
                "code": code,
                "state": state,
                "explanation": explanation,
                "threshold": threshold,
                "direction": direction,
                "source_ids": source_ids(inputs),
            }
        )

    for filing in sorted(selected, key=lambda row: row["tax_year"]):
        values = {field: decimal(filing.get(field)) for field in FIELDS}
        revenue, expense, program, assets, liabilities, cash, unrestricted = (
            values[field] for field in FIELDS
        )
        caveats = list(filing.get("caveats", []))
        duration = None
        if filing.get("period_start") and filing.get("period_end"):
            duration = (_day(filing["period_end"]) - _day(filing["period_start"])).days + 1
            if duration <= 0:
                raise ValueError("Financial period end precedes start")
        result = {
            "id": str(filing.get("id", "")),
            "tax_year": filing["tax_year"],
            "currency": filing.get("currency"),
            "form_type": filing.get("form_type"),
            "period_days": duration,
            "source_ids": source_ids([filing]),
            "caveats": caveats,
            "values": {field: number(value) for field, value in values.items()},
            "missing_fields": [field for field, value in values.items() if value is None],
        }
        metrics = {}

        def metric(name, value, reason=None):
            metrics[name] = {
                "value": number(value),
                "status": "available" if value is not None else "unavailable",
                "reason": reason,
            }

        valid_program = (
            expense is not None and expense > 0 and program is not None and 0 <= program <= expense
        )
        metric(
            "program_spending_share",
            program / expense if valid_program else None,
            None
            if valid_program
            else "Requires positive total expenses and comparable program expenses between zero and total",
        )
        deficit = (
            revenue - expense
            if revenue is not None and expense is not None and expense >= 0
            else None
        )
        metric(
            "operating_surplus",
            deficit,
            None if deficit is not None else "Revenue or nonnegative expenses unavailable",
        )
        margin = deficit / revenue if deficit is not None and revenue > 0 else None
        metric(
            "operating_margin",
            margin,
            None if margin is not None else "Requires positive revenue and nonnegative expenses",
        )
        leverage = (
            liabilities / assets
            if assets is not None and assets > 0 and liabilities is not None and liabilities >= 0
            else None
        )
        metric(
            "liabilities_assets",
            leverage,
            None
            if leverage is not None
            else "Requires positive assets and nonnegative liabilities",
        )
        net_assets = (
            assets - liabilities if assets is not None and liabilities is not None else None
        )
        metric("net_assets", net_assets)
        cash_eligible = (
            unrestricted is not None
            and unrestricted >= 0
            and filing.get("cash_restrictions_known") is True
        )
        if cash is not None and (cash < 0 or (unrestricted is not None and unrestricted > cash)):
            cash_eligible = False
        months = (
            unrestricted / (expense / 12)
            if cash_eligible and expense is not None and expense > 0 and _annual(result)
            else None
        )
        metric(
            "reported_unrestricted_cash_months",
            months,
            None
            if months is not None
            else "Requires documented unrestricted cash, restrictions and a full annual expense period; net assets are not cash",
        )
        metric("revenue_growth", None, "No comparable consecutive baseline")
        metric("expense_growth", None, "No comparable consecutive baseline")
        metric("program_expense_growth", None, "No comparable consecutive baseline")
        result["metrics"] = metrics
        if not _annual(result):
            caveats.append("Short, exceptional or unknown fiscal duration; not annualized")
        if filing.get("currency") is None:
            caveats.append("Currency unknown; growth and comparisons unavailable")
        if net_assets is not None and net_assets < 0:
            signal(
                "negative_net_assets",
                "flag",
                "Reported liabilities exceed reported assets; not a cash balance",
                [filing],
                "< 0",
            )
        if leverage is not None and leverage >= decimal(policy["leverage"]):
            signal(
                "leverage",
                "flag",
                "Liabilities/assets meets the disclosed policy threshold",
                [filing],
                policy["leverage"],
            )
        periods.append(result)

    comparable_pairs = []
    for previous, current in zip(periods, periods[1:]):
        comparable = (
            current["tax_year"] == previous["tax_year"] + 1
            and _annual(previous)
            and _annual(current)
            and current["currency"] is not None
            and current["currency"] == previous["currency"]
            and not current["caveats"]
            and not previous["caveats"]
        )
        comparable_pairs.append(comparable)
        if not comparable:
            continue
        for field, name in (
            ("revenue", "revenue_growth"),
            ("expenses", "expense_growth"),
            ("program_expenses", "program_expense_growth"),
        ):
            before, after = decimal(previous["values"][field]), decimal(current["values"][field])
            if before is not None and before > 0 and after is not None and after >= 0:
                current["metrics"][name] = {
                    "value": number((after - before) / before),
                    "status": "available",
                    "reason": None,
                }
        inputs = [
            selected[years.index(previous["tax_year"])],
            selected[years.index(current["tax_year"])],
        ]
        pdef, cdef = (
            decimal(row["metrics"]["operating_surplus"]["value"]) for row in (previous, current)
        )
        if pdef is not None and cdef is not None and pdef < 0 and cdef < 0:
            signal(
                "repeated_deficits",
                "flag",
                "Operating expenses exceed revenue in two comparable consecutive periods",
                inputs,
                "2 consecutive periods",
            )
        pg = decimal(current["metrics"]["program_expense_growth"]["value"])
        if pg is not None and pg < 0:
            signal(
                "shrinking_program_expenses",
                "flag",
                "Reported program expenses declined; outcomes cannot be inferred",
                inputs,
                "< 0",
            )
        eg, rg = (
            decimal(current["metrics"][name]["value"])
            for name in ("expense_growth", "revenue_growth")
        )
        if eg is not None and rg is not None and eg > 0 and eg > rg:
            signal(
                "expense_growth_above_revenue_growth",
                "flag",
                "Expense growth exceeds revenue growth; investigate funding and timing",
                inputs,
                "expense growth > max(0, revenue growth)",
            )

    variability = None
    if len(periods) >= 3 and all(comparable_pairs):
        revenues = [decimal(row["values"]["revenue"]) for row in periods]
        if all(value is not None and value > 0 for value in revenues):
            mean = sum(revenues) / len(revenues)
            variability = (
                sum((value - mean) ** 2 for value in revenues) / len(revenues)
            ).sqrt() / mean
            if variability >= decimal(policy["revenue_variability"]):
                signal(
                    "revenue_variability",
                    "flag",
                    "Population coefficient of variation across reported comparable annual revenues",
                    selected,
                    policy["revenue_variability"],
                )
    if selected:
        latest = max(selected, key=lambda row: row["tax_year"])
        end = latest.get("period_end")
        stale = (today - _day(end)).days > policy["stale_days"] if end else None
        signal(
            "filing_freshness",
            "unknown" if stale is None else "flag" if stale else "clear",
            "Age uses reporting period end, not download date; lag is not proof of misconduct",
            [latest],
            policy["stale_days"],
            "data_quality",
        )
    missing = sum(len(row["missing_fields"]) for row in periods)
    signal(
        "completeness",
        "flag" if missing else "clear" if periods else "unknown",
        "Missing financial values remain unknown; form variants have different available fields",
        selected,
        None,
        "data_quality",
    )
    return {
        "status": "available" if periods else "insufficient_data",
        "method_version": METHOD_VERSION,
        "as_of": today.isoformat(),
        "periods": periods,
        "signals": signals,
        "thresholds": policy,
        "revenue_variability": number(variability),
        "source_ids": source_ids(selected),
        "limitations": [
            "Policy warning signals are not validated collapse probabilities",
            "Program-spending share is not impact",
            "Revenue categories do not establish funder concentration",
        ],
    }
