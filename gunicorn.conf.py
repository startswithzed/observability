import os
import sys

from src.core.telemetry import init_telemetry

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.core.settings")


def post_fork(server, worker):
    """
    This hook runs in every worker process immediately after it is created.
    We initialize telemetry here to ensure each worker has its own
    gRPC connection to the OTel collector.
    """
    server.log.info(f"Worker spawned (pid: {worker.pid}). Initializing telemetry...")
    init_telemetry(os.getenv("SERVICE_NAME", "pricewatch-api"))
