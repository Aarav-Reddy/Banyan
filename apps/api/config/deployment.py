"""Production process startup refuses an unmigrated or copied seeded demo database."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection


def validate_production_database():
    if settings.ENVIRONMENT != "production":
        return
    from django.contrib.auth import get_user_model
    from django.db.migrations.executor import MigrationExecutor
    from philanthra.core.models import AuditEvent

    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise ImproperlyConfigured("Apply migrations before starting production processes.")
    if (
        AuditEvent.objects.filter(action="demo.seed").exists()
        or get_user_model()
        .objects.filter(
            username__in=[
                "foundation-admin",
                "foundation-analyst",
                "foundation-viewer",
                "second-foundation",
                "ngo-owner",
                "ngo-editor",
                "ngo-viewer",
                "reviewer",
                "platform-admin",
                "ngo2-owner",
                "ngo3-owner",
                "ngo4-owner",
            ],
            email__endswith="@demo.invalid",
        )
        .exists()
    ):
        raise ImproperlyConfigured(
            "Production refuses seeded demo credentials/data; provision a clean database."
        )
