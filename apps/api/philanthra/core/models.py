"""Normalized pilot records. JSON fields contain explicit versioned snapshots/context."""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(Record):
    name = models.CharField(max_length=200)
    mission = models.TextField(blank=True)
    source_kind = models.CharField(max_length=24, default="synthetic_demo")
    country = models.CharField(max_length=2, default="US")
    headquarters_zip = models.CharField(max_length=12, blank=True)
    cause = models.CharField(max_length=80, default="food_security")
    population = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=80, default="unverified")
    capacity_cents = models.BigIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    capacity_note = models.TextField(blank=True)


class ExternalIdentifier(Record):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="identifiers"
    )
    namespace = models.CharField(max_length=40)
    value = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "value"], name="unique_external_identifier"
            )
        ]


class Workspace(Record):
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=[("foundation", "Foundation"), ("ngo", "NGO")])
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    plan = models.CharField(max_length=30, default="contributor_free")
    metrics_opt_in = models.BooleanField(default=False)


class Membership(Record):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(
        max_length=30,
        choices=[
            (r, r) for r in ["owner", "administrator", "analyst", "editor", "viewer", "reviewer"]
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace", "user"], name="one_workspace_membership")
        ]


class Invitation(Record):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=30)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    redeemed_at = models.DateTimeField(null=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class Source(Record):
    owner = models.ForeignKey(
        Workspace, null=True, blank=True, on_delete=models.PROTECT, related_name="sources"
    )
    title = models.CharField(max_length=240)
    kind = models.CharField(
        max_length=24,
        choices=[(s, s) for s in ["public_source", "ngo_contributed", "synthetic_demo"]],
    )
    source_url = models.URLField(blank=True)
    upload_identifier = models.CharField(max_length=160, blank=True)
    retrieved_at = models.DateTimeField()
    published_at = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    parser_version = models.CharField(max_length=80)
    checksum = models.CharField(max_length=64)
    locator = models.CharField(max_length=240, blank=True)
    transformations = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=20, default="active")
    cause = models.CharField(max_length=80, default="food_security")
    geography = models.CharField(max_length=80, default="US-MD-Baltimore")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(owner__isnull=False) | Q(kind__in=["public_source", "synthetic_demo"]),
                name="private_source_has_owner",
            )
        ]


class DataGrant(Record):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="grants")
    purpose = models.CharField(max_length=30)
    recipient = models.ForeignKey(Workspace, null=True, blank=True, on_delete=models.CASCADE)
    audience = models.CharField(max_length=20, default="workspace")
    cause = models.CharField(max_length=80)
    geography = models.CharField(max_length=80)
    expires_at = models.DateTimeField(null=True, blank=True)
    attribution = models.CharField(max_length=240, blank=True)
    external_processing = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)


class Geography(Record):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=30, default="reported_service_area")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    context = models.JSONField(default=dict)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="geographies")


class ServiceArea(Record):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="service_areas"
    )
    geography = models.ForeignKey(Geography, on_delete=models.PROTECT)
    basis = models.CharField(max_length=30, default="reported")
    source = models.ForeignKey(Source, on_delete=models.PROTECT)


class Filing(Record):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="filings")
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    form = models.CharField(max_length=10, default="990")
    tax_year = models.PositiveIntegerField()
    period_start = models.DateField()
    period_end = models.DateField()
    revision = models.PositiveIntegerField(default=1)
    amended = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default="USD")
    revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    program_expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    assets = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    liabilities = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    cash = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    caveats = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "tax_year", "form", "revision"],
                name="unique_filing_revision",
            )
        ]


class FundingRecord(Record):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    funder = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="funding_provided"
    )
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    amount_cents = models.BigIntegerField(validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="USD")
    date = models.DateField()
    type = models.CharField(max_length=20, default="commitment")


class Program(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="programs"
    )
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    cause = models.CharField(max_length=80, default="food_security")
    intervention = models.CharField(max_length=160)
    population = models.CharField(max_length=160)
    geography = models.CharField(max_length=80)
    context = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)


class OutcomeDefinition(Record):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    definition = models.TextField()
    unit = models.CharField(max_length=40, default="binary")
    direction = models.CharField(max_length=20, default="higher_better")


class Observation(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="observations")
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    outcome = models.ForeignKey(OutcomeDefinition, on_delete=models.PROTECT)
    numerator = models.PositiveIntegerField(null=True)
    denominator = models.PositiveIntegerField(null=True)
    cohort_id = models.CharField(max_length=100)
    study_id = models.CharField(max_length=100)
    independent = models.BooleanField(default=False)
    period_start = models.DateField()
    period_end = models.DateField()
    followup_months = models.PositiveIntegerField(default=6)
    comparator = models.CharField(max_length=160, default="none")
    study_design = models.CharField(max_length=80, default="observational")
    uncertainty = models.CharField(max_length=240, blank=True)
    missingness = models.CharField(max_length=240, blank=True)
    stratum = models.CharField(max_length=100, blank=True)
    locator = models.CharField(max_length=160, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(denominator__isnull=True)
                | Q(numerator__isnull=True)
                | Q(numerator__lte=models.F("denominator")),
                name="valid_binary_numerator",
            ),
            models.UniqueConstraint(
                fields=["source", "cohort_id", "outcome"], name="unique_source_cohort_outcome"
            ),
        ]


class CostObservation(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3)
    denominator = models.PositiveIntegerField(null=True)
    unit = models.CharField(max_length=80)
    period_start = models.DateField()
    period_end = models.DateField()


class Artifact(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="artifacts")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=240)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, default="draft")
    purpose = models.CharField(max_length=30, default="donor_access")
    cause = models.CharField(max_length=80, default="food_security")
    geography = models.CharField(max_length=80, default="US-MD-Baltimore")
    payload = models.JSONField(default=dict)
    method_version = models.CharField(max_length=80, default="pilot-v1")
    policy_version = models.CharField(max_length=80, default="consent-v1")
    source_kind = models.CharField(max_length=24, default="ngo_contributed")
    sources = models.ManyToManyField(Source, through="Dependency")


class Dependency(Record):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name="dependencies")
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    source_revision = models.PositiveIntegerField()
    grant = models.ForeignKey(DataGrant, on_delete=models.PROTECT, null=True)
    grant_revision = models.PositiveIntegerField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["artifact", "source"], name="unique_artifact_dependency"
            )
        ]


class Card(Record):
    artifact = models.OneToOneField(Artifact, on_delete=models.CASCADE, related_name="card")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="cards")
    evidence_label = models.CharField(max_length=80, default="descriptive observation")
    study_design = models.CharField(max_length=80, default="observational")
    implementation_steps = models.TextField(blank=True)
    barriers = models.TextField(blank=True)
    failures = models.TextField(blank=True)
    caveats = models.TextField(blank=True)
    attribution = models.CharField(max_length=240, blank=True)


class Claim(Record):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name="claims")
    text = models.TextField()
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    locator = models.CharField(max_length=240)
    label = models.CharField(max_length=80)


class ReviewAssignment(Record):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name="assignments")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="review_assignments_made"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["artifact", "reviewer", "revision"], name="one_revision_assignment"
            )
        ]


class ReviewDecision(Record):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name="decisions")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()
    decision = models.CharField(max_length=30)
    reason = models.TextField()
    snapshot = models.JSONField(default=dict)


class Portfolio(Record):
    artifact = models.OneToOneField(Artifact, on_delete=models.CASCADE, related_name="portfolio")
    budget_cents = models.BigIntegerField(validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="USD")
    constraints = models.JSONField(default=dict)
    unallocated_cents = models.BigIntegerField(default=0)


class Allocation(Record):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="allocations")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    amount_cents = models.BigIntegerField(validators=[MinValueValidator(0)])
    cap_cents = models.BigIntegerField(validators=[MinValueValidator(0)])
    weight = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    explanation = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "organization"], name="one_portfolio_organization"
            ),
            models.CheckConstraint(
                condition=Q(amount_cents__gte=0) & Q(amount_cents__lte=models.F("cap_cents")),
                name="allocation_in_cap",
            ),
        ]


class GraphEdge(Record):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=30)
    source_id = models.CharField(max_length=80)
    target_type = models.CharField(max_length=30)
    target_id = models.CharField(max_length=80)
    relation = models.CharField(max_length=80)
    supporting_source = models.ForeignKey(Source, on_delete=models.PROTECT)


class Alert(Record):
    target_program = models.ForeignKey(Program, null=True, blank=True, on_delete=models.SET_NULL)
    target_source = models.ForeignKey(Source, null=True, blank=True, on_delete=models.PROTECT)
    target_source_revision = models.PositiveIntegerField(null=True, blank=True)
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE)
    title = models.CharField(max_length=240)
    explanation = models.TextField()
    fingerprint = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=20, default="unread")
    feedback = models.CharField(max_length=30, blank=True)
    adoption_note = models.TextField(blank=True)


class Subscription(Record):
    owner = models.OneToOneField(Workspace, on_delete=models.CASCADE)
    evidence = models.BooleanField(default=True)
    financial = models.BooleanField(default=True)
    stale = models.BooleanField(default=True)


class ImportBatch(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    source = models.OneToOneField(Source, on_delete=models.PROTECT)
    program = models.ForeignKey(Program, null=True, on_delete=models.PROTECT)
    filename = models.CharField(max_length=200)
    checksum = models.CharField(max_length=64)
    format = models.CharField(max_length=20)
    status = models.CharField(max_length=30, default="queued")
    mapping = models.JSONField(default=dict)
    columns = models.JSONField(default=list)
    preview = models.JSONField(default=list)
    diagnostics = models.JSONField(default=list)
    raw = models.BinaryField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "checksum"], name="idempotent_upload")
        ]


class Job(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    kind = models.CharField(max_length=40)
    idempotency_key = models.CharField(max_length=160, unique=True)
    payload = models.JSONField(default=dict)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, null=True)
    source_revision = models.PositiveIntegerField(null=True)
    state = models.CharField(max_length=30, default="queued")
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    lease_token = models.UUIDField(null=True)
    lease_expires_at = models.DateTimeField(null=True)
    available_at = models.DateTimeField()
    error_code = models.CharField(max_length=80, blank=True)


class JobAttempt(Record):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="executions")
    token = models.UUIDField()
    status = models.CharField(max_length=30)
    error_code = models.CharField(max_length=80, blank=True)


class Withdrawal(Record):
    source = models.OneToOneField(Source, on_delete=models.PROTECT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, default="queued")
    completed_at = models.DateTimeField(null=True)


class AuditEvent(Record):
    owner = models.ForeignKey(Workspace, null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    metadata = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit events are append-only through the application.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit events are retained.")


class Opportunity(Record):
    title = models.CharField(max_length=240)
    cause = models.CharField(max_length=80)
    geography = models.CharField(max_length=80)
    eligibility = models.TextField()
    deadline = models.DateField()
    amount_cents = models.BigIntegerField(null=True)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)


class ServiceRequest(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    kind = models.CharField(max_length=30)
    target = models.ForeignKey(
        Workspace, null=True, on_delete=models.SET_NULL, related_name="received_requests"
    )
    note = models.TextField()
    state = models.CharField(max_length=30, default="requested")


class PilotEvent(Record):
    owner = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    metric = models.CharField(max_length=80)
    value = models.DecimalField(max_digits=20, decimal_places=4)
    denominator = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    period_start = models.DateField()
    period_end = models.DateField()
    collection_method = models.TextField()
    source_kind = models.CharField(max_length=24, default="ngo_contributed")
