"""Local normalization or explicitly opted-in official-source download."""

import argparse
import json
import sys
from pathlib import Path

from .common import MAX_BYTES, ImportProblem
from .network import SOURCES, fetch_source
from .sources import ADAPTERS, parse_archive, parse_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=ADAPTERS, required=True)
    locations = parser.add_mutually_exclusive_group(required=True)
    locations.add_argument("--local", type=Path)
    locations.add_argument("--source", choices=SOURCES)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--metadata", type=Path, help="Trusted local source manifest JSON")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text()) if args.metadata else {}
    try:
        if args.local:
            with args.local.open("rb") as stream:
                payload = stream.read(MAX_BYTES + 1)
        else:
            payload = fetch_source(args.source, enabled=args.allow_network)
            metadata.update(source_url=SOURCES[args.source], source_kind="public_source")
        result = (parse_archive if args.archive else parse_source)(payload, args.adapter, metadata)
        print(json.dumps(result, indent=2))
        return 1 if isinstance(result, dict) and result["status"] == "invalid" else 0
    except ImportProblem as exc:
        print(json.dumps({"status": "unavailable", "code": exc.code, "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
