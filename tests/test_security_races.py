"""Independent regression: queued edits must reauthorize after withdrawal wins a row lock."""

import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.utils import timezone
from philanthra.core import models as m
from philanthra.core.services import create_artifact, withdraw
from rest_framework.test import APIClient

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


@pytest.fixture
def edit_records():
    user = get_user_model().objects.create_user("security-edit-owner")
    org = m.Organization.objects.create(name="Synthetic security race organization")
    workspace = m.Workspace.objects.create(
        name="Security race workspace", kind="ngo", organization=org
    )
    m.Membership.objects.create(user=user, workspace=workspace, role="owner")
    source = m.Source.objects.create(
        owner=workspace,
        title="Private race source",
        kind="ngo_contributed",
        retrieved_at=timezone.now(),
        parser_version="security-test-v1",
        checksum="9" * 64,
    )
    program = m.Program.objects.create(
        owner=workspace,
        organization=org,
        source=source,
        name="Private original program",
        cause=source.cause,
        geography=source.geography,
        population="households",
        intervention="parcels",
        context={"setting": "urban"},
    )
    card = create_artifact(
        workspace, user, kind="card", title="Private original card", sources=[source]
    )
    m.Card.objects.create(artifact=card, program=program)
    portfolio = create_artifact(
        workspace, user, kind="portfolio", title="Private original plan", sources=[source]
    )
    m.Portfolio.objects.create(
        artifact=portfolio,
        budget_cents=100,
        currency="USD",
        constraints={"candidates": []},
        unallocated_cents=100,
    )
    batch = m.ImportBatch.objects.create(
        owner=workspace,
        source=source,
        created_by=user,
        filename="private.csv",
        checksum="8" * 64,
        format="csv",
        raw=b"private fixture",
        status="validated",
        mapping={},
    )
    return user, workspace, source, program, card, portfolio, batch


def wait_for_postgres_lock(pid):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", [pid])
            state = cursor.fetchone()
        if state and state[0] == "Lock":
            return
        time.sleep(0.02)
    pytest.fail("PATCH did not reach the intended PostgreSQL source-row lock")


@pytest.mark.parametrize("kind", ["card", "portfolio", "program", "import"])
def test_withdrawal_before_waiting_patch_prevents_mutation_and_response_disclosure(
    edit_records, kind
):
    user, workspace, source, program, card, portfolio, batch = edit_records
    endpoint, payload = {
        "card": (
            f"/api/v1/cards/{card.id}/",
            {"revision": 1, "title": "Must never restore this title"},
        ),
        "portfolio": (f"/api/v1/portfolios/{portfolio.id}/", {"revision": 1, "allocations": []}),
        "program": (
            f"/api/v1/programs/{program.id}/",
            {"revision": 1, "name": "Must never restore this name"},
        ),
        "import": (f"/api/v1/imports/{batch.id}/", {"mapping": {"private": "program_name"}}),
    }[kind]
    pids = Queue()

    def patch_request():
        close_old_connections()
        try:
            connection.ensure_connection()
            pids.put(connection.connection.info.backend_pid)
            client = APIClient()
            client.force_authenticate(user)
            client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
            return client.patch(endpoint, payload, format="json")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            m.Source.objects.select_for_update().get(pk=source.id)
            pending = executor.submit(patch_request)
            wait_for_postgres_lock(pids.get(timeout=5))
            withdraw(source, user)
        response = pending.result(timeout=10)

    assert response.status_code in {403, 404, 409}, response.data
    assert "Private original" not in str(response.data)
    source.refresh_from_db()
    assert source.state == "withdrawn"
    program.refresh_from_db()
    card.refresh_from_db()
    portfolio.refresh_from_db()
    batch.refresh_from_db()
    assert program.name == "Private original program"
    assert program.revision == 1
    assert card.title == "Private original card"
    assert card.status == "invalidated"
    assert card.revision == 1
    assert portfolio.status == "invalidated"
    assert portfolio.revision == 1
    assert batch.mapping == {}
    assert batch.status == "validated"
    assert not m.Job.objects.filter(source=source, state="queued").exists()


@pytest.mark.parametrize(
    "invalidation", ["pending", "rejected", "withdrawn", "grant", "source_edit"]
)
def test_verified_identity_is_removed_on_every_review_invalidation(edit_records, invalidation):
    from philanthra.core.services import decide_review, submit_review
    from philanthra.pilot.models import IdentityClaim

    owner, workspace, source, program, *_ = edit_records
    organization = workspace.organization
    workspace.organization = None
    workspace.save(update_fields=["organization"])
    reviewer = get_user_model().objects.create_user("security-independent-reviewer")
    review_workspace = m.Workspace.objects.create(name="Independent review", kind="foundation")
    m.Membership.objects.create(user=reviewer, workspace=review_workspace, role="reviewer")
    artifact = create_artifact(
        workspace,
        owner,
        kind="identity_claim",
        title="Synthetic identity proof review",
        sources=[source],
    )
    claim = IdentityClaim.objects.create(
        artifact=artifact,
        organization=organization,
        proof_source=source,
        statement="Synthetic evidence supplied only for the identity revocation regression.",
    )
    submit_review(artifact, owner, reviewer.id, 1)
    decide_review(artifact, reviewer, 1, "approved", "Test verifies authorized identity linkage.")
    workspace.refresh_from_db()
    assert workspace.organization_id == organization.id

    if invalidation in {"pending", "rejected"}:
        submit_review(artifact, owner, reviewer.id, 1)
        if invalidation == "rejected":
            decide_review(artifact, reviewer, 1, "rejected", "Authority cannot be confirmed.")
    elif invalidation == "withdrawn":
        decide_review(
            artifact, reviewer, 1, "withdrawn", "Previously approved authority withdrawn."
        )
    else:
        client = APIClient()
        client.force_authenticate(owner)
        client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
        if invalidation == "grant":
            grant = m.DataGrant.objects.create(
                source=source,
                purpose="donor_access",
                audience="public",
                cause=source.cause,
                geography=source.geography,
            )
            response = client.delete(f"/api/v1/grants/{grant.id}/")
        else:
            response = client.patch(
                f"/api/v1/programs/{program.id}/",
                {"revision": 1, "name": "Changed underlying source profile"},
                format="json",
            )
        assert response.status_code == 200, response.data

    workspace.refresh_from_db()
    claim.refresh_from_db()
    assert workspace.organization_id is None
    assert claim.linked_revision is None
