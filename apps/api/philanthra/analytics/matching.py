"""Inspectable transfer matches and compatible peer benchmarks."""

from decimal import Decimal

from .common import decimal, number, source_ids

METHOD_VERSION = "context-match-v1"
CONTEXT_FIELDS = (
    "cause",
    "population",
    "outcome_definition",
    "delivery_mechanism",
    "setting",
    "duration_days",
    "infrastructure",
    "resource_level",
    "language",
    "public_services",
    "delivery_partner",
    "constraints",
)


def match_transfer(profile: dict, cards: list[dict]) -> dict:
    matches = []
    for card in sorted(cards, key=lambda row: str(row.get("id", ""))):
        context = card.get("context", card)
        similarities, differences, missing = [], [], []
        for field in CONTEXT_FIELDS:
            wanted, observed = profile.get(field), context.get(field)
            if wanted is None or observed is None or wanted == "" or observed == "":
                missing.append(field)
            elif wanted == observed:
                similarities.append(
                    {"field": field, "value": wanted, "source_ids": source_ids([card])}
                )
            else:
                differences.append(
                    {
                        "field": field,
                        "target": wanted,
                        "source": observed,
                        "source_ids": source_ids([card]),
                    }
                )
        # An explicit cause mismatch is not rescued by incidental similarities.
        if profile.get("cause") and context.get("cause") and profile["cause"] != context["cause"]:
            continue
        if not any(
            item["field"] in ("cause", "population", "outcome_definition") for item in similarities
        ):
            continue
        known = len(similarities) + len(differences)
        matches.append(
            {
                "id": str(card.get("id", "")),
                "title": str(card.get("title") or "Untitled intervention record"),
                "source_ids": source_ids([card]),
                "similarities": similarities,
                "differences": differences,
                "missing_context": missing,
                "matched_fields": len(similarities),
                "known_fields": known,
                "context_agreement": number(Decimal(len(similarities)) / known) if known else None,
                "coverage": number(Decimal(known) / len(CONTEXT_FIELDS)),
                "evidence_label": card.get("evidence_label", "early hypothesis"),
                "study_design": card.get("study_design"),
                "review_status": card.get("review_status", "unknown"),
                "contradictions": card.get("contradictions", []),
                "failures": card.get("failures", []),
                "adaptation_questions": [
                    f"How will the {item['field']} difference affect delivery?"
                    for item in differences
                ]
                + [f"Collect {field} before assessing transfer." for field in missing],
                "explanation": "Matches on "
                + ", ".join(item["field"] for item in similarities)
                + "; evidence strength and context gaps remain separate.",
            }
        )
    matches.sort(key=lambda row: (-row["matched_fields"], row["id"]))
    return {
        "method_version": METHOD_VERSION,
        "status": "available" if matches else "insufficient_evidence",
        "matches": matches,
        "source_ids": sorted({s for row in matches for s in row["source_ids"]}),
        "limitations": [
            "Transferability heuristic, not a validated likelihood of success",
            "Country identity does not establish compatibility",
            "Missing context is reported, never a favorable zero",
        ],
    }


def benchmark(target: dict, peers: list[dict]) -> dict:
    keys = ("cause", "size_band", "period", "context", "metric", "unit")
    base = {"method_version": "compatible-benchmark-v1", "source_ids": []}
    if any(target.get(key) is None for key in keys):
        return base | {
            "status": "insufficient_data",
            "reason": "Specify cause, size, period, context, metric and unit",
        }
    included, excluded = [], []
    for peer in peers:
        if str(peer.get("organization_id")) == str(target.get("organization_id")):
            continue
        if any(peer.get(key) != target[key] for key in keys) or peer.get("value") is None:
            excluded.append(
                {
                    "id": str(peer.get("id", "")),
                    "reason": "Missing value or incompatible peer dimensions",
                }
            )
            continue
        included.append(peer)
    # One value per organization: multiple submissions cannot inflate coverage.
    if len({row.get("organization_id") for row in included}) != len(included) or any(
        not row.get("organization_id") for row in included
    ):
        return base | {
            "status": "incompatible",
            "reason": "Exactly one value per identified peer organization required",
        }
    if len(included) < 3:
        return base | {
            "status": "suppressed",
            "reason": "At least three compatible peer organizations required",
        }
    values = sorted(decimal(row["value"]) for row in included)
    mid = len(values) // 2
    median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
    own = decimal(target.get("value"))
    return base | {
        "status": "available",
        "source_ids": source_ids(included + [target]),
        "peer_organization_count": len(included),
        "median": number(median),
        "minimum": number(min(values)),
        "maximum": number(max(values)),
        "target_value": number(own),
        "difference_from_median": number(own - median) if own is not None else None,
        "excluded": excluded,
        "dimensions": {key: target[key] for key in keys},
        "limitations": [
            "Descriptive compatible-peer sample; not a rank or impact measure",
            "Missing reporting is not poor performance",
        ],
    }
