import structlog
from django.utils.deprecation import MiddlewareMixin
from opentelemetry import trace

logger = structlog.get_logger()


class ObservabilityMiddleware(MiddlewareMixin):
    """
    Middleware to glue OpenTelemetry tracing to Structlog logging
    and provide trace IDs in HTTP responses.
    """

    def process_request(self, request):
        structlog.contextvars.clear_contextvars()
        span = trace.get_current_span()
        span_context = span.get_span_context()

        if span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            structlog.contextvars.bind_contextvars(
                trace_id=trace_id,
                path=request.path,
                method=request.method,
                user_agent=request.META.get(
                    "HTTP_USER_AGENT",
                    "unknown",
                ),
            )

    def process_response(self, request, response):
        span = trace.get_current_span()
        span_context = span.get_span_context()

        if span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            response["X-Trace-Id"] = trace_id

        return response
