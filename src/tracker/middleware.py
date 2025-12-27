from django.utils.deprecation import MiddlewareMixin
from opentelemetry import trace


class TraceHeaderMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if span_context.is_valid:
            response["X-Trace-Id"] = format(span_context.trace_id, "032x")
        return response
