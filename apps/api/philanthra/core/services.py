"""Transactional application operations. All publication locks source rows first."""

import hashlib
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from .models import (
    Alert,
    Allocation,
    Artifact,
    AuditEvent,
    DataGrant,
    Dependency,
    Job,
    Portfolio,
    ReviewAssignment,
    ReviewDecision,
    Source,
    Withdrawal,
)
from .policy import can_artifact, can_source, matching_grant


class Conflict(APIException):
    status_code = 409
    default_code = "stale_revision"
    default_detail = "The record changed. Reload before continuing."


def audit(owner, actor, action, object_id, **metadata):
    return AuditEvent.objects.create(
        owner=owner, actor=actor, action=action, object_id=str(object_id), metadata=metadata
    )


def enqueue(owner, kind, key, payload=None, source=None):
    return Job.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "owner": owner,
            "kind": kind,
            "payload": payload or {},
            "source": source,
            "source_revision": source.revision if source else None,
            "available_at": timezone.now(),
        },
    )[0]


def attach_sources(artifact, sources):
    for source in sorted(sources, key=lambda s: str(s.id)):
        if not can_source(
            source, artifact.owner, artifact.purpose, artifact.cause, artifact.geography
        ):
            raise PermissionDenied("Sources do not permit this complete use scope.")
        grant = (
            None
            if source.owner_id in {None, artifact.owner_id}
            else matching_grant(
                source, artifact.owner, artifact.purpose, artifact.cause, artifact.geography
            )
        )
        Dependency.objects.update_or_create(
            artifact=artifact,
            source=source,
            defaults={
                "source_revision": source.revision,
                "grant": grant,
                "grant_revision": grant.revision if grant else None,
            },
        )


@transaction.atomic
def create_artifact(
    owner,
    actor,
    *,
    kind,
    title,
    sources,
    payload=None,
    purpose="donor_access",
    cause="food_security",
    geography="US-MD-Baltimore",
):
    locked = list(
        Source.objects.select_for_update().filter(id__in=[s.id for s in sources]).order_by("id")
    )
    if not locked or len(locked) != len({s.id for s in sources}):
        raise ValidationError({"source_ids": "At least one accessible source is required."})
    artifact = Artifact.objects.create(
        owner=owner,
        created_by=actor,
        kind=kind,
        title=title,
        payload=payload or {},
        purpose=purpose,
        cause=cause,
        geography=geography,
        source_kind="synthetic_demo"
        if any(s.kind == "synthetic_demo" for s in locked)
        else "ngo_contributed",
    )
    attach_sources(artifact, locked)
    audit(owner, actor, "artifact.created", artifact.id, kind=kind)
    return artifact


@transaction.atomic
def submit_review(artifact, actor, reviewer_id, revision):
    list(Source.objects.select_for_update().filter(dependency__artifact=artifact).order_by("id"))
    artifact = Artifact.objects.select_for_update().get(pk=artifact.pk)
    if artifact.revision != revision:
        raise Conflict()
    if str(actor.pk) == str(reviewer_id) or str(artifact.created_by_id) == str(reviewer_id):
        raise ValidationError({"reviewer_id": "Choose an independent reviewer."})
    from django.contrib.auth import get_user_model

    reviewer = (
        get_user_model()
        .objects.filter(pk=reviewer_id, memberships__role="reviewer")
        .distinct()
        .first()
    )
    if reviewer is None:
        raise ValidationError({"reviewer_id": "An active assigned reviewer is required."})
    from .policy import reviewer_scope_allowed

    if not reviewer_scope_allowed(artifact, reviewer):
        raise PermissionDenied(
            "The source owners have not permitted this reviewer's workspace to use all third-party evidence."
        )
    if not can_artifact(artifact, artifact.owner):
        raise Conflict("The source snapshot is no longer authorized.")
    ReviewAssignment.objects.get_or_create(
        artifact=artifact, reviewer=reviewer, revision=revision, defaults={"assigned_by": actor}
    )
    artifact.status = "pending_review"
    artifact.save(update_fields=["status", "updated_at"])
    audit(artifact.owner, actor, "review.submitted", artifact.id, revision=revision)
    return artifact


@transaction.atomic
def decide_review(artifact, actor, revision, decision, reason):
    list(Source.objects.select_for_update().filter(dependency__artifact=artifact).order_by("id"))
    artifact = Artifact.objects.select_for_update().get(pk=artifact.pk)
    if artifact.revision != revision or artifact.status != "pending_review":
        raise Conflict()
    if (
        artifact.created_by_id == actor.id
        or not artifact.assignments.filter(reviewer=actor, revision=revision).exists()
    ):
        raise PermissionDenied("Only the independent assigned reviewer may decide.")
    from .policy import reviewer_scope_allowed

    if not reviewer_scope_allowed(artifact, actor):
        raise PermissionDenied("Reviewer source scope is no longer authorized.")
    if (
        decision not in {"approved", "rejected", "changes_requested", "withdrawn"}
        or not reason.strip()
    ):
        raise ValidationError({"decision": "Decision and substantive reason are required."})
    if not can_artifact(artifact, artifact.owner):
        raise Conflict("The source snapshot is no longer authorized.")
    if (
        decision == "approved"
        and artifact.kind == "analysis"
        and artifact.payload.get("status") not in {"draft"}
    ):
        raise ValidationError(
            {"analysis": "Suppressed or incompatible analysis cannot be published."}
        )
    publication_grants = []
    if decision == "approved" and artifact.kind == "analysis":
        for dep in artifact.dependencies.select_related("source"):
            if (
                dep.source.owner_id is not None
                and matching_grant(
                    dep.source, artifact.owner, "publication", artifact.cause, artifact.geography
                )
                is None
            ):
                raise PermissionDenied(
                    "Every private source needs explicit publication consent for the release recipient, including owner contributions."
                )
            if dep.source.owner_id is not None:
                grant = matching_grant(
                    dep.source, artifact.owner, "publication", artifact.cause, artifact.geography
                )
                publication_grants.append(
                    {
                        "source_id": str(dep.source_id),
                        "id": str(grant.id),
                        "revision": grant.revision,
                    }
                )
    snapshot = {
        "publication_grants": publication_grants,
        "payload": artifact.payload,
        "sources": [
            {
                "id": str(d.source_id),
                "revision": d.source_revision,
                "grant_id": str(d.grant_id) if d.grant_id else None,
                "grant_revision": d.grant_revision,
            }
            for d in artifact.dependencies.all()
        ],
    }
    ReviewDecision.objects.create(
        artifact=artifact,
        reviewer=actor,
        revision=revision,
        decision=decision,
        reason=reason,
        snapshot=snapshot,
    )
    artifact.status = decision
    artifact.save(update_fields=["status", "updated_at"])
    from philanthra.pilot.services import after_review

    after_review(artifact, actor, decision)
    if decision == "approved":
        enqueue(
            artifact.owner,
            "recommendations",
            f"recommendations:{artifact.id}:{revision}",
            {"artifact_id": str(artifact.id)},
        )
    audit(
        artifact.owner, actor, "review.decided", artifact.id, revision=revision, decision=decision
    )
    return artifact


@transaction.atomic
def withdraw(source, actor):
    source = Source.objects.select_for_update().get(pk=source.pk)
    if source.owner_id is None:
        raise PermissionDenied("Public-source governance is independent of private consent.")
    if source.state == "active":
        source.state = "withdrawn"
        source.revision += 1
        source.save(update_fields=["state", "revision", "updated_at"])
        from philanthra.pilot.services import after_source_withdrawal

        after_source_withdrawal(source)
        DataGrant.objects.filter(source=source).update(active=False)
        artifact_ids = Dependency.objects.filter(source=source).values_list(
            "artifact_id", flat=True
        )
        Artifact.objects.filter(id__in=artifact_ids).update(status="invalidated")
        Alert.objects.filter(artifact_id__in=artifact_ids).update(state="invalidated")
        Alert.objects.filter(target_source=source).update(state="invalidated")
        Job.objects.filter(source=source, state__in=["queued", "processing"]).update(
            state="canceled"
        )
    request, _ = Withdrawal.objects.get_or_create(source=source, defaults={"requested_by": actor})
    enqueue(source.owner, "delete_source", f"delete:{source.id}", {"source_id": str(source.id)})
    audit(source.owner, actor, "source.withdrawn", source.id)
    return request


def filing_input(f):
    fields = ["revenue", "expenses", "program_expenses", "assets", "liabilities", "cash"]
    return {
        **{k: str(getattr(f, k)) if getattr(f, k) is not None else None for k in fields},
        "id": str(f.id),
        "source_id": str(f.source_id),
        "tax_year": f.tax_year,
        "period_start": str(f.period_start),
        "period_end": str(f.period_end),
        "currency": f.currency,
        "form_type": f.form,
        "active": f.active,
        "retrieved_at": f.source.retrieved_at.isoformat(),
        "caveats": f.caveats,
    }


def observation_input(o):
    return {
        "id": str(o.id),
        "source_id": str(o.source_id),
        "organization_id": str(o.program.organization_id),
        "study_id": o.study_id,
        "cohort_id": o.cohort_id,
        "independent": o.independent,
        "numerator": o.numerator,
        "denominator": o.denominator,
        "outcome_definition": o.outcome.code,
        "unit": {"binary": "proportion"}.get(o.outcome.unit, o.outcome.unit),
        "direction": {"higher_better": "higher_is_better", "lower_better": "lower_is_better"}.get(
            o.outcome.direction, o.outcome.direction
        ),
        "window_days": o.followup_months * 30,
        "population": o.program.population,
        "intervention": o.program.intervention,
        "comparator": o.comparator,
        "period": f"{o.period_start}/{o.period_end}",
        "stratum": o.stratum,
    }


@transaction.atomic
def create_portfolio(owner, actor, data):
    from philanthra.analytics.allocation import allocate

    from .models import Organization

    candidates = data.get("candidates", [])
    if not isinstance(candidates, list) or len(candidates) > 100:
        raise ValidationError({"candidates": "Provide at most 100 candidates."})
    if not isinstance(data.get("constraints", {}), dict) or "candidates" in data.get(
        "constraints", {}
    ):
        raise ValidationError(
            {"constraints": "Validated candidate constraints cannot be overridden."}
        )
    list(
        Organization.objects.select_for_update()
        .filter(pk__in=[c.get("organization_id") for c in candidates])
        .order_by("id")
    )
    import json

    planning_source = Source.objects.create(
        owner=owner,
        title="Donor planning inputs",
        kind="ngo_contributed",
        retrieved_at=timezone.now(),
        parser_version="planning-input-v1",
        checksum=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
        locator="donor-entered constraints",
    )
    normalized = []
    sources = [planning_source]
    organizations = {}
    for c in candidates:
        org = Organization.objects.filter(pk=c.get("organization_id")).first()
        if not org:
            raise ValidationError({"candidates": "Unknown public organization."})
        if str(org.id) in organizations:
            raise ValidationError({"candidates": "Duplicate organization."})
        organizations[str(org.id)] = org
        filings = list(
            org.filings.filter(active=True, source__owner__isnull=True, source__state="active")
            .select_related("source")
            .order_by("-tax_year")
        )
        sources.extend(f.source for f in filings)
        list(
            Source.objects.select_for_update()
            .filter(pk__in=[f.source_id for f in filings])
            .order_by("id")
        )
        filings = list(
            org.filings.filter(active=True, source__owner__isnull=True, source__state="active")
            .select_related("source")
            .order_by("-tax_year")
        )
        cap = c.get("cap_cents")
        if cap is None:
            cap = org.capacity_cents
        note = c.get("assumption_note", "")
        if org.capacity_cents is None and cap is not None and not note:
            raise ValidationError(
                {"cap_cents": "Unknown capacity requires an explicit planning assumption note."}
            )
        if org.capacity_cents is not None and cap is not None and cap > org.capacity_cents:
            raise ValidationError(
                {"cap_cents": "Planning cap exceeds the recorded approved capacity."}
            )
        normalized.append(
            {
                "id": str(org.id),
                "cap_cents": cap if org.capacity_cents is not None else None,
                "assumption_cap_cents": cap if org.capacity_cents is None else None,
                "assumption_note": note,
                "weight": str(c.get("weight", "1")),
                "minimum_cents": c.get("minimum_cents", 0),
                "excluded": c.get("excluded", False),
                "source_ids": [str(f.source_id) for f in filings],
            }
        )
    try:
        result = allocate(data.get("budget_cents"), normalized)
    except (ValueError, TypeError) as exc:
        raise ValidationError({"allocation": str(exc)}) from exc
    artifact = create_artifact(
        owner,
        actor,
        kind="portfolio",
        title=data.get("name", "Planning portfolio"),
        sources=list({s.id: s for s in sources}.values()),
        payload=result,
    )
    portfolio = Portfolio.objects.create(
        artifact=artifact,
        budget_cents=data["budget_cents"],
        currency=data.get("currency", "USD"),
        constraints={**data.get("constraints", {}), "candidates": normalized},
        unallocated_cents=result["unallocated_cents"],
    )
    for row in result["allocations"]:
        identifier = str(row.get("id", row.get("organization_id")))
        candidate = next(c for c in normalized if c["id"] == identifier)
        Allocation.objects.create(
            portfolio=portfolio,
            organization=organizations[identifier],
            amount_cents=row["amount_cents"],
            cap_cents=0 if candidate.get("excluded") else (row.get("cap_cents") or 0),
            weight=Decimal(candidate["weight"]),
            explanation=str(
                row.get("explanation", "Proportional constrained planning allocation.")
            ),
        )
    return artifact
