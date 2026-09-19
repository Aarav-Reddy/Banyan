"""Current, public service-area coverage of a private planning portfolio."""

from django.utils import timezone

from .models import ServiceArea


def geographic_coverage(portfolio):
    allocations = list(portfolio.allocations.select_related("organization"))
    selected = {a.organization_id: a for a in allocations if a.amount_cents > 0}
    # Filter private/revoked existence before aggregating or counting anything.
    areas = (
        ServiceArea.objects.select_related("organization", "geography__source", "source")
        .filter(
            source__owner__isnull=True,
            source__state="active",
            geography__source__owner__isnull=True,
            geography__source__state="active",
            organization__cause__in={a.organization.cause for a in allocations},
            organization__country__in={a.organization.country for a in allocations},
            basis__in=["reported", "verified", "synthetic_reported"],
        )
        .order_by("geography__code", "organization__name")
    )
    groups = {}
    known_selected = set()
    sources = {}
    for area in areas:
        row = groups.setdefault(
            area.geography.code,
            {
                "code": area.geography.code,
                "name": area.geography.name,
                "kind": area.geography.kind,
                "directory_organization_ids": set(),
                "selected": {},
                "source_ids": set(),
            },
        )
        row["directory_organization_ids"].add(area.organization_id)
        for source in (area.source, area.geography.source):
            row["source_ids"].add(str(source.id))
            sources[str(source.id)] = {
                "id": str(source.id),
                "title": source.title,
                "kind": source.kind,
                "revision": source.revision,
                "checksum": source.checksum,
                "retrieved_at": source.retrieved_at,
                "period_end": source.period_end,
            }
        if area.organization_id in selected:
            known_selected.add(area.organization_id)
            row["selected"][str(area.organization_id)] = {
                "id": str(area.organization_id),
                "name": area.organization.name,
                "basis": area.basis,
            }
    rows = []
    for row in groups.values():
        organizations = list(row.pop("selected").values())
        row["directory_organization_count"] = len(row.pop("directory_organization_ids"))
        row["selected_organizations"] = organizations
        row["source_ids"] = sorted(row["source_ids"])
        row["status"] = (
            "potential_collaboration"
            if len(organizations) > 1
            else "represented"
            if organizations
            else "not_represented_in_plan"
        )
        rows.append(row)
    return {
        "method_version": "reported-service-area-coverage-v1",
        "as_of": timezone.now(),
        "scope": "Current active public reported/verified service areas in this directory for the candidates' causes and countries. This live view is separate from the approved allocation snapshot.",
        "caveat": "Areas absent from this plan are possible investigation gaps within this dataset, not proof of unmet need or underfunding. Shared areas suggest potential collaboration, not waste. An organization's allocation is not split across its service areas; no geographic funding totals are inferred. Headquarters addresses are excluded.",
        "areas": rows,
        "unknown_service_area_organizations": [
            {"id": str(a.organization_id), "name": a.organization.name}
            for a in allocations
            if a.organization_id in selected and a.organization_id not in known_selected
        ],
        "sources": list(sources.values()),
    }
