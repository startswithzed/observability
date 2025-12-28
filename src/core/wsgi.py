import os
import sys

from django.core.wsgi import get_wsgi_application

from src.core.telemetry import init_telemetry

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.core.settings")

init_telemetry("pricewatch-api")

application = get_wsgi_application()
