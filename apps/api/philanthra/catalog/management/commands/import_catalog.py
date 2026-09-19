import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from philanthra.catalog.manual import import_manual
from philanthra.ingestion.common import MAX_BYTES


class Command(BaseCommand):
    help = "Import a manually reviewed public registry/grant CSV using exact versioned templates."

    def add_arguments(self, parser):
        parser.add_argument("--kind", choices=["organization", "opportunity"], required=True)
        parser.add_argument("--file", type=Path, required=True)
        parser.add_argument("--manifest", type=Path, required=True)
        parser.add_argument("--actor", required=True)

    def handle(self, *args, **options):
        actor = (
            get_user_model()
            .objects.filter(username=options["actor"], is_active=True, is_staff=True)
            .first()
        )
        if actor is None:
            raise CommandError("An active authorized platform operator is required.")
        with options["file"].open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
        result = import_manual(
            payload, options["kind"], json.loads(options["manifest"].read_text()), actor
        )
        self.stdout.write(json.dumps(result))
