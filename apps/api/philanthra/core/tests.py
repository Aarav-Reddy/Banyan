from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from philanthra.jobs.worker import claim_job, finish_job, run_once

from . import models as m
from .policy import can_artifact, can_source
from .services import (
    Conflict,
    create_artifact,
    create_portfolio,
    decide_review,
    enqueue,
    submit_review,
    withdraw,
)


class DomainFixture(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("owner", password="Owner-password-334!")
        self.other = get_user_model().objects.create_user("other", password="Other-password-334!")
        self.reviewer = get_user_model().objects.create_user(
            "reviewer", password="Review-password-334!", is_staff=True
        )
        self.org = m.Organization.objects.create(name="Synthetic NGO", capacity_cents=10000)
        self.ws = m.Workspace.objects.create(name="NGO", kind="ngo", organization=self.org)
        self.donor = m.Workspace.objects.create(name="Donor", kind="foundation")
        self.reviewws = m.Workspace.objects.create(name="Review", kind="foundation")
        m.Membership.objects.create(user=self.owner, workspace=self.ws, role="owner")
        m.Membership.objects.create(user=self.other, workspace=self.donor, role="administrator")
        m.Membership.objects.create(user=self.reviewer, workspace=self.reviewws, role="reviewer")
        self.source = self.source_for(self.ws)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.ws.id))

    def source_for(self, owner=None, **kwargs):
        return m.Source.objects.create(
            owner=owner,
            title="Aggregate evidence",
            kind="ngo_contributed" if owner else "synthetic_demo",
            retrieved_at=timezone.now(),
            parser_version="test-v1",
            checksum="a" * 64,
            **kwargs,
        )

    def grant(self, source=None, **kwargs):
        values = {
            "source": source or self.source,
            "purpose": "donor_access",
            "recipient": self.donor,
            "audience": "workspace",
            "cause": "food_security",
            "geography": "US-MD-Baltimore",
        }
        values.update(kwargs)
        return m.DataGrant.objects.create(**values)

    def artifact(self, source=None):
        return create_artifact(
            self.ws,
            self.owner,
            kind="test",
            title="Private finding",
            sources=[source or self.source],
        )


class PolicyTests(DomainFixture):
    def test_private_by_default_and_staff_no_bypass(self):
        self.assertFalse(can_source(self.source, self.donor))
        a = self.artifact()
        self.assertFalse(can_artifact(a, self.reviewws, user=self.reviewer))

    def test_complete_tuple_not_cross_grant_assembly(self):
        self.grant(cause="other")
        self.grant(geography="other")
        self.assertFalse(can_source(self.source, self.donor))
        self.grant()
        self.assertTrue(can_source(self.source, self.donor))

    def test_expired_unknown_external_ai_fail_closed(self):
        self.grant(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertFalse(can_source(self.source, self.donor))
        self.grant(purpose="external_ai", external_processing=False)
        self.assertFalse(can_source(self.source, self.donor, "external_ai"))
        self.assertFalse(can_source(self.source, self.donor, "anything"))

    def test_intersection_all_dependencies(self):
        second = self.source_for(self.ws)
        a = create_artifact(
            self.ws, self.owner, kind="test", title="Two inputs", sources=[self.source, second]
        )
        a.status = "approved"
        a.save()
        self.grant()
        self.assertFalse(can_artifact(a, self.donor))
        self.grant(source=second)
        self.assertTrue(can_artifact(a, self.donor))

    def test_changed_source_blocks_owner_and_other_reads(self):
        a = self.artifact()
        self.source.revision += 1
        self.source.save()
        self.assertFalse(can_artifact(a, self.ws))

    def test_forged_workspace_denied(self):
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        self.assertEqual(self.client.get("/api/v1/programs/").status_code, 404)

    def test_private_source_detail_and_lists_no_existence_leak(self):
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        self.assertEqual(self.client.get(f"/api/v1/sources/{self.source.id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/sources/").json()["meta"]["total"], 0)

    def test_withdraw_invalidates_and_deletes_via_worker(self):
        artifact = self.artifact()
        self.grant()
        artifact.status = "approved"
        artifact.save()
        m.Alert.objects.create(
            owner=self.donor,
            artifact=artifact,
            title="Alert",
            explanation="A source finding",
            fingerprint="one",
        )
        withdraw(self.source, self.owner)
        artifact.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(artifact.status, "invalidated")
        self.assertFalse(can_source(self.source, self.ws))
        self.assertFalse(can_artifact(artifact, self.donor))
        run_once()
        self.assertEqual(m.Withdrawal.objects.get(source=self.source).status, "completed")
        self.assertEqual(m.Alert.objects.get(fingerprint="one").explanation, "")

    def test_running_job_cannot_publish_after_withdrawal(self):
        batch = m.ImportBatch.objects.create(
            owner=self.ws,
            created_by=self.owner,
            source=self.source,
            filename="outcomes.csv",
            checksum="b" * 64,
            format="csv",
            raw=b"a,b",
        )
        enqueue(self.ws, "parse_import", "parse-one", {"batch_id": str(batch.id)}, self.source)
        job = claim_job()
        withdraw(self.source, self.owner)
        self.assertFalse(finish_job(job, {"status": "validated", "preview": [{"secret": 22}]}))
        batch.refresh_from_db()
        self.assertEqual(batch.preview, [])

    def test_stale_lease_cannot_commit(self):
        batch = m.ImportBatch.objects.create(
            owner=self.ws,
            created_by=self.owner,
            source=self.source,
            filename="data.csv",
            checksum="b" * 64,
            format="csv",
        )
        enqueue(self.ws, "parse_import", "lease", {"batch_id": str(batch.id)}, self.source)
        old = claim_job()
        m.Job.objects.filter(pk=old.pk).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        new = claim_job()
        self.assertNotEqual(old.lease_token, new.lease_token)
        self.assertFalse(finish_job(old, {"status": "validated"}))
        self.assertTrue(finish_job(new, {"status": "validated"}))

    def test_assignment_not_staff_authority_and_stale_review(self):
        a = self.artifact()
        with self.assertRaises(Exception):
            decide_review(a, self.reviewer, 1, "approved", "Looks consistent.")
        submit_review(a, self.owner, self.reviewer.id, 1)
        with self.assertRaises(Conflict):
            decide_review(a, self.reviewer, 2, "approved", "Looks consistent.")
        decided = decide_review(a, self.reviewer, 1, "approved", "Source and caveats reviewed.")
        self.assertEqual(decided.status, "approved")

    def test_no_self_review(self):
        a = self.artifact()
        with self.assertRaises(Exception):
            submit_review(a, self.owner, self.owner.id, 1)

    def test_withdraw_blocks_queued_review(self):
        a = self.artifact()
        submit_review(a, self.owner, self.reviewer.id, 1)
        withdraw(self.source, self.owner)
        with self.assertRaises(Conflict):
            decide_review(a, self.reviewer, 1, "approved", "Cannot approve stale input.")

    def test_readonly_cannot_create_source(self):
        m.Membership.objects.filter(user=self.owner, workspace=self.ws).update(role="viewer")
        self.assertEqual(
            self.client.post("/api/v1/sources/", {"title": "No"}, format="json").status_code, 403
        )


class SessionTests(DomainFixture):
    def test_anonymous_login_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            "/api/v1/login/",
            {"username": "owner", "password": "Owner-password-334!"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        token = client.get("/api/v1/session/").json()["data"]["csrfToken"]
        response = client.post(
            "/api/v1/login/",
            {"username": "owner", "password": "Owner-password-334!"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.post("/api/v1/logout/").status_code, 403)
        self.assertEqual(
            client.post(
                "/api/v1/logout/", HTTP_X_CSRFTOKEN=response.json()["data"]["csrfToken"]
            ).status_code,
            200,
        )

    def test_invitation_single_use_and_scope(self):
        response = self.client.post(
            "/api/v1/invitations/",
            {"email": "fictional@example.invalid", "role": "viewer"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        anonymous = APIClient()
        body = {
            "token": response.json()["data"]["token"],
            "username": "invited",
            "password": "An-invited-password-334!",
        }
        first = anonymous.post("/api/v1/invitations/redeem/", body, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(
            m.Membership.objects.get(user__username="invited").workspace_id, self.ws.id
        )
        self.assertEqual(
            anonymous.post("/api/v1/invitations/redeem/", body, format="json").status_code, 400
        )


class PortfolioTests(DomainFixture):
    def setUp(self):
        super().setUp()
        self.public = self.source_for()
        m.Filing.objects.create(
            organization=self.org,
            source=self.public,
            tax_year=2025,
            period_start="2025-01-01",
            period_end="2025-12-31",
            revenue=100,
            expenses=120,
            program_expenses=80,
            assets=100,
            liabilities=50,
        )

    def test_exact_cents_and_manual_budget_cap_guard(self):
        a = create_portfolio(
            self.donor,
            self.other,
            {
                "name": "Draft",
                "budget_cents": 10001,
                "candidates": [{"organization_id": str(self.org.id), "cap_cents": 10000}],
            },
        )
        self.assertEqual(a.portfolio.unallocated_cents, 1)
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        response = self.client.patch(
            f"/api/v1/portfolios/{a.id}/",
            {
                "revision": 1,
                "allocations": [{"organization_id": str(self.org.id), "amount_cents": 10001}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_capacity_needs_documented_assumption(self):
        self.org.capacity_cents = None
        self.org.save()
        with self.assertRaises(Exception):
            create_portfolio(
                self.donor,
                self.other,
                {
                    "name": "Draft",
                    "budget_cents": 100,
                    "candidates": [{"organization_id": str(self.org.id), "cap_cents": 100}],
                },
            )
        a = create_portfolio(
            self.donor,
            self.other,
            {
                "name": "Draft",
                "budget_cents": 100,
                "candidates": [
                    {
                        "organization_id": str(self.org.id),
                        "cap_cents": 100,
                        "assumption_note": "Donor-entered pilot limit pending confirmation.",
                    }
                ],
            },
        )
        self.assertEqual(a.portfolio.allocations.first().amount_cents, 100)

    def test_private_portfolio_export_denied(self):
        a = create_portfolio(
            self.donor,
            self.other,
            {
                "name": "Draft",
                "budget_cents": 100,
                "candidates": [{"organization_id": str(self.org.id), "cap_cents": 100}],
            },
        )
        self.assertEqual(self.client.get(f"/api/v1/reports/{a.id}/?format=csv").status_code, 404)

    def test_public_finance_detail_real_calculation(self):
        response = self.client.get(f"/api/v1/organizations/{self.org.id}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["financial_signals"]
        self.assertEqual(payload["status"], "available")
        self.assertTrue(payload["periods"])


class ImportAndPoolTests(DomainFixture):
    def outcome_row(self):
        return {
            "record_type": "outcome",
            "program_name": "Aggregate pilot",
            "cause": "food_security",
            "intervention": "food_access",
            "population": "households",
            "geography": "US-MD-Baltimore",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "outcome_code": "food-improvement",
            "outcome_definition": "Reported improved household food access",
            "unit": "binary",
            "direction": "higher_better",
            "numerator": 20,
            "denominator": 40,
            "cohort_id": "cohort-new",
            "study_id": "study-new",
            "independent": "true",
            "followup_months": 6,
            "study_design": "observational",
        }

    def test_real_csv_upload_worker_commit_and_duplicate(self):
        import json

        from django.core.files.uploadedfile import SimpleUploadedFile

        from philanthra.ingestion import safe_csv

        row = self.outcome_row()
        raw = safe_csv([row]).encode()
        response = self.client.post(
            "/api/v1/imports/",
            {
                "file": SimpleUploadedFile("sample.csv", raw),
                "mapping": json.dumps({key: key for key in row}),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 202)
        batch = m.ImportBatch.objects.get(pk=response.json()["data"]["id"])
        self.assertTrue(run_once())
        batch.refresh_from_db()
        self.assertEqual(batch.status, "validated")
        response = self.client.post(f"/api/v1/imports/{batch.id}/commit/", {}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertTrue(run_once())
        batch.refresh_from_db()
        self.assertEqual(batch.status, "completed")
        self.assertIsNone(batch.raw)
        self.assertEqual(m.Observation.objects.filter(source=batch.source).count(), 1)
        repeated = self.client.post(
            "/api/v1/imports/",
            {"file": SimpleUploadedFile("renamed.csv", raw), "mapping": "{}"},
            format="multipart",
        )
        self.assertEqual(repeated.json()["data"]["id"], str(batch.id))
        self.assertEqual(m.ImportBatch.objects.count(), 1)

    def test_sensitive_upload_never_commits(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            "/api/v1/imports/",
            {
                "file": SimpleUploadedFile("unsafe.csv", b"participant_name,numerator\nJane,10\n"),
                "mapping": '{"participant_name":"program_name","numerator":"numerator"}',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 202)
        run_once()
        batch = m.ImportBatch.objects.get(pk=response.json()["data"]["id"])
        self.assertEqual(batch.status, "invalid")
        self.assertEqual(
            self.client.post(f"/api/v1/imports/{batch.id}/commit/", {}, format="json").status_code,
            400,
        )
        self.assertFalse(m.Observation.objects.exists())

    def pool_fixture(self, numerator=20, denominator=40):
        outcome = m.OutcomeDefinition.objects.create(
            code="pool", name="Outcome", definition="Improved access"
        )
        rows = []
        for i in range(3):
            org = m.Organization.objects.create(name=f"Synthetic contributor {i}")
            ws = m.Workspace.objects.create(name=f"Contributor {i}", kind="ngo", organization=org)
            source = self.source_for(ws)
            self.grant(source=source, recipient=self.ws, purpose="pooled_analysis")
            self.grant(source=source, recipient=self.reviewws, purpose="pooled_analysis")
            p = m.Program.objects.create(
                owner=ws,
                organization=org,
                source=source,
                name="Food access",
                intervention="food_access",
                population="households",
                geography=source.geography,
            )
            rows.append(
                m.Observation.objects.create(
                    owner=ws,
                    program=p,
                    source=source,
                    outcome=outcome,
                    numerator=numerator,
                    denominator=denominator,
                    cohort_id=f"cohort-{i}",
                    study_id=f"study-{i}",
                    independent=True,
                    period_start="2025-01-01",
                    period_end="2025-12-31",
                )
            )
        return rows

    def test_fixed_release_calculates_and_arbitrary_subset_rejected(self):
        rows = self.pool_fixture()
        response = self.client.post(
            "/api/v1/analyses/",
            {"title": "Actual descriptive pattern", "observation_ids": [str(o.id) for o in rows]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["payload"]["weighted_rate"], "0.500000")
        subset = self.client.post(
            "/api/v1/analyses/", {"observation_ids": [str(rows[0].id)]}, format="json"
        )
        self.assertEqual(subset.status_code, 400)

    def test_suppression_has_no_rates_totals_or_source_ids(self):
        rows = self.pool_fixture(numerator=3, denominator=20)
        response = self.client.post(
            "/api/v1/analyses/", {"observation_ids": [str(o.id) for o in rows]}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()["data"]["payload"]
        self.assertEqual(payload["status"], "suppressed")
        self.assertNotIn("numerator", payload)
        self.assertNotIn("denominator", payload)
        self.assertEqual(payload["source_ids"], [])
        artifact = m.Artifact.objects.get(pk=response.json()["data"]["id"])
        submit_review(artifact, self.owner, self.reviewer.id, 1)
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            decide_review(artifact, self.reviewer, 1, "approved", "Suppressed data cannot release.")

    def test_cross_tenant_import_job_and_graph_absent(self):
        batch = m.ImportBatch.objects.create(
            owner=self.ws,
            created_by=self.owner,
            source=self.source,
            filename="private.csv",
            format="csv",
            checksum="c" * 64,
        )
        job = enqueue(
            self.ws, "parse_import", "private-job", {"batch_id": str(batch.id)}, self.source
        )
        a = self.artifact()
        m.GraphEdge.objects.create(
            artifact=a,
            source_type="program",
            source_id="private-id",
            target_type="evidence",
            target_id=str(a.id),
            relation="supports",
            supporting_source=self.source,
        )
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        self.assertEqual(self.client.get(f"/api/v1/imports/{batch.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{job.id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/graph/").json()["data"]["edges"], [])

    def test_publication_needs_separate_consent_and_binds_expiry(self):
        rows = self.pool_fixture()
        response = self.client.post(
            "/api/v1/analyses/", {"observation_ids": [str(o.id) for o in rows]}, format="json"
        )
        artifact = m.Artifact.objects.get(pk=response.json()["data"]["id"])
        submit_review(artifact, self.owner, self.reviewer.id, 1)
        from rest_framework.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            decide_review(
                artifact, self.reviewer, 1, "approved", "Needs separate publication permission."
            )
        grants = [
            self.grant(source=o.source, recipient=self.ws, purpose="publication") for o in rows
        ]
        artifact = decide_review(
            artifact,
            self.reviewer,
            1,
            "approved",
            "Reviewed fixed release and explicit publication scope.",
        )
        self.assertTrue(can_artifact(artifact, self.ws))
        grants[0].expires_at = timezone.now() - timedelta(seconds=1)
        grants[0].save()
        self.assertFalse(can_artifact(artifact, self.ws))

    def test_owner_contribution_does_not_bypass_publication(self):
        artifact = create_artifact(
            self.ws,
            self.owner,
            kind="analysis",
            title="Owner contribution",
            sources=[self.source],
            payload={"status": "draft"},
            purpose="pooled_analysis",
        )
        submit_review(artifact, self.owner, self.reviewer.id, 1)
        from rest_framework.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            decide_review(
                artifact, self.reviewer, 1, "approved", "Owner still must grant publication."
            )

    def test_quarantine_expires_and_cancels_pending_job(self):
        from philanthra.jobs.worker import expire_uploads

        batch = m.ImportBatch.objects.create(
            owner=self.ws,
            created_by=self.owner,
            source=self.source,
            filename="stale.csv",
            format="csv",
            checksum="d" * 64,
            raw=b"old private content",
            preview=[{"value": "old"}],
        )
        m.ImportBatch.objects.filter(pk=batch.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        job = enqueue(
            self.ws, "parse_import", "stale-file", {"batch_id": str(batch.id)}, self.source
        )
        expire_uploads()
        batch.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(batch.status, "expired")
        self.assertIsNone(batch.raw)
        self.assertEqual(batch.preview, [])
        self.assertEqual(job.state, "canceled")

    def test_outcome_horizon_filters_respect_permissions(self):
        rows = self.pool_fixture()
        source = rows[0].source
        self.grant(source=source, recipient=self.ws, purpose="donor_access")
        response = self.client.get(
            "/api/v1/organizations/?outcome_definition=pool&horizon_days=180"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["total"], 1)
        response = self.client.get("/api/v1/organizations/?outcome_definition=pool&horizon_days=90")
        self.assertEqual(response.json()["meta"]["total"], 0)
        response = self.client.get("/api/v1/organizations/?outcome_definition=missing")
        self.assertEqual(response.json()["meta"]["total"], 0)

    def test_unknown_job_retries_are_bounded(self):
        from philanthra.jobs.worker import fail_job

        job = enqueue(self.ws, "unknown", "unknown-kind")
        for attempt in range(3):
            m.Job.objects.filter(pk=job.id).update(
                available_at=timezone.now() - timedelta(seconds=1)
            )
            claimed = claim_job()
            self.assertIsNotNone(claimed)
            fail_job(claimed, "unsupported_job_kind")
        job.refresh_from_db()
        self.assertEqual(job.state, "failed")
        self.assertEqual(job.attempts, 3)

    def test_postgresql_fulltext_search_stems_and_scopes(self):
        self.org.mission = "Delivering nutritious meals through community kitchens."
        self.org.save()
        response = self.client.get("/api/v1/organizations/?q=deliver%20meal")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["total"], 1)
        self.assertEqual(self.client.get("/api/v1/cards/?q=secret").json()["meta"]["total"], 0)
