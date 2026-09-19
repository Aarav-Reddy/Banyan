from django.db import models

from philanthra.core.models import Artifact, Organization, Record, Source, Workspace


class IdentityClaim(Record):
    artifact = models.OneToOneField(
        Artifact, on_delete=models.CASCADE, related_name="identity_claim"
    )
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    proof_source = models.ForeignKey(Source, on_delete=models.PROTECT)
    statement = models.TextField()
    linked_revision = models.PositiveIntegerField(null=True)


class Bookmark(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "artifact"], name="pilot_unique_bookmark")
        ]


class WatchItem(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    source = models.OneToOneField(Source, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "organization"], name="pilot_unique_watch")
        ]


class MonitorSnapshot(Record):
    watch = models.OneToOneField(WatchItem, on_delete=models.CASCADE, related_name="snapshot")
    fingerprint = models.CharField(max_length=64)
    state = models.JSONField(default=dict)


class WorkspaceProfile(Record):
    owner = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name="profile")
    mission = models.TextField(blank=True)
    cause = models.CharField(max_length=80, default="food_security")
    population = models.CharField(max_length=160, blank=True)
    service_area_codes = models.JSONField(default=list, blank=True)
    context = models.JSONField(default=dict, blank=True)
    revision = models.PositiveIntegerField(default=1)


class ContactConsent(Record):
    owner = models.OneToOneField(Workspace, on_delete=models.CASCADE)
    email = models.EmailField()
    name = models.CharField(max_length=160)
    enabled = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
