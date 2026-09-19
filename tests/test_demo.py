import pytest
from django.contrib.auth import get_user_model
from philanthra.analytics.pooling import pool_observations
from philanthra.core import models as m
from philanthra.core.services import observation_input
from philanthra.demo.seed import seed_demo


@pytest.mark.django_db
def test_seed_idempotency_preserves_user_records_and_real_calculated_pattern():
    seed_demo()
    assert m.Organization.objects.count() == 24
    assert m.Observation.objects.count() == 60
    assert m.Artifact.objects.filter(kind="card").count() == 24
    assert m.Portfolio.objects.count() == 3
    user_record = m.Organization.objects.create(name="User-created example retained")
    models = [
        get_user_model(),
        m.Organization,
        m.Source,
        m.Observation,
        m.CostObservation,
        m.Artifact,
        m.Membership,
        m.Job,
        m.AuditEvent,
    ]
    before = {model.__name__: model.objects.count() for model in models}
    seed_demo()
    assert {model.__name__: model.objects.count() for model in models} == before
    assert m.Organization.objects.filter(pk=user_record.id).exists()
    compatible = m.Observation.objects.filter(
        outcome__code="food_security_improved", period_start="2025-01-01"
    )
    pooled = pool_observations([observation_input(o) for o in compatible])
    assert pooled["status"] == "draft" and pooled["weighted_rate"] == "0.650000"
    suppressed = m.Observation.objects.filter(period_start="2024-01-01")
    result = pool_observations([observation_input(o) for o in suppressed])
    assert result["status"] == "suppressed" and "denominator" not in result
    incompatible = m.Observation.objects.filter(outcome__code="meals_distributed")
    assert incompatible.exists()
    assert (
        pool_observations([observation_input(o) for o in incompatible])["status"] == "incompatible"
    )
