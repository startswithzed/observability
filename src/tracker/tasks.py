import random
import time

import dramatiq
import structlog
from opentelemetry import metrics, trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.tracker.models import Product

logger = structlog.get_logger()
tracer = trace.get_tracer("pricewatch.worker")
propagator = TraceContextTextMapPropagator()
meter = metrics.get_meter("pricewatch.worker")

product_price_update_counter = meter.create_counter(
    name="price_update_tasks_processed_total",
    description="Total number of price update tasks processed",
    unit="1",
)

# 2. Scrape latency (Histogram)
product_price_scrape_duration_histogram = meter.create_histogram(
    name="price_update_scrape_duration_seconds",
    description="Time taken to scrape price data",
    unit="s",
)

# 3. Failed tasks
product_price_update_failed_counter = meter.create_counter(
    name="price_update_tasks_failed_total",
    description="Total number of failed price update tasks",
    unit="1",
)


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

    start_time = time.time()

    # 4. Start a new span in the worker
    with tracer.start_as_current_span(
        "worker.update_product_price",
        context=parent_ctx,
        links=[link],
    ) as span:
        # bind the domain-specific data for all logs
        # trace_id is handled automatically by the telemetry processor
        structlog.contextvars.bind_contextvars(product_id=product_id)

        try:
            scrape_time = random.uniform(0.5, 2.5)
            time.sleep(scrape_time)

            new_price = random.uniform(40.99, 89.99)

            product_price_scrape_duration_histogram.record(
                time.time() - start_time,
                {"status": "success"},
            )
            product_price_update_counter.add(1, {"status": "success"})

            Product.objects.filter(id=product_id).update(target_price=new_price)

            logger.info(
                "product_price_updated",
                product_id=product_id,
                new_price=new_price,
            )
        except Exception as e:
            product_price_update_failed_counter.add(1, {"error_type": type(e).__name__})
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR)
            logger.error(
                "product_price_update_failed",
                product_id=product_id,
                error=str(e),
            )
            # Not re-raising since there are no retries at the moment
