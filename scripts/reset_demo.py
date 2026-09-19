import os
import sys
from pathlib import Path

import django
from django.conf import settings
from django.core.management import call_command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

if (
    sys.argv[1:] != ["philanthra-demo"]
    or not settings.DEMO_MODE
    or settings.DATABASES["default"]["NAME"] != "philanthra_demo"
):
    raise SystemExit(
        "Refusing reset: requires CONFIRM=philanthra-demo, PHILANTHRA_ENV=demo, and database philanthra_demo."
    )
if settings.DATABASES["default"]["HOST"] not in {"127.0.0.1", "localhost", "db"}:
    raise SystemExit("Refusing reset of a non-local database.")
call_command("flush", interactive=False)
call_command("seed_demo")
