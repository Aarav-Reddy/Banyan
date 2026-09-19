"""Strict normalized input helpers, deliberately independent of transport."""

from decimal import Decimal, InvalidOperation


def decimal(value):
    if value is None or value == "":
        return None
    if isinstance(value, (bool, float)):
        raise ValueError("Decimal inputs must be strings, integers or Decimal, never float/bool")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("Decimal must be finite")
    return result


def integer(value, name, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def number(value):
    return None if value is None else format(value.quantize(Decimal("0.000001")), "f")


def source_ids(rows):
    return sorted(
        {str(s) for row in rows for s in ([row.get("source_id")] + row.get("source_ids", [])) if s}
    )
