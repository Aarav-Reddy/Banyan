"""Narrow operator-reviewed registry/opportunity imports, preserving source records."""

import csv
import hashlib
import io
from datetime import date, datetime
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.validators import URLValidator
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from philanthra.core import models as m
from philanthra.core.services import audit
from philanthra.ingestion.common import MAX_BYTES

FIELDS = {
    "organization": {
        "namespace",
        "external_id",
        "name",
        "mission",
        "country",
        "cause",
        "headquarters_zip",
    },
    "opportunity": {
        "external_id",
        "title",
        "cause",
        "geography",
        "eligibility",
        "deadline",
        "amount_cents",
    },
}


@transaction.atomic
def import_manual(payload, kind, metadata, actor):
    if not actor.is_active or not actor.is_staff:
        raise PermissionDenied("Platform operator required for public catalogue imports.")
    if kind not in FIELDS or len(payload) > MAX_BYTES:
        raise ValidationError("Unsupported import type or excessive size.")
    source_kind = metadata.get("source_kind")
    if source_kind not in {"public_source", "synthetic_demo"}:
        raise ValidationError("Explicit source kind required.")
    if source_kind == "synthetic_demo" and settings.ENVIRONMENT not in {"demo", "test"}:
        raise ValidationError("Synthetic imports require demo/test mode.")
    url = metadata.get("source_url", "")
    if source_kind == "public_source":
        URLValidator(schemes=["https"])(url)
    try:
        retrieved = datetime.fromisoformat(metadata["retrieved_at"].replace("Z", "+00:00"))
        if timezone.is_naive(retrieved):
            raise ValueError()
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
        if not reader.fieldnames or set(reader.fieldnames) != FIELDS[kind]:
            raise ValueError()
        rows = list(reader)
        if not rows or len(rows) > 1000:
            raise ValueError()
        for row in rows:
            if any(
                v is None or len(v) > 4000 or v.lstrip().startswith(("=", "+", "-", "@"))
                for v in row.values()
            ):
                raise ValueError()
            if not row["external_id"] or not row.get("name", row.get("title")):
                raise ValueError()
    except (KeyError, ValueError, UnicodeDecodeError, csv.Error) as exc:
        raise ValidationError(
            "Exact template headers, bounded plain-text fields and timezone retrieval timestamp required; transaction rejected."
        ) from exc
    checksum = hashlib.sha256(payload).hexdigest()
    inserted = 0
    for number, row in enumerate(rows, 2):
        sid = uuid5(NAMESPACE_URL, f"manual:{kind}:{checksum}:{row['external_id']}")
        src, created = m.Source.objects.get_or_create(
            id=sid,
            defaults={
                "title": ("Fictional demo · " if source_kind == "synthetic_demo" else "")
                + row.get("name", row.get("title")),
                "kind": source_kind,
                "source_url": url,
                "retrieved_at": retrieved,
                "parser_version": "manual-catalog-v1",
                "checksum": checksum,
                "locator": f"CSV row {number}",
                "transformations": [{"reported_fields": row}],
            },
        )
        if not created:
            continue
        if kind == "organization":
            namespace = row["namespace"]
            if not namespace or namespace in {"irs_ein", "philanthra_demo"}:
                raise ValidationError(
                    "Use an explicit country/registry namespace; IRS identities require the IRS adapter."
                )
            if source_kind == "synthetic_demo":
                namespace = "synthetic:" + namespace
            identifier = m.ExternalIdentifier.objects.filter(
                namespace=namespace, value=row["external_id"]
            ).first()
            if identifier:
                if identifier.organization.source_kind != source_kind:
                    raise ValidationError("Synthetic/real identity collision.")
                continue
            org = m.Organization.objects.create(
                name=src.title,
                mission=row["mission"],
                country=row["country"],
                cause=row["cause"],
                headquarters_zip=row["headquarters_zip"],
                source_kind=source_kind,
                status="source_reported_unverified",
            )
            m.ExternalIdentifier.objects.create(
                organization=org, namespace=namespace, value=row["external_id"]
            )
        else:
            try:
                amount = int(row["amount_cents"]) if row["amount_cents"] else None
                if amount is not None and not 0 <= amount <= 10**15:
                    raise ValueError()
                deadline = date.fromisoformat(row["deadline"])
            except ValueError as exc:
                raise ValidationError("Invalid deadline or integer minor-unit amount.") from exc
            m.Opportunity.objects.create(
                title=src.title,
                cause=row["cause"],
                geography=row["geography"],
                eligibility=row["eligibility"],
                deadline=deadline,
                amount_cents=amount,
                source=src,
            )
        audit(None, actor, "catalog.manual_imported", src.id, kind=kind)
        inserted += 1
    return {"inserted": inserted, "rows": len(rows)}
