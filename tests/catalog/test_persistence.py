from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from philanthra.catalog.context import ensure_public_context
from philanthra.catalog.services import persist_public
from philanthra.core import models as m
from philanthra.core.services import create_artifact
from philanthra.ingestion import parse_source
from rest_framework.exceptions import PermissionDenied

pytestmark = pytest.mark.django_db
FIXTURES = Path(__file__).resolve().parents[2] / "data/fixtures/ingestion"


def records(name):
    result = parse_source(
        (FIXTURES / name).read_bytes(),
        "irs_xml",
        {"source_kind": "synthetic_demo", "retrieved_at": "2026-09-01T12:00:00Z"},
    )
    assert result["status"] == "validated", result["diagnostics"]
    return result["records"]


def test_public_ingestion_revisions_idempotency_and_source_invalidation():
    actor = get_user_model().objects.create_user("operator", is_staff=True)
    ws = m.Workspace.objects.create(name="Operator test", kind="foundation")
    original = records("irs_990_2024.xml")
    counts = persist_public(original, actor, activate=True)
    assert counts["filings"] == 1
    assert persist_public(original, actor)["duplicates"] == 1
    filing = m.Filing.objects.get()
    assert m.ExternalIdentifier.objects.get().namespace == "parser_fixture"
    artifact = create_artifact(
        ws, actor, kind="portfolio", title="Snapshot", sources=[filing.source]
    )
    assert (
        persist_public(records("irs_990_2024_amended.xml"), actor, activate=False)["filings"] == 1
    )
    filing.refresh_from_db()
    artifact.refresh_from_db()
    assert filing.active and artifact.status == "draft"
    persist_public(records("irs_990_2024_amended.xml"), actor, activate=True)
    filing.refresh_from_db()
    artifact.refresh_from_db()
    assert not filing.active and artifact.status == "invalidated"
    assert m.Filing.objects.get(active=True).amended
    assert m.Filing.objects.count() == 2


def test_operator_authority_is_required_and_context_is_real_city_only():
    actor = get_user_model().objects.create_user("ordinary")
    with pytest.raises(PermissionDenied):
        persist_public(records("irs_990_2024.xml"), actor)
    ensure_public_context()
    ensure_public_context()
    geo = m.Geography.objects.get()
    assert geo.kind == "census_place" and geo.latitude is None
    assert (
        geo.source.kind == "public_source" and geo.context["indicators"][0]["estimate"] == "62177"
    )
    assert geo.context["indicators"][0]["margin_of_error"] is None
    assert not m.ServiceArea.objects.exists()


def test_manual_registry_and_grant_import_are_atomic_idempotent_and_scoped():
    from philanthra.catalog.manual import import_manual
    from rest_framework.exceptions import ValidationError

    actor = get_user_model().objects.create_user("manual-operator", is_staff=True)
    metadata = {"source_kind": "synthetic_demo", "retrieved_at": "2026-09-01T12:00:00Z"}
    csv = b"external_id,title,cause,geography,eligibility,deadline,amount_cents\nG1,Training grant,food_security,US-MD-Baltimore,Local registered contributors,2026-12-01,100000\n"
    assert import_manual(csv, "opportunity", metadata, actor)["inserted"] == 1
    assert import_manual(csv, "opportunity", metadata, actor)["inserted"] == 0
    assert m.Opportunity.objects.get().amount_cents == 100000
    before = m.Source.objects.count()
    with pytest.raises(ValidationError):
        import_manual(csv.replace(b"100000", b"invalid"), "opportunity", metadata, actor)
    assert m.Source.objects.count() == before
    registry = b"namespace,external_id,name,mission,country,cause,headquarters_zip\nMX:registry,000012,Fictional manual NGO,Food distribution,MX,food_security,00120\n"
    import_manual(registry, "organization", metadata, actor)
    org = m.Organization.objects.get()
    assert org.headquarters_zip == "00120"
    assert m.ExternalIdentifier.objects.get().value == "000012"
    assert not m.Workspace.objects.filter(organization=org).exists()
    with pytest.raises(ValidationError):
        import_manual(
            csv.replace(b"title,cause", b"beneficiary_name,cause"), "opportunity", metadata, actor
        )
