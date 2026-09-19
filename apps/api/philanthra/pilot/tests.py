from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from philanthra.core import models as c
from philanthra.core.services import (
    create_artifact,
    decide_review,
    enqueue,
    submit_review,
    withdraw,
)

from .models import Bookmark, ContactConsent, IdentityClaim, MonitorSnapshot
from .services import (
    add_watch,
    after_review,
    after_source_withdrawal,
    financial_benchmark,
    impact_report,
    run_monitor,
)


class PilotFixture(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            "pilot-owner", email="owner@example.invalid", password="A-strong-pilot-pass-998!"
        )
        self.other = get_user_model().objects.create_user(
            "pilot-other", email="other@example.invalid", password="A-strong-pilot-pass-998!"
        )
        self.reviewer = get_user_model().objects.create_user(
            "pilot-review", password="A-strong-review-pass-998!"
        )
        self.org = c.Organization.objects.create(
            name="Synthetic Test Organization", mission="Food access", capacity_cents=10000
        )
        self.ws = c.Workspace.objects.create(name="Pilot NGO", kind="ngo", organization=self.org)
        self.donor = c.Workspace.objects.create(name="Pilot Donor", kind="foundation")
        self.reviewws = c.Workspace.objects.create(name="Reviewer", kind="foundation")
        c.Membership.objects.create(user=self.owner, workspace=self.ws, role="owner")
        c.Membership.objects.create(user=self.other, workspace=self.donor, role="owner")
        c.Membership.objects.create(user=self.reviewer, workspace=self.reviewws, role="reviewer")
        self.source = self.make_source(self.ws)
        self.public = self.make_source(None)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.ws.id))

    def make_source(self, owner):
        return c.Source.objects.create(
            owner=owner,
            title="Private aggregate source" if owner else "Synthetic public filing",
            kind="ngo_contributed" if owner else "synthetic_demo",
            retrieved_at=timezone.now(),
            parser_version="test-v1",
            checksum="a" * 64,
            locator="row:2",
        )

    def filing(self, org=None, year=2025, source=None, **kwargs):
        values = {
            "organization": org or self.org,
            "source": source or self.public,
            "tax_year": year,
            "period_start": date(year, 1, 1),
            "period_end": date(year, 12, 31),
            "revenue": 100000,
            "expenses": 90000,
            "program_expenses": 72000,
            "assets": 100000,
            "liabilities": 20000,
        }
        values.update(kwargs)
        return c.Filing.objects.create(**values)

    def program(self):
        return c.Program.objects.create(
            owner=self.ws,
            organization=self.org,
            source=self.source,
            name="Food access pilot",
            intervention="food_access",
            population="households",
            geography=self.source.geography,
        )

    def card(self):
        a = create_artifact(
            self.ws, self.owner, kind="card", title="Food access evidence", sources=[self.source]
        )
        c.Card.objects.create(artifact=a, program=self.program())
        return a


class IdentityTests(PilotFixture):
    def test_workspace_creation_does_not_assign_existing_identity(self):
        response = self.client.post(
            "/api/v1/pilot/workspaces/",
            {"name": "New workspace", "kind": "ngo", "organization_id": str(self.org.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/v1/pilot/workspaces/", {"name": "New workspace", "kind": "ngo"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["data"]["organization_id"])
        self.assertTrue(
            c.Membership.objects.filter(
                user=self.owner, workspace_id=response.json()["data"]["id"], role="owner"
            ).exists()
        )

    def claim(self):
        self.ws.organization = None
        self.ws.save()
        response = self.client.post(
            "/api/v1/pilot/identity-claims/",
            {
                "organization_id": str(self.org.id),
                "proof_source_id": str(self.source.id),
                "statement": "The attached source identifies our authorized organizational representative.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return IdentityClaim.objects.get(pk=response.json()["data"]["id"])

    def test_identity_approval_is_independent_revision_bound_and_revocable(self):
        claim = self.claim()
        self.ws.refresh_from_db()
        self.assertIsNone(self.ws.organization_id)
        with self.assertRaises(Exception):
            after_review(claim.artifact, self.owner, "approved")
        submit_review(claim.artifact, self.owner, self.reviewer.id, 1)
        approved = decide_review(
            claim.artifact,
            self.reviewer,
            1,
            "approved",
            "Reviewed the authority evidence and organizational identity.",
        )
        after_review(approved, self.reviewer, "approved")
        self.ws.refresh_from_db()
        self.assertEqual(self.ws.organization_id, self.org.id)
        withdraw(self.source, self.owner)
        after_source_withdrawal(self.source)
        self.ws.refresh_from_db()
        claim.refresh_from_db()
        self.assertIsNone(self.ws.organization_id)
        self.assertEqual(claim.statement, "Withdrawn identity proof")

    def test_cannot_claim_other_tenant_proof(self):
        self.ws.organization = None
        self.ws.save()
        other_source = self.make_source(self.donor)
        response = self.client.post(
            "/api/v1/pilot/identity-claims/",
            {
                "organization_id": str(self.org.id),
                "proof_source_id": str(other_source.id),
                "statement": "This is someone else private source and must be denied.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_identity_proof_requires_owner_or_assigned_reviewer(self):
        claim = self.claim()
        endpoint = f"/api/v1/pilot/identity-claims/{claim.artifact_id}/proof/"
        self.assertEqual(self.client.get(endpoint).status_code, 200)
        self.client.force_authenticate(self.reviewer)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.reviewws.id))
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        submit_review(claim.artifact, self.owner, self.reviewer.id, 1)
        self.assertEqual(self.client.get(endpoint).status_code, 200)
        self.assertTrue(
            c.AuditEvent.objects.filter(
                action="identity.proof_viewed", actor=self.reviewer
            ).exists()
        )

    def test_existing_identity_cannot_be_taken_over(self):
        claim = self.claim()
        c.Workspace.objects.create(name="Already verified", kind="ngo", organization=self.org)
        submit_review(claim.artifact, self.owner, self.reviewer.id, 1)
        from philanthra.core.services import Conflict

        with self.assertRaises(Conflict):
            approved = decide_review(
                claim.artifact,
                self.reviewer,
                1,
                "approved",
                "Verified but cannot transfer an assigned identity.",
            )
            after_review(approved, self.reviewer, "approved")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ResetTests(PilotFixture):
    def test_anonymous_reset_requires_csrf_and_does_not_enumerate(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            "/api/v1/pilot/password-reset/request/", {"email": self.owner.email}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        csrf = client.get("/api/v1/session/").json()["data"]["csrfToken"]
        known = client.post(
            "/api/v1/pilot/password-reset/request/",
            {"email": self.owner.email},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        unknown = client.post(
            "/api/v1/pilot/password-reset/request/",
            {"email": "unknown@example.invalid"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(known.status_code, 202)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("token", known.json()["data"])

    def test_reset_token_single_use_and_old_password_invalidated(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        token = default_token_generator.make_token(self.owner)
        body = {
            "uid": urlsafe_base64_encode(force_bytes(self.owner.pk)),
            "token": token,
            "password": "New-password-secure-441!",
        }
        client = APIClient()
        response = client.post("/api/v1/pilot/password-reset/confirm/", body, format="json")
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(body["password"]))
        self.assertEqual(
            client.post("/api/v1/pilot/password-reset/confirm/", body, format="json").status_code,
            400,
        )

    @override_settings(ENVIRONMENT="production")
    def test_production_reset_fails_honestly_without_configured_delivery(self):
        with patch.dict("os.environ", {"PHILANTHRA_PASSWORD_RESET_EMAIL_ENABLED": "0"}):
            response = APIClient().post(
                "/api/v1/pilot/password-reset/request/", {"email": self.owner.email}, format="json"
            )
        self.assertEqual(response.status_code, 503)


class MonitorTests(PilotFixture):
    def test_watch_baseline_no_fake_alert_then_actual_filing_change(self):
        filing = self.filing()
        watch = add_watch(self.donor, self.other, self.org)
        job = enqueue(self.donor, "pilot_monitor", "test-monitor")
        run_monitor(job)
        self.assertFalse(c.Alert.objects.exists())
        filing.active = False
        filing.save()
        self.filing(revision=2, amended=True, revenue=70000)
        run_monitor(job)
        self.assertEqual(c.Alert.objects.count(), 1)
        alert = c.Alert.objects.get()
        self.assertIn("active filing revision", alert.explanation)
        run_monitor(job)
        self.assertEqual(c.Alert.objects.count(), 1)
        self.assertTrue(MonitorSnapshot.objects.filter(watch=watch).exists())

    def test_withdrawn_private_evidence_not_copied_into_new_alert(self):
        self.filing()
        artifact = self.card()
        artifact.status = "approved"
        artifact.save()
        c.DataGrant.objects.create(
            source=self.source,
            purpose="donor_access",
            recipient=self.donor,
            audience="workspace",
            cause=self.source.cause,
            geography=self.source.geography,
        )
        watch = add_watch(self.donor, self.other, self.org)
        self.assertTrue(watch.snapshot.state["evidence"])
        withdraw(self.source, self.owner)
        job = enqueue(self.donor, "pilot_monitor", "withdraw-monitor")
        run_monitor(job)
        alert = c.Alert.objects.get(owner=self.donor)
        self.assertIn("currently accessible approved evidence", alert.explanation)
        self.assertNotIn(str(self.source.id), str(alert.artifact.payload))
        self.assertFalse(alert.artifact.sources.filter(pk=self.source.id).exists())

    def test_watchlist_cross_tenant_isolation_and_subscription(self):
        self.filing()
        watch = add_watch(self.donor, self.other, self.org)
        self.assertEqual(self.client.get("/api/v1/pilot/watchlist/").json()["data"], [])
        self.assertEqual(
            self.client.delete(f"/api/v1/pilot/watchlist/{watch.id}/").status_code, 404
        )
        c.Subscription.objects.create(
            owner=self.donor, financial=False, evidence=False, stale=False
        )
        self.public.revision += 1
        self.public.save()
        run_monitor(enqueue(self.donor, "pilot_monitor", "off-monitor"))
        self.assertFalse(c.Alert.objects.exists())

    def test_bookmark_reauthorizes_after_withdrawal(self):
        artifact = self.card()
        response = self.client.post(
            "/api/v1/pilot/bookmarks/", {"artifact_id": str(artifact.id)}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.client.get("/api/v1/pilot/bookmarks/").json()["data"]), 1)
        withdraw(self.source, self.owner)
        self.assertEqual(self.client.get("/api/v1/pilot/bookmarks/").json()["data"], [])
        self.assertTrue(Bookmark.objects.exists())


class ContributorTests(PilotFixture):
    def test_impact_report_contains_real_aggregates_costs_and_provenance(self):
        program = self.program()
        outcome = c.OutcomeDefinition.objects.create(
            code="test", name="Food access", definition="Reported food access"
        )
        c.Observation.objects.create(
            owner=self.ws,
            program=program,
            source=self.source,
            outcome=outcome,
            numerator=20,
            denominator=40,
            cohort_id="one",
            study_id="one",
            independent=True,
            period_start="2025-01-01",
            period_end="2025-12-31",
        )
        c.CostObservation.objects.create(
            owner=self.ws,
            program=program,
            source=self.source,
            amount="123.45",
            currency="USD",
            unit="program",
            period_start="2025-01-01",
            period_end="2025-12-31",
        )
        report = impact_report(self.ws)
        self.assertEqual(report["observations"][0]["numerator"], 20)
        self.assertEqual(report["costs"][0]["amount"], "123.45")
        self.assertEqual(report["status"], "draft")
        self.assertEqual(report["sources"][0]["id"], str(self.source.id))
        response = self.client.get("/api/v1/pilot/impact-report/?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"123.45", response.content)
        self.assertEqual(impact_report(self.donor)["observations"], [])

    def test_benchmark_requires_compatible_four_organization_context(self):
        geo = c.Geography.objects.create(
            code="test-area", name="Reported service context", source=self.public
        )
        for index in range(4):
            org = (
                self.org
                if index == 0
                else c.Organization.objects.create(name=f"Synthetic peer {index}")
            )
            self.filing(org=org, program_expenses=72000 - index * 9000)
            c.ServiceArea.objects.create(organization=org, geography=geo, source=self.public)
        report = financial_benchmark(self.ws)
        self.assertEqual(report["status"], "available")
        self.assertEqual(report["peer_organization_count"], 3)
        self.assertEqual(report["median"], "0.600000")

    def test_profile_revision_and_area_validation(self):
        response = self.client.get("/api/v1/pilot/profile/")
        revision = response.json()["data"]["revision"]
        response = self.client.patch(
            "/api/v1/pilot/profile/",
            {
                "revision": revision,
                "mission": "Owner-reported mission",
                "service_area_codes": ["invented-zcta"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            "/api/v1/pilot/profile/",
            {"revision": revision, "mission": "Owner-reported mission"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.patch(
                "/api/v1/pilot/profile/", {"revision": revision, "mission": "Stale"}, format="json"
            ).status_code,
            409,
        )
        self.org.refresh_from_db()
        self.assertEqual(self.org.mission, "Food access")

    def test_contact_requires_accepted_request_and_current_consent(self):
        request = c.ServiceRequest.objects.create(
            owner=self.donor,
            target=self.ws,
            kind="introduction",
            note="Request a manual introduction.",
        )
        ContactConsent.objects.create(
            owner=self.ws, name="Fictional contact", email="contact@example.invalid", enabled=True
        )
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        endpoint = f"/api/v1/pilot/introductions/{request.id}/contact/"
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        request.state = "accepted"
        request.save()
        self.assertEqual(self.client.get(endpoint).status_code, 200)
        ContactConsent.objects.filter(owner=self.ws).update(enabled=False)
        self.assertEqual(self.client.get(endpoint).status_code, 404)


class WorkerIntegrationTests(PilotFixture):
    def test_monitor_runs_through_real_leased_worker(self):
        from philanthra.jobs.worker import run_once

        self.filing()
        add_watch(self.donor, self.other, self.org)
        self.public.revision += 1
        self.public.save()
        job = enqueue(self.donor, "pilot_monitor", "real-worker-monitor")
        self.assertTrue(run_once())
        job.refresh_from_db()
        self.assertEqual(job.state, "completed")
        self.assertEqual(c.Alert.objects.filter(owner=self.donor).count(), 1)

    def test_stale_source_change_creates_freshness_alert(self):
        from philanthra.pilot.services import today

        self.filing()
        add_watch(self.donor, self.other, self.org)
        self.public.retrieved_at = timezone.make_aware(
            timezone.datetime.combine(today() - timedelta(days=366), timezone.datetime.min.time())
        )
        self.public.save()
        run_monitor(enqueue(self.donor, "pilot_monitor", "freshness-change"))
        self.assertIn("source freshness", c.Alert.objects.get().explanation)
