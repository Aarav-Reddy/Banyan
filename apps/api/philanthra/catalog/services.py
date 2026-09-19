"""Operator-authorized, idempotent persistence for normalized public records.

Financial amendments are retained; active revision selection is explicit. Source
snapshots preserve fields that cannot responsibly be mapped to outcome observations.
"""

from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from philanthra.core import models as m
from philanthra.core.services import audit


def identity(record):
    provenance = record["source"]
    if provenance["source_kind"] == "synthetic_demo":
        return "parser_fixture", str(
            record.get("reporting_org") or record.get("ein") or record["external_id"]
        )
    if record.get("ein"):
        return "irs_ein", record["ein"]
    return "iati_org", record.get("reporting_org", record["external_id"])


def invalidate_filings(filings):
    """Changing active selection invalidates prior snapshots without rewriting reported figures."""
    for filing in filings:
        source = m.Source.objects.select_for_update().get(pk=filing.source_id)
        source.revision += 1
        source.save(update_fields=["revision", "updated_at"])
        artifacts = m.Artifact.objects.filter(dependencies__source=source)
        artifacts.update(status="invalidated")
        m.Alert.objects.filter(artifact__in=artifacts).update(state="invalidated")
        filing.active = False
        filing.save(update_fields=["active", "updated_at"])


@transaction.atomic
def persist_public(records, actor, *, activate=False):
    if not actor.is_active or not actor.is_staff:
        raise PermissionDenied("An authorized platform operator must run public-source imports.")
    counts = {"sources": 0, "organizations": 0, "filings": 0, "contexts": 0, "duplicates": 0}
    # Serializes source idempotency and cross-file amendment selection for this narrow operator path.
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(72401927)")
    for record in records:
        metadata = record.get("source", {})
        kind = metadata.get("source_kind")
        if kind not in {"public_source", "synthetic_demo"}:
            raise ValidationError(
                "Public import requires an explicit trusted public/synthetic manifest."
            )
        if kind == "synthetic_demo" and not settings.DEMO_MODE and settings.ENVIRONMENT != "test":
            raise ValidationError(
                "Synthetic catalog records are restricted to demo/test environments."
            )
        if kind == "public_source" and not metadata.get("source_url"):
            raise ValidationError("Public imports require the verified original source location.")
        retrieved = metadata.get("retrieved_at")
        if not retrieved:
            raise ValidationError(
                "A retrieval timestamp is required independently of the reporting period."
            )
        try:
            retrieved_at = datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
            if timezone.is_naive(retrieved_at):
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise ValidationError("Retrieval time must include a timezone.") from exc
        key = f"philanthra/source/{metadata['checksum']}/{record['external_id']}"
        sid = uuid5(NAMESPACE_URL, key)
        if m.Source.objects.filter(pk=sid).exists():
            counts["duplicates"] += 1
            if activate:
                existing = m.Filing.objects.filter(source_id=sid).first()
                if existing and not existing.active:
                    invalidate_filings(
                        m.Filing.objects.filter(
                            organization=existing.organization,
                            tax_year=existing.tax_year,
                            form=existing.form,
                            active=True,
                        ).exclude(pk=existing.pk)
                    )
                    existing.active = True
                    existing.save(update_fields=["active", "updated_at"])
            continue
        title = record.get("name") or next(
            (x["text"] for x in record.get("title", []) if x.get("text")), record["external_id"]
        )
        src = m.Source.objects.create(
            id=sid,
            title=("Fictional parser fixture · " if kind == "synthetic_demo" else "")
            + str(title)[:180],
            kind=kind,
            source_url=metadata.get("source_url") or "",
            retrieved_at=retrieved_at,
            period_start=record.get("period_start"),
            period_end=record.get("period_end"),
            parser_version=metadata["parser_version"],
            checksum=metadata["checksum"],
            locator=record.get("locator", "/Return")[:240],
            transformations=[
                {
                    "method": "explicit schema normalization",
                    "record": {k: v for k, v in record.items() if k != "source"},
                }
            ],
        )
        counts["sources"] += 1
        record_kind = record["kind"]
        if record_kind == "community_context":
            code = record["external_id"]
            geography, _ = m.Geography.objects.get_or_create(
                code=code,
                defaults={
                    "name": f"{record['geography_type']} {'/'.join(record['geography'].values())}",
                    "kind": record["geography_type"],
                    "source": src,
                    "context": record,
                },
            )
            if geography.source_id != src.id:
                geography.source = src
                geography.context = record
                geography.save()
            counts["contexts"] += 1
        elif record_kind in {
            "nonprofit_filing",
            "foundation_filing",
            "eo_bmf_snapshot",
            "revocation_event",
            "filing_notice",
            "iati_activity",
        }:
            namespace, external = identity(record)
            identifier = (
                m.ExternalIdentifier.objects.select_related("organization")
                .filter(namespace=namespace, value=external)
                .first()
            )
            if identifier:
                org = m.Organization.objects.select_for_update().get(pk=identifier.organization_id)
                if org.source_kind != kind:
                    raise ValidationError(
                        "Cannot merge synthetic and real organization identities."
                    )
            else:
                org = m.Organization.objects.create(
                    name=("Fictional parser fixture · " if kind == "synthetic_demo" else "")
                    + str(title)[:160],
                    mission=record.get("mission") or "",
                    source_kind=kind,
                    headquarters_zip=record.get("filing_address_zip") or "",
                    status="source_reported_unverified",
                    cause="unclassified",
                    country="US" if record.get("ein") else "",
                )
                m.ExternalIdentifier.objects.create(
                    organization=org, namespace=namespace, value=external
                )
                counts["organizations"] += 1
            if record_kind in {"nonprofit_filing", "foundation_filing"}:
                previous = m.Filing.objects.filter(
                    organization=org, tax_year=record["tax_year"], form=record["form"]
                )
                revision = max(previous.values_list("revision", flat=True), default=0) + 1
                if activate:
                    invalidate_filings(previous.filter(active=True))
                cash = record.get("cash_noninterest")
                caveats = (
                    [
                        "Cash field is reported non-interest-bearing cash only; restrictions and completeness are unknown."
                    ]
                    if cash is not None
                    else []
                )
                if record["form"] == "990PF":
                    caveats.append(
                        "Foundation 990-PF: charitable disbursements are distinct from functional program spending."
                    )
                if (
                    record.get("functional_total")
                    and record.get("expenses") != record["functional_total"]
                ):
                    caveats.append(
                        "Functional expense total differs from summary expenses; program share is not comparable."
                    )
                m.Filing.objects.create(
                    organization=org,
                    source=src,
                    form=record["form"],
                    tax_year=record["tax_year"],
                    period_start=record["period_start"],
                    period_end=record["period_end"],
                    revision=revision,
                    amended=record["amended"],
                    active=activate,
                    currency="USD",
                    **{
                        field: Decimal(record[field]) if record.get(field) is not None else None
                        for field in ("revenue", "expenses", "assets", "liabilities")
                    },
                    program_expenses=Decimal(record["program_expenses"])
                    if record.get("program_expenses") is not None
                    and "not comparable" not in " ".join(caveats)
                    else None,
                    cash=Decimal(cash) if cash is not None else None,
                    caveats=caveats,
                )
                counts["filings"] += 1
            # Status events and IATI remain source-reported registry records; neither grants
            # workspace control, certifies deductibility, nor becomes effectiveness evidence.
        audit(
            None,
            actor,
            "public_source.imported",
            src.id,
            record_kind=record_kind,
            activated=activate,
        )
    return counts
