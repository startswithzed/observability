import os
import uuid

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
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
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    _IS_INITIALIZED = True
