import structlog
from django.dispatch import receiver
from django_structlog.signals import bind_extra_request_metadata
from opentelemetry import baggage, trace


@receiver(bind_extra_request_metadata)
def add_otel_trace_id(request, logger, **kwargs):
    """
    Bind OTel Trace ID to structlog context.
    Uses native structlog.contextvars which is now the standard for django-structlog.
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if span_context.is_valid:
        trace_id = format(span_context.trace_id, "032x")

        baggage.set_baggage("tenant_id", "default-org")

        # structlog.contextvars.bind_contextvars(trace_id=trace_id)
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            tenant_id="default-org",
        )
