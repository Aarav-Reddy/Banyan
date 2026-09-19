import time

from django.core.management.base import BaseCommand

from philanthra.jobs.worker import run_once


class Command(BaseCommand):
    help = "Process leased Philanthra jobs; --once claims at most one item."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--drain", action="store_true")

    def handle(self, *args, **options):
        while True:
            processed = run_once()
            if options["once"] or (options["drain"] and not processed):
                break
            if not processed:
                time.sleep(1)
