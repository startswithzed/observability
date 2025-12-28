from typing import List
from uuid import UUID

import structlog
from django.core.cache import cache
from django.db import connections
from ninja import NinjaAPI, Router
from opentelemetry import metrics, trace
from opentelemetry.trace import StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.tracker.models import Product
from src.tracker.schema import ProductIn, ProductOut
from src.tracker.tasks import update_product_price

api = NinjaAPI(title="PriceWatch API")
logger = structlog.get_logger()
meter = metrics.get_meter("pricewatch-api")
propagator = TraceContextTextMapPropagator()

product_created_counter = meter.create_counter(
    name="products_created_total",
    description="Total number of products created through the API",
    unit="1",
)

cache_hits_counter = meter.create_counter(
    name="product_cache_hits_total",
    description="Number of times product data was found in Redis",
    unit="1",
)

cache_misses_counter = meter.create_counter(
    name="product_cache_misses_total",
    description="Number of times product data had to be fetched from DB",
    unit="1",
)

v1_router = Router()


@api.get("/healthz/live")
def liveness(request):
    """Is the process alive?"""
    logger.info("liveness_check_triggered")
    return {"status": "ok"}


@api.get("/healthz/ready")
def readiness(request):
    """Are dependencies (DB, Redis) reachable?"""
    logger.info("readiness_check_triggered")

    try:
        db_conn = connections["default"]
        db_conn.cursor()
    except Exception as e:
        logger.error(
            "readiness_check_failed_db",
            error=str(e),
        )
        return api.create_response(
            request,
            {
                "status": "unready",
                "reason": "db",
            },
            status=503,
        )

    try:
        cache.get("healthcheck")
    except Exception as e:
        logger.error(
            "readiness_check_failed_redis",
            error=str(e),
        )
        return api.create_response(
            request,
            {
                "status": "unready",
                "reason": "redis",
            },
            status=503,
        )

    return {"status": "ready"}


@api.get("/health")
def health_alias(request):
    return liveness(request)


@api.exception_handler(Exception)
def on_exception(request, exc):
    span = trace.get_current_span()

    # Mark the Trace as "Error" so it turns red in the UI
    span.set_status(StatusCode.ERROR, description=str(exc))
    span.record_exception(exc)

    logger.error(
        "unhandled_api_exception",
        path=request.path,
        error=str(exc),
        exc_info=True,
    )

    return api.create_response(
        request,
        {
            "error": "Internal Server Error",
            "trace_id": format(span.get_span_context().trace_id, "032x"),
        },
        status=500,
    )


@v1_router.post("/products", response=ProductOut)
def create_product(request, data: ProductIn):
    product = Product.objects.create(**data.dict())
    product_created_counter.add(1, {"tenant_id": "default-org"})

    # --- TRIGGER WORKER WITH TRACE CONTEXT ---
    # 1. Create a 'carrier' dictionary
    carrier = {}
    # 2. Inject current trace context into the carrier
    propagator.inject(carrier=carrier)

    # 3. Send to Dramatiq
    update_product_price.send(str(product.id), carrier)

    logger.info(
        "product_created",
        product_id=str(product.id),
        product_url=product.url,
    )
    return product


@v1_router.get("/products", response=List[ProductOut])
def list_products(request):
    return Product.objects.all()


@v1_router.get("/products/{product_id}", response=ProductOut)
def get_product(
    request,
    product_id: UUID,
):
    cache_key = f"product:{product_id}"
    cached_product = cache.get(cache_key)

    if cached_product:
        cache_hits_counter.add(1, {"service": "pricewatch-api"})
        logger.info("product_cache_hit", product_id=product_id)
        return cached_product

    try:
        product = Product.objects.get(id=product_id)
        cache_misses_counter.add(1, {"service": "pricewatch-api"})
        cache.set(cache_key, product, timeout=300)

        logger.info("product_cache_miss", product_id=product_id)
        return product
    except Product.DoesNotExist:  # type: ignore[unresolved-attribute]
        return api.create_response(
            request,
            {"error": "Not Found"},
            status=404,
        )
