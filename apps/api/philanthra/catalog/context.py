"""Small, verified public-context snapshot; no network required at runtime."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from philanthra.core.models import Geography, Source


def ensure_public_context():
    path = (
        Path(__file__).resolve().parents[4]
        / "data/fixtures/public-context/baltimore-quickfacts.json"
    )
    payload = path.read_bytes()
    data = json.loads(payload)
    source, _ = Source.objects.get_or_create(
        id=uuid5(NAMESPACE_URL, data["source_url"] + "2020-2024"),
        defaults={
            "title": data["title"],
            "kind": "public_source",
            "source_url": data["source_url"],
            "retrieved_at": datetime.fromisoformat(data["retrieved_at"].replace("Z", "+00:00")),
            "period_start": data["period_start"],
            "period_end": data["period_end"],
            "parser_version": "manual-verified-quickfacts-v1",
            "checksum": hashlib.sha256(payload).hexdigest(),
            "locator": "QuickFacts / Income & Poverty; Computer and Internet Use",
            "geography": data["geography_code"],
            "transformations": [
                "Small manual factual extract; no ZIP substitution or inferred uncertainty"
            ],
        },
    )
    Geography.objects.get_or_create(
        code=data["geography_code"],
        defaults={
            "name": data["geography_name"],
            "kind": data["geography_type"],
            "source": source,
            "context": data,
        },
    )
