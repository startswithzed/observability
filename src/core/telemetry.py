import logging
import os
import uuid

import structlog
from opentelemetry import metrics, trace
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry_instrumentor_dramatiq import DramatiqInstrumentor

_IS_INITIALIZED = False


class OTLPLogHandler(LoggingHandler):
    def __init__(self, level=logging.NOTSET):
        provider = get_logger_provider()
        super().__init__(level=level, logger_provider=provider)


def add_otel_context(_, __, event_dict):
    span = trace.get_current_span()

    if span.get_span_context().is_valid:
        event_dict["trace_id"] = format(span.get_span_context().trace_id, "032x")
        event_dict["span_id"] = format(span.get_span_context().span_id, "016x")

    return event_dict


def filter_request_logs(_, __, event_dict):
    if event_dict.get("event") in ["request_started", "request_finished"]:
        raise structlog.DropEvent
    return event_dict


def recursive_stringify(value):
    """
    Recursively converts complex objects (UUID, Decimal, etc.) to strings.
    Passes through basic JSON types safely.
    """
    # 1. Pass-through safe OTLP types
    if isinstance(value, (str, int, float, bool, type(None))):
        return value

    # 2. Handle Lists/Tuples
    if isinstance(value, (list, tuple)):
        return [recursive_stringify(v) for v in value]

    # 3. Handle Dictionaries
    if isinstance(value, dict):
        return {k: recursive_stringify(v) for k, v in value.items()}

    # 4. Catch-all: Convert everything else (UUID, Decimal, Datetime) to String
    try:
        return str(value)
    except Exception:
        return repr(value)


def sanitize_for_serialization(_, __, event_dict):
    """
    Structlog processor to ensure all values in the event dict
    are safe for the OTLP Exporter.
    """
    # We create a new dict to avoid side-effects
    return {k: recursive_stringify(v) for k, v in event_dict.items()}


def init_telemetry(service_name: str):
    global _IS_INITIALIZED
    if _IS_INITIALIZED:
        # We only want to initialize once per process
        return

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_INSTANCE_ID: str(uuid.uuid4()),
            DEPLOYMENT_ENVIRONMENT: os.getenv("APP_ENV", "development"),
            # TODO: We should set this up to read from uv version
            # and for every update bump the uv version and use it to create tags
            "service.version": "1.0.0",
        }
    )

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    # Tracing Setup
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=True,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics Setup
    metrics_exporter = OTLPMetricExporter(
        endpoint=endpoint,
        insecure=True,
    )
    metric_reader = PeriodicExportingMetricReader(metrics_exporter)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)

    # Logging Setup
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    log_exporter = OTLPLogExporter(
        endpoint=endpoint,
        insecure=True,
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # OTEL instrumentations
    DjangoInstrumentor().instrument()
    PsycopgInstrumentor().instrument(enable_commenter=True)
    RedisInstrumentor().instrument()
    PikaInstrumentor().instrument()
    DramatiqInstrumentor().instrument()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            add_otel_context,
            filter_request_logs,
            sanitize_for_serialization,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    _IS_INITIALIZED = True
