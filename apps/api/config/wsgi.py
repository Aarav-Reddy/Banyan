import os

from django.core.wsgi import get_wsgi_application

from config.deployment import validate_production_database

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

validate_production_database()
