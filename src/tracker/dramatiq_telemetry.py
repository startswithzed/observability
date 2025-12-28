import os

import dramatiq
import structlog

from src.core.telemetry import init_telemetry


class DramatiqWorkerTelemetry(dramatiq.Middleware):
    """
    Handles the boot-time telemetry for background processes.
    """

    def after_worker_boot(self, broker, worker):
        # This executes in the forked worker process.
        # It ensures a fresh gRPC connection for the worker.
        service_name = os.getenv("SERVICE_NAME", "pricewatch-worker")
        init_telemetry(service_name)

        logger = structlog.get_logger()
        logger.info("worker_telemetry_online")
