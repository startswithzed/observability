import random

import dramatiq
import structlog
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.tracker.models import Product

logger = structlog.get_logger()
tracer = trace.get_tracer("pricewatch.worker")
propagator = TraceContextTextMapPropagator()


@dramatiq.actor(max_retries=0)
def update_product_price(
    product_id: str,
    trace_carrier: dict,
):
    """
    Background task to 'scrape' a price and update the database.

    :param product_id: The UUID of the product.
    :param trace_carrier: A dictionary containing the trace context from the API.
    """
    # 1. Extract context sent from API
    parent_ctx = propagator.extract(carrier=trace_carrier)

    # 2. Get Span Context for Linking
    parent_span_context = trace.get_current_span(parent_ctx).get_span_context()

    # 3. Create a Link
    link = trace.Link(parent_span_context)

    # 4. Start a new span in the worker
    with tracer.start_as_current_span(
        "worker.update_product_price",
        context=parent_ctx,
        links=[link],
    ):
        # bind the domain-specific data for all logs
        # trace_id is handled automatically by the telemetry processor
        structlog.contextvars.bind_contextvars(product_id=product_id)

        new_price = random.uniform(40.99, 89.99)
        Product.objects.filter(id=product_id).update(target_price=new_price)

        logger.info(
            "product_price_updated",
            product_id=product_id,
            new_price=new_price,
        )
