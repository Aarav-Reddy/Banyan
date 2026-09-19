import os
import subprocess
import sys

from philanthra.core import models as m
from philanthra.core.services import decide_review, submit_review
from philanthra.core.tests import DomainFixture
from rest_framework.exceptions import PermissionDenied


class HardeningTests(DomainFixture):
    def test_successful_request_logs_correlation_without_private_query(self):
        import logging

        from config.logging import MetadataFormatter

        self.assertTrue(logging.getLogger("philanthra.requests").isEnabledFor(logging.INFO))
        with self.assertLogs("philanthra.requests", level="INFO") as captured:
            response = self.client.get("/api/health/?private=secret-beneficiary")
        self.assertEqual(response.status_code, 200)
        rendered = MetadataFormatter().format(captured.records[-1])
        self.assertIn(response["X-Request-ID"], rendered)
        self.assertNotIn("secret-beneficiary", rendered)
        self.assertIn("request_completed", rendered)

    def test_workspace_admin_cannot_mint_trusted_reviewer(self):
        response = self.client.post(
            "/api/v1/invitations/",
            {"email": "review@example.invalid", "role": "reviewer"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(m.Invitation.objects.exists())

    def test_contributor_with_separate_reviewer_role_cannot_review_own_revision(self):
        a = self.artifact()
        m.Membership.objects.create(workspace=self.ws, user=self.reviewer, role="editor")
        with self.assertRaises(PermissionDenied):
            submit_review(a, self.owner, self.reviewer.id, 1)
        m.Membership.objects.filter(workspace=self.ws, user=self.reviewer).delete()
        submit_review(a, self.owner, self.reviewer.id, 1)
        m.Membership.objects.create(workspace=self.ws, user=self.reviewer, role="analyst")
        with self.assertRaises(PermissionDenied):
            decide_review(
                a, self.reviewer, 1, "approved", "A contributor cannot independently approve."
            )

    def test_required_attribution_survives_recipient_csv_export(self):
        a = self.artifact()
        self.grant(attribution="Required source attribution alpha")
        submit_review(a, self.owner, self.reviewer.id, 1)
        decide_review(a, self.reviewer, 1, "approved", "Review source scope.")
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        response = self.client.get(f"/api/v1/reports/{a.id}/?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Required source attribution alpha", response.content)

    def test_source_issue_review_and_opportunity_are_backed_by_sources(self):
        response = self.client.post(
            "/api/v1/source-issues/",
            {
                "source_id": str(self.source.id),
                "title": "Check measurement period",
                "issue": "The report does not state a denominator.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        a = m.Artifact.objects.get(pk=response.json()["data"]["id"])
        self.assertEqual(a.kind, "source_issue")
        submit_review(a, self.owner, self.reviewer.id, 1)
        decide_review(
            a,
            self.reviewer,
            1,
            "changes_requested",
            "Obtain denominator; no reliability claim approved.",
        )
        src = self.source_for()
        m.Opportunity.objects.create(
            title="Fictional opportunity",
            cause="food_security",
            geography="US-MD-Baltimore",
            eligibility="Confirm eligibility",
            deadline="2027-01-01",
            source=src,
        )
        result = self.client.get("/api/v1/opportunities/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["data"][0]["source"]["id"], str(src.id))


def test_production_refuses_missing_explicit_hosts():
    environment = {
        **os.environ,
        "PYTHONPATH": "apps/api",
        "PHILANTHRA_ENV": "production",
        "SECRET_KEY": "S" * 60,
        "DATABASE_URL": "postgresql://prod:longpassword@database/production",
        "CSRF_TRUSTED_ORIGINS": "https://pilot.example.invalid",
        "STORAGE_ENCRYPTION_ACK": "configured",
        "DEBUG": "0",
    }
    environment.pop("ALLOWED_HOSTS", None)
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "explicit deployment hostnames" in result.stderr


def test_structured_logs_drop_private_prompts_messages_and_exception_text():
    import logging

    from config.logging import MetadataFormatter

    record = logging.LogRecord(
        "django.request",
        logging.ERROR,
        "private-path",
        1,
        "private row: %s",
        ("secret beneficiary",),
        (ValueError, ValueError("private prompt"), None),
    )
    record.request_id = "safe-request-id"
    rendered = MetadataFormatter().format(record)
    assert "safe-request-id" in rendered
    assert "secret" not in rendered and "private" not in rendered and "beneficiary" not in rendered


def test_real_validation_command_reports_unavailable_without_labels():
    result = subprocess.run(
        [sys.executable, "-m", "philanthra.analytics.evaluate"],
        env={**os.environ, "PYTHONPATH": "apps/api"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert (
        '"status": "not_validated"' in result.stdout and '"model_enabled": false' in result.stdout
    )


class ProductionDatabaseTests(DomainFixture):
    def test_production_process_refuses_a_copied_demo_database(self):
        from config.deployment import validate_production_database
        from django.core.exceptions import ImproperlyConfigured
        from django.test import override_settings

        m.AuditEvent.objects.create(
            owner=self.ws, actor=self.owner, action="demo.seed", object_id="fixture"
        )
        with override_settings(ENVIRONMENT="production"):
            with self.assertRaisesMessage(ImproperlyConfigured, "seeded demo"):
                validate_production_database()
