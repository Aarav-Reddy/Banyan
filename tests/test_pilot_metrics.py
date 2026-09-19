from datetime import UTC, datetime
from unittest.mock import patch

from django.test import override_settings
from philanthra.core import models as m
from philanthra.core.tests import DomainFixture


class MetricsTests(DomainFixture):
    def event_payload(self, **overrides):
        return {
            "metric": "alert_usefulness",
            "value": "2",
            "denominator": "3",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "collection_method": "=Private user-entered note",
            **overrides,
        }

    @override_settings(DEMO_MODE=True)
    def test_opt_in_scoped_safe_csv_and_demo_label(self):
        self.assertEqual(
            self.client.post("/api/v1/metrics/", self.event_payload(), format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.patch("/api/v1/metrics/", {"opted_in": True}, format="json").status_code,
            200,
        )
        response = self.client.post("/api/v1/metrics/", self.event_payload(), format="json")
        self.assertEqual(response.status_code, 201)
        csv = self.client.get("/api/v1/metrics/?format=csv")
        self.assertEqual(csv.status_code, 200)
        self.assertIn(b"synthetic_demo", csv.content)
        self.assertIn(b"not traction", csv.content)
        self.assertIn(b"'=Private", csv.content)
        self.assertIn(b"Alerts rated useful / alerts rated", csv.content)
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        other = self.client.get("/api/v1/metrics/?format=csv")
        self.assertEqual(other.status_code, 200)
        self.assertNotIn(b"Private", other.content)
        self.assertEqual(m.PilotEvent.objects.count(), 1)

    def test_bad_denominators_and_periods_do_not_persist(self):
        self.ws.metrics_opt_in = True
        self.ws.save()
        for overrides in [
            {"denominator": "0"},
            {"denominator": "1"},
            {"value": "-1"},
            {"period_end": "2025-01-01"},
        ]:
            result = self.client.post(
                "/api/v1/metrics/", self.event_payload(**overrides), format="json"
            )
            self.assertEqual(result.status_code, 400)
        self.assertFalse(m.PilotEvent.objects.exists())

    def test_signed_outcome_change_can_leave_inapplicable_denominator_unknown(self):
        self.ws.metrics_opt_in = True
        self.ws.save()
        result = self.client.post(
            "/api/v1/metrics/",
            self.event_payload(metric="outcome_change", value="-2.5", denominator=None),
            format="json",
        )
        self.assertEqual(result.status_code, 201)
        self.assertIsNone(m.PilotEvent.objects.get().denominator)

    def test_periodic_monitor_is_idempotent_per_workspace_hour(self):
        from philanthra.core.management.commands.worker import enqueue_periodic_monitoring
        from philanthra.pilot.models import WatchItem

        WatchItem.objects.create(owner=self.ws, organization=self.org, source=self.source)
        with patch("django.utils.timezone.now", return_value=datetime(2026, 9, 1, 1, tzinfo=UTC)):
            enqueue_periodic_monitoring()
            enqueue_periodic_monitoring()
        self.assertEqual(m.Job.objects.filter(kind="pilot_monitor").count(), 1)
        with patch("django.utils.timezone.now", return_value=datetime(2026, 9, 1, 2, tzinfo=UTC)):
            enqueue_periodic_monitoring()
        self.assertEqual(m.Job.objects.filter(kind="pilot_monitor").count(), 2)
