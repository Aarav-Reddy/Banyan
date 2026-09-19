"""Pilot workflows that use the same source policy and version-bound review as core."""

import hashlib
import json
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from philanthra.analytics.finance import financial_signals
from philanthra.analytics.matching import benchmark
from philanthra.core import models as c
from philanthra.core.policy import can_artifact, can_source, visible_artifacts
from philanthra.core.serializers import SourceSerializer
from philanthra.core.services import Conflict, audit, create_artifact, filing_input

from .models import IdentityClaim, MonitorSnapshot, WatchItem


def today():
    return (
        timezone.datetime.fromisoformat(
            settings.PHILANTHRA_DEMO_CLOCK.replace("Z", "+00:00")
        ).date()
        if settings.DEMO_MODE
        else timezone.now().date()
    )


@transaction.atomic
def after_review(artifact, actor, decision):
    """Call within core decide_review transaction after writing status/decision."""
    if artifact.kind != "identity_claim":
        return
    claim = IdentityClaim.objects.select_related("proof_source", "organization").get(
        artifact=artifact
    )
    if decision != "approved":
        if claim.linked_revision is not None:
            c.Workspace.objects.filter(
                pk=artifact.owner_id, organization_id=claim.organization_id
            ).update(organization=None)
            claim.linked_revision = None
            claim.save(update_fields=["linked_revision", "updated_at"])
        return
    if artifact.status != "approved" or not can_artifact(artifact, artifact.owner):
        raise Conflict("Identity proof is stale or unavailable.")
    if (
        artifact.created_by_id == actor.id
        or not artifact.assignments.filter(reviewer=actor, revision=artifact.revision).exists()
    ):
        raise PermissionDenied("Independent assigned identity review required.")
    if not artifact.decisions.filter(
        reviewer=actor, revision=artifact.revision, decision="approved"
    ).exists():
        raise Conflict("The exact revision has no recorded approval.")
    if claim.proof_source.owner_id != artifact.owner_id or claim.proof_source.state != "active":
        raise PermissionDenied("The workspace must own the reviewed identity proof.")
    organization = c.Organization.objects.select_for_update().get(pk=claim.organization_id)
    workspace = c.Workspace.objects.select_for_update().get(pk=artifact.owner_id)
    if workspace.kind != "ngo":
        raise ValidationError({"workspace": "Only NGO workspaces can claim an NGO identity."})
    if workspace.organization_id and workspace.organization_id != organization.id:
        raise Conflict("This workspace already has a different verified identity.")
    if c.Workspace.objects.filter(organization=organization).exclude(pk=workspace.pk).exists():
        raise Conflict(
            "This identity is already assigned; resolve ownership through a separate operator process."
        )
    workspace.organization = organization
    workspace.save(update_fields=["organization", "updated_at"])
    claim.linked_revision = artifact.revision
    claim.save(update_fields=["linked_revision", "updated_at"])
    audit(workspace, actor, "identity.linked", claim.id, revision=artifact.revision)


def _watch_state(watch):
    org = watch.organization
    filings = list(
        org.filings.filter(active=True, source__owner__isnull=True, source__state="active")
        .select_related("source")
        .order_by("tax_year", "id")
    )
    financial = financial_signals([filing_input(f) for f in filings], as_of=today().isoformat())
    cards = [
        a
        for a in visible_artifacts(watch.owner, kind="card")
        if a.status == "approved" and a.card.program.organization_id == org.id
    ]
    funding = list(
        c.FundingRecord.objects.filter(
            organization=org, source__owner__isnull=True, source__state="active"
        )
        .select_related("source")
        .order_by("id")
    )
    sources = {f.source_id: f.source for f in filings}
    sources.update({f.source_id: f.source for f in funding})
    for card in cards:
        sources.update({source.id: source for source in card.sources.all()})
    state = {
        "filings": sorted(f"{f.id}:{f.revision}:{f.source.revision}" for f in filings),
        "signals": sorted(f"{signal['code']}:{signal['state']}" for signal in financial["signals"]),
        "funding": sorted(f"{f.id}:{f.source.revision}:{f.amount_cents}:{f.type}" for f in funding),
        "evidence": sorted(f"{a.id}:{a.revision}" for a in cards),
        "sources": sorted(f"{source.id}:{source.revision}" for source in sources.values()),
        "stale": sorted(
            str(source.id)
            for source in sources.values()
            if (today() - source.retrieved_at.date()).days > 365
        ),
    }
    return state, list(sources.values())


@transaction.atomic
def add_watch(workspace, actor, organization):
    c.Workspace.objects.select_for_update().get(pk=workspace.pk)
    watch = WatchItem.objects.filter(owner=workspace, organization=organization).first()
    if watch:
        return watch
    source = c.Source.objects.create(
        owner=workspace,
        title="Watchlist monitoring preference",
        kind="ngo_contributed",
        retrieved_at=timezone.now(),
        parser_version="watch-input-v1",
        checksum=hashlib.sha256(f"{workspace.id}:{organization.id}".encode()).hexdigest(),
        locator="workspace watch selection",
    )
    watch = WatchItem.objects.create(owner=workspace, organization=organization, source=source)
    state, _ = _watch_state(watch)
    MonitorSnapshot.objects.create(
        watch=watch,
        state=state,
        fingerprint=hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest(),
    )
    audit(workspace, actor, "watch.added", watch.id)
    return watch


@transaction.atomic
def run_monitor(job):
    """Worker extension: invoke inside core finish_job after lease fencing."""
    if job.kind != "pilot_monitor":
        raise ValueError("unsupported_job_kind")
    actor = (
        c.Membership.objects.filter(workspace=job.owner, role__in=["owner", "administrator"])
        .select_related("user")
        .first()
    )
    if not actor:
        return
    for watch in WatchItem.objects.filter(owner=job.owner).select_related(
        "organization", "owner", "source"
    ):
        if not can_source(watch.source, job.owner):
            continue
        state, sources = _watch_state(watch)
        source_ids = [source.id for source in sources] + [watch.source_id]
        list(c.Source.objects.select_for_update().filter(id__in=source_ids).order_by("id"))
        # A source could change while locks were acquired; derive only from the fresh scope.
        state, sources = _watch_state(watch)
        snapshot = MonitorSnapshot.objects.select_for_update().get(watch=watch)
        digest = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
        if digest == snapshot.fingerprint:
            continue
        changed = (
            ["sources", "evidence"]
            if snapshot.state.get("revoked_dependency")
            else [key for key in state if state[key] != snapshot.state.get(key)]
        )
        subscription = c.Subscription.objects.filter(owner=job.owner).first()
        enabled = not subscription or any(
            (key in {"filings", "signals", "funding", "sources"} and subscription.financial)
            or (key == "evidence" and subscription.evidence)
            or (key == "stale" and subscription.stale)
            for key in changed
        )
        if enabled:
            # Never copy revoked prior evidence, titles, or private numerical values into a fresh alert.
            labels = {
                "filings": "active filing revision",
                "signals": "financial warning signals",
                "funding": "recorded funding context",
                "evidence": "currently accessible approved evidence",
                "sources": "source revision or availability",
                "stale": "source freshness",
            }
            explanation = (
                "Changed "
                + ", ".join(labels[key] for key in changed)
                + ". Compare current source records; this dataset does not establish a real funding gap."
            )
            artifact = create_artifact(
                job.owner,
                actor.user,
                kind="monitor",
                title=f"Monitoring update: {watch.organization.name}",
                sources=[watch.source, *sources],
                payload={
                    "organization_id": str(watch.organization_id),
                    "changed_dimensions": changed,
                    "explanation": explanation,
                    "observed_on": today().isoformat(),
                },
                purpose="donor_access",
            )
            c.Alert.objects.get_or_create(
                fingerprint="monitor:"
                + hashlib.sha256(f"{watch.id}:{digest}".encode()).hexdigest(),
                defaults={
                    "owner": job.owner,
                    "artifact": artifact,
                    "title": artifact.title,
                    "explanation": explanation,
                },
            )
        snapshot.state = state
        snapshot.fingerprint = digest
        snapshot.save()
        audit(job.owner, None, "monitor.recomputed", watch.id, changed_dimensions=changed)


def impact_report(workspace):
    programs = list(
        c.Program.objects.filter(owner=workspace, source__state="active").select_related(
            "source", "organization"
        )
    )
    observations = list(
        c.Observation.objects.filter(
            owner=workspace, source__state="active", program__source__state="active"
        ).select_related("source", "outcome", "program")
    )
    costs = list(
        c.CostObservation.objects.filter(
            owner=workspace, source__state="active", program__source__state="active"
        ).select_related("source", "program")
    )
    cards = [a for a in visible_artifacts(workspace, kind="card") if a.owner_id == workspace.id]
    sources = {p.source_id: p.source for p in programs}
    sources.update({o.source_id: o.source for o in observations})
    sources.update({o.source_id: o.source for o in costs})
    for card in cards:
        sources.update({source.id: source for source in card.sources.all()})
    quality = []
    for observation in observations:
        if observation.denominator is None:
            quality.append(
                {
                    "observation_id": str(observation.id),
                    "issue": "Missing denominator; no rate or pooled inclusion.",
                }
            )
        if not observation.independent:
            quality.append(
                {
                    "observation_id": str(observation.id),
                    "issue": "Cohort independence unconfirmed; no pooled inclusion.",
                }
            )
        if not observation.uncertainty:
            quality.append(
                {
                    "observation_id": str(observation.id),
                    "issue": "Uncertainty not reported; no inferential interval.",
                }
            )
    return {
        "workspace": {"id": str(workspace.id), "name": workspace.name},
        "status": "draft",
        "generated_at": timezone.now().isoformat(),
        "programs": [
            {
                "id": str(p.id),
                "name": p.name,
                "cause": p.cause,
                "intervention": p.intervention,
                "population": p.population,
                "geography": p.geography,
                "context": p.context,
                "source_id": str(p.source_id),
            }
            for p in programs
        ],
        "observations": [
            {
                "id": str(o.id),
                "program_id": str(o.program_id),
                "outcome_definition": o.outcome.definition,
                "unit": o.outcome.unit,
                "direction": o.outcome.direction,
                "numerator": o.numerator,
                "denominator": o.denominator,
                "period_start": str(o.period_start),
                "period_end": str(o.period_end),
                "followup_months": o.followup_months,
                "study_design": o.study_design,
                "comparator": o.comparator,
                "uncertainty": o.uncertainty or None,
                "missingness": o.missingness or None,
                "source_id": str(o.source_id),
                "locator": o.locator,
                "source_kind": o.source.kind,
            }
            for o in observations
        ],
        "costs": [
            {
                "id": str(cost.id),
                "program_id": str(cost.program_id),
                "amount": str(cost.amount),
                "currency": cost.currency,
                "unit": cost.unit,
                "denominator": cost.denominator,
                "period_start": str(cost.period_start),
                "period_end": str(cost.period_end),
                "source_id": str(cost.source_id),
                "source_kind": cost.source.kind,
            }
            for cost in costs
        ],
        "cards": [
            {
                "id": str(a.id),
                "title": a.title,
                "status": a.status,
                "revision": a.revision,
                "evidence_label": a.card.evidence_label,
                "caveats": a.card.caveats,
                "failures": a.card.failures,
                "source_ids": [str(source.id) for source in a.sources.all()],
            }
            for a in cards
        ],
        "sources": SourceSerializer(list(sources.values()), many=True).data,
        "data_quality": quality,
        "source_kind": "synthetic_demo"
        if any(source.kind == "synthetic_demo" for source in sources.values())
        else "ngo_contributed",
        "limitations": [
            "Draft for human review; source-reported outcomes do not establish causality.",
            "Missing data remain unknown. Costs with different units, currencies or periods must not be combined.",
            "Contains private workspace aggregates; no external disclosure is implied by this owner export.",
        ],
    }


def financial_benchmark(workspace):
    if not workspace.organization_id:
        return {
            "status": "insufficient_data",
            "reason": "A reviewed organization identity is required.",
        }
    organizations = list(c.Organization.objects.filter(cause=workspace.organization.cause))
    rows = []
    for org in organizations:
        filing = (
            org.filings.filter(active=True, source__owner__isnull=True, source__state="active")
            .select_related("source")
            .order_by("-tax_year")
            .first()
        )
        if (
            not filing
            or filing.revenue is None
            or filing.expenses is None
            or filing.expenses <= 0
            or filing.program_expenses is None
        ):
            continue
        duration = (filing.period_end - filing.period_start).days + 1
        if not 330 <= duration <= 370:
            continue
        if not Decimal(0) <= filing.program_expenses <= filing.expenses:
            continue
        size = (
            "small"
            if filing.revenue < 500000
            else ("medium" if filing.revenue < 2000000 else "large")
        )
        areas = sorted(
            org.service_areas.filter(
                source__owner__isnull=True,
                source__state="active",
                geography__source__owner__isnull=True,
                geography__source__state="active",
            ).values_list("geography__code", flat=True)
        )
        if not areas:
            continue
        rows.append(
            {
                "id": str(filing.id),
                "organization_id": str(org.id),
                "cause": org.cause,
                "size_band": size,
                "period": f"{filing.period_start}/{filing.period_end}",
                "context": ",".join(areas),
                "metric": "program_spending_share",
                "unit": f"ratio_{filing.currency}",
                "value": str(filing.program_expenses / filing.expenses),
                "source_ids": [str(filing.source_id)],
            }
        )
    target = next(
        (row for row in rows if row["organization_id"] == str(workspace.organization_id)), None
    )
    if not target:
        return {
            "status": "insufficient_data",
            "reason": "Comparable full-year public financial fields and reported service context are missing.",
        }
    result = benchmark(target, rows)
    result["limitations"] = [
        "Only public financial records with matching cause, size band, full fiscal period, currency and reported service-area context.",
        "Program-spending share is not impact or organizational quality.",
        "No private outcome cells or arbitrary slices are disclosed.",
    ]
    return result


@transaction.atomic
def after_source_withdrawal(source):
    """Root withdrawal calls this synchronously: verification is a revocable derivative."""
    source = c.Source.objects.select_for_update().get(pk=source.pk)
    for claim in IdentityClaim.objects.filter(proof_source=source).select_related("artifact"):
        if claim.linked_revision is not None:
            c.Workspace.objects.filter(
                pk=claim.artifact.owner_id, organization_id=claim.organization_id
            ).update(organization=None)
        claim.statement = (
            "Withdrawn identity proof"
            if source.state != "active"
            else "Identity proof changed; new review required."
        )
        claim.linked_revision = None
        claim.save()

    for snapshot in MonitorSnapshot.objects.all():
        if any(str(source.id) in value for value in snapshot.state.get("sources", [])):
            snapshot.state = {"revoked_dependency": True}
            snapshot.fingerprint = hashlib.sha256(
                f"revoked:{source.id}:{timezone.now().isoformat()}".encode()
            ).hexdigest()
            snapshot.save()
