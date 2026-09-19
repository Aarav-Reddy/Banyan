"""Targeted card events retain consent checks without scanning unrelated cards."""

from django.db import connection
from django.test.utils import CaptureQueriesContext
from philanthra.core import models as m
from philanthra.core.policy import can_artifact
from philanthra.core.services import create_artifact, enqueue
from philanthra.core.tests import DomainFixture
from philanthra.jobs.worker import claim_job, finish_job


class TargetedRecommendationTests(DomainFixture):
    def setUp(self):
        super().setUp()
        self.donor.kind = "ngo"
        self.donor.save(update_fields=["kind"])
        self.denied = m.Workspace.objects.create(name="Unconsented NGO", kind="ngo")
        self.recipient_program = self.program(self.donor, self.source_for(self.donor))
        self.program(self.denied, self.source_for(self.denied))
        self.publisher_program = self.program(self.ws, self.source)
        self.public_source = self.source_for()
        self.public_program = self.program(self.ws, self.public_source)
        self.private_source = self.source_for(self.ws)
        self.private_program = self.program(self.ws, self.private_source)
        self.target = self.card(self.source, self.publisher_program, "Target evidence")
        self.unrelated = self.card(self.public_source, self.public_program, "Unrelated evidence")
        self.private = self.card(self.private_source, self.private_program, "Private evidence")
        self.grant(source=self.source, recipient=self.donor, purpose="benchmarking")
        self.sequence = 0

    def program(self, workspace, source):
        return m.Program.objects.create(
            owner=workspace,
            organization=self.org,
            source=source,
            name=f"Food program for {workspace.name}",
            intervention="food parcels",
            population="households",
            cause=source.cause,
            geography=source.geography,
        )

    def card(self, source, program, title):
        artifact = create_artifact(self.ws, self.owner, kind="card", title=title, sources=[source])
        m.Card.objects.create(artifact=artifact, program=program)
        # Isolate post-approval event handling; review authorization is tested separately.
        artifact.status = "approved"
        artifact.save(update_fields=["status"])
        return artifact

    def claimed_event(self, artifact):
        self.sequence += 1
        expected = enqueue(
            self.ws,
            "recommendations",
            f"targeted-card-{self.sequence}",
            {"artifact_id": str(artifact.id)},
            artifact.dependencies.get().source,
        )
        claimed = claim_job()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.id, expected.id)
        return claimed

    def test_targeted_event_only_notifies_authorized_recipient_about_target_card(self):
        self.assertTrue(can_artifact(self.target, self.donor))
        self.assertFalse(can_artifact(self.target, self.denied))
        self.assertTrue(can_artifact(self.unrelated, self.donor))
        self.assertFalse(can_artifact(self.private, self.donor))

        self.assertTrue(finish_job(self.claimed_event(self.target)))
        alert = m.Alert.objects.get()
        self.assertEqual(alert.owner_id, self.donor.id)
        self.assertEqual(alert.artifact_id, self.target.id)
        self.assertEqual(alert.target_program_id, self.recipient_program.id)
        self.assertEqual(alert.target_source_id, self.recipient_program.source_id)
        self.assertEqual(alert.target_source_revision, self.recipient_program.source.revision)

        # A new job for the same source revision must not duplicate the alert.
        self.assertTrue(finish_job(self.claimed_event(self.target)))
        self.assertEqual(m.Alert.objects.count(), 1)
        # A private card event must not become a grant merely because it is approved.
        self.assertTrue(finish_job(self.claimed_event(self.private)))
        self.assertEqual(m.Alert.objects.count(), 1)

    def test_donor_visibility_without_benchmarking_consent_cannot_generate_alert(self):
        m.DataGrant.objects.filter(source=self.source).update(purpose="donor_access")
        self.assertTrue(can_artifact(self.target, self.donor))
        self.assertTrue(finish_job(self.claimed_event(self.target)))
        self.assertFalse(m.Alert.objects.exists())

    def test_targeted_event_query_count_does_not_grow_with_unrelated_cards(self):
        first = self.claimed_event(self.target)
        with CaptureQueriesContext(connection) as baseline:
            self.assertTrue(finish_job(first))
        self.assertEqual(m.Alert.objects.get().artifact_id, self.target.id)
        m.Alert.objects.all().delete()

        # Keep recipients and programs fixed: only the irrelevant card corpus grows.
        for index in range(24):
            source, program = (
                (self.public_source, self.public_program)
                if index % 2
                else (self.private_source, self.private_program)
            )
            self.card(source, program, f"Unrelated corpus card {index}")

        second = self.claimed_event(self.target)
        with CaptureQueriesContext(connection) as expanded:
            self.assertTrue(finish_job(second))
        alert = m.Alert.objects.get()
        self.assertEqual((alert.owner_id, alert.artifact_id), (self.donor.id, self.target.id))
        self.assertLessEqual(
            len(expanded),
            len(baseline) + 2,
            "A targeted event must not perform per-card authorization queries for unrelated cards",
        )
