import os
import sys

from django.core.wsgi import get_wsgi_application

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.telemetry import init_telemetry

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.core.settings")

# Initialize Observability before any other imports
init_telemetry(os.getenv("SERVICE_NAME", "pricewatch-api"))

application = get_wsgi_application()
