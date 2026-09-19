"""Independent adversarial integration checks, using real PostgreSQL transactions."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta
from threading import Event
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.utils import timezone
from philanthra.core import models as m
from philanthra.core.policy import can_artifact
from philanthra.core.services import (
    Conflict,
    create_artifact,
    decide_review,
    enqueue,
    submit_review,
    withdraw,
)
from philanthra.jobs.worker import claim_job, finish_job
from rest_framework.test import APIClient

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


@pytest.fixture
def records():
    assert connection.vendor == "postgresql"
    user = get_user_model().objects.create_user("qa-owner")
    reviewer = get_user_model().objects.create_user("qa-reviewer")
    outsider = get_user_model().objects.create_user("qa-outsider")
    org = m.Organization.objects.create(name="QA fictional organization")
    owner = m.Workspace.objects.create(name="QA contributor", kind="ngo", organization=org)
    other = m.Workspace.objects.create(name="QA other contributor", kind="ngo", organization=org)
    review = m.Workspace.objects.create(name="QA review", kind="foundation")
    for actor, ws, role in [
        (user, owner, "owner"),
        (outsider, other, "owner"),
        (reviewer, review, "reviewer"),
    ]:
        m.Membership.objects.create(user=actor, workspace=ws, role=role)
    source = m.Source.objects.create(
        owner=owner,
        title="QA secret source",
        kind="ngo_contributed",
        retrieved_at=timezone.now(),
        parser_version="qa-v1",
        checksum="1" * 64,
    )
    artifact = create_artifact(
        owner, user, kind="card", title="QA secret finding", sources=[source]
    )
    program = m.Program.objects.create(
        owner=owner,
        organization=org,
        source=source,
        name="QA program",
        intervention="food parcels",
        population="households",
        geography=source.geography,
    )
    m.Card.objects.create(artifact=artifact, program=program)
    batch = m.ImportBatch.objects.create(
        owner=owner,
        source=source,
        created_by=user,
        filename="qa.csv",
        checksum="2" * 64,
        format="csv",
        raw=b"private",
    )
    return dict(
        user=user,
        reviewer=reviewer,
        outsider=outsider,
        owner=owner,
        other=other,
        source=source,
        artifact=artifact,
        program=program,
        batch=batch,
    )


def in_connection(fn):
    close_old_connections()
    try:
        return fn()
    finally:
        connection.close()


def test_withdrawal_commits_before_waiting_worker_can_finalize(records):
    r = records
    enqueue(r["owner"], "parse_import", "qa-parse", {"batch_id": str(r["batch"].id)}, r["source"])
    job = claim_job()
    started = Event()

    def finish():
        started.set()
        return finish_job(
            job, {"status": "validated", "preview": [{"private": "must never publish"}]}
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Source.objects.select_for_update().get(pk=r["source"].id)
            future = pool.submit(in_connection, finish)
            assert started.wait(5)
            withdraw(r["source"], r["user"])
        assert future.result(timeout=10) is False
    r["batch"].refresh_from_db()
    assert r["batch"].preview == []
    assert m.Job.objects.get(pk=job.id).state == "canceled"


def test_withdrawal_wins_against_waiting_publication(records):
    r = records
    submit_review(r["artifact"], r["user"], r["reviewer"].id, 1)
    started = Event()

    def approve():
        started.set()
        with pytest.raises(Conflict):
            decide_review(
                r["artifact"], r["reviewer"], 1, "approved", "Reviewed precise source revision."
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            m.Source.objects.select_for_update().get(pk=r["source"].id)
            future = pool.submit(in_connection, approve)
            assert started.wait(5)
            withdraw(r["source"], r["user"])
        future.result(timeout=10)
    assert not m.ReviewDecision.objects.filter(artifact=r["artifact"], decision="approved").exists()
    r["artifact"].refresh_from_db()
    assert not can_artifact(r["artifact"], r["owner"])


def test_reclaimed_lease_fences_concurrent_old_worker(records):
    r = records
    enqueue(r["owner"], "parse_import", "qa-lease", {"batch_id": str(r["batch"].id)}, r["source"])
    old = claim_job()
    m.Job.objects.filter(pk=old.id).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    current = claim_job()
    with ThreadPoolExecutor(max_workers=2) as pool:
        old_result = pool.submit(
            in_connection,
            lambda: finish_job(old, {"status": "validated", "preview": [{"version": "stale"}]}),
        )
        new_result = pool.submit(
            in_connection,
            lambda: finish_job(
                current, {"status": "validated", "preview": [{"version": "current"}]}
            ),
        )
        assert old_result.result(timeout=10) is False
        assert new_result.result(timeout=10) is True
    r["batch"].refresh_from_db()
    assert r["batch"].preview == [{"version": "current"}]


def test_no_alert_is_created_after_authorization_races_with_withdrawal(records):
    r = records
    r["artifact"].status = "approved"
    r["artifact"].save()
    m.DataGrant.objects.create(
        source=r["source"],
        purpose="donor_access",
        recipient=r["other"],
        cause=r["source"].cause,
        geography=r["source"].geography,
    )
    m.DataGrant.objects.create(
        source=r["source"],
        purpose="benchmarking",
        recipient=r["other"],
        cause=r["source"].cause,
        geography=r["source"].geography,
    )
    other_source = m.Source.objects.create(
        owner=r["other"],
        title="Other source",
        kind="ngo_contributed",
        retrieved_at=timezone.now(),
        parser_version="qa-v1",
        checksum="3" * 64,
    )
    m.Program.objects.create(
        owner=r["other"],
        organization=r["program"].organization,
        source=other_source,
        name="Other program",
        intervention="food parcels",
        population="households",
        geography=r["source"].geography,
    )
    enqueue(r["owner"], "recommendations", "qa-recommend", {"artifact_id": str(r["artifact"].id)})
    job = claim_job()
    reached = Event()
    resume = Event()
    from philanthra.analytics.matching import match_transfer

    def paused_match(*args, **kwargs):
        reached.set()
        assert resume.wait(10), "withdrawal did not finish"
        return match_transfer(*args, **kwargs)

    with patch("philanthra.analytics.matching.match_transfer", side_effect=paused_match):
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(in_connection, lambda: finish_job(job))
            if not reached.wait(10):
                future.result(timeout=1)
                pytest.fail("fixture did not reach recommendation authorization boundary")
            try:
                withdrawal = pool.submit(in_connection, lambda: withdraw(r["source"], r["user"]))
                try:
                    withdrawal.result(timeout=0.5)
                except TimeoutError:
                    pass  # Correct source locking serializes withdrawal after finalization.
            finally:
                resume.set()
            future.result(timeout=10)
            withdrawal.result(timeout=10)
    assert (
        not m.Alert.objects.filter(artifact=r["artifact"]).exclude(state="invalidated").exists()
    ), "worker created a live derivative after source withdrawal"


def test_guessed_ids_lists_exports_graph_and_jobs_reveal_no_private_records(records):
    r = records
    job = enqueue(
        r["owner"], "parse_import", "qa-hidden", {"batch_id": str(r["batch"].id)}, r["source"]
    )
    client = APIClient()
    client.force_authenticate(r["outsider"])
    client.credentials(HTTP_X_WORKSPACE_ID=str(r["other"].id))
    for path in [
        f"sources/{r['source'].id}/",
        f"cards/{r['artifact'].id}/",
        f"reports/{r['artifact'].id}/",
        f"reports/{r['artifact'].id}/?format=csv",
        f"jobs/{job.id}/",
        f"imports/{r['batch'].id}/",
        f"imports/{r['batch'].id}/rejected/",
    ]:
        response = client.get("/api/v1/" + path)
        assert response.status_code == 404, (path, response.content)
        assert b"QA secret" not in response.content
    for path in ["sources/", "cards/?q=secret", "jobs/", "imports/", "programs/", "reviews/"]:
        response = client.get("/api/v1/" + path)
        assert response.status_code == 200, (path, response.content)
        assert response.json()["data"] == []
    for root in [r["artifact"].id, r["source"].id]:
        assert client.get(f"/api/v1/graph/?root={root}").json()["data"]["edges"] == []
    assert (
        client.patch(
            f"/api/v1/cards/{r['artifact'].id}/", {"revision": 1, "title": "stolen"}, format="json"
        ).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/sources/{r['source'].id}/withdraw/", {}, format="json").status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/explanations/{r['artifact'].id}/", {}, format="json").status_code
        == 404
    )


def test_source_owner_loses_upload_preview_immediately_on_withdrawal(records):
    r = records
    r["batch"].preview = [{"private": "normalized aggregate value"}]
    r["batch"].save()
    withdraw(r["source"], r["user"])
    client = APIClient()
    client.force_authenticate(r["user"])
    client.credentials(HTTP_X_WORKSPACE_ID=str(r["owner"].id))
    assert client.get(f"/api/v1/imports/{r['batch'].id}/").status_code == 404
    assert client.get(f"/api/v1/imports/{r['batch'].id}/rejected/").status_code == 404
    assert client.get("/api/v1/imports/").json()["data"] == []


def test_review_assignment_cannot_expand_third_party_source_grant(records):
    r = records
    m.DataGrant.objects.create(
        source=r["source"],
        purpose="donor_access",
        recipient=r["other"],
        cause=r["source"].cause,
        geography=r["source"].geography,
    )
    derived = create_artifact(
        r["other"],
        r["outsider"],
        kind="test",
        title="Third-party derivative",
        sources=[r["source"]],
    )
    from rest_framework.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):
        submit_review(derived, r["outsider"], r["reviewer"].id, 1)
    assert not derived.assignments.exists()


def test_target_program_withdrawal_invalidates_preexisting_recommendation(records):
    r = records
    # A public peer finding must still be denied when the private target context disappears.
    peer = m.Source.objects.create(
        title="Synthetic public peer finding",
        kind="synthetic_demo",
        retrieved_at=timezone.now(),
        parser_version="qa-v1",
        checksum="4" * 64,
    )
    card = create_artifact(
        r["other"], r["outsider"], kind="test", title="Peer result", sources=[peer]
    )
    card.status = "approved"
    card.save()
    alert = m.Alert.objects.create(
        owner=r["owner"],
        artifact=card,
        target_program=r["program"],
        target_source=r["source"],
        target_source_revision=r["source"].revision,
        title="Private target recommendation",
        explanation="Uses target context",
        fingerprint="qa-target",
    )
    withdraw(r["source"], r["user"])
    alert.refresh_from_db()
    assert alert.state == "invalidated"
    client = APIClient()
    client.force_authenticate(r["user"])
    client.credentials(HTTP_X_WORKSPACE_ID=str(r["owner"].id))
    assert client.get("/api/v1/alerts/").json()["data"] == []


def test_manual_allocation_cannot_break_exclusions_or_minimums(records):
    from philanthra.core.services import create_portfolio

    r = records
    r["owner"].kind = "foundation"
    r["owner"].save()
    one = r["program"].organization
    one.capacity_cents = 10000
    one.save()
    two = m.Organization.objects.create(
        name="Excluded synthetic organization", capacity_cents=10000
    )
    artifact = create_portfolio(
        r["owner"],
        r["user"],
        {
            "name": "Frozen constraints",
            "budget_cents": 10000,
            "candidates": [
                {"organization_id": str(one.id), "minimum_cents": 1000},
                {"organization_id": str(two.id), "excluded": True},
            ],
        },
    )
    client = APIClient()
    client.force_authenticate(r["user"])
    client.credentials(HTTP_X_WORKSPACE_ID=str(r["owner"].id))
    for first, second in [(9999, 1), (999, 0)]:
        response = client.patch(
            f"/api/v1/portfolios/{artifact.id}/",
            {
                "revision": 1,
                "allocations": [
                    {"organization_id": str(one.id), "amount_cents": first},
                    {"organization_id": str(two.id), "amount_cents": second},
                ],
            },
            format="json",
        )
        assert response.status_code == 400, response.content
    artifact.refresh_from_db()
    assert artifact.revision == 1
    assert artifact.portfolio.allocations.get(organization=one).amount_cents == 10000
    assert artifact.portfolio.allocations.get(organization=two).amount_cents == 0


def test_suppressed_complete_release_has_no_reconstructable_totals_or_citations(records):
    r = records
    definition = m.OutcomeDefinition.objects.create(
        code="qa_binary",
        name="QA indicator",
        definition="QA fixed binary measure",
        unit="proportion",
        direction="higher_is_better",
    )
    observations = []
    for i, counts in enumerate([(9, 100), (50, 100), (60, 100)]):
        organization = m.Organization.objects.create(name=f"QA synthetic pooling {i}")
        owner = m.Workspace.objects.create(
            name=f"QA pooling owner {i}", kind="ngo", organization=organization
        )
        source = m.Source.objects.create(
            owner=owner,
            title=f"QA private contributor {i}",
            kind="ngo_contributed",
            retrieved_at=timezone.now(),
            parser_version="qa-v1",
            checksum=str(i) * 64,
        )
        m.DataGrant.objects.create(
            source=source,
            purpose="pooled_analysis",
            recipient=r["owner"],
            cause=source.cause,
            geography=source.geography,
        )
        program = m.Program.objects.create(
            owner=owner,
            organization=organization,
            source=source,
            name="QA comparable program",
            intervention="food parcels",
            population="households",
            geography=source.geography,
        )
        observations.append(
            m.Observation.objects.create(
                owner=owner,
                source=source,
                program=program,
                outcome=definition,
                numerator=counts[0],
                denominator=counts[1],
                cohort_id=f"qa-{i}",
                study_id=f"qa-study-{i}",
                independent=True,
                period_start="2025-01-01",
                period_end="2025-06-30",
            )
        )
    client = APIClient()
    client.force_authenticate(r["user"])
    client.credentials(HTTP_X_WORKSPACE_ID=str(r["owner"].id))
    ids = [str(o.id) for o in observations]
    response = client.post(
        "/api/v1/analyses/",
        {"title": "QA suppressed fixed release", "observation_ids": ids},
        format="json",
    )
    assert response.status_code == 201, response.content
    result = response.json()["data"]
    assert result["payload"]["status"] == "suppressed"
    for key in [
        "weighted_rate",
        "equal_organization_rate",
        "denominator",
        "numerator",
        "organization_count",
        "cohort_count",
        "per_organization",
    ]:
        assert key not in result["payload"], f"Suppression leaked {key}"
    assert result["payload"]["source_ids"] == []
    assert result["sources"] == []
    report = client.get(f"/api/v1/reports/{result['id']}/?format=csv")
    assert report.status_code == 200
    assert b"weighted_rate" not in report.content
    for observation in observations:
        assert str(observation.source_id).encode() not in report.content
    for subset in [ids[:2], ids[1:]]:
        assert (
            client.post("/api/v1/analyses/", {"observation_ids": subset}, format="json").status_code
            == 400
        )
    assert client.get("/api/v1/observations/").json()["data"] == []
