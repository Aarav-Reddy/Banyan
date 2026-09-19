"""Non-destructive correction of untouched early build fixture periods only."""

from datetime import date

from django.db import transaction

from philanthra.core import models as m
from philanthra.core.services import audit, source_revision_changed


@transaction.atomic
def upgrade_early_fixture_periods():
    from .seed import sid

    marker = "baltimore-fixture-periods-v2"
    if m.AuditEvent.objects.filter(action="demo.upgrade", object_id=marker).exists():
        return
    changed = 0
    # Imported/user records cannot match these stable seed IDs. Edited/withdrawn source
    # revisions are never rewritten. New seed data already has the corrected windows.
    for i in range(4):
        source = (
            m.Source.objects.select_for_update()
            .filter(
                pk=sid(f"source/outcomes/{i}"), kind="synthetic_demo", state="active", revision=1
            )
            .first()
        )
        if not source:
            continue
        for j, year in [(12, 2024), (14, 2023)]:
            changed += m.Observation.objects.filter(
                pk=sid(f"observation/{i}/{j}"), source=source, period_start=date(2025, 1, 1)
            ).update(period_start=date(year, 1, 1), period_end=date(year, 3, 31))
        if source.period_start and source.period_start.year == 2025:
            source.period_start = date(2023, 1, 1)
            source.revision += 1
            source.save()
            source_revision_changed(source)
    if changed:
        audit(None, None, "demo.upgrade", marker, corrected_fixture_rows=changed, synthetic=True)
