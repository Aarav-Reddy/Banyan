import time

from django.core.management.base import BaseCommand

from philanthra.jobs.worker import run_once


def enqueue_periodic_monitoring():
    from django.utils import timezone

    from philanthra.core.models import Workspace
    from philanthra.core.services import enqueue
    from philanthra.pilot.models import WatchItem

    bucket = timezone.now().strftime("%Y%m%d%H")
    for workspace in Workspace.objects.filter(
        id__in=WatchItem.objects.values("owner_id")
    ).distinct():
        enqueue(workspace, "pilot_monitor", f"monitor:hourly:{workspace.id}:{bucket}", {})


class Command(BaseCommand):
    help = "Process leased Philanthra jobs; --once claims at most one item."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--drain", action="store_true")

    def handle(self, *args, **options):
        from config.deployment import validate_production_database

        validate_production_database()
        next_monitor_check = 0.0
        while True:
            if time.monotonic() >= next_monitor_check:
                enqueue_periodic_monitoring()
                next_monitor_check = time.monotonic() + 60
            processed = run_once()
            if options["once"] or (options["drain"] and not processed):
                break
            if not processed:
                time.sleep(1)
