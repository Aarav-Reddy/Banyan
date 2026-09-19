"""Explicit opt-in source normalization/persistence, never part of default startup."""

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from philanthra.catalog.services import persist_public
from philanthra.ingestion import parse_archive, parse_source
from philanthra.ingestion.common import MAX_BYTES, ImportProblem
from philanthra.ingestion.network import SOURCES, fetch_source
from philanthra.ingestion.sources import ADAPTERS


class Command(BaseCommand):
    help = "Normalize an inspected official/local file, then persist with explicit revision activation."

    def add_arguments(self, parser):
        parser.add_argument("--adapter", choices=ADAPTERS, required=True)
        locations = parser.add_mutually_exclusive_group(required=True)
        locations.add_argument("--file", type=Path)
        locations.add_argument("--source", choices=SOURCES)
        parser.add_argument("--allow-network", action="store_true")
        parser.add_argument("--manifest", type=Path, required=True)
        parser.add_argument("--actor", required=True)
        parser.add_argument("--activate", action="store_true")
        parser.add_argument("--archive", action="store_true")

    def handle(self, *args, **options):
        actor = (
            get_user_model()
            .objects.filter(username=options["actor"], is_active=True, is_staff=True)
            .first()
        )
        if actor is None:
            raise CommandError("An active platform-operator account is required.")
        metadata = json.loads(options["manifest"].read_text())
        try:
            if options["file"]:
                with options["file"].open("rb") as stream:
                    payload = stream.read(MAX_BYTES + 1)
            else:
                payload = fetch_source(options["source"], enabled=options["allow_network"])
                metadata.update(source_url=SOURCES[options["source"]], source_kind="public_source")
            results = (
                parse_archive(payload, options["adapter"], metadata)
                if options["archive"]
                else [parse_source(payload, options["adapter"], metadata)]
            )
            if any(r["status"] != "validated" for r in results):
                codes = sorted({d["code"] for r in results for d in r["diagnostics"]})
                raise CommandError("Source rejected: " + ", ".join(codes))
            counts = persist_public(
                [record for result in results for record in result["records"]],
                actor,
                activate=options["activate"],
            )
        except ImportProblem as exc:
            raise CommandError(f"Source unavailable: {exc.code}") from exc
        self.stdout.write(json.dumps(counts, sort_keys=True))
