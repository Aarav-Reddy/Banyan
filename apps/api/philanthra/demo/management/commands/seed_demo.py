from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from philanthra.demo.seed import seed_demo


class Command(BaseCommand):
    help = "Idempotently seed the explicitly named Philanthra demo database."

    def handle(self, *args, **options):
        name = settings.DATABASES["default"]["NAME"]
        if not settings.DEMO_MODE or name != "philanthra_demo":
            raise CommandError("Seeding requires PHILANTHRA_ENV=demo and database philanthra_demo.")
        result = seed_demo()
        self.stdout.write(self.style.SUCCESS(result))
