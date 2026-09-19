"""Leased PostgreSQL work with idempotency and final token/source fencing."""

import hashlib
import logging
import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from philanthra.core import models as m
from philanthra.core.policy import can_artifact, can_source, visible_artifacts
from philanthra.core.services import audit


@transaction.atomic
def claim_job():
    now = timezone.now()
    job = (
        m.Job.objects.select_for_update(skip_locked=True)
        .filter(
            Q(state="queued", available_at__lte=now)
            | Q(state="processing", lease_expires_at__lt=now)
        )
        .order_by("created_at")
        .first()
    )
    if not job:
        return None
    if job.attempts >= job.max_attempts:
        job.state = "failed"
        job.error_code = "retry_limit"
        job.save()
        return None
    job.state = "processing"
    job.attempts += 1
    job.lease_token = uuid.uuid4()
    job.lease_expires_at = now + timedelta(minutes=2)
    job.save()
    m.JobAttempt.objects.create(job=job, token=job.lease_token, status="processing")
    return job


def _parse(job):
    from philanthra.ingestion import parse_upload

    batch = m.ImportBatch.objects.get(pk=job.payload["batch_id"], owner=job.owner)
    result = parse_upload(bytes(batch.raw or b""), batch.filename, batch.mapping)
    return result


def _commit_import(job):
    from philanthra.ingestion import parse_upload

    batch = m.ImportBatch.objects.select_for_update().get(
        pk=job.payload["batch_id"], owner=job.owner
    )
    if batch.status == "completed":
        return
    if batch.status != "validated":
        raise ValueError("import_not_validated")
    result = parse_upload(bytes(batch.raw or b""), batch.filename, batch.mapping)
    if result["status"] != "validated":
        raise ValueError("import_not_validated")
    if not batch.owner.organization_id:
        raise ValueError("verified_organization_required")
    for record in result["records"]:
        program, _ = m.Program.objects.get_or_create(
            owner=batch.owner,
            source=batch.source,
            name=record["program_name"],
            defaults={
                "organization": batch.owner.organization,
                "cause": record["cause"],
                "intervention": record["intervention"],
                "population": record["population"],
                "geography": record["geography"],
            },
        )
        if record["cause"] != batch.source.cause or record["geography"] != batch.source.geography:
            # Source scope is fixed to the imported program scope; mixed-scope imports fail closed.
            if (
                m.Observation.objects.filter(source=batch.source).exists()
                or m.CostObservation.objects.filter(source=batch.source).exists()
            ):
                raise ValueError("mixed_source_scope")
            batch.source.cause = record["cause"]
            batch.source.geography = record["geography"]
            batch.source.save()
        if record["record_type"] == "outcome":
            outcome, created = m.OutcomeDefinition.objects.get_or_create(
                code=record["outcome_code"],
                defaults={
                    "name": record["outcome_definition"],
                    "definition": record["outcome_definition"],
                    "unit": record["unit"],
                    "direction": record["direction"],
                },
            )
            if not created and (
                outcome.definition != record["outcome_definition"]
                or outcome.unit != record["unit"]
                or outcome.direction != record["direction"]
            ):
                raise ValueError("outcome_definition_conflict")
            fields = {
                k: record[k]
                for k in [
                    "numerator",
                    "denominator",
                    "cohort_id",
                    "study_id",
                    "independent",
                    "period_start",
                    "period_end",
                    "followup_months",
                    "comparator",
                    "study_design",
                    "uncertainty",
                    "missingness",
                    "stratum",
                    "locator",
                ]
                if k in record
            }
            m.Observation.objects.get_or_create(
                source=batch.source,
                cohort_id=record["cohort_id"],
                outcome=outcome,
                defaults={
                    "owner": batch.owner,
                    "program": program,
                    **{k: v for k, v in fields.items() if k != "cohort_id"},
                },
            )
        elif record["record_type"] == "cost":
            m.CostObservation.objects.get_or_create(
                owner=batch.owner,
                program=program,
                source=batch.source,
                amount=record["amount"],
                currency=record["currency"],
                denominator=record.get("denominator"),
                unit=record["unit"],
                period_start=record["period_start"],
                period_end=record["period_end"],
            )
    batch.status = "completed"
    batch.preview = []
    batch.raw = None
    batch.save()
    audit(batch.owner, batch.created_by, "import.committed", batch.id)


def _delete_source(job):
    source = m.Source.objects.select_for_update().get(pk=job.payload["source_id"], owner=job.owner)
    m.Alert.objects.filter(target_source=source).update(
        state="invalidated",
        title="Withdrawn program alert",
        explanation="",
        adoption_note="",
        feedback="",
    )
    if source.state != "withdrawn":
        raise ValueError("source_not_withdrawn")
    m.ImportBatch.objects.filter(source=source).update(
        raw=None, preview=[], diagnostics=[], mapping={}, columns=[]
    )
    m.Observation.objects.filter(source=source).delete()
    m.CostObservation.objects.filter(source=source).delete()
    m.Claim.objects.filter(source=source).delete()
    artifacts = m.Artifact.objects.filter(dependencies__source=source)
    m.Card.objects.filter(artifact__in=artifacts).update(
        implementation_steps="", barriers="", failures="", caveats="", attribution=""
    )
    m.ReviewDecision.objects.filter(artifact__in=artifacts).update(
        snapshot={}, reason="Source withdrawn; decision metadata retained."
    )
    m.Alert.objects.filter(artifact__in=artifacts).update(
        title="Withdrawn source alert", explanation="", adoption_note="", state="invalidated"
    )
    m.ImportBatch.objects.filter(source=source).update(filename="withdrawn-upload")
    artifacts.update(payload={}, title="Withdrawn source derivative", status="invalidated")
    m.Program.objects.filter(source=source).update(
        context={}, name="Withdrawn program", intervention="withdrawn", population="withdrawn"
    )
    m.GraphEdge.objects.filter(supporting_source=source).delete()
    source.title = "Withdrawn source"
    source.upload_identifier = ""
    source.locator = ""
    source.transformations = []
    source.save()
    m.Withdrawal.objects.filter(source=source).update(
        status="completed", completed_at=timezone.now()
    )


def _recommendations(job):
    from philanthra.analytics.matching import match_transfer

    target_artifact = None
    if job.payload.get("artifact_id"):
        target_artifact = m.Artifact.objects.get(pk=job.payload["artifact_id"])
        if target_artifact.status != "approved" or not can_artifact(
            target_artifact, target_artifact.owner
        ):
            return
    workspaces = m.Workspace.objects.filter(kind="ngo")
    if job.payload.get("program_id"):
        workspaces = workspaces.filter(program__id=job.payload["program_id"])
    for ws in workspaces.distinct():
        subscription = m.Subscription.objects.filter(owner=ws).first()
        if subscription and not subscription.evidence:
            continue
        if target_artifact:
            # A card-review event concerns exactly one card. Rechecking every
            # unrelated card for every recipient made seeded jobs quadratic.
            cards = (
                [target_artifact]
                if target_artifact.owner_id != ws.id and can_artifact(target_artifact, ws)
                else []
            )
        else:
            cards = [
                a
                for a in visible_artifacts(ws, kind="card")
                if a.status == "approved" and a.owner_id != ws.id
            ]
        programs = m.Program.objects.filter(owner=ws, source__state="active")
        for program in programs:
            profile = {
                "cause": program.cause,
                "population": program.population,
                "intervention": program.intervention,
                **program.context,
            }
            for artifact in cards:
                if not all(
                    can_source(dep.source, ws, "benchmarking", program.cause, program.geography)
                    for dep in artifact.dependencies.select_related("source")
                ):
                    continue
                card = artifact.card
                other = card.program
                candidate = {
                    "id": str(artifact.id),
                    "title": artifact.title,
                    "cause": other.cause,
                    "population": other.population,
                    "intervention": other.intervention,
                    "evidence_label": card.evidence_label,
                    "failures": card.failures,
                    **other.context,
                }
                matches = match_transfer(profile, [candidate])
                if matches.get("status") == "insufficient_evidence":
                    continue
                if program.cause != other.cause:
                    continue
                fingerprint = (
                    "match:"
                    + hashlib.sha256(
                        f"{ws.id}:{program.id}:{artifact.id}:{artifact.revision}".encode()
                    ).hexdigest()
                )
                m.Alert.objects.get_or_create(
                    fingerprint=fingerprint,
                    defaults={
                        "owner": ws,
                        "artifact": artifact,
                        "target_program": program,
                        "target_source": program.source,
                        "target_source_revision": program.source.revision,
                        "title": "New evidence for " + program.name,
                        "explanation": "Cause and population/context overlap. Inspect similarities, differences, missing evidence and adaptation questions before a pilot.",
                    },
                )


@transaction.atomic
def finish_job(job, result=None):
    # Every output commits after source lock and fresh lease check. Withdrawal uses same lock.
    if job.kind == "recommendations":
        artifact_sources = m.Source.objects.filter(
            dependency__artifact__kind="card", dependency__artifact__status="approved"
        ).values_list("id", flat=True)
        program_sources = m.Program.objects.filter(source__state="active").values_list(
            "source_id", flat=True
        )
        input_ids = set(artifact_sources) | set(program_sources)
        if job.source_id:
            input_ids.add(job.source_id)
        if len(input_ids) > 5000:
            raise ValueError("recommendation_batch_too_large")
        list(m.Source.objects.select_for_update().filter(pk__in=input_ids).order_by("id"))
    if job.source_id:
        m.Source.objects.select_for_update().get(pk=job.source_id)
    current = m.Job.objects.select_for_update().get(pk=job.id)
    if (
        current.state != "processing"
        or current.lease_token != job.lease_token
        or current.lease_expires_at <= timezone.now()
    ):
        return False
    if current.source_id:
        source = m.Source.objects.get(pk=current.source_id)
        if source.state != "active" or source.revision != current.source_revision:
            current.state = "canceled"
            current.save()
            return False
    if current.kind == "parse_import":
        batch = m.ImportBatch.objects.select_for_update().get(
            pk=current.payload["batch_id"], owner=current.owner
        )
        batch.status = result["status"]
        batch.columns = result.get("columns", [])[:64]
        batch.preview = result.get("preview", [])[:100]
        batch.diagnostics = result.get("diagnostics", [])[:1000]
        batch.save()
        batch.source.parser_version = result.get("parser_version", "aggregate-v1")
        batch.source.save()
    elif current.kind == "commit_import":
        _commit_import(current)
    elif current.kind == "delete_source":
        _delete_source(current)
    elif current.kind == "recommendations":
        _recommendations(current)
    elif current.kind == "pilot_monitor":
        from philanthra.pilot.services import run_monitor

        run_monitor(current)
    else:
        raise ValueError("unsupported_job_kind")
    current.state = "completed"
    current.lease_token = None
    current.lease_expires_at = None
    current.save()
    m.JobAttempt.objects.filter(job=current, token=job.lease_token).update(status="completed")
    logging.getLogger("philanthra.jobs").info(
        "job_completed",
        extra={
            "job_id": str(current.id),
            "workspace_id": str(current.owner_id),
            "status": current.state,
        },
    )
    return True


@transaction.atomic
def fail_job(job, code):
    current = m.Job.objects.select_for_update().get(pk=job.pk)
    if current.lease_token != job.lease_token or current.state != "processing":
        return
    logging.getLogger("philanthra.jobs").warning(
        "job_failed",
        extra={
            "job_id": str(current.id),
            "workspace_id": str(current.owner_id),
            "error_code": code,
        },
    )
    current.error_code = code
    current.state = "failed" if current.attempts >= current.max_attempts else "queued"
    current.available_at = timezone.now() + timedelta(seconds=2**current.attempts)
    current.lease_token = None
    current.lease_expires_at = None
    current.save()
    m.JobAttempt.objects.filter(job=current, token=job.lease_token).update(
        status="failed", error_code=code
    )


def run_once():
    expire_uploads()
    job = claim_job()
    if not job:
        return False
    try:
        result = _parse(job) if job.kind == "parse_import" else None
        finish_job(job, result)
    except Exception as exc:
        # Never put uploaded content or database exception text in logs/API.
        fail_job(job, type(exc).__name__)
    return True


@transaction.atomic
def expire_uploads():
    cutoff = timezone.now() - timedelta(hours=24)
    ids = list(
        m.ImportBatch.objects.filter(created_at__lt=cutoff, raw__isnull=False)
        .exclude(status="completed")
        .values_list("id", "source_id")
    )
    for batch_id, source_id in ids:
        m.Source.objects.select_for_update().get(pk=source_id)
        list(m.Job.objects.select_for_update().filter(source_id=source_id))
        batch = m.ImportBatch.objects.select_for_update().get(pk=batch_id)
        if batch.raw is None or batch.status == "completed":
            continue
        batch.raw = None
        batch.preview = []
        batch.columns = []
        batch.status = "expired"
        batch.save()
        m.Job.objects.filter(source=batch.source, state__in=["queued", "processing"]).update(
            state="canceled"
        )
        audit(batch.owner, None, "upload.expired", batch.id)
